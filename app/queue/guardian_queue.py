"""
Guardian Queue (Phase 5.2, 5.3, 11.F #7): "every waiting patient is
continuously re-evaluated against new data, trends, elapsed time and
overdue reassessment."

This module owns the lexicographic ordering that makes "waiting does not
make you sicker, waiting makes us look again" (Phase 5.2) an enforced
property rather than a slogan: `final_acuity` dominates every other sort
key, so a lower-acuity (less urgent) case can NEVER outrank a higher-acuity
one no matter how long it has waited -- see test_guardian_queue.py's
`test_lexicographic_ordering_cannot_be_overcome_by_waiting` for the direct
proof.

No scheduler/cron exists in this prototype (Phase 15 deliberately avoids
extra infrastructure for a hackathon build). Both of this module's write
side effects -- flagging a newly-overdue reassessment, and backfilling a
first RiskAssessment for a case that somehow has none yet -- are therefore
performed opportunistically whenever the queue is read, which is
functionally equivalent to a scheduled sweep for as long as at least one
nurse/control-tower view is open, and is documented here rather than
silently smuggled in as a side effect of a GET request.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from app.config.hospital_profile import HospitalProfile
from app.models.case import Case
from app.models.enums import CaseStatus, DeteriorationTrend, NurseAttentionFlag
from app.ops.wait_time import CaseSnapshot, count_available_capacity, build_case_snapshots, estimate_wait_time
from app.queue import time_engine
from app.queue.models import QueueEntry
from app.scoring.presentation import one_line_presentation as _one_line_presentation
from app.scoring.risk_orchestrator import assess_case
from app.store.event_store import EventStore
from app.timeutil import to_naive_utc, utcnow

# Phase 5.2's "descending" direction for deterioration_trend_direction,
# expressed as an ordinal so it composes into a single sortable tuple
# alongside the other (mixed ascending/descending) keys.
_TREND_ORDINAL = {
    DeteriorationTrend.WORSENING: 2,
    DeteriorationTrend.STABLE: 1,
    DeteriorationTrend.UNKNOWN: 1,
    DeteriorationTrend.IMPROVING: 0,
}


def _primary_attention_flag(
    store: EventStore,
    case_id: str,
    deterioration_trend: DeteriorationTrend,
    reassessment_is_due: bool,
    rule_component_breakdown,
) -> NurseAttentionFlag:
    """Phase 8.2: 'the flag that most needs attention (deteriorating,
    overdue, unknown vitals, conflict).' Exactly one flag, in that listed
    priority order -- a case can genuinely match more than one condition
    at once (e.g. deteriorating AND overdue), and the nurse only has room
    to act on the single most urgent one."""
    if deterioration_trend == DeteriorationTrend.WORSENING:
        return NurseAttentionFlag.DETERIORATING
    if reassessment_is_due:
        return NurseAttentionFlag.REASSESSMENT_OVERDUE
    if any(component.get("is_missing") for component in rule_component_breakdown):
        return NurseAttentionFlag.UNKNOWN_VITALS
    if store.list_data_conflicts(case_id):  # open (unresolved) by default
        return NurseAttentionFlag.DATA_CONFLICT
    return NurseAttentionFlag.NONE


def _build_entry(
    case: Case,
    store: EventStore,
    profile: HospitalProfile,
    as_of: datetime,
    snapshots: List[CaseSnapshot],
    available_capacity: int,
) -> QueueEntry:
    history = store.get_risk_assessment_history(case.case_id)
    if not history:
        # Self-healing backfill: every ACTIVE case should already have an
        # initial assessment (wired into case creation / arrival in
        # app/api/cases.py), but if one is somehow missing, compute it now
        # rather than silently omitting the case from its own queue.
        #
        # save_risk_assessment() treats any assessment as "a reassessment
        # happened" and clears reassessment_overdue (correct for the
        # normal case: new data really was just collected). But a case
        # with zero history could -- in principle, e.g. a future intake
        # path that doesn't go through app/api/cases.py's wiring -- still
        # have been flagged overdue by something else (CP8: a patient's
        # "I feel worse" tap) before ever getting its first real
        # assessment. That flag reflects a genuine external signal the
        # backfill knows nothing about, so it must survive the backfill
        # rather than being silently consumed by it.
        was_overdue = case.reassessment_overdue
        assess_case(case, store, profile, as_of=as_of)
        if was_overdue:
            store.flag_reassessment_overdue(case.case_id, occurred_at=as_of, reason="PRE_EXISTING_FLAG_SURVIVED_BACKFILL")
        history = store.get_risk_assessment_history(case.case_id)

    latest = history[-1]
    reassessment = time_engine.reassessment_status(latest.final_acuity, case.last_reassessed_at, profile, as_of=as_of)
    if reassessment.is_due and not case.reassessment_overdue:
        # Newly discovered via the elapsed-time clock -- flag it now.
        store.flag_reassessment_overdue(case.case_id, occurred_at=as_of)
    elif case.reassessment_overdue and not reassessment.is_due:
        # Flagged some other way (CP8: a patient's "I feel worse" tap
        # forces this immediately, regardless of elapsed time) --
        # `case.reassessment_overdue` is the authoritative, event-logged
        # state; the pure elapsed-time calculation above doesn't know
        # about that trigger, so it's corrected here for display rather
        # than silently shown as "not due" while the DB says otherwise.
        reassessment = reassessment.model_copy(update={"is_due": True})

    arrival_time = case.arrived_at or case.created_at
    waiting_minutes = (as_of - arrival_time).total_seconds() / 60.0

    wait_time_estimate = estimate_wait_time(
        store,
        profile,
        case.case_id,
        latest.final_acuity,
        snapshots=snapshots,
        available_capacity=available_capacity,
    )

    trend = time_engine.deterioration_trend(history)
    attention_flag = _primary_attention_flag(
        store, case.case_id, trend, reassessment.is_due, latest.rule_component_breakdown
    )

    return QueueEntry(
        case_id=case.case_id,
        display_name=case.display_name,
        mrn=case.mrn,
        final_acuity=latest.final_acuity,
        confidence_band=latest.confidence_band,
        should_abstain=latest.should_abstain,
        # time_critical_pathway_flag: always False -- no pathway-flagging
        # engine exists in this prototype (e.g. STEMI/stroke/sepsis
        # protocols). The sort key is wired for it now so adding that
        # engine later is a data change here, not a re-architecture.
        time_critical_pathway_flag=False,
        deterioration_trend=trend,
        time_in_current_band_minutes=time_engine.time_in_current_band_minutes(history, as_of=as_of),
        arrival_time=arrival_time,
        waiting_minutes=waiting_minutes,
        reassessment=reassessment,
        emergency_bypass_active=case.emergency_bypass_active,
        wait_time_estimate=wait_time_estimate,
        one_line_presentation=_one_line_presentation(store, case.case_id),
        primary_attention_flag=attention_flag,
    )


def _sort_key(entry: QueueEntry):
    # Phase 5.2, in exact stated priority order. Every "descending" key is
    # negated so the whole tuple sorts ascending in one pass.
    return (
        entry.final_acuity,
        -int(entry.time_critical_pathway_flag),
        -_TREND_ORDINAL[entry.deterioration_trend],
        -(entry.time_in_current_band_minutes or 0.0),
        entry.arrival_time,
    )


def build_queue(store: EventStore, profile: HospitalProfile, as_of: Optional[datetime] = None) -> List[QueueEntry]:
    """Builds the queue for exactly the cases configured under `profile`
    (matched by `hospital_profile_id`) -- never scores one hospital's
    cases against another's reassessment intervals/thresholds."""
    now = to_naive_utc(as_of) if as_of is not None else utcnow()
    active_cases = [
        c for c in store.list_cases(status=CaseStatus.ACTIVE) if c.hospital_profile_id == profile.profile_id
    ]
    # Phase 6.4 wait-time inputs shared across every entry in this build:
    # computed once so a queue of n cases costs O(n) store queries rather
    # than O(n^2). Snapshot is taken up front, so a case that gets
    # self-healing-backfilled its first RiskAssessment during this same
    # pass (see _build_entry above) won't retroactively count towards
    # *other* cases' "patients ahead" until the next queue read -- an
    # acceptable one-read staleness given that backfill is itself already
    # an exceptional fallback path, not the normal case.
    snapshots = build_case_snapshots(store, profile)
    available_capacity = count_available_capacity(store, profile)
    entries = [_build_entry(case, store, profile, now, snapshots, available_capacity) for case in active_cases]
    entries.sort(key=_sort_key)
    return entries
