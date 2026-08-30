"""
Tests for the Phase 8 dashboard-facing read APIs (CP15): patient view
(with its "never show" guarantee), the nurse queue's new presentation
fields, the doctor view (incl. "what changed since last review"), and the
control tower's five tiles.
"""
from datetime import timedelta

from app.config.hospital_profile import load_hospital_profile
from app.dashboard.control_tower import build_control_tower
from app.dashboard.doctor_view import build_doctor_view
from app.dashboard.patient_view import build_patient_view
from app.models.enums import (
    ArrivalMode,
    MeasurementStatus,
    NurseAttentionFlag,
    PatientStage,
    ReliabilityTier,
    ResourceType,
    SourceType,
    ValueType,
)
from app.queue.guardian_queue import build_queue
from app.scoring import concepts
from app.scoring.risk_orchestrator import assess_case
from app.store.event_store import EventStore
from app.timeutil import utcnow

PROFILE = load_hospital_profile("default")


def _full_adult_vitals(store, case_id, *, rr=18, spo2=96, hr=80, sbp=120, temp=37.0, observed_at=None):
    for code, val in (
        (concepts.RESP_RATE, rr), (concepts.SPO2, spo2), (concepts.HEART_RATE, hr),
        (concepts.SYSTOLIC_BP, sbp), (concepts.TEMPERATURE, temp),
    ):
        store.add_observation(
            case_id=case_id, concept_code=code, value=val, value_type=ValueType.NUMERIC,
            source_type=SourceType.DEVICE, reliability_tier=ReliabilityTier.MACHINE_MEASURED,
            measurement_status=MeasurementStatus.MEASURED, observed_at=observed_at or utcnow(),
        )
    store.add_observation(
        case_id=case_id, concept_code=concepts.CONSCIOUSNESS_LEVEL, value="ALERT", value_type=ValueType.CODED,
        source_type=SourceType.DEVICE, reliability_tier=ReliabilityTier.MACHINE_MEASURED,
        measurement_status=MeasurementStatus.MEASURED, observed_at=observed_at or utcnow(),
    )
    store.add_observation(
        case_id=case_id, concept_code=concepts.SUPPLEMENTAL_OXYGEN, value=False, value_type=ValueType.BOOLEAN,
        source_type=SourceType.DEVICE, reliability_tier=ReliabilityTier.MACHINE_MEASURED,
        measurement_status=MeasurementStatus.MEASURED, observed_at=observed_at or utcnow(),
    )


# ---------------------------------------------------------------------
# Patient view (Phase 8.1)
# ---------------------------------------------------------------------
def test_patient_view_never_carries_acuity_or_confidence_fields():
    from app.schemas.case import PatientCaseView

    field_names = set(PatientCaseView.model_fields.keys())
    forbidden = {"final_acuity", "acuity", "confidence_band", "confidence_score", "risk", "probability"}
    assert field_names.isdisjoint(forbidden)


def test_patient_view_stage_waiting_and_wait_estimate_present(store: EventStore):
    case = store.create_case(age_years=40)
    _full_adult_vitals(store, case.case_id)
    assess_case(case, store, PROFILE)

    view = build_patient_view(case, store, PROFILE)
    assert view.stage == PatientStage.WAITING
    assert view.wait_time_estimate is not None
    assert "waiting" in view.next_step_message.lower()


def test_patient_view_stage_in_treatment_once_occupying_a_resource(store: EventStore):
    store.create_resource(resource_type=ResourceType.TREATMENT_SPACE, label="Bay 1")
    case = store.create_case(age_years=40)
    _full_adult_vitals(store, case.case_id)
    assess_case(case, store, PROFILE)
    store.assign_resource(case.case_id, ResourceType.TREATMENT_SPACE, PROFILE)

    view = build_patient_view(case, store, PROFILE)
    assert view.stage == PatientStage.IN_TREATMENT
    assert view.wait_time_estimate is None  # no longer waiting -- nothing to estimate


def test_patient_view_stage_pre_arrival_has_no_wait_estimate(store: EventStore):
    case = store.create_case(age_years=40, arrival_mode=ArrivalMode.AMBULANCE)
    view = build_patient_view(case, store, PROFILE)
    assert view.stage == PatientStage.PRE_ARRIVAL
    assert view.wait_time_estimate is None


