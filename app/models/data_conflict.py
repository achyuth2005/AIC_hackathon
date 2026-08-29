"""
DataConflict (Phase 9.3, CP13): "Do not average, do not silently pick one.
Flag both values with their sources and times, surface a
DATA_CONFLICT_DETECTED event, and compute acuity from the more
conservative value until a human resolves it."

One row per distinct SET of disagreeing current observations for one
concept on one case -- `observation_ids` is that set, sorted, and is the
dedupe key (see app/scoring/conflict_detection.py): the same set of
observations never raises a second DATA_CONFLICT_DETECTED, but a
genuinely new observation joining (or replacing) the set is a new
conflict instance. Like Alert (CP12) and HumanDecision (CP10), this row
is mutable-by-dismissal-equivalent ("resolved") rather than append-only --
the underlying Observation rows it references remain fully immutable.
"""
from __future__ import annotations

import uuid

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, String

from app.db import Base
from app.timeutil import utcnow as _utcnow


def _uuid() -> str:
    return str(uuid.uuid4())


class DataConflict(Base):
    __tablename__ = "data_conflicts"

    conflict_id = Column(String, primary_key=True, default=_uuid)
    case_id = Column(String, ForeignKey("cases.case_id"), nullable=False, index=True)
    concept_code = Column(String, nullable=False, index=True)

    observation_ids = Column(JSON, nullable=False)  # sorted list -- the dedupe key
    conservative_observation_id = Column(String, nullable=False)  # what scoring used automatically
    detected_at = Column(DateTime(), nullable=False, default=_utcnow)

    resolved = Column(Boolean, nullable=False, default=False)
    resolved_at = Column(DateTime(), nullable=True)
    resolved_by = Column(String, nullable=True)
    kept_observation_id = Column(String, nullable=True)  # the human's chosen authoritative value, once resolved
    resolution_note = Column(String, nullable=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<DataConflict case={self.case_id} concept={self.concept_code} resolved={self.resolved}>"
