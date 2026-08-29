"""
HumanDecision (Phase 4.3, 9.6): the persisted record of a clinician
accepting, escalating, or de-escalating the system's own recommendation.
Never mutated -- one override is one row, the same append-only discipline
as Observation/RiskAssessment.

Phase 9.6's asymmetric friction itself is enforced in
app/store/event_store.py's record_human_override(), not here: this model
just stores the outcome of whichever path the caller took (clinician_action),
what the system had recommended beforehand (system_recommendation), what
the human decided instead (resulting_acuity), and whether that decision
needed the extra scrutiny a de-escalation always gets (flagged_for_review).
"""
from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Enum as SAEnum

from app.db import Base
from app.models.enums import DeEscalationReasonCode, HumanDecisionAction
from app.timeutil import utcnow as _utcnow


def _uuid() -> str:
    return str(uuid.uuid4())


class HumanDecision(Base):
    __tablename__ = "human_decisions"

    decision_id = Column(String, primary_key=True, default=_uuid)
    case_id = Column(String, ForeignKey("cases.case_id"), nullable=False, index=True)

    # Identity comes from a verified auth token (app/auth/deps.py), never
    # from a request body field -- exactly the gap CP9.5 closed for
    # emergency-bypass, applied here from the start rather than retrofitted.
    clinician_id = Column(String, nullable=False)
    role = Column(String, nullable=False)
    timestamp = Column(DateTime(), nullable=False, default=_utcnow)

    system_recommendation = Column(Integer, nullable=False)  # final_acuity before this decision
    clinician_action = Column(SAEnum(HumanDecisionAction), nullable=False)
    resulting_acuity = Column(Integer, nullable=False)
    reason_code = Column(SAEnum(DeEscalationReasonCode), nullable=True)  # required only for DE_ESCALATE
    free_text_reason = Column(String, nullable=True)

    linked_assessment_id = Column(String, ForeignKey("risk_assessments.assessment_id"), nullable=False)
    flagged_for_review = Column(Boolean, nullable=False, default=False)

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<HumanDecision case={self.case_id} action={self.clinician_action} "
            f"{self.system_recommendation}->{self.resulting_acuity}>"
        )
