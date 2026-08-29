"""
Schemas for the Phase 8.4 control tower (CP15): "anticipate, not report.
Five tiles maximum, every tile actionable."
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel

from app.ops.models import StuckPatternResult


class AcuityBandTile(BaseModel):
    """Tile 1: 'patients by acuity band, with overdue reassessments
    highlighted.'"""
    acuity: int
    case_count: int
    overdue_count: int


class DeterioratingPatientTile(BaseModel):
    """Tile 2: 'deteriorating patients.'"""
    case_id: str
    display_name: Optional[str]
    from_acuity: int
    to_acuity: int


class CapacityTile(BaseModel):
    """Tile 4: 'capacity: spaces and clinicians free versus needed.'
    `needed_estimate` is [Assumption]: the count of ACTIVE cases not
    currently occupying a resource of this type -- a proxy for "still
    waiting for one", not a clinically-derived requirement (no rule in
    this project maps an acuity level to a specific resource type)."""
    resource_type: str
    available: int
    occupied: int
    out_of_service: int
    needed_estimate: int


class IncomingAmbulanceTile(BaseModel):
    """Tile 5: 'incoming ambulances with predicted acuity.'"""
    case_id: str
    display_name: Optional[str]
    predicted_acuity: Optional[int]


class ControlTowerResponse(BaseModel):
    patients_by_acuity_band: List[AcuityBandTile]
    deteriorating_patients: List[DeterioratingPatientTile]
    stuck_patients: List[StuckPatternResult]
    capacity: List[CapacityTile]
    incoming_ambulances: List[IncomingAmbulanceTile]
