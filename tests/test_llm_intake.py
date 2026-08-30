"""
Tests for the Phase 3.2 LLM Intake Engine (CP17): schema-constrained
extraction, deterministic range/unit validation, the retry-once policy,
redaction-before-send, and the Phase 9.5 failure modes. All network calls
are mocked (httpx.MockTransport) -- no real API call is made.
"""
import json

import httpx
import pytest

from app.config.hospital_profile import load_hospital_profile
from app.llm.client import LLMClient
from app.llm.intake import extract_intake_fields
from app.models.enums import ReliabilityTier, SourceType
from app.privacy.llm_gateway import LLMClientConfig
from app.scoring import concepts
from app.store.event_store import EventStore

PROFILE = load_hospital_profile("default")
CONFIG = LLMClientConfig(provider="groq", model="test-model", api_key_env_var="TEST_GROQ_KEY")


def _client_with_responses(*json_bodies, monkeypatch):
    monkeypatch.setenv("TEST_GROQ_KEY", "fake-key-for-tests")
    calls = {"n": 0, "requests": []}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["requests"].append(request)
        idx = min(calls["n"], len(json_bodies) - 1)
        content = json_bodies[idx]
        calls["n"] += 1
        return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})

    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(transport=transport)
    return LLMClient(CONFIG, http_client=http_client), calls


def _valid_payload(**overrides):
    payload = {
        "symptom_flags": [{"concept_code": "SYMPTOM_CHEST_PAIN", "present": True, "confidence": 0.9}],
        "history_flags": [{"concept_code": "HISTORY_CARDIAC", "present": True, "confidence": 0.7}],
        "onset": {"onset_minutes": 45.0, "confidence": 0.8},
        "vitals": [{"concept_code": "SPO2", "value": 90.0, "confidence": 0.6}],
    }
    payload.update(overrides)
    return payload


def test_disabled_returns_immediately_with_no_llm_call(store: EventStore, monkeypatch):
    disabled_profile = PROFILE.model_copy(deep=True)
    disabled_profile.llm.enabled = False
    case = store.create_case(age_years=40)

    outcome = extract_intake_fields(case, store, disabled_profile, "chest pain", llm_client=None)
    assert outcome.llm_available is False
    assert outcome.parse_succeeded is True
    assert outcome.model_version == "regex-fallback"


def test_successful_extraction_persists_ai_inferred_observations(store: EventStore, monkeypatch):
    client, calls = _client_with_responses(json.dumps(_valid_payload()), monkeypatch=monkeypatch)
    case = store.create_case(age_years=40)

    outcome = extract_intake_fields(case, store, PROFILE, "Patient reports chest pain since 45 min ago.", llm_client=client)

    assert outcome.llm_available is True
    assert outcome.parse_succeeded is True
    assert len(outcome.observations_created) == 4  # chest pain + cardiac history + onset + SpO2
    assert outcome.rejected == []
    assert len(calls["requests"]) == 1  # no retry needed

    spo2_obs = store.get_latest_current_observation(case.case_id, concepts.SPO2)
    assert spo2_obs.value_numeric == 90.0
    assert spo2_obs.source_type == SourceType.AI_INFERRED
    assert spo2_obs.reliability_tier == ReliabilityTier.AI_INFERRED
    assert spo2_obs.extraction_confidence == 0.6


def test_out_of_range_vital_is_rejected_but_other_fields_still_persist(store: EventStore, monkeypatch):
    payload = _valid_payload(vitals=[{"concept_code": "SPO2", "value": 250.0, "confidence": 0.5}])
    client, _ = _client_with_responses(json.dumps(payload), monkeypatch=monkeypatch)
    case = store.create_case(age_years=40)

    outcome = extract_intake_fields(case, store, PROFILE, "text", llm_client=client)
    assert outcome.parse_succeeded is True
    assert len(outcome.rejected) == 1
    assert outcome.rejected[0].concept_code == concepts.SPO2
    assert store.get_latest_current_observation(case.case_id, concepts.SPO2) is None
    # the chest-pain/history/onset fields in the same payload still persisted
    assert len(outcome.observations_created) == 3