# ---------------------------------------------------------------------
# Nurse queue enrichment (Phase 8.2)
# ---------------------------------------------------------------------
def test_queue_entry_carries_one_line_presentation(store: EventStore):
    case = store.create_case(age_years=40)
    store.add_observation(
        case_id=case.case_id, concept_code=concepts.SYMPTOM_TEXT, value="Chest pain radiating to left arm",
        value_type=ValueType.TEXT, source_type=SourceType.PATIENT, reliability_tier=ReliabilityTier.PATIENT_REPORTED,
        measurement_status=MeasurementStatus.MEASURED, observed_at=utcnow(),
    )
    _full_adult_vitals(store, case.case_id)
    assess_case(case, store, PROFILE)

    entry = next(e for e in build_queue(store, PROFILE) if e.case_id == case.case_id)
    assert entry.one_line_presentation == "Chest pain radiating to left arm"


def test_queue_entry_flags_deteriorating_above_all_else(store: EventStore):
    case = store.create_case(age_years=40)
    _full_adult_vitals(store, case.case_id, rr=18, spo2=96, hr=80, sbp=120, temp=37.0)
    assess_case(case, store, PROFILE)
    later = utcnow() + timedelta(minutes=10)
    _full_adult_vitals(store, case.case_id, rr=26, spo2=92, hr=115, sbp=95, temp=38.5, observed_at=later)
    assess_case(case, store, PROFILE, as_of=later)
    store.flag_reassessment_overdue(case.case_id)  # ALSO overdue -- deteriorating must still win

    entry = next(e for e in build_queue(store, PROFILE, as_of=later) if e.case_id == case.case_id)
    assert entry.primary_attention_flag == NurseAttentionFlag.DETERIORATING


def test_queue_entry_flags_unknown_vitals_when_missing(store: EventStore):
    case = store.create_case(age_years=40)  # no vitals at all
    assess_case(case, store, PROFILE)

    entry = next(e for e in build_queue(store, PROFILE) if e.case_id == case.case_id)
    assert entry.primary_attention_flag == NurseAttentionFlag.UNKNOWN_VITALS


def test_queue_entry_flags_none_when_nothing_notable(store: EventStore):
    case = store.create_case(age_years=40)
    _full_adult_vitals(store, case.case_id)
    assess_case(case, store, PROFILE)

    entry = next(e for e in build_queue(store, PROFILE) if e.case_id == case.case_id)
    assert entry.primary_attention_flag == NurseAttentionFlag.NONE


# ---------------------------------------------------------------------
# Doctor view (Phase 8.3)
# ---------------------------------------------------------------------
def test_doctor_view_is_first_review_then_tracks_changes(store: EventStore):
    case = store.create_case(age_years=40)
    _full_adult_vitals(store, case.case_id)
    assess_case(case, store, PROFILE)

    first = build_doctor_view(case, store, PROFILE, reviewer_id="demo-doctor-01")
    assert first.is_first_review is True
    assert len(first.changed_since_last_review) > 0  # everything so far, since there's no prior review

    store.mark_case_reviewed(case.case_id, "demo-doctor-01")
    second = build_doctor_view(case, store, PROFILE, reviewer_id="demo-doctor-01")
    assert second.is_first_review is False
    assert second.changed_since_last_review == []  # nothing happened since the review

    store.report_patient_worsening(case.case_id, note="feeling worse")
    third = build_doctor_view(case, store, PROFILE, reviewer_id="demo-doctor-01")
    assert any(e.event_type == "PATIENT_SELF_REPORTED_WORSENING" for e in third.changed_since_last_review)


def test_doctor_view_trends_require_two_readings(store: EventStore):
    case = store.create_case(age_years=40)
    _full_adult_vitals(store, case.case_id, hr=80)
    assess_case(case, store, PROFILE)
    view = build_doctor_view(case, store, PROFILE, reviewer_id="demo-doctor-01")
    assert view.trends == []  # only one reading per concept so far

    store.add_observation(
        case_id=case.case_id, concept_code=concepts.HEART_RATE, value=95.0, value_type=ValueType.NUMERIC,
        source_type=SourceType.DEVICE, reliability_tier=ReliabilityTier.MACHINE_MEASURED,
        measurement_status=MeasurementStatus.MEASURED, observed_at=utcnow(),
    )
    view2 = build_doctor_view(case, store, PROFILE, reviewer_id="demo-doctor-01")
    hr_trend = next(t for t in view2.trends if t.concept_code == concepts.HEART_RATE)
    assert hr_trend.delta == 15.0


