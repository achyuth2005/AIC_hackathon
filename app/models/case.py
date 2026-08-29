"""
Case: the single longitudinal patient record (Phase 1 "Core concept", Phase
7.1 "the pre-hospital case and the ED case are the same record from
creation"). A Case is created at first contact (ambulance dispatch or ED
registration) and continues to disposition. Arrival is an event on this same
Case, never a new record.
"""
from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Column, String, DateTime, Integer, Date, Enum as SAEnum
from sqlalchemy.orm import relationship

from app.db import Base
from app.models.enums import ArrivalMode, BypassSource, CaseStatus, IdentityLinkStatus
from app.timeutil import utcnow as _utcnow


def _uuid() -> str:
    return str(uuid.uuid4())


class Case(Base):
    __tablename__ = "cases"

    case_id = Column(String, primary_key=True, default=_uuid)

    # Phase 18.1: HospitalProfile is configuration data, not a DB-owned
    # entity here — we store which profile this case is scored under so the
    # audit trail can reproduce "which configuration version produced which
    # decision" (Phase 18.1).
    hospital_profile_id = Column(String, nullable=False, default="default")

    # Identity. May be partially or fully unknown at creation time (Phase
    # 3.3 "First-time versus returning patients"; Phase 7.1 ambulance
    # identity matching).
    mrn = Column(String, nullable=True, index=True)
    display_name = Column(String, nullable=True)
    date_of_birth = Column(Date, nullable=True)
    age_years = Column(Integer, nullable=True)  # convenience field consumed by the Age Router (CP3)
    sex = Column(String, nullable=True)

    arrival_mode = Column(SAEnum(ArrivalMode), nullable=False, default=ArrivalMode.WALK_IN)
    status = Column(SAEnum(CaseStatus), nullable=False, default=CaseStatus.ACTIVE)
    identity_link_status = Column(
        SAEnum(IdentityLinkStatus), nullable=False, default=IdentityLinkStatus.CONFIRMED
    )

    created_at = Column(DateTime(), nullable=False, default=_utcnow)
    arrived_at = Column(DateTime(), nullable=True)  # set when PATIENT_ARRIVED fires

    # Phase 3.5 Emergency Bypass: "an alert plus a state flag ... the
    # patient skips all queues". Never cleared automatically by this
    # backend -- clearing a bypass is a clinical decision, out of CP4's
    # scope; only activation is implemented here. `last_*` reflects the
    # most recent of possibly several independent firings (any detector can
    # fire again; none can cancel another), while `first_activated_at`
    # anchors when the case first became critical.
    emergency_bypass_active = Column(Boolean, nullable=False, default=False)
    emergency_bypass_first_activated_at = Column(DateTime(), nullable=True)
    emergency_bypass_last_activated_at = Column(DateTime(), nullable=True)
    emergency_bypass_last_reason = Column(String, nullable=True)
    emergency_bypass_last_source = Column(SAEnum(BypassSource), nullable=True)
    emergency_bypass_last_trigger_id = Column(String, nullable=True)

    # Phase 5.3 reassessment timer: "Each acuity band has a hospital-
    # configured reassessment interval. When a patient exceeds it,
    # REASSESSMENT_DUE fires." `last_reassessed_at` is the single clock
    # this is measured against, and is updated by BOTH triggers Phase 5.3
    # describes as equivalent ("reassessment collects new observations"):
    # every automatic re-score when new data arrives (CP6's assess_case,
    # since new observations ARE a reassessment), and an explicit nurse
    # "mark reassessed" action (Phase 8.2) even without new numeric
    # readings. `reassessment_overdue`/`_since` exist so the Guardian Queue
    # (CP7) only emits REASSESSMENT_DUE once per overdue period rather than
    # on every read that happens to notice it's still overdue.
    last_reassessed_at = Column(DateTime(), nullable=True)
    reassessment_overdue = Column(Boolean, nullable=False, default=False)
    reassessment_overdue_since = Column(DateTime(), nullable=True)

    observations = relationship(
        "Observation", back_populates="case", cascade="all, delete-orphan", order_by="Observation.recorded_at"
    )
    events = relationship(
        "Event", back_populates="case", cascade="all, delete-orphan", order_by="Event.recorded_at"
    )

    def __repr__(self) -> str:  # pragma: no cover - debug convenience only
        return f"<Case {self.case_id} status={self.status} arrival_mode={self.arrival_mode}>"
