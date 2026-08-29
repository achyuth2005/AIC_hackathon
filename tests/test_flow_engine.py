"""
Tests for the Flow/Operations Engine (Phase 6): resources, capacity
conflicts, diagnostic-test lifecycle, and Stuck Patient Detection.
"""
from datetime import timedelta

import pytest

from app.config.hospital_profile import load_hospital_profile
from app.models.enums import ResourceStatus, ResourceType
from app.ops.flow_engine import check_stuck_patients
from app.store.event_store import CapacityConflictError, EventStore
from app.timeutil import utcnow

PROFILE = load_hospital_profile("default")


# ---------------------------------------------------------------------
# Resources / capacity conflicts (Phase 6.1, 6.2)
# ---------------------------------------------------------------------
def test_assign_resource_picks_an_available_one(store: EventStore):
    store.create_resource(resource_type=ResourceType.TREATMENT_SPACE, label="Bay 1")
    case = store.create_case(age_years=40)

    resource = store.assign_resource(case.case_id, ResourceType.TREATMENT_SPACE, PROFILE)
    assert resource.status == ResourceStatus.OCCUPIED
    assert resource.assigned_case_id == case.case_id

    event_types = [e.event_type for e in store.get_timeline(case.case_id)]
    assert "RESOURCE_ASSIGNED" in event_types


def test_assign_resource_raises_capacity_conflict_when_none_available(store: EventStore):
    case = store.create_case(age_years=40)  # no resources registered at all
    with pytest.raises(CapacityConflictError) as exc_info:
        store.assign_resource(case.case_id, ResourceType.RESUSCITATION_BAY, PROFILE)

    assert exc_info.value.resource_type == ResourceType.RESUSCITATION_BAY
    assert len(exc_info.value.candidate_actions) > 0

    event_types = [e.event_type for e in store.get_timeline(case.case_id)]
    assert "CAPACITY_CONFLICT_RAISED" in event_types


def test_capacity_conflict_never_touches_acuity(store: EventStore):
    """Phase 6.2: 'Clinical urgency and resource availability are computed
    independently ... Capacity never modifies acuity.'"""
    case = store.create_case(age_years=40)
    from app.scoring.risk_orchestrator import assess_case

    before = assess_case(case, store, PROFILE)

    with pytest.raises(CapacityConflictError):
        store.assign_resource(case.case_id, ResourceType.TREATMENT_SPACE, PROFILE)

    after = store.get_latest_risk_assessment(case.case_id)
    assert after.assessment_id == before.assessment_id  # unchanged -- no new assessment was triggered
    assert after.final_acuity == before.final_acuity


def test_release_then_reassign(store: EventStore):
    r = store.create_resource(resource_type=ResourceType.TREATMENT_SPACE, label="Bay 2")
    case1 = store.create_case(age_years=30)
    store.assign_resource(case1.case_id, ResourceType.TREATMENT_SPACE, PROFILE)

    case2 = store.create_case(age_years=50)
    with pytest.raises(CapacityConflictError):
        store.assign_resource(case2.case_id, ResourceType.TREATMENT_SPACE, PROFILE)

    store.release_resource(r.resource_id)
    reassigned = store.assign_resource(case2.case_id, ResourceType.TREATMENT_SPACE, PROFILE)
    assert reassigned.resource_id == r.resource_id
    assert reassigned.assigned_case_id == case2.case_id


def test_confirm_occupancy_resets_stuck_flag(store: EventStore):
    r = store.create_resource(resource_type=ResourceType.RESUSCITATION_BAY, label="Resus 1")
    case = store.create_case(age_years=40)
    store.assign_resource(case.case_id, ResourceType.RESUSCITATION_BAY, PROFILE)

    store.flag_resource_occupancy_stuck(r.resource_id)
    assert store.get_resource(r.resource_id).occupancy_stuck_flagged is True

    store.confirm_occupancy(r.resource_id)
    assert store.get_resource(r.resource_id).occupancy_stuck_flagged is False


# ---------------------------------------------------------------------
# Diagnostic tests / Stuck Patient Detection (Phase 6.3)
# ---------------------------------------------------------------------
def test_test_ordered_not_collected_is_stuck_after_its_window(store: EventStore):
    now = utcnow()
    case = store.create_case(age_years=40)
    store.order_test(case.case_id, "CBC", occurred_at=now - timedelta(minutes=60))  # window is 45 min

    stuck = check_stuck_patients(store, PROFILE, as_of=now)
    matches = [s for s in stuck if s.pattern_id == "TEST_ORDERED_NOT_COLLECTED" and s.case_id == case.case_id]
    assert len(matches) == 1
    assert matches[0].route_to == "NURSE_OPS"
    assert matches[0].minutes_overdue == pytest.approx(15.0, abs=0.1)