def test_doctor_view_pending_actions_include_unreviewed_result_and_open_conflict(store: EventStore):
    case = store.create_case(age_years=40)
    _full_adult_vitals(store, case.case_id)
    assess_case(case, store, PROFILE)

    now = utcnow()
    test = store.order_test(case.case_id, "XRAY", occurred_at=now)
    store.mark_sample_collected(test.test_id, occurred_at=now)
    store.mark_result_available(test.test_id, occurred_at=now)

    store.add_observation(
        case_id=case.case_id, concept_code=concepts.HEART_RATE, value=200.0, value_type=ValueType.NUMERIC,
        source_type=SourceType.PATIENT, reliability_tier=ReliabilityTier.PATIENT_REPORTED,
        measurement_status=MeasurementStatus.MEASURED, observed_at=now,
    )
    assess_case(case, store, PROFILE, as_of=now)  # HR now conflicts with the earlier device reading -> conflict

    view = build_doctor_view(case, store, PROFILE, reviewer_id="demo-doctor-01")
    kinds = {a.kind for a in view.pending_actions}
    assert "RESULT_AWAITING_REVIEW" in kinds
    assert "UNRESOLVED_DATA_CONFLICT" in kinds


# ---------------------------------------------------------------------
# Control tower (Phase 8.4)
# ---------------------------------------------------------------------
def test_control_tower_five_tiles_reflect_real_state(store: EventStore):
    store.create_resource(resource_type=ResourceType.TREATMENT_SPACE, label="Bay 1")

    active = store.create_case(age_years=40)
    _full_adult_vitals(store, active.case_id, rr=18, spo2=96, hr=80, sbp=120, temp=37.0)
    assess_case(active, store, PROFILE)
    store.flag_reassessment_overdue(active.case_id)

    ambulance = store.create_case(age_years=50, arrival_mode=ArrivalMode.AMBULANCE)
    _full_adult_vitals(store, ambulance.case_id, rr=24, spo2=90, hr=110, sbp=95, temp=37.0)
    assess_case(ambulance, store, PROFILE)

    tower = build_control_tower(store, PROFILE)

    assert sum(t.case_count for t in tower.patients_by_acuity_band) == 1
    assert sum(t.overdue_count for t in tower.patients_by_acuity_band) == 1

    space_tile = next(t for t in tower.capacity if t.resource_type == "TREATMENT_SPACE")
    assert space_tile.available == 1
    assert space_tile.needed_estimate == 1  # the one ACTIVE case, not yet occupying anything

    assert len(tower.incoming_ambulances) == 1
    assert tower.incoming_ambulances[0].case_id == ambulance.case_id
    assert tower.incoming_ambulances[0].predicted_acuity is not None

    assert isinstance(tower.deteriorating_patients, list)
    assert isinstance(tower.stuck_patients, list)


# ---------------------------------------------------------------------
# HTTP surface
# ---------------------------------------------------------------------
def test_patient_view_endpoint_requires_no_auth(client, nurse_headers):
    case_id = client.post("/cases", json={"age_years": 40}, headers=nurse_headers).json()["case_id"]
    resp = client.get(f"/cases/{case_id}/patient-view")
    assert resp.status_code == 200
    assert "stage" in resp.json()
    assert "final_acuity" not in resp.json()


def test_doctor_view_endpoint_requires_auth(client, nurse_headers):
    case_id = client.post("/cases", json={"age_years": 40}, headers=nurse_headers).json()["case_id"]
    unauth = client.get(f"/cases/{case_id}/doctor-view")
    assert unauth.status_code == 401

    token = client.post("/auth/login", json={"role": "DOCTOR"}).json()["access_token"]
    ok = client.get(f"/cases/{case_id}/doctor-view", headers={"Authorization": f"Bearer {token}"})
    assert ok.status_code == 200
    assert ok.json()["is_first_review"] is True


def test_mark_reviewed_endpoint(client):
    token = client.post("/auth/login", json={"role": "DOCTOR"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    case_id = client.post("/cases", json={"age_years": 40}, headers=headers).json()["case_id"]

    resp = client.post(f"/cases/{case_id}/mark-reviewed", headers=headers)
    assert resp.status_code == 200

    view = client.get(f"/cases/{case_id}/doctor-view", headers=headers).json()
    assert view["is_first_review"] is False


def test_control_tower_endpoint(client, nurse_headers):
    unauth = client.get("/control-tower")
    assert unauth.status_code == 401

    resp = client.get("/control-tower", headers=nurse_headers)
    assert resp.status_code == 200
    body = resp.json()
    for key in ("patients_by_acuity_band", "deteriorating_patients", "stuck_patients", "capacity", "incoming_ambulances"):
        assert key in body
