"""
Tests for the Phase 10.2 Privacy & Redaction Layer (CP16): text-level
redaction/rehydration, the redacted case snapshot, and the zero-retention-
enforced LLM gateway. No LLM call is made anywhere here -- this checkpoint
is entirely "the gatekeeper before the gates".
"""
import pytest
from pydantic import ValidationError

from app.config.hospital_profile import load_hospital_profile
from app.models.enums import MeasurementStatus, ReliabilityTier, SourceType, ValueType
from app.privacy.llm_gateway import LLMClientConfig, prepare_llm_request
from app.privacy.redaction import redact_text
from app.privacy.snapshot import build_redacted_snapshot
from app.scoring import concepts
from app.scoring.risk_orchestrator import assess_case
from app.store.event_store import EventStore
from app.timeutil import utcnow

PROFILE = load_hospital_profile("default")


# ---------------------------------------------------------------------
# Text-level redaction
# ---------------------------------------------------------------------
def test_known_identifiers_are_scrubbed_verbatim():
    result = redact_text(
        "Patient Priya Sharma, MRN AB1234XY, says she feels dizzy.",
        known_identifiers={"NAME": "Priya Sharma", "MRN": "AB1234XY"},
    )
    assert "Priya Sharma" not in result.redacted_text
    assert "AB1234XY" not in result.redacted_text
    assert result.token_map  # something was recorded


def test_phone_and_email_are_redacted():
    result = redact_text("Call me on 9876543210 or reach my son at son@example.com")
    assert "9876543210" not in result.redacted_text
    assert "son@example.com" not in result.redacted_text


def test_alphanumeric_id_shaped_token_is_redacted():
    result = redact_text("My old hospital ID was MH7788221 last year.")
    assert "MH7788221" not in result.redacted_text


def test_plain_clinical_text_with_no_pii_is_left_alone():
    text = "Patient reports chest pain and mild breathlessness since this morning."
    result = redact_text(text)
    assert result.redacted_text == text
    assert result.token_map == {}


def test_none_and_empty_text_are_handled():
    assert redact_text(None).redacted_text == ""
    assert redact_text("").redacted_text == ""


def test_rehydrate_reverses_redaction_exactly():
    original = "Contact Priya Sharma on 9876543210 about her results."
    result = redact_text(original, known_identifiers={"NAME": "Priya Sharma"})
    assert result.rehydrate(result.redacted_text) == original


def test_repeated_identifier_gets_a_stable_but_distinct_token_each_occurrence():
    result = redact_text(
        "Priya Sharma called. Priya Sharma says she feels better.",
        known_identifiers={"NAME": "Priya Sharma"},
    )
    assert "Priya Sharma" not in result.redacted_text
    assert result.rehydrate(result.redacted_text) == (
        "Priya Sharma called. Priya Sharma says she feels better."
    )


# ---------------------------------------------------------------------
# Redacted case snapshot
# ---------------------------------------------------------------------
def _add_symptom_text(store, case_id, text, observed_at=None):
    store.add_observation(
        case_id=case_id, concept_code=concepts.SYMPTOM_TEXT, value=text, value_type=ValueType.TEXT,
        source_type=SourceType.PATIENT, reliability_tier=ReliabilityTier.PATIENT_REPORTED,
        measurement_status=MeasurementStatus.MEASURED, observed_at=observed_at or utcnow(),
    )


def test_snapshot_excludes_identifying_fields_by_construction():
    from app.privacy.snapshot import RedactedCaseSnapshot

    field_names = set(RedactedCaseSnapshot.model_fields.keys())
    assert field_names.isdisjoint({"case_id", "mrn", "display_name", "date_of_birth", "sex"})


def test_snapshot_redacts_free_text_but_keeps_structured_vitals(store: EventStore):
    case = store.create_case(age_years=45, mrn="MRN-99120", display_name="Priya Sharma")
    _add_symptom_text(store, case.case_id, "Priya Sharma reports chest pain, call her son on 9876543210.")
    store.add_observation(
        case_id=case.case_id, concept_code=concepts.HEART_RATE, value=110.0, value_type=ValueType.NUMERIC,
        source_type=SourceType.DEVICE, reliability_tier=ReliabilityTier.MACHINE_MEASURED,
        measurement_status=MeasurementStatus.MEASURED, observed_at=utcnow(),
    )

    snapshot, token_map = build_redacted_snapshot(case, store, PROFILE)

    text_obs = next(o for o in snapshot.observations if o.concept_code == concepts.SYMPTOM_TEXT)
    assert "Priya Sharma" not in text_obs.value
    assert "9876543210" not in text_obs.value
    assert token_map  # something was recorded server-side

    hr_obs = next(o for o in snapshot.observations if o.concept_code == concepts.HEART_RATE)
    assert hr_obs.value == 110.0  # structured clinical data passes through untouched

    assert snapshot.age_years == 45
    assert not hasattr(snapshot, "mrn")
    assert not hasattr(snapshot, "display_name")


def test_snapshot_includes_risk_summary_when_assessed(store: EventStore):
    case = store.create_case(age_years=40)
    assess_case(case, store, PROFILE)
    snapshot, _ = build_redacted_snapshot(case, store, PROFILE)
    assert snapshot.latest_risk_summary is not None
    assert snapshot.latest_risk_summary.final_acuity is not None


def test_snapshot_risk_summary_strips_internal_observation_ids(store: EventStore):
    case = store.create_case(age_years=40)
    store.add_observation(
        case_id=case.case_id, concept_code=concepts.HEART_RATE, value=90.0, value_type=ValueType.NUMERIC,
        source_type=SourceType.DEVICE, reliability_tier=ReliabilityTier.MACHINE_MEASURED,
        measurement_status=MeasurementStatus.MEASURED, observed_at=utcnow(),
    )
    assess_case(case, store, PROFILE)
    snapshot, _ = build_redacted_snapshot(case, store, PROFILE)
    for component in snapshot.latest_risk_summary.rule_component_breakdown:
        assert "observation_id" not in component


def test_snapshot_risk_summary_is_none_before_any_assessment(store: EventStore):
    case = store.create_case(age_years=40)
    snapshot, _ = build_redacted_snapshot(case, store, PROFILE)
    assert snapshot.latest_risk_summary is None


# ---------------------------------------------------------------------
# Zero-retention-enforced LLM gateway
# ---------------------------------------------------------------------
def test_llm_config_rejects_non_zero_retention():
    with pytest.raises(ValidationError):
        LLMClientConfig(provider="acme", model="acme-1", api_key_env_var="ACME_API_KEY", zero_retention=False)


def test_llm_config_defaults_to_zero_retention():
    config = LLMClientConfig(provider="acme", model="acme-1", api_key_env_var="ACME_API_KEY")
    assert config.zero_retention is True


def test_prepare_llm_request_never_carries_the_token_map_on_the_request_itself(store: EventStore):
    case = store.create_case(age_years=45, mrn="MRN-1", display_name="Priya Sharma")
    _add_symptom_text(store, case.case_id, "Priya Sharma feels breathless.")
    config = LLMClientConfig(provider="acme", model="acme-1", api_key_env_var="ACME_API_KEY")

    request, token_map = prepare_llm_request(case, store, PROFILE, config)

    assert "token_map" not in request.model_dump()
    assert "Priya Sharma" not in str(request.model_dump())
    assert token_map  # returned separately, for server-side rehydration only
    assert request.config.zero_retention is True