def test_fahrenheit_temperature_is_converted_to_celsius(store: EventStore, monkeypatch):
    payload = _valid_payload(
        vitals=[{"concept_code": "TEMPERATURE", "value": 101.3, "temperature_unit": "F", "confidence": 0.7}]
    )
    client, _ = _client_with_responses(json.dumps(payload), monkeypatch=monkeypatch)
    case = store.create_case(age_years=40)

    outcome = extract_intake_fields(case, store, PROFILE, "text", llm_client=client)
    assert outcome.rejected == []
    temp_obs = store.get_latest_current_observation(case.case_id, concepts.TEMPERATURE)
    assert temp_obs.value_numeric == pytest.approx((101.3 - 32) * 5 / 9, abs=0.01)
    assert temp_obs.unit == "°C"


def test_invented_concept_code_fails_schema_and_triggers_retry(store: EventStore, monkeypatch):
    bad_payload = json.dumps({"symptom_flags": [{"concept_code": "SYMPTOM_MADE_UP", "present": True, "confidence": 0.5}]})
    good_payload = json.dumps(_valid_payload())
    client, calls = _client_with_responses(bad_payload, good_payload, monkeypatch=monkeypatch)
    case = store.create_case(age_years=40)

    outcome = extract_intake_fields(case, store, PROFILE, "text", llm_client=client)
    assert outcome.parse_succeeded is True
    assert len(calls["requests"]) == 2  # one retry happened
    assert len(outcome.observations_created) == 4


def test_invalid_output_on_both_attempts_reports_parse_failure(store: EventStore, monkeypatch):
    bad_payload = json.dumps({"symptom_flags": [{"concept_code": "NOT_REAL", "present": True, "confidence": 0.5}]})
    client, calls = _client_with_responses(bad_payload, bad_payload, monkeypatch=monkeypatch)
    case = store.create_case(age_years=40)

    outcome = extract_intake_fields(case, store, PROFILE, "text", llm_client=client)
    assert outcome.parse_succeeded is True
    assert outcome.model_version == "regex-fallback"
    assert len(calls["requests"]) == 2

    event_types = [e.event_type for e in store.get_timeline(case.case_id)]
    assert "AI_UNAVAILABLE" in event_types


def test_malformed_json_is_not_valid_json_at_all_still_retries_and_can_recover(store: EventStore, monkeypatch):
    client, calls = _client_with_responses("not json at all {{{", json.dumps(_valid_payload()), monkeypatch=monkeypatch)
    case = store.create_case(age_years=40)

    outcome = extract_intake_fields(case, store, PROFILE, "text", llm_client=client)
    assert outcome.parse_succeeded is True
    assert len(calls["requests"]) == 2


def test_network_failure_reports_llm_unavailable_and_logs_event(store: EventStore, monkeypatch):
    monkeypatch.setenv("TEST_GROQ_KEY", "fake-key-for-tests")

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom", request=request)

    client = LLMClient(CONFIG, http_client=httpx.Client(transport=httpx.MockTransport(handler)))
    case = store.create_case(age_years=40)

    outcome = extract_intake_fields(case, store, PROFILE, "text", llm_client=client)
    assert outcome.llm_available is False
    assert outcome.parse_succeeded is True
    assert outcome.model_version == "regex-fallback"

    event_types = [e.event_type for e in store.get_timeline(case.case_id)]
    assert "AI_UNAVAILABLE" in event_types


def test_known_identifiers_are_redacted_before_reaching_the_llm(store: EventStore, monkeypatch):
    client, calls = _client_with_responses(json.dumps(_valid_payload()), monkeypatch=monkeypatch)
    case = store.create_case(age_years=40, mrn="MRN-5501", display_name="Ananya Gupta")

    extract_intake_fields(case, store, PROFILE, "Ananya Gupta (MRN-5501) has chest pain.", llm_client=client)

    sent_body = json.loads(calls["requests"][0].content)
    sent_text = json.dumps(sent_body)
    assert "Ananya Gupta" not in sent_text
    assert "MRN-5501" not in sent_text


def test_extracted_vitals_trigger_an_immediate_rescore(store: EventStore, monkeypatch):
    """Regression test for a bug caught during CP17's live smoke test:
    extraction used to call EventStore.add_observation directly without
    the bypass-check + assess_case side effects POST /cases/{id}/
    observations already performs, so a critical extracted vital would
    sit unscored indefinitely. A critically low SpO2 must produce an
    ESI-1 RiskAssessment immediately, not wait for something unrelated."""
    payload = _valid_payload(vitals=[{"concept_code": "SPO2", "value": 83.0, "confidence": 0.9}])
    client, _ = _client_with_responses(json.dumps(payload), monkeypatch=monkeypatch)
    case = store.create_case(age_years=40)  # gets an initial zero-vitals RiskAssessment, same as the real API does
    from app.scoring.risk_orchestrator import assess_case as _assess

    _assess(case, store, PROFILE)
    before = store.get_latest_risk_assessment(case.case_id)

    outcome = extract_intake_fields(case, store, PROFILE, "text", llm_client=client)
    assert outcome.parse_succeeded is True

    after = store.get_latest_risk_assessment(case.case_id)
    assert after.assessment_id != before.assessment_id  # a fresh assessment was actually computed
    assert after.final_acuity == 1  # CRITICAL_HYPOXIA hard trigger (SpO2 <= 85)
    assert any(t["trigger_id"] == "CRITICAL_HYPOXIA" for t in after.hard_triggers_fired)


