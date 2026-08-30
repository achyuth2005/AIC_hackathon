"""
Redacted case snapshot (Phase 10.2): the de-identified view of a case that
a future LLM-calling engine (Intake, Explanation -- both explicitly
deferred pending a user-supplied API key) is required to build its prompt
from. Nothing here calls an LLM; this is the shape of "what the LLM is
allowed to see", assembled once so every future caller gets the same
minimisation applied the same way rather than each hand-rolling it.

What's INCLUDED: age (not date of birth -- Phase 10.2's own example is
"a 67-year-old patient"), arrival mode, the free-text medical_history
field (Medical History feature -- redacted via app/privacy/redaction.py
before inclusion, exactly like SYMPTOM_TEXT below, since a nurse-entered
history field carries the same risk of an incidentally-typed name), every
current clinical observation (structured vitals/history/symptom-flags are
not patient- identifying; a free-text SYMPTOM_TEXT value is redacted via
app/privacy/redaction.py before inclusion), and the latest RiskAssessment
summary (acuity/confidence/component breakdown -- system output, not PII,
and exactly what an Explanation engine exists to narrate).

What's EXCLUDED, unconditionally: case_id, mrn, display_name,
date_of_birth, sex, and every Observation's source_id/observation_id.
Sex and exact DOB are excluded on a minimisation basis -- neither is used
by any scoring engine in this codebase, so neither is "needed for the
clinical purpose" Phase 10.2 tests against. case_id is withheld so an
external LLM call carries nothing that could be used to correlate a
prompt back to a specific record; the CALLING code is responsible for
keeping that correlation locally, never inside the prompt itself.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from app.config.hospital_profile import HospitalProfile
from app.models.case import Case
from app.models.enums import ArrivalMode
from app.scoring import concepts
from app.store.event_store import EventStore

from app.privacy.redaction import RedactionResult, redact_text


class RedactedObservation(BaseModel):
    concept_code: str
    value: Any
    unit: Optional[str] = None
    observed_at: datetime


class RedactedRiskSummary(BaseModel):
    final_acuity: int
    confidence_band: Optional[str]
    should_abstain: bool
    rule_component_breakdown: List[Dict[str, Any]]
    hard_triggers_fired: List[Dict[str, Any]]


class RedactedCaseSnapshot(BaseModel):
    """This -- and only this -- is what a future LLM-calling engine may
    serialise into a prompt. No field on this model can carry a name, an
    MRN, a DOB, or an internal case_id; see this module's own docstring
    for why each was excluded."""
    age_years: Optional[int]
    arrival_mode: ArrivalMode
    medical_history: Optional[str]
    observations: List[RedactedObservation]
    latest_risk_summary: Optional[RedactedRiskSummary]


def _strip_observation_id(component: Dict[str, Any]) -> Dict[str, Any]:
    """rule_component_breakdown entries (app/scoring/models.py's
    ScoreComponent) carry an internal observation_id UUID -- withheld here
    for the same minimisation reason case_id is withheld: it's an internal
    correlation key an external LLM has no clinical need for."""
    return {k: v for k, v in component.items() if k != "observation_id"}


def build_redacted_snapshot(
    case: Case, store: EventStore, profile: HospitalProfile
) -> tuple[RedactedCaseSnapshot, Dict[str, str]]:
    """Returns (snapshot, token_map). `token_map` must be kept server-side
    only -- it is what app/privacy/redaction.py's RedactionResult.rehydrate
    uses to turn a returned LLM response's tokens back into the original
    free-text content for clinician display; it must never itself be sent
    anywhere."""
    known_identifiers = {"NAME": case.display_name, "MRN": case.mrn}
    combined_token_map: Dict[str, str] = {}

    redacted_medical_history = case.medical_history
    if redacted_medical_history:
        history_result: RedactionResult = redact_text(redacted_medical_history, known_identifiers=known_identifiers)
        redacted_medical_history = history_result.redacted_text
        combined_token_map.update(history_result.token_map)

    observations: List[RedactedObservation] = []
    for obs in store.get_current_observations(case.case_id):
        value = obs.value
        if obs.concept_code == concepts.SYMPTOM_TEXT and isinstance(value, str):
            result: RedactionResult = redact_text(value, known_identifiers=known_identifiers)
            value = result.redacted_text
            combined_token_map.update(result.token_map)
        observations.append(
            RedactedObservation(concept_code=obs.concept_code, value=value, unit=obs.unit, observed_at=obs.observed_at)
        )

    latest = store.get_latest_risk_assessment(case.case_id)
    risk_summary = (
        RedactedRiskSummary(
            final_acuity=latest.final_acuity,
            confidence_band=latest.confidence_band.value if latest.confidence_band else None,
            should_abstain=latest.should_abstain,
            rule_component_breakdown=[_strip_observation_id(c) for c in latest.rule_component_breakdown],
            hard_triggers_fired=latest.hard_triggers_fired,
        )
        if latest is not None
        else None
    )

    snapshot = RedactedCaseSnapshot(
        age_years=case.age_years,
        arrival_mode=case.arrival_mode,
        medical_history=redacted_medical_history,
        observations=observations,
        latest_risk_summary=risk_summary,
    )
    return snapshot, combined_token_map
