"""
Phase 8.4 control tower endpoint (CP15).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_store
from app.config.hospital_profile import load_hospital_profile
from app.dashboard.control_tower import build_control_tower
from app.schemas.control_tower import ControlTowerResponse
from app.store.event_store import EventStore

router = APIRouter(prefix="/control-tower", tags=["control-tower"])


@router.get("", response_model=ControlTowerResponse)
def get_control_tower(
    hospital_profile_id: str = Query(default="default"),
    store: EventStore = Depends(get_store),
) -> ControlTowerResponse:
    """Phase 8.4: five tiles, every one actionable -- patients by acuity
    band (overdue highlighted), deteriorating patients, stuck patients,
    capacity free-vs-needed, and incoming ambulances with predicted
    acuity. Reading this endpoint has the same documented side effects as
    /ops/stuck-patients (it calls the same sweep)."""
    profile = load_hospital_profile(hospital_profile_id)
    return build_control_tower(store, profile)
