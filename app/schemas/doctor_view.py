"""
Schemas for the Phase 8.3 doctor view (CP15).
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel

from app.schemas.event import EventResponse
from app.schemas.observation import ObservationResponse
from app.schemas.risk_assessment import RiskAssessmentResponse


class VitalTrend(BaseModel):
    """Phase 8.3: 'trends over raw values.' One entry per concept with at
    least two current readings -- deliberately not shown at all for a
    concept with only one reading (there is no trend yet, not a flat one)."""
    concept_code: str
    previous_value: Any
    previous_observed_at: datetime
    current_value: Any
    current_observed_at: datetime
    delta: Optional[float] = None  # numeric concepts only


class PendingAction(BaseModel):
    """Phase 8.3: 'pending actions and results.'"""
    kind: str  # "RESULT_AWAITING_REVIEW" | "UNRESOLVED_DATA_CONFLICT"
    description: str
    reference_id: str


class DoctorCaseView(BaseModel):
    """Phase 8.3: 'assigned patients -> synthesised summary with source
    attribution -> trends over raw values -> what changed since last
    review -> pending actions and results.' Deliberately does NOT include
    differential diagnoses or treatment suggestions -- this project
    generates neither, so there is nothing to withhold, but the shape
    itself has no field that could carry one."""
    case_id: str
    display_name: Optional[str]
    # Medical History feature: surfaced directly on the doctor's decision-
    # support summary (Phase 8.3) -- a high-risk history is exactly the
    # kind of context a reviewing physician needs alongside current vitals.
    medical_history: Optional[str]
    current_observations: List[ObservationResponse]
    latest_risk_assessment: Optional[RiskAssessmentResponse]
    trends: List[VitalTrend]

    is_first_review: bool
    last_reviewed_at: Optional[datetime]
    changed_since_last_review: List[EventResponse]

    pending_actions: List[PendingAction]