def test_test_within_window_is_not_stuck(store: EventStore):
    now = utcnow()
    case = store.create_case(age_years=40)
    store.order_test(case.case_id, "CBC", occurred_at=now - timedelta(minutes=10))

    stuck = check_stuck_patients(store, PROFILE, as_of=now)
    assert not any(s.case_id == case.case_id for s in stuck)


def test_sample_collected_resolves_pattern_one(store: EventStore):
    now = utcnow()
    case = store.create_case(age_years=40)
    test = store.order_test(case.case_id, "CBC", occurred_at=now - timedelta(minutes=60))
    store.mark_sample_collected(test.test_id, occurred_at=now)

    stuck = check_stuck_patients(store, PROFILE, as_of=now)
    assert not any(s.pattern_id == "TEST_ORDERED_NOT_COLLECTED" and s.case_id == case.case_id for s in stuck)


def test_result_available_not_reviewed_is_stuck_after_its_window(store: EventStore):
    now = utcnow()
    case = store.create_case(age_years=40)
    test = store.order_test(case.case_id, "XRAY", occurred_at=now - timedelta(hours=2))
    store.mark_sample_collected(test.test_id, occurred_at=now - timedelta(minutes=90))
    store.mark_result_available(test.test_id, occurred_at=now - timedelta(minutes=45))  # window is 30 min

    stuck = check_stuck_patients(store, PROFILE, as_of=now)
    matches = [s for s in stuck if s.pattern_id == "RESULT_NOT_REVIEWED" and s.case_id == case.case_id]
    assert len(matches) == 1
    assert matches[0].route_to == "DOCTOR_QUEUE"


def test_result_reviewed_resolves_pattern_two(store: EventStore):
    now = utcnow()
    case = store.create_case(age_years=40)
    test = store.order_test(case.case_id, "XRAY", occurred_at=now - timedelta(hours=2))
    store.mark_sample_collected(test.test_id, occurred_at=now - timedelta(minutes=90))
    store.mark_result_available(test.test_id, occurred_at=now - timedelta(minutes=45))
    store.mark_result_reviewed(test.test_id, occurred_at=now)

    stuck = check_stuck_patients(store, PROFILE, as_of=now)
    assert not any(s.case_id == case.case_id for s in stuck)


def test_stuck_flag_is_set_once_not_repeated_on_every_sweep(store: EventStore):
    now = utcnow()
    case = store.create_case(age_years=40)
    store.order_test(case.case_id, "CBC", occurred_at=now - timedelta(minutes=60))

    check_stuck_patients(store, PROFILE, as_of=now)
    check_stuck_patients(store, PROFILE, as_of=now + timedelta(minutes=1))

    event_types = [e.event_type for e in store.get_timeline(case.case_id)]
    assert event_types.count("STUCK_PATIENT_DETECTED") == 1


def test_assigned_space_never_occupied_is_stuck_after_its_window(store: EventStore):
    now = utcnow()
    store.create_resource(resource_type=ResourceType.TREATMENT_SPACE, label="Bay 3")
    case = store.create_case(age_years=40)
    store.assign_resource(case.case_id, ResourceType.TREATMENT_SPACE, PROFILE, occurred_at=now - timedelta(minutes=20))

    stuck = check_stuck_patients(store, PROFILE, as_of=now)
    matches = [s for s in stuck if s.pattern_id == "ASSIGNED_SPACE_NOT_OCCUPIED" and s.case_id == case.case_id]
    assert len(matches) == 1
    assert matches[0].route_to == "CHARGE_NURSE"


def test_stuck_detection_never_touches_acuity_or_queue_order(store: EventStore):
    """Phase 6.2's independence principle applies to Stuck Patient
    Detection too, not just capacity conflicts."""
    now = utcnow()
    case = store.create_case(age_years=40)
    from app.scoring.risk_orchestrator import assess_case

    before = assess_case(case, store, PROFILE, as_of=now)
    store.order_test(case.case_id, "CBC", occurred_at=now - timedelta(minutes=60))

    check_stuck_patients(store, PROFILE, as_of=now)

    after = store.get_latest_risk_assessment(case.case_id)
    assert after.assessment_id == before.assessment_id
    assert after.final_acuity == before.final_acuity
