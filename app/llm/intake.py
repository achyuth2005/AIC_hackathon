"""
LLM Intake Engine (Phase 3.2, CP17): "Clinical entity extraction from
free text -> LLM, schema-constrained. Force structured JSON output and
validate it against a schema; reject and retry rather than accept
malformed output." Paired with: "Mapping extracted terms to coded
concepts -> Deterministic lookup ... prevents invented concepts entering
the clinical record" and "Converting text to numerical model features ->
Deterministic code ... values pass through range checks."

Responsibility split, exactly as those three rows assign it:
  1. LLM: read free text, propose which of a FIXED set of concepts are
     present and what values were stated. It cannot propose a concept
     outside that set -- IntakeExtractionSchema's `Literal` typing makes
     an out-of-vocabulary concept_code a schema validation failure, not
     a value this code has to separately reject. This is "a controlled
     terminology table decides" implemented as the schema itself, not a
     second matching step after the fact.
  2. Deterministic code (this module): range-checks every numeric value,
     normalises temperature units, and is the ONLY thing that ever calls
     EventStore.add_observation. The LLM's output never reaches the
     patient record un-validated.

Every accepted field is persisted as SourceType.AI_INFERRED /
ReliabilityTier.AI_INFERRED (tier 4, the lowest) -- not because the
extraction is untrustworthy in some special sense, but because that is
exactly what Phase 4.2's source/reliability vocabulary is FOR, and it has
a real, automatic consequence already built at CP5: the Confidence Engine
applies its largest per-component reliability penalty to tier-4 inputs, so
an LLM-extracted vital or symptom flag legitimately lowers confidence
compared to a device reading, with zero new code in confidence.py.

This engine never assigns or adjusts acuity ITSELF -- it only adds
Observations. It does, however, trigger the exact same re-scoring
EventStore.add_observation's own callers already trigger (see the
"if observation_ids:" block below): the Emergency Bypass check and a
fresh assess_case() call, mirroring POST /cases/{id}/observations
(app/api/cases.py) exactly. There is no path from LLM output to acuity
that does not pass through NEWS2/PEWS/hard-triggers/ML/min() exactly as
normal -- this engine just makes sure that pipeline actually runs on the
data it adds, the same as it would for a nurse-typed observation.
"""
from __future__ import annotations

import json
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, ValidationError

from app.bypass.engine import evaluate_and_activate
from app.config.hospital_profile import HospitalProfile
from app.llm.client import LLMClient, LLMUnavailableError
from app.models.case import Case
from app.models.enums import MeasurementStatus, ReliabilityTier, SourceType, ValueType
from app.privacy.redaction import redact_text
from app.scoring import concepts
from app.scoring.risk_orchestrator import assess_case
from app.store.event_store import EventStore
from app.timeutil import utcnow

# Deterministic range checks (Phase 3.2: "values pass through range
# checks and unit normalisation"). Canonical unit per concept; TEMPERATURE
# is the one vital where a lay caller might reasonably state Fahrenheit,
# so it alone carries a unit field in the schema below.
_VITAL_RANGES = {
    concepts.RESP_RATE: (0.0, 100.0),
    concepts.SPO2: (0.0, 100.0),
    concepts.HEART_RATE: (0.0, 300.0),
    concepts.SYSTOLIC_BP: (0.0, 300.0),
    concepts.TEMPERATURE: (25.0, 45.0),  # Celsius
}
_VITAL_UNITS = {
    concepts.RESP_RATE: "breaths/min",
    concepts.SPO2: "%",
    concepts.HEART_RATE: "bpm",
    concepts.SYSTOLIC_BP: "mmHg",
    concepts.TEMPERATURE: "°C",
}

_SYMPTOM_CODES = (concepts.SYMPTOM_CHEST_PAIN, concepts.SYMPTOM_BREATHLESSNESS, concepts.SYMPTOM_ALTERED_CONSCIOUSNESS)
_HISTORY_CODES = (concepts.HISTORY_CARDIAC, concepts.HISTORY_RESPIRATORY, concepts.HISTORY_DIABETES)
_VITAL_CODES = tuple(_VITAL_RANGES.keys())


class ExtractedSymptomFlag(BaseModel):
    concept_code: Literal[_SYMPTOM_CODES]  # type: ignore[valid-type]
    present: bool
    confidence: float = Field(ge=0.0, le=1.0)


class ExtractedHistoryFlag(BaseModel):
    concept_code: Literal[_HISTORY_CODES]  # type: ignore[valid-type]
    present: bool
    confidence: float = Field(ge=0.0, le=1.0)


class ExtractedOnset(BaseModel):
    onset_minutes: float = Field(gt=0)
    confidence: float = Field(ge=0.0, le=1.0)


