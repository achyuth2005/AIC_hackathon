"""
Medical History risk escalation (Medical History feature, Phase 3.3 Layer
4-adjacent): a small, deterministic keyword scan over the free-text
`Case.medical_history` field (app/models/case.py), applied inside the
Clinical Scoring Engine (app/scoring/engine.py) immediately after Layer 4
hard triggers.

This is deliberately NOT a hard trigger (app/scoring/hard_triggers.py): a
hard trigger forces an ABSOLUTE target ESI level off a single vital-sign
reading. This instead RELATIVELY escalates -- one ESI level more urgent
than the vitals alone would produce -- and only when BOTH conditions hold:
  1. the free-text history contains at least one HIGH_RISK_HISTORY_KEYWORDS
     match (COPD, coronary artery disease, heart failure, immunosuppressed,
     ...), and
  2. the vitals are already abnormal (`aggregate_score > 0` -- at least one
     physiological parameter deviated from its normal range).

Requiring condition 2 is deliberate: a high-risk history alone, on
perfectly normal vitals, must not by itself force an escalation -- Phase
3.3's framing is a risk *multiplier* on top of abnormal physiology, not an
unconditional bump for anyone with a chronic condition on their chart. A
patient whose vitals could not be scored at all (`aggregate_score is None`
-- e.g. no observations recorded yet) is also left alone here, for the same
"abstain, don't guess" reason the missing-data cap exists (Phase 9.2):
there is nothing "abnormal" to have been detected yet.

[Assumption], like every clinical threshold in this codebase: the keyword
list below is illustrative, not a validated comorbidity ontology -- a real
deployment would map to coded problem-list entries (e.g. ICD-10), not scan
free text.
"""
from __future__ import annotations

from typing import Optional

from app.scoring.models import ClinicalScoreResult

# [Assumption] illustrative high-risk chronic conditions named directly by
# the feature spec (COPD, CAD, Heart Failure, Immunosuppressed), plus their
# common synonyms/abbreviations so a nurse's free-text entry in any of the
# usual forms is recognised. Matched case-insensitively as substrings.
HIGH_RISK_HISTORY_KEYWORDS = (
    "copd",
    "chronic obstructive pulmonary disease",
    "emphysema",
    "cad",
    "coronary artery disease",
    "ischemic heart disease",
    "ischaemic heart disease",
    "heart failure",
    "chf",
    "congestive heart failure",
    "immunosuppressed",
    "immunosuppression",
    "immunocompromised",
    "immunocompromise",
)


def has_high_risk_history(medical_history: Optional[str]) -> bool:
    """True if the free-text history mentions any high-risk chronic
    condition. None/empty -> False (Phase 3 frontend's "no known medical
    history" case carries no escalation, by construction)."""
    if not medical_history:
        return False
    text = medical_history.lower()
    return any(keyword in text for keyword in HIGH_RISK_HISTORY_KEYWORDS)


def apply_medical_history_escalation(
    result: ClinicalScoreResult, medical_history: Optional[str]
) -> ClinicalScoreResult:
    """Escalates `result.rule_acuity` by exactly one ESI level (never below
    1, never applied twice) when a high-risk history is present AND the
    vitals that produced `result` were already abnormal. Returns `result`
    unchanged otherwise -- in particular, unchanged (not merely a no-op
    value) when `result.aggregate_score` is None or zero, so a healthy
    patient with the same normal vitals as a patient with a high-risk
    history is never escalated past them just for having a chronic
    condition on file."""
    if not has_high_risk_history(medical_history):
        return result
    if result.aggregate_score is None or result.aggregate_score <= 0:
        return result

    escalated_acuity = max(1, result.rule_acuity - 1)
    if escalated_acuity == result.rule_acuity:
        return result  # already at ESI 1; nothing more urgent to escalate to

    return result.model_copy(
        update={
            "rule_acuity": escalated_acuity,
            "medical_history_escalation_applied": True,
            "reason": (
                result.reason
                + f"; MEDICAL HISTORY ESCALATION: high-risk history present with abnormal vitals "
                f"-> ESI {result.rule_acuity} escalated to {escalated_acuity}"
            ),
        }
    )
