"""
Schemas for the Phase 9.3 Contradictory-Information engine (CP13).
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class DataConflictResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    conflict_id: str
    case_id: str
    concept_code: str
    observation_ids: List[str]
    conservative_observation_id: str
    detected_at: datetime
    resolved: bool
    resolved_at: Optional[datetime]
    resolved_by: Optional[str]
    kept_observation_id: Optional[str]
    resolution_note: Optional[str]


class DataConflictResolveRequest(BaseModel):
    """Phase 9.3: 'until a human resolves it.' The human picks which of
    the conflicting observations is authoritative going forward."""
    kept_observation_id: str
    resolution_note: Optional[str] = None
