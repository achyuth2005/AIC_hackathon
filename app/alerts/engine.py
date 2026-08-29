"""
Alert Aggregation Engine (Phase 8.5): "The queue is the notification.
Ambient by default. Only three things interrupt: a new critical-bypass
patient, a patient crossing into a higher acuity band, and a reassessment
past its hard limit."

Like Stuck Patient Detection (CP9) and the Guardian Queue's own reassessment
flagging (CP7), this prototype has no scheduler -- there is no background
process to notice these three conditions the instant they occur. `sync_alerts`
is the same "check on read" substitute used everywhere else: called whenever
a nurse/control-tower view reads the alert feed, it raises any newly-true
condition as an Alert row (deduped so it is never raised twice for the same
underlying fact) and returns the current open list.

Deliberately NOT alerts: deterioration trend shown in queue ordering, stuck
patients on the ops list, capacity conflicts surfaced via 409. Those are all
ambient/on-demand by design (Phase 8.5's whole point) -- adding them here
would be exactly the alert-fatigue mistake this engine exists to prevent.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from app.config.hospital_profile import HospitalProfile
from app.models.enums import AlertType, CaseStatus
from app.store.event_store import EventStore
from app.timeutil import to_naive_utc, utcnow


def _sync_critical_bypass_alerts(store: EventStore, profile: HospitalProfile, as_of: datetime) -> None:
    """'A NEW critical-bypass patient' -- keyed by case, not by event: a
    second detector firing for an already-critical case (Phase 3.5's
    'any of which can fire, none of which can cancel another') is not a
    new interrupt, so it must not raise a second alert."""
    for case in store.list_cases():
        if case.hospital_profile_id != profile.profile_id:
            continue
        if not case.emergency_bypass_active:
            continue
        if store.existing_alert_for_case(AlertType.CRITICAL_BYPASS_PATIENT, case.case_id) is not None:
            continue
        store.create_alert(
            hospital_profile_id=profile.profile_id,
            alert_type=AlertType.CRITICAL_BYPASS_PATIENT,
            payload={
                "case_id": case.case_id,
                "source": case.emergency_bypass_last_source.value if case.emergency_bypass_last_source else None,
                "reason": case.emergency_bypass_last_reason,
            },
            dedupe_case_id=case.case_id,
            occurred_at=case.emergency_bypass_first_activated_at or as_of,
        )


def _sync_acuity_escalation_alerts(store: EventStore, profile: HospitalProfile, as_of: datetime) -> None:
    """'A patient crossing into a higher (more urgent) acuity band' --
    keyed by the resulting RiskAssessment.assessment_id: each genuine
    worsening transition in a case's history is its own dedupe unit, so a
    case with several real escalations over its stay raises one alert per
    transition, not one per case."""
    for case in store.list_cases():
        if case.hospital_profile_id != profile.profile_id or case.status == CaseStatus.DISPOSED:
            continue
        history = store.get_risk_assessment_history(case.case_id)
        for previous, current in zip(history, history[1:]):
            if current.final_acuity >= previous.final_acuity:
                continue  # not more urgent than before -- not a crossing
            if store.existing_alert_for_assessment(current.assessment_id) is not None:
                continue
            store.create_alert(
                hospital_profile_id=profile.profile_id,
                alert_type=AlertType.ACUITY_BAND_CROSSED_UPWARD,
                payload={
                    "case_id": case.case_id,
                    "from_acuity": previous.final_acuity,
                    "to_acuity": current.final_acuity,
                    "assessment_id": current.assessment_id,
                },
                dedupe_case_id=case.case_id,
                dedupe_assessment_id=current.assessment_id,
                occurred_at=current.computed_at,
            )


def _sync_reassessment_overdue_aggregate(store: EventStore, profile: HospitalProfile, as_of: datetime) -> None:
    """'Three overdue reassessments is one notification, not three.' At
    most one undismissed REASSESSMENT_OVERDUE_AGGREGATE alert exists per
    hospital profile at a time; its payload (member case_ids + count) is
    refreshed in place as the overdue set changes, rather than raising a
    fresh alert per newly-overdue case. If the set empties out before a
    human dismisses it, the system resolves it automatically -- there is
    nothing left to interrupt anyone about."""
    from app.models.enums import AlertDismissalReasonCode

    overdue_case_ids = sorted(
        c.case_id
        for c in store.list_cases(status=CaseStatus.ACTIVE)
        if c.hospital_profile_id == profile.profile_id and c.reassessment_overdue
    )
    existing = store.get_open_aggregate_alert(profile.profile_id)

    if not overdue_case_ids:
        if existing is not None:
            store.dismiss_alert(
                existing.alert_id,
                dismissed_by="SYSTEM",
                reason_code=AlertDismissalReasonCode.RESOLVED_AUTOMATICALLY,
                free_text_reason="No cases remain reassessment-overdue.",
                occurred_at=as_of,
            )
        return

    payload = {"case_ids": overdue_case_ids, "count": len(overdue_case_ids)}
    if existing is None:
        store.create_alert(
            hospital_profile_id=profile.profile_id,
            alert_type=AlertType.REASSESSMENT_OVERDUE_AGGREGATE,
            payload=payload,
            occurred_at=as_of,
        )
    elif existing.payload != payload:
        store.update_alert_payload(existing.alert_id, payload)


def sync_alerts(store: EventStore, profile: HospitalProfile, as_of: Optional[datetime] = None) -> List:
    """Raises any newly-true one of the three Phase 8.5 interrupt
    conditions (deduped) and returns every currently-open (undismissed)
    Alert for this hospital profile."""
    now = to_naive_utc(as_of) if as_of is not None else utcnow()
    _sync_critical_bypass_alerts(store, profile, now)
    _sync_acuity_escalation_alerts(store, profile, now)
    _sync_reassessment_overdue_aggregate(store, profile, now)
    return store.list_alerts(profile.profile_id)
