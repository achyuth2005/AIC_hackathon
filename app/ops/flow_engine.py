"""
Flow / Operations Engine (Phase 6): Stuck Patient Detection over the two
entities CP9 introduces for it (DiagnosticTest, Resource), plus the
capacity-conflict path lives in EventStore.assign_resource (Phase 6.2 --
"clinical urgency and resource availability are computed independently").

Like the Guardian Queue (CP7), there is no scheduler in this prototype:
checking and flagging happens opportunistically whenever this module is
read (see app/api/ops.py), which is the same documented substitute for a
cron sweep used throughout.

Phase 6.3's precise definition, applied to three of its five named
patterns (the other two: "reassessment overdue" is already CP7/8's
mechanism, entirely separate on purpose -- see StuckPatternResult's
docstring; "disposition decided, not executed" is out of scope, no
disposition workflow exists yet):

    Pattern                          Expected event        Route to
    Test ordered, no sample          SAMPLE_COLLECTED       Nurse ops list
    Result available, not reviewed   RESULT_REVIEWED        Doctor queue
    Assigned space never occupied    PATIENT_IN_SPACE       Charge nurse
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from app.config.hospital_profile import HospitalProfile
from app.models.enums import DiagnosticTestStatus, ResourceStatus
from app.ops.models import StuckPatternResult
from app.store.event_store import EventStore
from app.timeutil import to_naive_utc, utcnow


def _minutes_since(start: datetime, as_of: datetime) -> float:
    return (as_of - start).total_seconds() / 60.0


def check_stuck_diagnostic_tests(
    store: EventStore, profile: HospitalProfile, as_of: Optional[datetime] = None
) -> List[StuckPatternResult]:
    now = to_naive_utc(as_of) if as_of is not None else utcnow()
    results: List[StuckPatternResult] = []

    for test in store.list_in_flight_diagnostic_tests(profile.profile_id):
        if test.status == DiagnosticTestStatus.ORDERED:
            window = profile.ops.test_ordered_to_sample_window_minutes
            elapsed = _minutes_since(test.ordered_at, now)
            if elapsed > window:
                if not test.stuck_flagged:
                    store.flag_test_stuck(test.test_id, pattern_id="TEST_ORDERED_NOT_COLLECTED", occurred_at=now)
                results.append(
                    StuckPatternResult(
                        pattern_id="TEST_ORDERED_NOT_COLLECTED",
                        label=f"Test ordered ({test.test_type}), sample not yet collected",
                        case_id=test.case_id,
                        minutes_overdue=elapsed - window,
                        route_to="NURSE_OPS",
                    )
                )
        elif test.status == DiagnosticTestStatus.RESULT_AVAILABLE:
            window = profile.ops.result_available_to_reviewed_window_minutes
            elapsed = _minutes_since(test.result_available_at, now)
            if elapsed > window:
                if not test.stuck_flagged:
                    store.flag_test_stuck(test.test_id, pattern_id="RESULT_NOT_REVIEWED", occurred_at=now)
                results.append(
                    StuckPatternResult(
                        pattern_id="RESULT_NOT_REVIEWED",
                        label=f"Result available ({test.test_type}), not yet reviewed",
                        case_id=test.case_id,
                        minutes_overdue=elapsed - window,
                        route_to="DOCTOR_QUEUE",
                    )
                )
        # SAMPLE_COLLECTED (awaiting lab turnaround): no pattern defined
        # for this stage -- lab turnaround time is a "useful, optional"
        # diagnostics-integration concern (Phase 6.1), not one of the
        # patterns this checkpoint implements.

    return results


def check_stuck_resources(
    store: EventStore, profile: HospitalProfile, as_of: Optional[datetime] = None
) -> List[StuckPatternResult]:
    now = to_naive_utc(as_of) if as_of is not None else utcnow()
    results: List[StuckPatternResult] = []

    occupied = store.list_resources(profile.profile_id, status=ResourceStatus.OCCUPIED)
    for resource in occupied:
        if resource.assigned_at is None or resource.assigned_case_id is None:
            continue  # defensive only -- OCCUPIED should always carry both
        window = profile.ops.resource_assigned_to_occupied_window_minutes
        elapsed = _minutes_since(resource.assigned_at, now)
        if elapsed > window:
            if not resource.occupancy_stuck_flagged:
                store.flag_resource_occupancy_stuck(resource.resource_id, occurred_at=now)
            results.append(
                StuckPatternResult(
                    pattern_id="ASSIGNED_SPACE_NOT_OCCUPIED",
                    label=f"{resource.label} assigned, patient not yet confirmed in space",
                    case_id=resource.assigned_case_id,
                    minutes_overdue=elapsed - window,
                    route_to="CHARGE_NURSE",
                )
            )
    return results


def check_stuck_patients(
    store: EventStore, profile: HospitalProfile, as_of: Optional[datetime] = None
) -> List[StuckPatternResult]:
    """The full Stuck Patient Detection sweep: every pattern this
    checkpoint implements, across every in-flight test and occupied
    resource for `profile`. Deliberately does not touch acuity, the
    Guardian Queue's sort order, or RiskAssessment -- Phase 6.2's
    'clinical urgency and resource availability are computed
    independently and stored separately' applies here just as much as to
    capacity conflicts."""
    now = to_naive_utc(as_of) if as_of is not None else utcnow()
    return check_stuck_diagnostic_tests(store, profile, now) + check_stuck_resources(store, profile, now)
