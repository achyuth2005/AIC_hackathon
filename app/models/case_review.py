"""
CaseReview (Phase 8.3, CP15): "the high-value element is 'what changed
since you last looked at this patient.'" One row per (case_id,
reviewer_id) pair -- unlike almost everything else in this codebase, this
IS mutated in place (upserted) rather than appended, because it represents
a single fact ("when did THIS doctor last look at THIS case"), not a
history of facts. The event log (ALERT_RAISED-style append-only records)
remains the source of truth for "what actually happened"; this table only
tracks the read cursor into it, per reviewer.
"""
from __future__ import annotations

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, UniqueConstraint

from app.db import Base
from app.timeutil import utcnow as _utcnow


def _uuid() -> str:
    return str(uuid.uuid4())


class CaseReview(Base):
    __tablename__ = "case_reviews"
    __table_args__ = (UniqueConstraint("case_id", "reviewer_id", name="uq_case_review_case_reviewer"),)

    review_id = Column(String, primary_key=True, default=_uuid)
    case_id = Column(String, ForeignKey("cases.case_id"), nullable=False, index=True)
    reviewer_id = Column(String, nullable=False, index=True)
    reviewed_at = Column(DateTime(), nullable=False, default=_utcnow)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<CaseReview case={self.case_id} reviewer={self.reviewer_id} at={self.reviewed_at}>"
