"""
Phase 14.2 surge simulator: creates a baseline population, then a burst of
additional arrivals at `multiplier`x that volume, and demonstrates the six
named surge-time properties, in order:

  1. Queue length scales with arrival volume; acuity ordering does not
     degrade (verified: the queue is strictly non-decreasing by
     final_acuity, exactly as it must be at any volume).
  2. Reassessment-overdue counts climb across the low-acuity bands.
  3. The alert count does NOT scale with patient volume the way the raw
     arrival count does -- Phase 8.5's aggregation doing its job.
  4. A capacity conflict fires and is surfaced (never silently resolved,
     never reordered around, never used to downgrade anyone).
  5. Stuck diagnostics accumulate on the ops list, separate from the
     acuity-ordered clinical queue.
  6. One already-waiting patient deteriorates mid-surge and auto-escalates
     past newer, calmer arrivals.

This is DATA SIMULATION for the demo, distinct from both CP6's ML-training
generator (unlabelled bulk feature vectors, used only to fit/evaluate the
ML challenger) and CP11's twenty hand-curated narrative patients (one case
each, individually designed to teach one thing). This module produces
VOLUME -- many generic, tier-distributed patients, all through the real
Case/Observation/scoring pipeline -- to stress-test queue behaviour under
load exactly as a live demo would, and reports concrete, checkable
evidence for each of the six points above rather than just asserting them.

Deliberately deterministic, no RNG: a fixed, repeating acuity-tier cycle
(`_TIER_CYCLE`) stands in for a "realistic" ED case mix ([Assumption],
illustrative only) and guarantees every tier is represented regardless of
population size, so the capacity-conflict and escalation steps below are
guaranteed to actually happen on every run, not left to chance.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from app.alerts.engine import sync_alerts
from app.config.hospital_profile import HospitalProfile
from app.models.enums import BypassSource, MeasurementStatus, ReliabilityTier, ResourceType, SourceType, ValueType
from app.ops.flow_engine import check_stuck_patients
from app.queue.guardian_queue import build_queue
from app.scoring import concepts
from app.scoring.risk_orchestrator import assess_case
from app.store.event_store import CapacityConflictError, EventStore
from app.timeutil import utcnow

# Illustrative ESI-tier vitals, each independently verified (see CP11's
# checkpoint report) to land in its named tier for an ADULT case under
# this project's own default.yaml tables -- not invented independently.
_TIER_VITALS: Dict[int, Dict[str, Any]] = {
    1: dict(rr=18, spo2=83, hr=90, sbp=115, temp=37.0),   # hard trigger (SpO2 <= 85), stays queued (not a bypass -- 83 > 75)
    2: dict(rr=25, spo2=91, hr=95, sbp=115, temp=37.0),   # aggregate 7 -> ESI2
    3: dict(rr=22, spo2=94, hr=95, sbp=105, temp=37.0),   # aggregate 5 -> ESI3
    4: dict(rr=20, spo2=95, hr=88, sbp=122, temp=37.2),   # aggregate 1 -> ESI4
    5: dict(rr=16, spo2=98, hr=72, sbp=118, temp=36.8),   # aggregate 0 -> ESI5
}
# A 10-slot repeating cycle shaped like a plausible ED mix: few critical,
# more moderate/minor. [Assumption], illustrative only.
_TIER_CYCLE = [5, 4, 3, 4, 5, 2, 3, 4, 5, 1]


class SurgeSimulationResult(BaseModel):
    baseline_count: int
    surge_count: int
    total_cases: int
    queue_length_before: int
    queue_length_after: int
    acuity_ordering_holds: bool

    reassessment_overdue_count: int

    alerts_before: int
    alerts_after: int
    volume_multiplier: float
    alert_multiplier_actual: Optional[float]
    alert_growth_held_below_volume_growth: Optional[bool]

    capacity_conflict_demonstrated: bool
    capacity_conflict_detail: Optional[Dict[str, Any]]

    stuck_patient_count: int

    escalated_case_id: Optional[str]
    escalated_from_acuity: Optional[int]
    escalated_to_acuity: Optional[int]
    escalated_jumped_newer_arrivals_count: int

    narrative: List[str]


def _add_vital(store: EventStore, case_id: str, code: str, value, value_type: ValueType, observed_at=None):
    store.add_observation(
        case_id=case_id, concept_code=code, value=value, value_type=value_type,
        source_type=SourceType.DEVICE, reliability_tier=ReliabilityTier.MACHINE_MEASURED,
        measurement_status=MeasurementStatus.MEASURED, observed_at=observed_at or utcnow(),
    )


def _seed_patient(store: EventStore, profile: HospitalProfile, tier: int, age_years: int = 40):
    case = store.create_case(age_years=age_years, hospital_profile_id=profile.profile_id)
    v = _TIER_VITALS[tier]
    _add_vital(store, case.case_id, concepts.RESP_RATE, v["rr"], ValueType.NUMERIC)
    _add_vital(store, case.case_id, concepts.SPO2, v["spo2"], ValueType.NUMERIC)
    _add_vital(store, case.case_id, concepts.HEART_RATE, v["hr"], ValueType.NUMERIC)
    _add_vital(store, case.case_id, concepts.SYSTOLIC_BP, v["sbp"], ValueType.NUMERIC)
    _add_vital(store, case.case_id, concepts.TEMPERATURE, v["temp"], ValueType.NUMERIC)
    _add_vital(store, case.case_id, concepts.CONSCIOUSNESS_LEVEL, "ALERT", ValueType.CODED)
    _add_vital(store, case.case_id, concepts.SUPPLEMENTAL_OXYGEN, False, ValueType.BOOLEAN)
    assess_case(case, store, profile)
    return case


def _acuity_ordering_holds(queue) -> bool:
    return all(a.final_acuity <= b.final_acuity for a, b in zip(queue, queue[1:]))


def run_surge_simulation(
    store: EventStore, profile: HospitalProfile, *, baseline_count: int = 10, multiplier: int = 3
) -> SurgeSimulationResult:
    if baseline_count < 2:
        raise ValueError(
            "run_surge_simulation requires baseline_count >= 2 (needs at least one ESI-1 and one "
            "low-acuity case to guarantee the capacity-conflict and deterioration steps)."
        )
    narrative: List[str] = []

    # --- Step 0: baseline population, at "normal" volume. ---------------
    # An ESI-1 and an ESI-5 case are guaranteed explicitly (not left to
    # wherever the repeating cycle happens to land) so the capacity-
    # conflict and deterioration steps below never depend on baseline_count
    # being large enough to reach those slots in _TIER_CYCLE.
    guaranteed_tiers = [1, 5]
    cycled_tiers = [_TIER_CYCLE[i % len(_TIER_CYCLE)] for i in range(baseline_count - len(guaranteed_tiers))]
    baseline_tiers = guaranteed_tiers + cycled_tiers
    baseline_cases = [_seed_patient(store, profile, tier) for tier in baseline_tiers]
    narrative.append(f"Baseline: {baseline_count} patients created across the full acuity range.")

    # One genuine baseline critical-bypass patient (the cycle's ESI-1
    # case), so alerts_before is a real nonzero figure to measure surge
    # growth against rather than zero -- a department is never truly
    # alert-free at any given moment.
    baseline_critical = next(
        c for c in baseline_cases if store.get_latest_risk_assessment(c.case_id).final_acuity == 1
    )
    store.activate_emergency_bypass(
        baseline_critical.case_id, source=BypassSource.HUMAN, reason="Baseline critical patient (surge simulator setup)."
    )

    queue_before = build_queue(store, profile)
    alerts_before = len(sync_alerts(store, profile))

    # The patient who will deteriorate mid-surge: a DIFFERENT already-
    # waiting, low-acuity (tier 4/5) baseline patient (not the bypass
    # patient above), so its eventual escalation is unambiguously "a
    # waiting patient overtakes newer, calmer arrivals" -- a distinct
    # mechanism from the bypass alert, not the same patient doing both.
    deteriorating_case = next(
        c for c in baseline_cases
        if c.case_id != baseline_critical.case_id and store.get_latest_risk_assessment(c.case_id).final_acuity >= 4
    )
    acuity_before_deterioration = store.get_latest_risk_assessment(deteriorating_case.case_id).final_acuity

    # --- Step 1: trigger the surge -- (multiplier - 1)x more arrivals. ---
    surge_count = baseline_count * (multiplier - 1)
    surge_cases = [_seed_patient(store, profile, _TIER_CYCLE[i % len(_TIER_CYCLE)]) for i in range(surge_count)]
    narrative.append(
        f"Surge: {surge_count} additional patients arrive ({multiplier}x total volume: "
        f"{baseline_count} -> {baseline_count + surge_count})."
    )

    # --- Step 2: reassessment intervals start lapsing. -------------------
    # A seed script cannot wait out a real interval; this reaches the
    # identical end state (case.reassessment_overdue=True) the elapsed-time
    # timer itself would produce, on a third of the newly-arrived low-
    # acuity (tier 4/5) surge patients, same shortcut CP11's scenario #11
    # already used and documented.
    low_acuity_surge = [
        c for c in surge_cases if store.get_latest_risk_assessment(c.case_id).final_acuity >= 4
    ]
    for c in low_acuity_surge[::3]:
        store.flag_reassessment_overdue(c.case_id)
    overdue_count = sum(
        1 for c in baseline_cases + surge_cases if store.get_case(c.case_id).reassessment_overdue
    )
    narrative.append(f"{overdue_count} cases are now reassessment-overdue across the low-acuity bands.")

    # --- Step 3: deliberately scarce capacity -> a conflict must fire. ---
    store.create_resource(resource_type=ResourceType.RESUSCITATION_BAY, label="Resus 1", hospital_profile_id=profile.profile_id)
    store.create_resource(resource_type=ResourceType.TREATMENT_SPACE, label="Bay 1", hospital_profile_id=profile.profile_id)
    store.create_resource(resource_type=ResourceType.TREATMENT_SPACE, label="Bay 2", hospital_profile_id=profile.profile_id)

    tier1_cases = [
        c for c in baseline_cases + surge_cases if store.get_latest_risk_assessment(c.case_id).final_acuity == 1
    ]
    capacity_conflict_detail = None
    for c in tier1_cases:
        try:
            store.assign_resource(c.case_id, ResourceType.RESUSCITATION_BAY, profile)
        except CapacityConflictError as exc:
            capacity_conflict_detail = {
                "case_id": c.case_id,
                "resource_type": exc.resource_type.value,
                "candidate_actions": exc.candidate_actions,
            }
            break
    if capacity_conflict_detail:
        narrative.append(
            f"Capacity conflict: no RESUSCITATION_BAY free for case {capacity_conflict_detail['case_id']} -- "
            f"surfaced with candidate actions, not silently resolved. No acuity was changed."
        )
    else:
        narrative.append(
            "No capacity conflict occurred this run (fewer ESI-1 patients than registered resus bays)."
        )

    # --- Step 4: diagnostics back up -> stuck patients accumulate. -------
    from datetime import timedelta

    stuck_targets = (surge_cases + baseline_cases)[:3]
    for c in stuck_targets:
        now = utcnow()
        test = store.order_test(c.case_id, "XRAY", occurred_at=now - timedelta(hours=2))
        store.mark_sample_collected(test.test_id, occurred_at=now - timedelta(minutes=90))
        store.mark_result_available(test.test_id, occurred_at=now - timedelta(minutes=45))  # past the 30 min window
    stuck = check_stuck_patients(store, profile)
    narrative.append(f"{len(stuck)} patients now appear on the ops (stuck-patient) list, separately from the clinical queue.")

    # --- Step 5: the waiting patient deteriorates and auto-escalates. ----
    _add_vital(store, deteriorating_case.case_id, concepts.RESP_RATE, 26, ValueType.NUMERIC)
    _add_vital(store, deteriorating_case.case_id, concepts.SPO2, 92, ValueType.NUMERIC)
    _add_vital(store, deteriorating_case.case_id, concepts.HEART_RATE, 115, ValueType.NUMERIC)
    _add_vital(store, deteriorating_case.case_id, concepts.SYSTOLIC_BP, 95, ValueType.NUMERIC)
    _add_vital(store, deteriorating_case.case_id, concepts.TEMPERATURE, 38.5, ValueType.NUMERIC)
    escalated_assessment = assess_case(deteriorating_case, store, profile)
    narrative.append(
        f"Waiting patient {deteriorating_case.case_id} deteriorates: "
        f"ESI {acuity_before_deterioration} -> ESI {escalated_assessment.final_acuity}."
    )

    # --- Final snapshots + verification. ---------------------------------
    queue_after = build_queue(store, profile)
    alerts_after = len(sync_alerts(store, profile))

    surge_case_ids = {c.case_id for c in surge_cases}
    jumped = sum(
        1
        for entry in queue_after
        if entry.case_id in surge_case_ids and entry.final_acuity > escalated_assessment.final_acuity
    )
    escalated_rank = next(i for i, e in enumerate(queue_after) if e.case_id == deteriorating_case.case_id)
    narrative.append(
        f"Now ranked #{escalated_rank + 1} of {len(queue_after)} in the queue, ahead of {jumped} "
        f"newer, less-urgent arrivals from the surge batch."
    )

    volume_multiplier = (baseline_count + surge_count) / baseline_count if baseline_count else None
    alert_multiplier_actual = (alerts_after / alerts_before) if alerts_before else None
    alert_growth_held = (
        (alert_multiplier_actual <= volume_multiplier) if alert_multiplier_actual is not None else None
    )
    if alert_growth_held is not None:
        narrative.append(
            f"Alert count grew {alert_multiplier_actual:.2f}x while volume grew {volume_multiplier:.2f}x -- "
            f"aggregation held interruptions well below arrival growth."
            if alert_growth_held
            else f"Alert count grew {alert_multiplier_actual:.2f}x, volume grew {volume_multiplier:.2f}x."
        )

    ordering_holds = _acuity_ordering_holds(queue_after)
    narrative.append(
        "Acuity ordering holds: every queue row's acuity is >= the row before it, at 3x volume."
        if ordering_holds
        else "ACUITY ORDERING VIOLATED -- this should never happen; treat as a bug."
    )

    return SurgeSimulationResult(
        baseline_count=baseline_count,
        surge_count=surge_count,
        total_cases=baseline_count + surge_count,
        queue_length_before=len(queue_before),
        queue_length_after=len(queue_after),
        acuity_ordering_holds=ordering_holds,
        reassessment_overdue_count=overdue_count,
        alerts_before=alerts_before,
        alerts_after=alerts_after,
        volume_multiplier=volume_multiplier,
        alert_multiplier_actual=alert_multiplier_actual,
        alert_growth_held_below_volume_growth=alert_growth_held,
        capacity_conflict_demonstrated=capacity_conflict_detail is not None,
        capacity_conflict_detail=capacity_conflict_detail,
        stuck_patient_count=len(stuck),
        escalated_case_id=deteriorating_case.case_id,
        escalated_from_acuity=acuity_before_deterioration,
        escalated_to_acuity=escalated_assessment.final_acuity,
        escalated_jumped_newer_arrivals_count=jumped,
        narrative=narrative,
    )
