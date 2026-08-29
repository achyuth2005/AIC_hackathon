"""
Phase 9.6/9.7 read surfaces: the retrospective-review queue for flagged
de-escalations, and the override/equity monitoring report. The write side
(making an override) is case-scoped and lives in app/api/cases.py
alongside the other case actions (emergency-bypass, assign-resource, ...).
"""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_store
from app.audit.monitoring import OverrideMonitoringReport, compute_override_monitoring
from app.auth.deps import require_role
from app.auth.roles import Role
from app.config.hospital_profile import load_hospital_profile
from app.schemas.human_decision import HumanDecisionResponse
from app.store.event_store import EventStore

router = APIRouter(prefix="/overrides", tags=["audit"])


@router.get("/flagged-for-review", response_model=List[HumanDecisionResponse])
def list_flagged_for_review(
    hospital_profile_id: str = Query(default="default"),
    store: EventStore = Depends(get_store),
    _current_user=Depends(require_role(Role.NURSE, Role.DOCTOR, Role.ADMIN)),
) -> List[HumanDecisionResponse]:
    """Phase 9.6: every de-escalation is 'flagged for retrospective
    review.' Read-only queue -- no 'mark reviewed' mutation exists yet
    (see EventStore.list_flagged_for_review's docstring); closing the loop
    on a flagged review is a distinct, unscoped piece of follow-on work."""
    return [HumanDecisionResponse.model_validate(d) for d in store.list_flagged_for_review(hospital_profile_id)]


@router.get("/monitoring", response_model=OverrideMonitoringReport)
def get_override_monitoring(
    hospital_profile_id: str = Query(default="default"),
    store: EventStore = Depends(get_store),
    _current_user=Depends(require_role(Role.ADMIN)),
) -> OverrideMonitoringReport:
    """Phase 9.6 ('override rate and direction ... primary model-
    monitoring signals') + Phase 9.7 ('measure acuity distribution and
    override rate by demographic subgroup as a standing evaluation
    output'). ADMIN-only: this is an oversight/equity report, not a
    point-of-care view -- Phase 10.2's 'least privilege by role' applied
    to the one read surface in this checkpoint where it has an obvious,
    narrow answer, rather than retrofitting role-scoping onto every
    existing endpoint (see CP9.5's checkpoint report for that scope
    boundary)."""
    profile = load_hospital_profile(hospital_profile_id)
    return compute_override_monitoring(store, profile)
