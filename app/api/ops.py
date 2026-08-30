"""
Flow/Operations Engine endpoint (Phase 6.3): the Stuck Patient Detection
sweep, exposed for a nurse/charge-nurse ops view.
"""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends

from app.api.deps import get_store
from app.auth.deps import get_current_user
from app.auth.models import AuthenticatedUser
from app.config.hospital_profile import load_hospital_profile
from app.ops.flow_engine import check_stuck_patients
from app.ops.models import StuckPatternResult
from app.store.event_store import EventStore

router = APIRouter(prefix="/ops", tags=["ops"])


@router.get("/stuck-patients", response_model=List[StuckPatternResult])
def get_stuck_patients(
    store: EventStore = Depends(get_store),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> List[StuckPatternResult]:
    """Reading this endpoint has documented side effects: it flags newly-
    stuck tests/resources as it finds them (see app/ops/flow_engine.py and
    app/queue/guardian_queue.py's module docstring for why -- no scheduler
    exists in this prototype).

    Audit fix (Critical, dimension 1/IDOR): previously unauthenticated
    with a caller-suppliable hospital_profile_id -- this view exposes
    PHI-adjacent operational state (which case is stuck and why) for an
    entire hospital. Now requires a staff token and is always scoped to
    that token's own hospital."""
    profile = load_hospital_profile(current_user.hospital_profile_id)
    return check_stuck_patients(store, profile)
