"""
Phase 8.5 Alert Aggregation Engine endpoints: the interruptive-alert feed,
dismissal, and the alert-budget measurement.
"""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, Query

from app.alerts.budget import AlertBudgetReport, compute_alert_budget
from app.alerts.engine import sync_alerts
from app.api.deps import get_store
from app.auth.deps import get_current_user, require_hospital_scope, require_role
from app.auth.models import AuthenticatedUser
from app.auth.roles import Role
from app.config.hospital_profile import load_hospital_profile
from app.schemas.alert import AlertDismissRequest, AlertResponse
from app.store.event_store import EventStore, NotFoundError

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=List[AlertResponse])
def get_alerts(
    store: EventStore = Depends(get_store),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> List[AlertResponse]:
    """Phase 8.5's interruptive-alert feed -- deliberately NOT everything
    that changed; only a new critical-bypass patient, an upward acuity
    crossing, or the (aggregated) reassessment-overdue set. Reading this
    endpoint has documented side effects: it raises any newly-true
    condition as it finds it (see app/alerts/engine.py's module docstring
    -- same 'check on read' substitute as /queue and /ops/stuck-patients,
    since no scheduler exists in this prototype).

    Audit fix (Critical, dimension 1/IDOR): previously unauthenticated
    with a caller-suppliable hospital_profile_id -- anyone could read (and,
    via the side effect above, mutate) any hospital's alert feed. Now
    requires a staff token and is always scoped to that token's own
    hospital."""
    profile = load_hospital_profile(current_user.hospital_profile_id)
    alerts = sync_alerts(store, profile)
    return [AlertResponse.model_validate(a) for a in alerts]


@router.post("/{alert_id}/dismiss", response_model=AlertResponse)
def dismiss_alert(
    alert_id: str,
    body: AlertDismissRequest,
    store: EventStore = Depends(get_store),
    current_user: AuthenticatedUser = Depends(require_role(Role.NURSE, Role.DOCTOR, Role.ADMIN)),
) -> AlertResponse:
    """Phase 8.5: 'every alert is dismissible with a reason, and dismissal
    reasons feed the tuning loop.'"""
    alert = store.get_alert(alert_id)
    if alert is None:
        raise NotFoundError(f"No alert {alert_id}")
    # Audit fix (High, dimension 1/IDOR): Alert carries hospital_profile_id
    # directly, so tenancy is checked without an extra case lookup.
    require_hospital_scope(current_user, alert.hospital_profile_id)
    dismissed = store.dismiss_alert(
        alert_id,
        dismissed_by=current_user.user_id,
        reason_code=body.reason_code,
        free_text_reason=body.free_text_reason,
    )
    return AlertResponse.model_validate(dismissed)


@router.get("/budget", response_model=AlertBudgetReport)
def get_alert_budget(
    nurses_on_shift: float = Query(default=1.0, gt=0),
    window_minutes: int = Query(default=60, gt=0),
    store: EventStore = Depends(get_store),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> AlertBudgetReport:
    """Phase 8.5: 'set a target for interruptive alerts per nurse per
    hour, measure it in the demo, and show it on a slide.' `nurses_on_shift`
    has no roster to derive from in this prototype, so it is supplied by
    the caller (see app/alerts/budget.py's module docstring)."""
    profile = load_hospital_profile(current_user.hospital_profile_id)
    return compute_alert_budget(store, profile, nurses_on_shift=nurses_on_shift, window_minutes=window_minutes)
