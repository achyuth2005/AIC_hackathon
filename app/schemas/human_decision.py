"""
Schemas for the Phase 4.3/9.6 Audit & Override Service (CP10).
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import DeEscalationReasonCode, HumanDecisionAction

# Audit fix (Medium, dimension 3): the valid ESI/acuity scale used
# throughout this codebase (RiskAssessment.final_acuity, HardTriggerDefinition
# .target_esi_level, AcuityBand.esi_level, ...) is always 1-5. target_acuity
# previously had no bound at all here, so e.g. -999 or 0 could reach
# EventStore.record_human_override's own comparison logic and be persisted
# to the permanent audit trail as a "resulting_acuity" outside the scale.
MIN_ACUITY = 1
MAX_ACUITY = 5


class OverrideRequest(BaseModel):
    """Phase 9.6's asymmetric override friction, as a single endpoint:
    `{"action": "ESCALATE"}` alone is a complete, valid body -- "one tap,
    no reason required" -- while `action: DE_ESCALATE` additionally
    requires `target_acuity` and `reason_code`. That asymmetry is enforced
    server-side (EventStore.record_human_override), not just by this
    schema, so it can't be bypassed by a client that skips whatever UI
    would normally prompt for the extra fields.

    `target_acuity` is optional for ESCALATE (defaults to one level more
    urgent than the case's current final_acuity) and ignored for ACCEPT;
    it is required for DE_ESCALATE."""
    action: HumanDecisionAction
    target_acuity: Optional[int] = Field(default=None, ge=MIN_ACUITY, le=MAX_ACUITY)
    reason_code: Optional[DeEscalationReasonCode] = None
    free_text_reason: Optional[str] = Field(default=None, max_length=2000)


class HumanDecisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    decision_id: str
    case_id: str
    clinician_id: str
    role: str
    timestamp: datetime
    system_recommendation: int
    clinician_action: HumanDecisionAction
    resulting_acuity: int
    reason_code: Optional[DeEscalationReasonCode]
    free_text_reason: Optional[str]
    linked_assessment_id: str
    flagged_for_review: bool
