"""
Event: the append-only stream every engine in the architecture consumes
(Phase 4.4, Phase 11.H "The continuous loop, stated precisely").

The model itself stores an event_type string plus a JSON payload rather than
one table per event type, because the architecture's event list is explicitly
open-ended ("Your event list is good. Keep it, and add: ..."). The set of
recognised types is enforced by app/store/event_store.py at append time
(KNOWN_EVENT_TYPES), not by a DB constraint, so adding a new event type is a
one-line change rather than a migration.
"""
from __future__ import annotations

import uuid

from sqlalchemy import Column, String, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship

from app.db import Base
from app.timeutil import utcnow as _utcnow


def _uuid() -> str:
    return str(uuid.uuid4())


class Event(Base):
    __tablename__ = "events"

    event_id = Column(String, primary_key=True, default=_uuid)

    # Nullable: most events are case-scoped, but a few (e.g. AI_UNAVAILABLE,
    # Phase 9.5) are system-wide banners rather than about one patient.
    case_id = Column(String, ForeignKey("cases.case_id"), nullable=True, index=True)

    event_type = Column(String, nullable=False, index=True)
    payload = Column(JSON, nullable=False, default=dict)

    occurred_at = Column(DateTime(), nullable=False, default=_utcnow)  # when it happened
    recorded_at = Column(DateTime(), nullable=False, default=_utcnow)  # when it entered the store

    case = relationship("Case", back_populates="events")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Event {self.event_type} case={self.case_id} at={self.occurred_at}>"


# Phase 4.4's explicit list, plus the additions the same phase calls for.
# This is the whitelist app/store/event_store.py enforces on append() so a
# typo in an event_type doesn't silently create an unrecognised event kind.
KNOWN_EVENT_TYPES = {
    # Core lifecycle (Phase 1 clinical workflow, Phase 7 ambulance)
    "CASE_CREATED",
    "PATIENT_ARRIVED",  # ambulance-to-ED transition; NOT a new case (Phase 4.4, 7.1)
    "OBSERVATION_RECORDED",
    "OBSERVATION_SUPERSEDED",
    "PATIENT_DISPOSED",
    # Guardian Queue / Time Engine (Phase 4.4, 5.3, 8.1)
    "REASSESSMENT_DUE",
    "REASSESSMENT_COMPLETED",
    "PATIENT_SELF_REPORTED_WORSENING",  # the "I feel worse" button
    # Data quality (Phase 4.4, 9.3, 9.4, CP13)
    "CONFIDENCE_DEGRADED",
    "DATA_CONFLICT_DETECTED",
    "DATA_CONFLICT_RESOLVED",
    "STALE_DATA_FLAGGED",
    # Failure modes (Phase 4.4, 9.5)
    "AI_UNAVAILABLE",
    "ML_UNAVAILABLE",
    "DEVICE_UNAVAILABLE",
    # Scoring / decisions (Phase 4.3, populated from CP6 onward)
    "RISK_ASSESSMENT_COMPUTED",
    "HUMAN_DECISION_RECORDED",
    "HARD_TRIGGER_FIRED",
    "EMERGENCY_BYPASS_ACTIVATED",
    # Operations (Phase 6, CP9)
    "STUCK_PATIENT_DETECTED",
    "CAPACITY_CONFLICT_RAISED",
    "RESOURCE_ASSIGNED",
    "RESOURCE_RELEASED",
    "PATIENT_IN_SPACE",       # Phase 6.3 "assigned space never occupied" pattern's resolving event
    "TEST_ORDERED",           # Phase 6.3 "test ordered, no sample collected" pattern
    "SAMPLE_COLLECTED",
    "RESULT_AVAILABLE",       # Phase 6.3 "result available, not reviewed" pattern
    "RESULT_REVIEWED",
    # Ambulance / identity (Phase 7.1, populated from CP11 onward)
    "IDENTITY_MATCH_PROPOSED",
    "IDENTITY_MATCH_CONFIRMED",
    # Alert Aggregation Engine (Phase 8.5, CP12)
    "ALERT_RAISED",
    "ALERT_DISMISSED",
    # Ambulance ETA simulation (Phase 7.2, CP18)
    "AMBULANCE_TRANSPORT_STARTED",
    "AMBULANCE_TRANSPORT_DELAYED",
}
