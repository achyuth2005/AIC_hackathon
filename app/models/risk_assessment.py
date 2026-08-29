"""
RiskAssessment (Phase 4.3): the immutable, persisted result of one run of
the scoring stack (Phase 3.3 Layers 1-4 + Phase 3.3 Layer 3 ML + Phase 9.1
confidence). Never mutated -- a new observation triggers a NEW
RiskAssessment row, exactly like Observation's own "never mutate, always
supersede" discipline (Phase 4.2), so the audit trail can always show
"this is exactly what the system saw at 14:32, and this is exactly why it
said what it said" (Phase 4.3).

`input_snapshot_hash` + `input_observation_ids` together are that promise:
given the observation_ids, an auditor can pull the exact rows that produced
this assessment; the hash lets two assessments be compared for "did the
same inputs produce a different output" without re-fetching anything.
"""
from __future__ import annotations

import uuid

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Enum as SAEnum

from app.db import Base
from app.models.enums import ConfidenceBand, DecidingLayer
from app.timeutil import utcnow as _utcnow


def _uuid() -> str:
    return str(uuid.uuid4())


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    assessment_id = Column(String, primary_key=True, default=_uuid)
    case_id = Column(String, ForeignKey("cases.case_id"), nullable=False, index=True)
    computed_at = Column(DateTime(), nullable=False, default=_utcnow)

    # Rules (Phase 3.3 Layers 1, 2, 4 combined -- this IS Phase 3.1's
    # "rule_based_acuity" term).
    rule_engine_version = Column(String, nullable=False)
    rule_acuity = Column(Integer, nullable=False)
    rule_component_breakdown = Column(JSON, nullable=False)  # List[ScoreComponent] as dicts

    # ML challenger (Phase 3.3 Layer 3). All nullable: None when the
    # challenger didn't run at all (age unknown, or disabled -- Phase 9.5),
    # not to be confused with "ran and suggested no escalation".
    ml_model_version = Column(String, nullable=True)
    ml_probability = Column(Float, nullable=True)
    ml_suggested_acuity = Column(Integer, nullable=True)

    hard_triggers_fired = Column(JSON, nullable=False, default=list)  # List[HardTriggerResult] as dicts

    # Phase 3.1's min(): final_acuity, and which term of the min() actually
    # bound it (see DecidingLayer's docstring for the ABSTENTION addition).
    final_acuity = Column(Integer, nullable=False)
    deciding_layer = Column(SAEnum(DecidingLayer), nullable=False)

    confidence_band = Column(SAEnum(ConfidenceBand), nullable=False)
    confidence_score = Column(Float, nullable=False)
    confidence_reasons = Column(JSON, nullable=False, default=list)
    should_abstain = Column(Boolean, nullable=False, default=False)
    abstention_message = Column(String, nullable=True)

    input_snapshot_hash = Column(String, nullable=False)
    input_observation_ids = Column(JSON, nullable=False, default=list)

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<RiskAssessment case={self.case_id} final_acuity={self.final_acuity} "
            f"deciding_layer={self.deciding_layer} computed_at={self.computed_at}>"
        )
