"""
Request/response contracts for Observations (Phase 4.2).

`_ObservationValueFields` is shared by create and supersede because the
value payload is identical either way. `concept_code` is deliberately NOT
on the shared base: a supersession corrects the *value* of an existing
concept, it cannot change *which* concept the observation is about (the
store carries `concept_code` forward from the original row unconditionally --
see EventStore.supersede_observation). Accepting a concept_code on the
supersede request and silently discarding it would be a misleading contract,
so the field only exists on ObservationCreateRequest.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional, Union

from pydantic import BaseModel, ConfigDict, model_validator

from app.models.enums import MeasurementStatus, ReliabilityTier, SourceType, ValueType


class _ObservationValueFields(BaseModel):
    value: Optional[Union[bool, float, str]] = None
    value_type: ValueType
    unit: Optional[str] = None
    source_type: SourceType
    source_id: Optional[str] = None
    reliability_tier: ReliabilityTier
    measurement_status: MeasurementStatus
    observed_at: datetime
    extraction_confidence: Optional[float] = None

    @model_validator(mode="after")
    def _check_consistency(self) -> "_ObservationValueFields":
        # Fail fast with a 422 here rather than relying solely on the store's
        # own check, but the store re-validates this independently (defence
        # in depth, not a substitute -- see EventStore.add_observation).
        if self.source_type == SourceType.AI_INFERRED and self.extraction_confidence is None:
            raise ValueError("extraction_confidence is required when source_type is AI_INFERRED (Phase 4.2).")

        if self.value is not None:
            # bool is a subclass of int in Python, so it is excluded
            # explicitly from the NUMERIC check -- otherwise a JSON `true`
            # would silently pass as a numeric vital.
            is_numeric = isinstance(self.value, (int, float)) and not isinstance(self.value, bool)
            is_boolean = isinstance(self.value, bool)
            is_text = isinstance(self.value, str)
            matches = {
                ValueType.NUMERIC: is_numeric,
                ValueType.BOOLEAN: is_boolean,
                ValueType.TEXT: is_text,
                ValueType.CODED: is_text,
            }[self.value_type]
            if not matches:
                raise ValueError(
                    f"value {self.value!r} (python type {type(self.value).__name__}) does not "
                    f"match value_type={self.value_type.value}."
                )
        return self


class ObservationCreateRequest(_ObservationValueFields):
    concept_code: str


class ObservationSupersedeRequest(_ObservationValueFields):
    pass


class ObservationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    observation_id: str
    case_id: str
    concept_code: str
    value_type: ValueType
    value: Optional[Union[bool, float, str]]
    unit: Optional[str]
    source_type: SourceType
    source_id: Optional[str]
    reliability_tier: ReliabilityTier
    measurement_status: MeasurementStatus
    observed_at: datetime
    recorded_at: datetime
    extraction_confidence: Optional[float]
    superseded_by: Optional[str]
    is_current: bool
