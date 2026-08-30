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

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import MeasurementStatus, ReliabilityTier, SourceType, ValueType
from app.scoring.concepts import KNOWN_CONCEPT_CODES, VITAL_PLAUSIBLE_RANGES


class _ObservationValueFields(BaseModel):
    value: Optional[Union[bool, float, str]] = None
    value_type: ValueType
    unit: Optional[str] = Field(default=None, max_length=32)
    source_type: SourceType
    source_id: Optional[str] = Field(default=None, max_length=200)
    reliability_tier: ReliabilityTier
    measurement_status: MeasurementStatus
    observed_at: datetime
    extraction_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _check_consistency(self) -> "_ObservationValueFields":
        # Fail fast with a 422 here rather than relying solely on the store's
        # own check, but the store re-validates this independently (defence
        # in depth, not a substitute -- see EventStore.add_observation).
        if self.source_type == SourceType.AI_INFERRED and self.extraction_confidence is None:
            raise ValueError("extraction_confidence is required when source_type is AI_INFERRED (Phase 4.2).")

        # Audit fix (Critical, data integrity): measurement_status=MEASURED
        # asserts "this concept was actually read" -- NOT_MEASURED and
        # UNOBTAINABLE are what a caller with no reading should send instead.
        # A null value under MEASURED previously sailed past every check
        # below (they're all gated on `self.value is not None`) and reached
        # a clean 201, silently persisting a row the scoring engine can
        # never read: evaluate_range_bands/evaluate_coded_points
        # (app/scoring/banding.py) have no band for "no value" and crash
        # with a raw TypeError the instant anything scores this concept for
        # this case again -- conflict detection, a rescore, or a future
        # observation on the same concept. Rejected here, at the door, for
        # every entry path that goes through this shared base (direct
        # create AND supersede).
        if self.measurement_status == MeasurementStatus.MEASURED and self.value is None:
            raise ValueError(
                "value is required when measurement_status is MEASURED -- use "
                "NOT_MEASURED or UNOBTAINABLE instead if no reading was taken."
            )

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

            # Audit fix (High, dimension 3): the direct nurse-entry path had
            # no plausibility bounds on numeric vitals at all -- a typo like
            # SPO2=980 or HEART_RATE=-40 previously sailed through as a
            # valid 201, then either silently scored as maximally abnormal
            # (an open-ended NEWS2/PEWS band) or surfaced as an opaque
            # UnbandedValueError deep in the scoring engine. Checked here,
            # with the same bounds the LLM Intake Engine already enforces
            # (app/scoring/concepts.py's VITAL_PLAUSIBLE_RANGES), so a bad
            # entry is rejected as a clear 422 at the door instead.
            concept_code = getattr(self, "concept_code", None)
            vital_range = VITAL_PLAUSIBLE_RANGES.get(concept_code)
            if vital_range is not None and is_numeric:
                low, high = vital_range
                if not (low <= self.value <= high):
                    raise ValueError(
                        f"value {self.value} is outside the plausible range [{low}, {high}] for "
                        f"{concept_code}. If this is a genuine, unusual reading, double-check it "
                        f"before re-submitting -- this is a data-entry safety check, not a clinical judgement."
                    )
        return self


class ObservationCreateRequest(_ObservationValueFields):
    # Audit fix (High, dimension 3): restricted to the controlled
    # vocabulary app/scoring/concepts.py defines -- previously a plain
    # `str`, so a typo'd concept_code (e.g. "HEART_RATEE") returned 201 and
    # was then silently invisible to every scoring engine forever, despite
    # app/models/observation.py's own docstring insisting on "controlled
    # vocabulary, not free text."
    concept_code: str

    @model_validator(mode="after")
    def _check_known_concept(self) -> "ObservationCreateRequest":
        if self.concept_code not in KNOWN_CONCEPT_CODES:
            raise ValueError(
                f"concept_code {self.concept_code!r} is not in the controlled vocabulary "
                f"(app/scoring/concepts.py). Add it there deliberately rather than sending an "
                f"unrecognised code that no scoring engine will ever read."
            )
        return self


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
