from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict

from app.models.enums import ConfidenceBand, DecidingLayer


class RiskAssessmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    assessment_id: str
    case_id: str
    computed_at: datetime

    rule_engine_version: str
    rule_acuity: int
    rule_component_breakdown: List[Dict[str, Any]]

    ml_model_version: Optional[str]
    ml_probability: Optional[float]
    ml_suggested_acuity: Optional[int]

    hard_triggers_fired: List[Dict[str, Any]]

    final_acuity: int
    deciding_layer: DecidingLayer

    confidence_band: ConfidenceBand
    confidence_score: float
    confidence_reasons: List[str]
    should_abstain: bool
    abstention_message: Optional[str]

    input_snapshot_hash: str
    input_observation_ids: List[str]
