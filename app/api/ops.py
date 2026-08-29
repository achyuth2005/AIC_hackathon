"""
Flow/Operations Engine endpoint (Phase 6.3): the Stuck Patient Detection
sweep, exposed for a nurse/charge-nurse ops view.
"""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_store
from app.config.hospital_profile import load_hospital_profile
from app.ops.flow_engine import check_stuck_patients
from app.ops.models import StuckPatternResult
from app.store.event_store import EventStore

router = APIRouter(prefix="/ops", tags=["ops"])


@router.get("/stuck-patients", response_model=List[StuckPatternResult])
def get_stuck_patients(
    hospital_profile_id: str = Query(default="default"),
    store: EventStore = Depends(get_store),
) -> List[StuckPatternResult]:
    """Reading this endpoint has documented side effects: it flags newly-
    stuck tests/resources as it finds them (see app/ops/flow_engine.py and
    app/queue/guardian_queue.py's module docstring for why -- no scheduler
    exists in this prototype)."""
    profile = load_hospital_profile(hospital_profile_id)
    return check_stuck_patients(store, profile)
