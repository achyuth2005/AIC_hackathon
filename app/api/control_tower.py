"""
Phase 8.4 control tower endpoint (CP15).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_store
from app.auth.deps import get_current_user
from app.auth.models import AuthenticatedUser
from app.config.hospital_profile import load_hospital_profile
from app.dashboard.control_tower import build_control_tower
from app.schemas.control_tower import ControlTowerResponse
from app.store.event_store import EventStore

router = APIRouter(prefix="/control-tower", tags=["control-tower"])


@router.get("", response_model=ControlTowerResponse)
def get_control_tower(
    store: EventStore = Depends(get_store),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> ControlTowerResponse:
    """Phase 8.4: five tiles, every one actionable -- patients by acuity
    band (overdue highlighted), deteriorating patients, stuck patients,
    capacity free-vs-needed, and incoming ambulances with predicted
    acuity. Reading this endpoint has the same documented side effects as
    /ops/stuck-patients (it calls the same sweep).

    Audit fix (Critical, dimension 1/IDOR): previously unauthenticated
    with a caller-suppliable hospital_profile_id -- this view aggregates
    PHI (patients by band, deteriorating/stuck patients) across an entire
    hospital and was readable by anyone. Now requires a staff token and is
    always scoped to that token's own hospital."""
    profile = load_hospital_profile(current_user.hospital_profile_id)
    return build_control_tower(store, profile)