class ExtractedVital(BaseModel):
    concept_code: Literal[_VITAL_CODES]  # type: ignore[valid-type]
    value: float
    temperature_unit: Optional[Literal["C", "F"]] = None  # only meaningful for TEMPERATURE
    confidence: float = Field(ge=0.0, le=1.0)


class IntakeExtractionSchema(BaseModel):
    """The ONLY shape the LLM's JSON output is accepted in. Anything that
    doesn't parse into this -- an invented concept_code, a missing
    required field, a wrong type -- is a validation failure, triggering
    the retry-once policy in extract_intake_fields(), never a silent
    best-effort partial parse."""
    symptom_flags: List[ExtractedSymptomFlag] = Field(default_factory=list)
    history_flags: List[ExtractedHistoryFlag] = Field(default_factory=list)
    onset: Optional[ExtractedOnset] = None
    vitals: List[ExtractedVital] = Field(default_factory=list)


class RejectedField(BaseModel):
    concept_code: str
    reason: str


class IntakeOutcome(BaseModel):
    llm_available: bool
    parse_succeeded: bool
    reason: Optional[str] = None  # "LLM_DISABLED" | "LLM_UNAVAILABLE" | "PARSE_FAILED_AFTER_RETRY" | None (success)
    observations_created: List[str] = Field(default_factory=list)  # observation_ids
    rejected: List[RejectedField] = Field(default_factory=list)
    model_version: Optional[str] = None


_SYSTEM_PROMPT = f"""You extract structured clinical facts from a single free-text patient/caregiver \
statement for an emergency department intake form. You do not diagnose, advise, or decide anything.

Respond with ONLY a JSON object matching exactly this shape (omit any field/array entry not clearly \
and explicitly stated in the text -- never guess, never infer beyond what is literally said):

{{
  "symptom_flags": [{{"concept_code": one of {list(_SYMPTOM_CODES)}, "present": true, "confidence": 0.0-1.0}}],
  "history_flags": [{{"concept_code": one of {list(_HISTORY_CODES)}, "present": true, "confidence": 0.0-1.0}}],
  "onset": {{"onset_minutes": number, "confidence": 0.0-1.0}} or omit entirely if no onset time is stated,
  "vitals": [{{"concept_code": one of {list(_VITAL_CODES)}, "value": number, \
"temperature_unit": "C" or "F" (TEMPERATURE only, omit otherwise), "confidence": 0.0-1.0}}]
}}

Rules:
- concept_code values MUST be exactly one of the listed strings. Never invent a new one.
- Only include a vital if an explicit number was stated in the text.
- confidence reflects how explicitly/clearly the text stated the fact, not a clinical judgement.
- Output ONLY the JSON object. No other text, no markdown fences."""


def _fahrenheit_to_celsius(value: float) -> float:
    return (value - 32.0) * 5.0 / 9.0


def _validate_and_normalize_vital(vital: ExtractedVital) -> tuple:
    """Returns (accepted_value, unit, reason_if_rejected). Deterministic
    range check + unit normalisation -- Phase 3.2's 'an LLM must never
    emit a number that feeds the risk model unvalidated'."""
    value = vital.value
    if vital.concept_code == concepts.TEMPERATURE and vital.temperature_unit == "F":
        value = _fahrenheit_to_celsius(value)

    low, high = _VITAL_RANGES[vital.concept_code]
    if not (low <= value <= high):
        return None, None, f"value {value} outside plausible range [{low}, {high}] for {vital.concept_code}"
    return value, _VITAL_UNITS[vital.concept_code], None


