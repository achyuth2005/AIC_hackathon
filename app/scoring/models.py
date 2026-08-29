"""
Result types for the Age Router and Clinical Scoring Engine (Phase 3.3
Layers 1-2, Phase 4.3 `rule_component_breakdown`).

Pydantic models (not dataclasses) so these are already API-serializable when
a scoring endpoint is added, and so `input_snapshot_hash` /
`input_observation_ids` (Phase 4.3 RiskAssessment) can be built from
`ScoreComponent.observation_id` without re-deriving anything.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field

from app.models.enums import ConfidenceBand, MeasurementStatus, ReliabilityTier


class VitalReading(BaseModel):
    """A DB-free carrier for 'the current observation of one concept', so
    news2.py/pews.py can be unit-tested as pure functions without a
    database. app/scoring/engine.py is the only place that converts real
    Observation ORM rows into these."""
    model_config = {"arbitrary_types_allowed": True}

    value: Any
    unit: Optional[str] = None
    measurement_status: MeasurementStatus
    observed_at: datetime
    observation_id: str
    is_stale: bool = False
    reliability_tier: ReliabilityTier  # CP5 confidence input 4 -- required, no default (see readings.py)


class AgeRoutingResult(BaseModel):
    """Phase 3.3 Layer 1 output."""
    age_years: Optional[float]
    age_band: Optional[str]  # None means routing failed -- age unknown
    reason: Optional[str] = None  # populated when age_band is None


class ScoreComponent(BaseModel):
    """One row of Phase 4.3's `rule_component_breakdown` -- one physiological
    parameter's contribution to the aggregate score, or its reason for
    being excluded."""
    concept_code: str
    label: str
    raw_value: Optional[Any] = None
    unit: Optional[str] = None
    points: Optional[int] = None  # None == excluded (missing/stale), never treated as 0
    is_missing: bool = False
    missing_reason: Optional[str] = None  # e.g. "NO_OBSERVATION_RECORDED", "NOT_MEASURED", "STALE"
    observation_id: Optional[str] = None
    observed_at: Optional[datetime] = None
    reliability_tier: Optional[ReliabilityTier] = None  # CP5 confidence input 4; None only when no reading exists at all


class HardTriggerResult(BaseModel):
    """Phase 3.3 Layer 4 / Phase 4.3 RiskAssessment's `hard_triggers_fired[]`
    -- one hospital-configured single-parameter trigger that fired."""
    trigger_id: str
    label: str
    concept_code: str
    raw_value: Any
    target_esi_level: int


class ClinicalScoreResult(BaseModel):
    """Phase 4.3 RiskAssessment's rule-layer fields:
    `rule_acuity`, `rule_component_breakdown` (== components here),
    `hard_triggers_fired`."""
    framework: str  # "NEWS2" | "PEWS"
    age_band: Optional[str]
    aggregate_score: Optional[int]  # None if the engine could not score at all (e.g. age unknown)

    # framework_acuity: the framework's own aggregate+single-parameter-rule
    # result, BEFORE Layer 4 hard triggers are applied -- this is what CP5's
    # confidence engine compares an eventual ML suggestion against, and what
    # its "distance from a band boundary" input measures. NOT the same
    # thing Phase 3.1's min(rule_based_acuity, ...) formula calls
    # "rule_based_acuity" -- that is `rule_acuity` below, which already
    # includes Layer 4. See app/scoring/confidence.py for why the
    # distinction matters.
    framework_acuity: int
    rule_acuity: int  # ESI 1-5, always populated; Phase 3.1's "rule_based_acuity" (Layers 1-4 combined)
    components: List[ScoreComponent]

    single_parameter_escalation: bool = False
    single_parameter_escalation_reason: Optional[str] = None

    hard_triggers_fired: List[HardTriggerResult] = Field(default_factory=list)  # Phase 3.3 Layer 4, applied on top of the framework score

    missing_data_cap_applied: bool = False
    has_any_missing_or_stale: bool = False

    age_unknown: bool = False
    reason: str = ""


class ConfidenceResult(BaseModel):
    """Phase 9.1 (confidence) + Phase 9.2 (abstention).

    `final_acuity` is `rule_acuity` unless abstention forces it more
    conservative (`min(rule_acuity, abstention_minimum_acuity)`) -- it is
    NEVER less conservative. Low confidence never means low acuity."""
    band: ConfidenceBand
    score: float  # 0-100, diagnostic/internal -- not shown raw to a nurse (Phase 8.2 wants plain language)
    reasons: List[str] = Field(default_factory=list)

    should_abstain: bool = False
    abstention_message: Optional[str] = None

    final_acuity: int
    ml_considered: bool = False  # False until CP6 supplies a real ml_suggested_acuity
