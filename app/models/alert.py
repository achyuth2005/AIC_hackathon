"""
Alert (Phase 8.5): the persisted record backing one interruptive
notification. Deliberately NOT every state change in the system --
"the queue is the notification, ambient by default" -- only the three
named interrupt types (AlertType) ever get one of these rows.

An Alert needs to be a real, mutable-by-dismissal row (unlike most of this
codebase's append-only discipline) because "every alert is dismissible
with a reason" (Phase 8.5) requires something concrete to dismiss. The
underlying clinical facts it summarises (a RiskAssessment, a bypass
activation, a case's reassessment_overdue flag) remain append-only/
event-sourced exactly as everywhere else in this project; this row is
purely the notification-layer wrapper around them.
"""
from __future__ import annotations

import uuid

from sqlalchemy import JSON, Boolean, Column, DateTime, String, Enum as SAEnum

from app.db import Base
from app.models.enums import AlertDismissalReasonCode, AlertType
from app.timeutil import utcnow as _utcnow


def _uuid() -> str:
    return str(uuid.uuid4())


class Alert(Base):
    __tablename__ = "alerts"

    alert_id = Column(String, primary_key=True, default=_uuid)
    hospital_profile_id = Column(String, nullable=False, default="default", index=True)
    alert_type = Column(SAEnum(AlertType), nullable=False, index=True)
    created_at = Column(DateTime(), nullable=False, default=_utcnow)

    # Free-form per-type payload (case_id, from/to acuity, list of
    # currently-overdue case_ids, ...) -- one generic shape rather than a
    # column per alert type, same rationale as Event.payload.
    payload = Column(JSON, nullable=False, default=dict)

    # Dedupe keys: what real-world fact this alert is "about", so
    # sync_alerts() never raises a second alert for the same thing.
    # Exactly one of these is populated depending on alert_type.
    dedupe_case_id = Column(String, nullable=True, index=True)              # CRITICAL_BYPASS_PATIENT
    dedupe_assessment_id = Column(String, nullable=True, index=True)        # ACUITY_BAND_CROSSED_UPWARD

    dismissed = Column(Boolean, nullable=False, default=False)
    dismissed_at = Column(DateTime(), nullable=True)
    dismissed_by = Column(String, nullable=True)  # a user_id, or "SYSTEM" for an auto-resolved aggregate
    dismissal_reason_code = Column(SAEnum(AlertDismissalReasonCode), nullable=True)
    dismissal_free_text = Column(String, nullable=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Alert {self.alert_type} dismissed={self.dismissed} payload={self.payload}>"
