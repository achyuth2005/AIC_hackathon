"""
Emergency Bypass tests (Phase 3.5): the text-pattern matcher in isolation,
the engine-level orchestration of detectors #2/#3 against real Case +
Observation rows, and the HTTP surface for detector #1 (human affordance)
plus the automatic hook on observation writes.
"""
from datetime import datetime, timezone

from app.bypass.engine import evaluate_and_activate
from app.bypass.text_patterns import detect_critical_phrase
from app.config.hospital_profile import load_hospital_profile
from app.models.enums import BypassSource, MeasurementStatus, ReliabilityTier, SourceType, ValueType
from app.scoring import concepts
from app.store.event_store import EventStore

PROFILE = load_hospital_profile("default")


def _now():
    return datetime.now(timezone.utc)


def _add(store: EventStore, case_id, concept_code, value, value_type):
    return store.add_observation(
        case_id=case_id,
        concept_code=concept_code,
        value=value,
        value_type=value_type,
        source_type=SourceType.NURSE,
        reliability_tier=ReliabilityTier.CLINICIAN_OBSERVED,
        measurement_status=MeasurementStatus.MEASURED,
        observed_at=_now(),
    )


# ---------------------------------------------------------------------
# Detector #3 in isolation
# ---------------------------------------------------------------------
def test_detect_critical_phrase_is_case_insensitive():
    phrases = ["not breathing", "chest pain"]
    assert detect_critical_phrase("Patient is NOT BREATHING and blue", phrases) == "not breathing"
    assert detect_critical_phrase("mild headache, otherwise fine", phrases) is None
    assert detect_critical_phrase(None, phrases) is None
    assert detect_critical_phrase("", phrases) is None


# ---------------------------------------------------------------------
# Engine-level (DB-backed) orchestration
# ---------------------------------------------------------------------
def test_physiological_trigger_activates_bypass(store: EventStore):
    case = store.create_case(age_years=40)
    _add(store, case.case_id, concepts.SPO2, 70.0, ValueType.NUMERIC)  # <=75 -> PROFOUND_HYPOXIA

    result = evaluate_and_activate(case, store, PROFILE)
    assert result is not None
    assert result.emergency_bypass_active is True
    assert result.emergency_bypass_last_source == BypassSource.PHYSIOLOGICAL

    event_types = [e.event_type for e in store.get_timeline(case.case_id)]
    assert "EMERGENCY_BYPASS_ACTIVATED" in event_types


def test_normal_vitals_do_not_activate_bypass(store: EventStore):
    case = store.create_case(age_years=40)
    _add(store, case.case_id, concepts.SPO2, 98.0, ValueType.NUMERIC)
    _add(store, case.case_id, concepts.HEART_RATE, 75.0, ValueType.NUMERIC)

    result = evaluate_and_activate(case, store, PROFILE)
    assert result is None

    fresh = store.get_case(case.case_id)
    assert fresh.emergency_bypass_active is False


def test_critical_phrase_in_symptom_text_activates_bypass(store: EventStore):
    case = store.create_case(age_years=40)
    _add(store, case.case_id, concepts.SYMPTOM_TEXT, "patient reports not breathing well", ValueType.TEXT)

    result = evaluate_and_activate(case, store, PROFILE)
    assert result is not None
    assert result.emergency_bypass_last_source == BypassSource.TEXT_PATTERN
    assert "not breathing" in result.emergency_bypass_last_reason


def test_first_activated_at_is_preserved_across_repeated_firings(store: EventStore):
    """Phase 3.5: 'any of which can fire, none of which can cancel
    another' -- a second, different detector firing later must not erase
    when the case FIRST became critical."""
    case = store.create_case(age_years=40)

    first = store.activate_emergency_bypass(
        case.case_id, source=BypassSource.HUMAN, reason="Nurse pressed the button"
    )
    assert first.emergency_bypass_first_activated_at is not None
    first_ts = first.emergency_bypass_first_activated_at

    second = store.activate_emergency_bypass(
        case.case_id, source=BypassSource.PHYSIOLOGICAL, reason="SpO2 <= 75", trigger_id="PROFOUND_HYPOXIA"
    )
    assert second.emergency_bypass_first_activated_at == first_ts  # unchanged
    assert second.emergency_bypass_last_source == BypassSource.PHYSIOLOGICAL  # updated
    assert second.emergency_bypass_last_trigger_id == "PROFOUND_HYPOXIA"

    event_types = [e.event_type for e in store.get_timeline(case.case_id)]
    assert event_types.count("EMERGENCY_BYPASS_ACTIVATED") == 2  # both firings logged, neither suppressed


def test_missing_observation_never_fires_physiological_trigger(store: EventStore):
    case = store.create_case(age_years=40)  # no observations recorded at all
    result = evaluate_and_activate(case, store, PROFILE)
    assert result is None


# ---------------------------------------------------------------------
# HTTP surface
# ---------------------------------------------------------------------
def _nurse_auth_header(client):
    token = client.post("/auth/login", json={"role": "NURSE"}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_human_affordance_endpoint_activates_bypass(client):
    headers = _nurse_auth_header(client)
    case_id = client.post("/cases", json={"age_years": 40}, headers=headers).json()["case_id"]

    resp = client.post(
        f"/cases/{case_id}/emergency-bypass",
        json={"reason": "Patient collapsed at reception"},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["emergency_bypass_active"] is True
    assert body["emergency_bypass_last_source"] == "HUMAN"
    assert "collapsed" in body["emergency_bypass_last_reason"]


def test_human_affordance_endpoint_requires_authentication(client):
    headers = _nurse_auth_header(client)
    case_id = client.post("/cases", json={"age_years": 40}, headers=headers).json()["case_id"]
    resp = client.post(f"/cases/{case_id}/emergency-bypass", json={"reason": "no token supplied"})
    assert resp.status_code == 401


def test_human_affordance_on_missing_case_is_404(client):
    resp = client.post(
        "/cases/does-not-exist/emergency-bypass", json={}, headers=_nurse_auth_header(client)
    )
    assert resp.status_code == 404


def test_adding_a_critical_vital_via_api_auto_activates_bypass(client):
    headers = _nurse_auth_header(client)
    case_id = client.post("/cases", json={"age_years": 40}, headers=headers).json()["case_id"]

    resp = client.post(
        f"/cases/{case_id}/observations",
        json={
            "concept_code": "SPO2",
            "value": 70.0,
            "value_type": "NUMERIC",
            "source_type": "DEVICE",
            "reliability_tier": 1,
            "measurement_status": "MEASURED",
            "observed_at": _now().isoformat(),
        },
        headers=headers,
    )
    assert resp.status_code == 201  # the observation write itself is unaffected by the bypass check

    case_detail = client.get(f"/cases/{case_id}", headers=headers).json()
    assert case_detail["emergency_bypass_active"] is True
    assert case_detail["emergency_bypass_last_source"] == "PHYSIOLOGICAL"


def test_adding_normal_vitals_via_api_does_not_activate_bypass(client):
    headers = _nurse_auth_header(client)
    case_id = client.post("/cases", json={"age_years": 40}, headers=headers).json()["case_id"]

    client.post(
        f"/cases/{case_id}/observations",
        json={
            "concept_code": "SPO2",
            "value": 98.0,
            "value_type": "NUMERIC",
            "source_type": "DEVICE",
            "reliability_tier": 1,
            "measurement_status": "MEASURED",
            "observed_at": _now().isoformat(),
        },
        headers=headers,
    )

    case_detail = client.get(f"/cases/{case_id}", headers=headers).json()
    assert case_detail["emergency_bypass_active"] is False
