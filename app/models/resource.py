"""
Resource (Phase 6.1 MVP scope): clinician / treatment space / resuscitation
bay availability. Deliberately NOT modelling medication inventory, staff
rostering, or equipment tracking -- Phase 6.1 names those out of scope or
future, and this table only has columns for the three "Essential (MVP)"
rows.

Phase 6.2: "Clinical urgency and resource availability are computed
independently and stored separately." This table has no acuity column and
no relationship that could let a scoring engine read from it -- capacity
state lives here, acuity lives in RiskAssessment, and the only thing that
ever crosses between them is a CAPACITY_CONFLICT_RAISED event surfaced to
a human, never a number fed back into scoring.
"""
from __future__ import annotations

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, Boolean, Enum as SAEnum
from sqlalchemy.orm import relationship

from app.db import Base
from app.models.enums import ResourceStatus, ResourceType
from app.timeutil import utcnow as _utcnow


def _uuid() -> str:
    return str(uuid.uuid4())


class Resource(Base):
    __tablename__ = "resources"

    resource_id = Column(String, primary_key=True, default=_uuid)
    hospital_profile_id = Column(String, nullable=False, default="default", index=True)

    resource_type = Column(SAEnum(ResourceType), nullable=False)
    label = Column(String, nullable=False)  # e.g. "Bay 4", "Resus 1", "Dr. Singh"
    status = Column(SAEnum(ResourceStatus), nullable=False, default=ResourceStatus.AVAILABLE)

    assigned_case_id = Column(String, ForeignKey("cases.case_id"), nullable=True)
    assigned_at = Column(DateTime(), nullable=True)

    # Phase 6.3 "assigned space never occupied" pattern: reset whenever the
    # resource is released or occupancy is confirmed, same pattern as
    # Case.reassessment_overdue (CP7) rather than re-deriving from events.
    occupancy_stuck_flagged = Column(Boolean, nullable=False, default=False)

    case = relationship("Case")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Resource {self.resource_type} '{self.label}' status={self.status}>"
