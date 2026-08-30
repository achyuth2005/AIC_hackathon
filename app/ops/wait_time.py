"""
Waiting-time prediction (Phase 6.4).

"Do not use machine learning here. A simple queue model is more defensible
and easier to explain":

    estimated_wait = f(patients ahead in same or higher band,
                        rolling median service time per band,
                        count of available clinicians and spaces)

Phase 6.4 is equally explicit about presentation: "Present it as a range
that widens with uncertainty, always accompanied by the statement that a
more urgent arrival can change it. Never present a single number, and
never present it as a commitment." `WaitTimeEstimate` below is a
lower/upper range plus that caveat string, never a scalar.

[Assumption], stated once here rather than scattered through the code:
this prototype has no distinct "consultation finished" event (no
discharge/disposition workflow exists yet -- Phase 6.3's own 5th stuck-
pattern, "disposition decided, not executed", is explicitly out of scope
as of CP9). So "service time" is approximated as the elapsed time between
a patient's arrival and their first CLINICIAN/TREATMENT_SPACE resource
assignment: how long previous patients in that acuity band actually
waited before being pulled into service. That is exactly the per-band
"how fast does this queue clear" rate the Phase 6.4 formula needs -- it is
just derived from data this system actually has, rather than inventing a
synthetic consultation-length figure. [Requires clinical validation], like
every other illustrative number in this codebase.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from statistics import median
from typing import List, Optional

from pydantic import BaseModel, Field

from app.config.hospital_profile import HospitalProfile
from app.models.enums import CaseStatus, ResourceStatus, ResourceType
from app.store.event_store import EventStore

_SERVICE_RESOURCE_TYPES = (ResourceType.CLINICIAN, ResourceType.TREATMENT_SPACE)

_WAIT_TIME_CAVEAT = (
    "This is an estimate based on current queue conditions, not a commitment, "
    "and can change if a more urgent patient arrives."
)


class WaitTimeEstimate(BaseModel):
    """Phase 6.4's output shape: always a range, never a single number."""
    lower_minutes: float
    upper_minutes: float
    patients_ahead: int
    available_capacity: int
    basis: str  # "BAND_HISTORY" | "GLOBAL_HISTORY" | "CONFIGURED_DEFAULT"
    sample_size: int
    caveat: str = Field(default=_WAIT_TIME_CAVEAT)


@dataclass
class CaseSnapshot:
    """One active case's state as far as the queue-clearing model cares:
    its acuity band and whether it is already being seen (and therefore no
    longer 'ahead' of anyone else waiting). Computed once per build_queue()
    call and shared across every case's estimate, so the whole queue's
    wait-time pass costs O(n) store queries rather than O(n^2)."""
    case_id: str
    final_acuity: Optional[int]
    in_service: bool


def build_case_snapshots(store: EventStore, profile: HospitalProfile) -> List[CaseSnapshot]:
    snapshots: List[CaseSnapshot] = []
    for case in store.list_cases(status=CaseStatus.ACTIVE, hospital_profile_id=profile.profile_id):
        latest = store.get_latest_risk_assessment(case.case_id)
        in_service = bool(store.get_assigned_resources_for_case(case.case_id))
        snapshots.append(
            CaseSnapshot(
                case_id=case.case_id,
                final_acuity=latest.final_acuity if latest else None,
                in_service=in_service,
            )
        )
    return snapshots


def count_available_capacity(store: EventStore, profile: HospitalProfile) -> int:
    """Phase 6.4: 'count of available clinicians and spaces.' Both resource
    types are counted together as one combined serving capacity -- either
    becoming free lets the next waiting patient move into service in this
    single-stage model. [Assumption]."""
    total = 0
    for resource_type in _SERVICE_RESOURCE_TYPES:
        total += len(
            store.list_resources(profile.profile_id, resource_type=resource_type, status=ResourceStatus.AVAILABLE)
        )
    return total


def _band_at_time(store: EventStore, case_id: str, at: datetime) -> Optional[int]:
    """Which acuity band a case was in at the moment a resource was
    assigned to it (used to group historical service-time samples by
    band). Falls back to the earliest known assessment if the assignment
    happened before the first one was computed."""
    history = store.get_risk_assessment_history(case_id)
    if not history:
        return None
    candidates = [h for h in history if h.computed_at <= at]
    chosen = candidates[-1] if candidates else history[0]
    return chosen.final_acuity


