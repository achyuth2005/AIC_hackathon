"""
DiagnosticTest (Phase 6.3): the lifecycle two of the five stuck-patient
patterns are defined against -- "test ordered, no sample collected" and
"result available, not reviewed". Diagnostics are named "useful, optional"
in Phase 6.1 (not an MVP-essential resource), so this exists specifically
to give Stuck Patient Detection something concrete to detect, not as a lab
information system.
"""
from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Enum as SAEnum

from app.db import Base
from app.models.enums import DiagnosticTestStatus
from app.timeutil import utcnow as _utcnow


def _uuid() -> str:
    return str(uuid.uuid4())


class DiagnosticTest(Base):
    __tablename__ = "diagnostic_tests"

    test_id = Column(String, primary_key=True, default=_uuid)
    case_id = Column(String, ForeignKey("cases.case_id"), nullable=False, index=True)

    test_type = Column(String, nullable=False)  # free-form, e.g. "CBC", "XRAY_CHEST" -- not a controlled vocabulary
    status = Column(SAEnum(DiagnosticTestStatus), nullable=False, default=DiagnosticTestStatus.ORDERED)

    ordered_at = Column(DateTime(), nullable=False, default=_utcnow)
    sample_collected_at = Column(DateTime(), nullable=True)
    result_available_at = Column(DateTime(), nullable=True)
    result_reviewed_at = Column(DateTime(), nullable=True)

    # Phase 6.3: reset whenever the test advances to its next stage, same
    # pattern as Case.reassessment_overdue (CP7) / Resource.occupancy_stuck_flagged.
    stuck_flagged = Column(Boolean, nullable=False, default=False)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<DiagnosticTest {self.test_type} status={self.status} case={self.case_id}>"
