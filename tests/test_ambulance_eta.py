"""
Tests for the Phase 7.2/7.3 ambulance ETA simulation and pre-alert (CP18):
the narrowing range, the paramedic delay flag, and the pre-alert view.
"""
from datetime import timedelta

from app.ambulance.eta import compute_eta_range
from app.ambulance.prealert import build_pre_alert
from app.config.hospital_profile import load_hospital_profile
from app.models.enums import ArrivalMode, MeasurementStatus, ReliabilityTier, SourceType, ValueType
from app.scoring import concepts
from app.scoring.risk_orchestrator import assess_case
from app.store.event_store import EventStore
from app.timeutil import utcnow

PROFILE = load_hospital_profile("default")


def test_eta_range_narrows_as_time_passes(store: EventStore):
    case = store.create_case(age_years=40, arrival_mode=ArrivalMode.AMBULANCE)
    now = utcnow()
    store.start_ambulance_transport(case.case_id, estimated_total_minutes=30.0, occurred_at=now)
    transport = store.get_ambulance_transport(case.case_id)

    early = compute_eta_range(transport, as_of=now)
    later = compute_eta_range(transport, as_of=now + timedelta(minutes=20))

    early_width = early.upper_minutes - early.lower_minutes
    later_width = later.upper_minutes - later.lower_minutes
    assert later_width < early_width  # the range genuinely narrows
    assert later.upper_minutes < early.upper_minutes  # and the estimate itself shrinks


def test_eta_range_never_a_single_number(store: EventStore):
    case = store.create_case(age_years=40, arrival_mode=ArrivalMode.AMBULANCE)
    store.start_ambulance_transport(case.case_id, estimated_total_minutes=15.0)
    transport = store.get_ambulance_transport(case.case_id)

    result = compute_eta_range(transport)
    assert result.lower_minutes < result.upper_minutes
    assert "narrow" in result.caveat.lower()


def test_arrived_once_estimated_time_has_fully_elapsed(store: EventStore):
    case = store.create_case(age_years=40, arrival_mode=ArrivalMode.AMBULANCE)
    now = utcnow()
    store.start_ambulance_transport(case.case_id, estimated_total_minutes=10.0, occurred_at=now)
    transport = store.get_ambulance_transport(case.case_id)

    result = compute_eta_range(transport, as_of=now + timedelta(minutes=15))
    assert result.arrived is True
    assert result.lower_minutes == 0.0 and result.upper_minutes == 0.0


def test_delay_extends_the_estimate_rather_than_replacing_it(store: EventStore):
    case = store.create_case(age_years=40, arrival_mode=ArrivalMode.AMBULANCE)
    now = utcnow()
    store.start_ambulance_transport(case.case_id, estimated_total_minutes=10.0, occurred_at=now)

    before = compute_eta_range(store.get_ambulance_transport(case.case_id), as_of=now)
    store.mark_transport_delayed(case.case_id, additional_minutes=20.0, reason="traffic", occurred_at=now)
    after = compute_eta_range(store.get_ambulance_transport(case.case_id), as_of=now)

    assert after.upper_minutes > before.upper_minutes
    assert after.delayed_additional_minutes == 20.0

    event_types = [e.event_type for e in store.get_timeline(case.case_id)]
    assert "AMBULANCE_TRANSPORT_STARTED" in event_types
    assert "AMBULANCE_TRANSPORT_DELAYED" in event_types


# ---------------------------------------------------------------------
# Pre-alert
# ---------------------------------------------------------------------
def test_pre_alert_contains_all_named_fields(store: EventStore):
    case = store.create_case(age_years=58, arrival_mode=ArrivalMode.AMBULANCE)
    store.start_ambulance_transport(case.case_id, estimated_total_minutes=12.0)
    store.add_observation(
        case_id=case.case_id, concept_code=concepts.SYMPTOM_TEXT, value="Severe chest pain, sweating",
        value_type=ValueType.TEXT, source_type=SourceType.PARAMEDIC, reliability_tier=ReliabilityTier.CLINICIAN_OBSERVED,
        measurement_status=MeasurementStatus.MEASURED, observed_at=utcnow(),
    )
    for code, val in ((concepts.RESP_RATE, 26), (concepts.SPO2, 90), (concepts.HEART_RATE, 115), (concepts.SYSTOLIC_BP, 95), (concepts.TEMPERATURE, 37.0)):
        store.add_observation(
            case_id=case.case_id, concept_code=code, value=val, value_type=ValueType.NUMERIC,
            source_type=SourceType.PARAMEDIC, reliability_tier=ReliabilityTier.CLINICIAN_OBSERVED,
            measurement_status=MeasurementStatus.MEASURED, observed_at=utcnow(),
        )
    assess_case(case, store, PROFILE)

    view = build_pre_alert(case, store, PROFILE)
    assert view.predicted_acuity_band is not None
    assert view.one_line_presentation == "Severe chest pain, sweating"
    assert len(view.key_abnormal_vitals) > 0
    assert view.interventions_already_performed == []
    assert view.eta_range is not None
    assert "prepare" in view.what_hospital_should_prepare.lower() or "space" in view.what_hospital_should_prepare.lower()


def test_pre_alert_handles_no_transport_and_no_assessment_gracefully(store: EventStore):
    case = store.create_case(age_years=40, arrival_mode=ArrivalMode.AMBULANCE)  # no transport, no vitals
    view = build_pre_alert(case, store, PROFILE)
    assert view.predicted_acuity_band is None
    assert view.eta_range is None
    assert view.key_abnormal_vitals == []


# ---------------------------------------------------------------------
# HTTP surface
# ---------------------------------------------------------------------
def test_ambulance_endpoints(client):
    case_id = client.post(
        "/cases", json={"age_years": 50, "arrival_mode": "AMBULANCE", "estimated_transport_minutes": 18.0}
    ).json()["case_id"]

    eta = client.get(f"/cases/{case_id}/eta").json()
    assert eta["lower_minutes"] < eta["upper_minutes"]

    delayed = client.post(f"/cases/{case_id}/ambulance/delay", json={"additional_minutes": 10.0, "reason": "traffic"})
    assert delayed.status_code == 200
    assert delayed.json()["delayed_additional_minutes"] == 10.0

    prealert = client.get(f"/cases/{case_id}/pre-alert")
    assert prealert.status_code == 200
    assert prealert.json()["eta_range"] is not None


def test_eta_endpoint_404s_for_a_walk_in(client):
    case_id = client.post("/cases", json={"age_years": 40}).json()["case_id"]
    resp = client.get(f"/cases/{case_id}/eta")
    assert resp.status_code == 404
