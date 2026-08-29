"""
Tests for the Phase 3.2/3.6 LLM Explanation Engine (CP17): the
deterministic fallback, the grounding check (both directions), and the
Phase 9.5 failure modes. All network calls are mocked -- no real API call
is made.
"""
import json

import httpx

from app.config.hospital_profile import load_hospital_profile
from app.llm.client import LLMClient
from app.llm.explanation import generate_explanation
from app.models.enums import MeasurementStatus, ReliabilityTier, SourceType, ValueType
from app.privacy.llm_gateway import LLMClientConfig
from app.scoring import concepts
from app.scoring.risk_orchestrator import assess_case
from app.store.event_store import EventStore
from app.timeutil import utcnow

PROFILE = load_hospital_profile("default")
CONFIG = LLMClientConfig(provider="groq", model="test-model", api_key_env_var="TEST_GROQ_KEY_2")


def _client_returning(text: str, monkeypatch) -> LLMClient:
    monkeypatch.setenv("TEST_GROQ_KEY_2", "fake-key-for-tests")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": text}}]})

    return LLMClient(CONFIG, http_client=httpx.Client(transport=httpx.MockTransport(handler)))


def _assessed_case(store: EventStore, *, rr=25, spo2=91, hr=95, sbp=115, temp=37.0):
    case = store.create_case(age_years=40)
    for code, val in ((concepts.RESP_RATE, rr), (concepts.SPO2, spo2), (concepts.HEART_RATE, hr), (concepts.SYSTOLIC_BP, sbp), (concepts.TEMPERATURE, temp)):
        store.add_observation(
            case_id=case.case_id, concept_code=code, value=val, value_type=ValueType.NUMERIC,
            source_type=SourceType.DEVICE, reliability_tier=ReliabilityTier.MACHINE_MEASURED,
            measurement_status=MeasurementStatus.MEASURED, observed_at=utcnow(),
        )
    store.add_observation(
        case_id=case.case_id, concept_code=concepts.CONSCIOUSNESS_LEVEL, value="ALERT", value_type=ValueType.CODED,
        source_type=SourceType.DEVICE, reliability_tier=ReliabilityTier.MACHINE_MEASURED,
        measurement_status=MeasurementStatus.MEASURED, observed_at=utcnow(),
    )
    store.add_observation(
        case_id=case.case_id, concept_code=concepts.SUPPLEMENTAL_OXYGEN, value=False, value_type=ValueType.BOOLEAN,
        source_type=SourceType.DEVICE, reliability_tier=ReliabilityTier.MACHINE_MEASURED,
        measurement_status=MeasurementStatus.MEASURED, observed_at=utcnow(),
    )
    assess_case(case, store, PROFILE)
    return case


def test_no_assessment_yet_returns_a_safe_placeholder(store: EventStore):
    case = store.create_case(age_years=40)
    result = generate_explanation(case, store, PROFILE)
    assert result.fallback_used is True
    assert result.fallback_reason == "NO_ASSESSMENT_YET"


def test_llm_disabled_uses_deterministic_explanation(store: EventStore):
    disabled_profile = PROFILE.model_copy(deep=True)
    disabled_profile.llm.enabled = False
    case = _assessed_case(store)

    result = generate_explanation(case, store, disabled_profile)
    assert result.fallback_used is True
    assert result.fallback_reason == "LLM_DISABLED"
    assert "ESI" in result.text  # the deterministic template mentions the level


def test_grounded_llm_explanation_is_used_as_is(store: EventStore, monkeypatch):
    case = _assessed_case(store)
    ra = store.get_latest_risk_assessment(case.case_id)
    # Only mentions the acuity level -- guaranteed to be a reference number.
    llm_text = f"This patient was assigned ESI level {ra.final_acuity} based on the recorded vitals."
    client = _client_returning(llm_text, monkeypatch)

    result = generate_explanation(case, store, PROFILE, llm_client=client)
    assert result.fallback_used is False
    assert result.grounded is True
    assert result.text == llm_text


def test_ungrounded_llm_explanation_is_discarded_and_falls_back(store: EventStore, monkeypatch):
    case = _assessed_case(store)
    # 9999 never appears anywhere in the structured input -- must be rejected.
    llm_text = "This patient's temperature was 9999 degrees, which is very concerning."
    client = _client_returning(llm_text, monkeypatch)

    result = generate_explanation(case, store, PROFILE, llm_client=client)
    assert result.fallback_used is True
    assert result.fallback_reason == "GROUNDING_CHECK_FAILED"
    assert result.text != llm_text

    event_types = [e.event_type for e in store.get_timeline(case.case_id)]
    assert "AI_UNAVAILABLE" in event_types


def test_llm_network_failure_falls_back_and_logs_event(store: EventStore, monkeypatch):
    monkeypatch.setenv("TEST_GROQ_KEY_2", "fake-key-for-tests")

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom", request=request)

    client = LLMClient(CONFIG, http_client=httpx.Client(transport=httpx.MockTransport(handler)))
    case = _assessed_case(store)

    result = generate_explanation(case, store, PROFILE, llm_client=client)
    assert result.fallback_used is True
    assert result.fallback_reason == "LLM_UNAVAILABLE"

    event_types = [e.event_type for e in store.get_timeline(case.case_id)]
    assert "AI_UNAVAILABLE" in event_types


def test_deterministic_explanation_never_invents_content(store: EventStore):
    """The fallback path (used directly here via LLM-disabled) must only
    ever narrate what's actually in rule_component_breakdown -- no
    diagnosis, no treatment suggestion vocabulary."""
    disabled_profile = PROFILE.model_copy(deep=True)
    disabled_profile.llm.enabled = False
    case = _assessed_case(store)

    result = generate_explanation(case, store, disabled_profile)
    forbidden_terms = ["diagnosis", "recommend", "treat", "prescribe"]
    assert not any(term in result.text.lower() for term in forbidden_terms)


# ---------------------------------------------------------------------
# HTTP surface
# ---------------------------------------------------------------------
def test_explanation_endpoint(client, monkeypatch):
    # LLM disabled here so this HTTP-level test exercises the deterministic
    # fallback path only -- fast, offline, no real network call.
    import app.api.cases as cases_module

    disabled_profile = PROFILE.model_copy(deep=True)
    disabled_profile.llm.enabled = False
    monkeypatch.setattr(cases_module, "load_hospital_profile", lambda profile_id="default": disabled_profile)

    case_id = client.post("/cases", json={"age_years": 40}).json()["case_id"]
    client.get("/queue")  # backfills an initial assessment

    resp = client.get(f"/cases/{case_id}/explanation")
    assert resp.status_code == 200
    body = resp.json()
    assert "text" in body
    assert body["fallback_used"] is True
    assert body["fallback_reason"] == "LLM_DISABLED"
