"""
LLM Explanation Engine (Phase 3.2, 3.6, CP17): "Explanation and summary
-> LLM, evidence-grounded. Constrained to narrate only structured facts
passed in the prompt. No new clinical content." And 3.6: "The LLM's
correct position is after the level exists, generating the human-readable
explanation from the structured evidence that produced it."

This engine NEVER computes, changes, or questions final_acuity -- it is
called strictly AFTER a RiskAssessment already exists, reads it read-only,
and produces prose. Nothing downstream consumes this engine's output as
an input to any decision; a caller that fed an explanation string back
into scoring would be violating this module's whole reason for existing.

Grounding is not just a prompt instruction (an LLM can ignore those) --
it is checked deterministically: every standalone number in the generated
explanation must match a number that was actually present in the
structured input (an acuity level, a component's raw_value, the
confidence score). Any number that doesn't match anything in the input
means the explanation is discarded outright and replaced with a fully
deterministic, template-built explanation from the same structured facts
-- never shown to a clinician as "the LLM's explanation" if it isn't
actually grounded in what was given to it. That deterministic template is
also Phase 9.5's own stated failure-mode behaviour ("explanations
replaced by the rule component breakdown, which is arguably clearer
anyway") and is what runs whenever the LLM is disabled or unavailable, so
there is always an explanation, generated the same way whether the LLM
is reachable or not.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from app.config.hospital_profile import HospitalProfile
from app.models.case import Case
from app.privacy.snapshot import RedactedRiskSummary, build_redacted_snapshot
from app.store.event_store import EventStore
from app.timeutil import utcnow
from app.llm.client import LLMClient, LLMUnavailableError

_NUMBER_PATTERN = re.compile(r"-?\d+(?:\.\d+)?")


class ExplanationResult(BaseModel):
    text: str
    grounded: bool  # True only if an LLM explanation was generated AND passed the grounding check
    fallback_used: bool
    fallback_reason: Optional[str] = None
    model_version: Optional[str] = None
    generated_at: datetime


def _deterministic_explanation(summary: RedactedRiskSummary) -> str:
    """Phase 9.5's own fallback: narrate the rule_component_breakdown
    directly. No LLM involved at all -- always available, always
    grounded by construction (it IS the structured facts, verbatim)."""
    scored = [c for c in summary.rule_component_breakdown if not c.get("is_missing")]
    missing = [c for c in summary.rule_component_breakdown if c.get("is_missing")]

    parts = []
    if scored:
        detail = "; ".join(
            f"{c['label']} scored {c['points']} point(s)" + (f" ({c['raw_value']}{c.get('unit') or ''})" if c.get("raw_value") is not None else "")
            for c in scored
        )
        parts.append(f"Assessed as ESI {summary.final_acuity}. {detail}.")
    else:
        parts.append(f"Assessed as ESI {summary.final_acuity} with no scoreable vitals recorded.")

    if summary.hard_triggers_fired:
        labels = ", ".join(t["label"] for t in summary.hard_triggers_fired)
        parts.append(f"Hard trigger(s) fired: {labels}.")

    if missing:
        labels = ", ".join(c["label"] for c in missing)
        parts.append(f"Missing/stale: {labels}.")

    if summary.should_abstain:
        parts.append("Confidence was too low for an automatic recommendation; a nurse assessment is required.")
    elif summary.confidence_band:
        parts.append(f"Confidence band: {summary.confidence_band}.")

    return " ".join(parts)


def _reference_numbers(summary: RedactedRiskSummary) -> List[float]:
    """Every number that legitimately appears in the structured input --
    what a grounded explanation is allowed to mention."""
    numbers = [float(summary.final_acuity)]
    for component in summary.rule_component_breakdown:
        if isinstance(component.get("raw_value"), (int, float)):
            numbers.append(float(component["raw_value"]))
        if isinstance(component.get("points"), (int, float)):
            numbers.append(float(component["points"]))
    return numbers


def _is_grounded(explanation_text: str, summary: RedactedRiskSummary) -> bool:
    reference = _reference_numbers(summary)
    for match in _NUMBER_PATTERN.findall(explanation_text):
        value = float(match)
        if not any(abs(value - ref) < 0.05 for ref in reference):
            return False
    return True


_SYSTEM_PROMPT = """You write a short, plain-language explanation of an emergency department triage decision \
for a clinician to read. You are given ONLY a structured JSON summary of the facts that produced the \
decision. Write 2-4 sentences explaining why this acuity level was assigned, using ONLY the numbers, \
labels, and facts present in that JSON. Do not introduce any clinical detail, number, symptom, diagnosis \
or treatment suggestion that is not present in the input. Do not suggest a diagnosis. Do not suggest a \
treatment. Do not say the level should be different from what is given. Output plain text only, no JSON, \
no markdown."""


def generate_explanation(
    case: Case, store: EventStore, profile: HospitalProfile, *, llm_client: Optional[LLMClient] = None
) -> ExplanationResult:
    now = utcnow()
    snapshot, _ = build_redacted_snapshot(case, store, profile)

    if snapshot.latest_risk_summary is None:
        return ExplanationResult(
            text="No assessment has been computed for this case yet.",
            grounded=True, fallback_used=True, fallback_reason="NO_ASSESSMENT_YET", generated_at=now,
        )

    summary = snapshot.latest_risk_summary

    if not profile.llm.enabled:
        return ExplanationResult(
            text=_deterministic_explanation(summary), grounded=True, fallback_used=True,
            fallback_reason="LLM_DISABLED", generated_at=now,
        )

    from app.privacy.llm_gateway import LLMClientConfig

    client = llm_client or LLMClient(
        LLMClientConfig(provider=profile.llm.provider, model=profile.llm.model, api_key_env_var=profile.llm.api_key_env_var),
        timeout=profile.llm.request_timeout_seconds,
    )

    try:
        raw_text = client.complete_text(
            system_prompt=_SYSTEM_PROMPT,
            user_prompt=f"Structured facts:\n{summary.model_dump_json(indent=2)}",
        )
    except LLMUnavailableError as exc:
        store.append_event(
            case_id=case.case_id, event_type="AI_UNAVAILABLE", payload={"engine": "EXPLANATION", "reason": str(exc)}
        )
        store.db.commit()
        return ExplanationResult(
            text=_deterministic_explanation(summary), grounded=True, fallback_used=True,
            fallback_reason="LLM_UNAVAILABLE", generated_at=now,
        )

    if not _is_grounded(raw_text, summary):
        store.append_event(
            case_id=case.case_id, event_type="AI_UNAVAILABLE",
            payload={"engine": "EXPLANATION", "reason": "Generated explanation failed the grounding check."},
        )
        store.db.commit()
        return ExplanationResult(
            text=_deterministic_explanation(summary), grounded=False, fallback_used=True,
            fallback_reason="GROUNDING_CHECK_FAILED", model_version=client.config.model, generated_at=now,
        )

    return ExplanationResult(
        text=raw_text.strip(), grounded=True, fallback_used=False, model_version=client.config.model, generated_at=now,
    )