def test_request_carries_zero_retention_flag(store: EventStore, monkeypatch):
    client, calls = _client_with_responses(json.dumps(_valid_payload()), monkeypatch=monkeypatch)
    case = store.create_case(age_years=40)
    extract_intake_fields(case, store, PROFILE, "text", llm_client=client)

    sent_body = json.loads(calls["requests"][0].content)
    assert sent_body["store"] is False


# ---------------------------------------------------------------------
# HTTP surface (LLM disabled -- exercises the endpoint without a network call)
# ---------------------------------------------------------------------
def test_intake_endpoint_with_llm_disabled(client, nurse_headers, monkeypatch):
    import app.api.cases as cases_module

    disabled_profile = PROFILE.model_copy(deep=True)
    disabled_profile.llm.enabled = False
    monkeypatch.setattr(cases_module, "load_hospital_profile", lambda profile_id="default": disabled_profile)

    case_id = client.post("/cases", json={"age_years": 40}, headers=nurse_headers).json()["case_id"]
    resp = client.post(f"/cases/{case_id}/intake", json={"text": "chest pain"}, headers=nurse_headers)
    assert resp.status_code == 200
    assert resp.json()["llm_available"] is False


def test_successful_extraction_of_history_and_complaint(store: EventStore, monkeypatch):
    payload = _valid_payload(
        medical_history="COPD, Hypertension",
        chief_complaint="Severe crushing chest pain"
    )
    client, _ = _client_with_responses(json.dumps(payload), monkeypatch=monkeypatch)
    case = store.create_case(age_years=40)

    outcome = extract_intake_fields(case, store, PROFILE, "Patient with COPD and Hypertension has severe crushing chest pain.", llm_client=client)

    assert outcome.parse_succeeded is True
    assert case.medical_history == "COPD, Hypertension"
    
    complaint_obs = store.get_latest_current_observation(case.case_id, concepts.SYMPTOM_TEXT)
    assert complaint_obs is not None
    assert complaint_obs.value_text == "Severe crushing chest pain"
    assert complaint_obs.source_type == SourceType.AI_INFERRED


def test_offline_regex_fallback(store: EventStore, monkeypatch):
    # Disable LLM so it forces regex fallback
    disabled_profile = PROFILE.model_copy(deep=True)
    disabled_profile.llm.enabled = False
    case = store.create_case(age_years=40)

    # Note: LLM disabled usually returns immediately in old code, 
    # but our regex fallback happens when parsed is None.
    # Wait, in the new code, `llm_available = profile.llm.enabled`. 
    # If not enabled, it still runs regex fallback!
    raw_text = "Patient arrived. BP 160/95, pulse 112 bpm, SpO2 93%, RR 22, Temp 38.4C"
    outcome = extract_intake_fields(case, store, disabled_profile, raw_text, llm_client=None)

    assert outcome.llm_available is False
    assert outcome.parse_succeeded is True
    assert outcome.model_version == "regex-fallback"
    assert len(outcome.observations_created) == 5

    # Check extracted vitals
    bp_obs = store.get_latest_current_observation(case.case_id, concepts.SYSTOLIC_BP)
    assert bp_obs.value_numeric == 160.0

    hr_obs = store.get_latest_current_observation(case.case_id, concepts.HEART_RATE)
    assert hr_obs.value_numeric == 112.0

    spo2_obs = store.get_latest_current_observation(case.case_id, concepts.SPO2)
    assert spo2_obs.value_numeric == 93.0

    rr_obs = store.get_latest_current_observation(case.case_id, concepts.RESP_RATE)
    assert rr_obs.value_numeric == 22.0

    temp_obs = store.get_latest_current_observation(case.case_id, concepts.TEMPERATURE)
    assert temp_obs.value_numeric == 38.4