def extract_intake_fields(
    case: Case, store: EventStore, profile: HospitalProfile, raw_text: str, *, llm_client: Optional[LLMClient] = None
) -> IntakeOutcome:
    """Phase 9.5 failure mode: if the LLM is disabled or unavailable,
    returns immediately with llm_available=False and nothing extracted --
    'structured entry forms replace conversational capture' means the
    caller's normal manual-observation endpoints remain the fallback path;
    this function does not itself provide one."""
    if not profile.llm.enabled:
        return IntakeOutcome(llm_available=False, parse_succeeded=False, reason="LLM_DISABLED")

    client = llm_client or LLMClient(
        _config_from_profile(profile), timeout=profile.llm.request_timeout_seconds
    )

    redacted = redact_text(raw_text, known_identifiers={"NAME": case.display_name, "MRN": case.mrn})

    try:
        parsed, model_version = _call_and_parse(client, redacted.redacted_text)
    except LLMUnavailableError as exc:
        store.append_event(
            case_id=case.case_id, event_type="AI_UNAVAILABLE",
            payload={"engine": "INTAKE", "reason": str(exc)},
        )
        store.db.commit()
        return IntakeOutcome(llm_available=False, parse_succeeded=False, reason="LLM_UNAVAILABLE")

    if parsed is None:
        store.append_event(
            case_id=case.case_id, event_type="AI_UNAVAILABLE",
            payload={"engine": "INTAKE", "reason": "Model output did not match the required schema after one retry."},
        )
        store.db.commit()
        return IntakeOutcome(
            llm_available=True, parse_succeeded=False, reason="PARSE_FAILED_AFTER_RETRY", model_version=model_version
        )

    observation_ids: List[str] = []
    rejected: List[RejectedField] = []
    now = utcnow()

    for flag in parsed.symptom_flags + parsed.history_flags:
        obs = store.add_observation(
            case_id=case.case_id, concept_code=flag.concept_code, value=flag.present, value_type=ValueType.BOOLEAN,
            source_type=SourceType.AI_INFERRED, reliability_tier=ReliabilityTier.AI_INFERRED,
            measurement_status=MeasurementStatus.MEASURED, observed_at=now, extraction_confidence=flag.confidence,
        )
        observation_ids.append(obs.observation_id)

    if parsed.onset is not None:
        obs = store.add_observation(
            case_id=case.case_id, concept_code=concepts.SYMPTOM_ONSET_MINUTES, value=parsed.onset.onset_minutes,
            value_type=ValueType.NUMERIC, source_type=SourceType.AI_INFERRED,
            reliability_tier=ReliabilityTier.AI_INFERRED, measurement_status=MeasurementStatus.MEASURED,
            observed_at=now, extraction_confidence=parsed.onset.confidence,
        )
        observation_ids.append(obs.observation_id)

    for vital in parsed.vitals:
        value, unit, reason = _validate_and_normalize_vital(vital)
        if reason is not None:
            rejected.append(RejectedField(concept_code=vital.concept_code, reason=reason))
            continue
        obs = store.add_observation(
            case_id=case.case_id, concept_code=vital.concept_code, value=value, value_type=ValueType.NUMERIC,
            unit=unit, source_type=SourceType.AI_INFERRED, reliability_tier=ReliabilityTier.AI_INFERRED,
            measurement_status=MeasurementStatus.MEASURED, observed_at=now, extraction_confidence=vital.confidence,
        )
        observation_ids.append(obs.observation_id)

    if observation_ids:
        # Mirrors POST /cases/{id}/observations exactly (app/api/cases.py):
        # a newly-arrived observation re-runs the Emergency Bypass check
        # and re-scores the case, whether it was typed in by a nurse or
        # extracted here. Self-discovered while live-testing this
        # checkpoint: calling EventStore.add_observation directly (as
        # this function does, rather than going through that endpoint)
        # skipped both side effects entirely, so an LLM-extracted SpO2 of
        # 70 would silently sit unscored until something unrelated
        # happened to trigger a rescore. Without this, Phase 5.2's "every
        # waiting patient is continuously re-evaluated against new data"
        # would quietly not hold for this one entry path.
        evaluate_and_activate(case, store, profile)
        assess_case(case, store, profile)

    return IntakeOutcome(
        llm_available=True, parse_succeeded=True, observations_created=observation_ids,
        rejected=rejected, model_version=model_version,
    )


def _call_and_parse(client: LLMClient, redacted_text: str) -> tuple:
    """Phase 3.2: 'reject and retry rather than accept malformed output.'
    One retry, with the validation error fed back to the model, then give
    up and report parse_succeeded=False rather than guessing."""
    user_prompt = f"Patient/caregiver statement:\n\n{redacted_text}"
    raw = client.complete_json(system_prompt=_SYSTEM_PROMPT, user_prompt=user_prompt)
    model_version = client.config.model

    parsed = _try_parse(raw)
    if parsed is not None:
        return parsed, model_version

    retry_prompt = (
        f"{user_prompt}\n\nYour previous response was not valid JSON matching the required schema:\n{raw}\n"
        f"Respond again with ONLY a valid JSON object matching the schema exactly."
    )
    raw_retry = client.complete_json(system_prompt=_SYSTEM_PROMPT, user_prompt=retry_prompt)
    return _try_parse(raw_retry), model_version


def _try_parse(raw: str) -> Optional[IntakeExtractionSchema]:
    try:
        return IntakeExtractionSchema.model_validate(json.loads(raw))
    except (json.JSONDecodeError, ValidationError):
        return None


def _config_from_profile(profile: HospitalProfile):
    from app.privacy.llm_gateway import LLMClientConfig

    return LLMClientConfig(
        provider=profile.llm.provider, model=profile.llm.model, api_key_env_var=profile.llm.api_key_env_var
    )
