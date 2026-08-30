"""
Phase 14.1 demo-data endpoint: seeds the twenty scripted synthetic
patients against a hospital profile. See app/demo/scenarios.py for what
each one is and its fidelity (a couple are PARTIAL, pending checkpoints
not yet built -- documented per-scenario, not hidden).

Audit fix (Critical, dimension 1): both endpoints below were previously
unauthenticated and could be called against a live database by anyone --
bulk-creating dozens of synthetic patients (data pollution / storage-
exhaustion risk) or running a surge simulation with no gate at all.
Restricted to ADMIN: seeding/surge-testing a hospital's live data is an
operational action, never a point-of-care one.
"""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_store
from app.auth.deps import require_role
from app.auth.models import AuthenticatedUser
from app.auth.roles import Role
from app.config.hospital_profile import load_hospital_profile
from app.demo.scenarios import DemoScenario, seed_demo_patients
from app.demo.surge import SurgeSimulationResult, run_surge_simulation
from app.store.event_store import EventStore

router = APIRouter(prefix="/demo", tags=["demo"])


@router.post("/seed", response_model=List[DemoScenario])
def seed_demo(
    hospital_profile_id: str = Query(default="default"),
    store: EventStore = Depends(get_store),
    current_user: AuthenticatedUser = Depends(require_role(Role.ADMIN)),
) -> List[DemoScenario]:
    """Creates all twenty Phase 14.1 demo patients against a fresh
    database. Calling this more than once creates additional batches
    rather than de-duplicating -- intended for a clean DB per demo run."""
    profile = load_hospital_profile(hospital_profile_id)
    return seed_demo_patients(store, profile)


@router.post("/surge", response_model=SurgeSimulationResult)
def trigger_surge(
    hospital_profile_id: str = Query(default="default"),
    baseline_count: int = Query(default=10, ge=2),
    multiplier: int = Query(default=3, gt=1),
    store: EventStore = Depends(get_store),
    current_user: AuthenticatedUser = Depends(require_role(Role.ADMIN)),
) -> SurgeSimulationResult:
    """Phase 14.2's surge demo: creates a baseline population, then a
    `multiplier`x burst of additional arrivals, and returns concrete,
    checkable evidence for each of the six named surge-time properties
    (queue scaling + ordering, reassessment lapses, alert aggregation,
    a capacity conflict, stuck-patient accumulation, and one waiting
    patient auto-escalating past newer arrivals) -- see
    app/demo/surge.py's module docstring. Intended for a fresh/dedicated
    database, same as /demo/seed."""
    profile = load_hospital_profile(hospital_profile_id)
    return run_surge_simulation(store, profile, baseline_count=baseline_count, multiplier=multiplier)