def _service_minutes_samples(
    store: EventStore, profile: HospitalProfile, acuity_level: Optional[int], limit: int
) -> List[float]:
    """Arrival -> first-service-resource-assignment minutes, read off the
    append-only event log (see EventStore.get_resource_assignment_history's
    docstring for why the live Resource row can't answer this).
    `acuity_level=None` means "all bands", used for the global fallback."""
    samples: List[float] = []
    for event in store.get_resource_assignment_history(profile.profile_id, limit=limit):
        case = store.get_case(event.case_id)
        if case is None:
            continue
        arrival = case.arrived_at or case.created_at
        if arrival is None:
            continue
        minutes = (event.occurred_at - arrival).total_seconds() / 60.0
        if minutes < 0:
            continue  # clock skew / bad data -- don't let it poison the median
        if acuity_level is not None:
            band = _band_at_time(store, event.case_id, event.occurred_at)
            if band != acuity_level:
                continue
        samples.append(minutes)
    return samples


def estimate_wait_time(
    store: EventStore,
    profile: HospitalProfile,
    case_id: str,
    final_acuity: int,
    *,
    snapshots: Optional[List[CaseSnapshot]] = None,
    available_capacity: Optional[int] = None,
) -> WaitTimeEstimate:
    """Phase 6.4's formula, assembled from the three named inputs.

    `snapshots`/`available_capacity` are optional pre-computed inputs so a
    whole-queue caller (guardian_queue.build_queue) can compute them once
    and reuse them across every entry; a standalone caller (a single-case
    endpoint, a test) can omit them and this function computes them itself.
    """
    cfg = profile.ops

    if snapshots is None:
        snapshots = build_case_snapshots(store, profile)
    if available_capacity is None:
        available_capacity = count_available_capacity(store, profile)

    # Phase 6.4 input 1: patients ahead in the same-or-more-urgent band who
    # are not already being seen (a lower acuity NUMBER is MORE urgent).
    patients_ahead = sum(
        1
        for s in snapshots
        if s.case_id != case_id
        and s.final_acuity is not None
        and s.final_acuity <= final_acuity
        and not s.in_service
    )

    # Phase 6.4 input 2: rolling median service time for this band, with a
    # documented fallback chain when there isn't enough history yet.
    band_samples = _service_minutes_samples(store, profile, final_acuity, cfg.wait_time_lookback_samples)
    if len(band_samples) >= cfg.wait_time_min_samples_for_band_specific_median:
        service_minutes = median(band_samples)
        basis = "BAND_HISTORY"
        sample_size = len(band_samples)
        widen = cfg.wait_time_range_widen_factor_normal
    else:
        global_samples = _service_minutes_samples(store, profile, None, cfg.wait_time_lookback_samples)
        if len(global_samples) >= cfg.wait_time_min_samples_for_band_specific_median:
            service_minutes = median(global_samples)
            basis = "GLOBAL_HISTORY"
            sample_size = len(global_samples)
        else:
            service_minutes = cfg.default_service_minutes_by_acuity.get(final_acuity, 45.0)
            basis = "CONFIGURED_DEFAULT"
            sample_size = 0
        widen = cfg.wait_time_range_widen_factor_low_confidence

    # Phase 6.4 input 3: available capacity feeds the denominator -- more
    # free clinicians/spaces means the queue clears faster.
    effective_capacity = max(available_capacity, 1)
    if available_capacity == 0:
        # Nobody can be pulled into service at all right now -- the point
        # estimate below would understate the wait, so widen further
        # rather than presenting a falsely precise number.
        widen = max(widen, 1.0)

    point_estimate = (patients_ahead / effective_capacity) * service_minutes

    lower = max(0.0, point_estimate * (1 - widen))
    upper = point_estimate * (1 + widen)
    if patients_ahead == 0:
        # Even "next in line" is a range, not a promise of zero wait --
        # floor the upper bound at half a typical service time.
        upper = max(upper, service_minutes * 0.5)

    return WaitTimeEstimate(
        lower_minutes=round(lower, 1),
        upper_minutes=round(upper, 1),
        patients_ahead=patients_ahead,
        available_capacity=available_capacity,
        basis=basis,
        sample_size=sample_size,
    )
