"""
Observation: the atomic, immutable fact record (Phase 4.2).

Three rules from the architecture that this model exists to enforce:
  1. "Missing is not normal. Reported is not measured. Inferred is not
     observed." -> measurement_status and reliability_tier are mandatory,
     not derived from whether `value` is populated.
  2. "observed_at separate from recorded_at" -> both are mandatory columns;
     callers must supply observed_at explicitly rather than relying on a
     default, so ambulance-vs-arrival timing is never silently collapsed.
  3. "Supersession instead of mutation" -> there is no update path on this
     model. Corrections are new rows with `superseded_by` set on the old
     row (enforced in app/store/event_store.py, not here).
"""
from __future__ import annotations

import uuid
from datetime import timedelta
from typing import Optional

from sqlalchemy import (
    Column,
    String,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Enum as SAEnum,
)
from sqlalchemy.orm import relationship

from app.db import Base
from app.models.enums import SourceType, ReliabilityTier, MeasurementStatus, ValueType
from app.timeutil import utcnow as _utcnow, to_naive_utc


def _uuid() -> str:
    return str(uuid.uuid4())


class Observation(Base):
    __tablename__ = "observations"

    observation_id = Column(String, primary_key=True, default=_uuid)
    case_id = Column(String, ForeignKey("cases.case_id"), nullable=False, index=True)

    # Controlled vocabulary, not free text (Phase 4.2 comment, Phase 3.2
    # "Mapping extracted terms to coded concepts -> Deterministic lookup").
    concept_code = Column(String, nullable=False, index=True)

    value_type = Column(SAEnum(ValueType), nullable=False)
    value_numeric = Column(Float, nullable=True)
    value_text = Column(String, nullable=True)
    value_coded = Column(String, nullable=True)
    value_boolean = Column(Boolean, nullable=True)
    unit = Column(String, nullable=True)

    source_type = Column(SAEnum(SourceType), nullable=False)
    source_id = Column(String, nullable=True)  # device serial or staff identity
    reliability_tier = Column(SAEnum(ReliabilityTier), nullable=False)
    measurement_status = Column(SAEnum(MeasurementStatus), nullable=False)

    observed_at = Column(DateTime(), nullable=False)  # when it happened in the world
    recorded_at = Column(DateTime(), nullable=False, default=_utcnow)  # when it entered the system

    extraction_confidence = Column(Float, nullable=True)  # only meaningful for AI_INFERRED

    superseded_by = Column(String, ForeignKey("observations.observation_id"), nullable=True)

    case = relationship("Case", back_populates="observations")

    @property
    def is_current(self) -> bool:
        """A current fact has not been superseded by a correction."""
        return self.superseded_by is None

    @property
    def value(self):
        """Convenience accessor returning whichever typed column applies."""
        return {
            ValueType.NUMERIC: self.value_numeric,
            ValueType.TEXT: self.value_text,
            ValueType.CODED: self.value_coded,
            ValueType.BOOLEAN: self.value_boolean,
        }[ValueType(self.value_type)]

    def is_stale(self, staleness_window: Optional[timedelta], as_of: Optional[datetime] = None) -> bool:
        """Phase 4.2 `is_stale`: "derived from concept-specific staleness
        window". Deliberately NOT a stored column -- staleness is a function
        of elapsed time, so storing it would itself go stale. The caller
        (Time Engine / Guardian Queue, CP7-8) supplies the concept-specific
        window from the HospitalProfile.

        A staleness_window of None means "this concept never goes stale"
        (e.g. a historical allergy record) and always returns False.
        """
        if staleness_window is None:
            return False
        now = to_naive_utc(as_of) if as_of is not None else _utcnow()
        return (now - self.observed_at) > staleness_window

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<Observation {self.concept_code}={self.value} "
            f"status={self.measurement_status} tier={self.reliability_tier} "
            f"case={self.case_id}>"
        )
