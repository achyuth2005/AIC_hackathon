"""
Time Engine (Phase 5.1): three clocks, three distinct consequences.

    Clinical time    -> may change acuity (handled by the scoring stack
                        itself, CP3-CP6: symptom onset feeds the ML
                        challenger, trend feeds both ML deltas and this
                        module's deterioration_trend)
    Queue time       -> may NEVER change acuity (Phase 5.2); orders
                        patients within a band and drives reassessment
                        (this module: reassessment_status, ordering keys
                        consumed by guardian_queue.py)
    Operational time -> stuck-patient detection, CP9's Flow/Operations
                        Engine, not implemented here

Every function in this module is pure -- given the same RiskAssessment
history and `as_of`, always the same answer, independent of when it's
actually called. app/queue/guardian_queue.py is what fetches history from
the DB and decides whether/when to write (flag overdue, emit events).
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Optional

from app.config.hospital_profile import HospitalProfile
from app.models.enums import DeteriorationTrend
from app.models.risk_assessment import RiskAssessment
from app.queue.models import ReassessmentStatus
from app.timeutil import to_naive_utc, utcnow


def reassessment_status(
    final_acuity: Optional[int],
    last_reassessed_at: Optional[datetime],
    profile: HospitalProfile,
    as_of: Optional[datetime] = None,
) -> ReassessmentStatus:
    """Phase 5.3: 'Each acuity band has a hospital-configured reassessment
    interval. When a patient exceeds it, REASSESSMENT_DUE fires.'
    `final_acuity=None` (no assessment has ever run for this case) or
    `last_reassessed_at=None` degrade to 'not due' rather than raising --
    there is nothing to be overdue against yet."""
    now = to_naive_utc(as_of) if as_of is not None else utcnow()

    if last_reassessed_at is None:
        return ReassessmentStatus(is_due=False, interval_minutes=None, minutes_since_last_reassessment=0.0)

    minutes_elapsed = (now - last_reassessed_at).total_seconds() / 60.0
    interval_minutes = profile.reassessment_minutes_for(final_acuity) if final_acuity is not None else None

    if interval_minutes is None:
        # No configured interval for this acuity level -- can't be overdue
        # against a target that doesn't exist (a hospital-profile gap, not
        # a normal state; the default profile configures all 5 levels).
        return ReassessmentStatus(
            is_due=False, interval_minutes=None, minutes_since_last_reassessment=minutes_elapsed
        )

    is_due = minutes_elapsed > interval_minutes
    return ReassessmentStatus(
        is_due=is_due,
        interval_minutes=interval_minutes,
        minutes_since_last_reassessment=minutes_elapsed,
        minutes_overdue=(minutes_elapsed - interval_minutes) if is_due else None,
    )


def deterioration_trend(history: List[RiskAssessment]) -> DeteriorationTrend:
    """Phase 5.4: 'Two readings in the same acuity band moving in the
    wrong direction is a signal no single-point score captures.' Computed
    here from consecutive final_acuity values (lower ESI number = more
    urgent), NOT re-derived from raw vitals -- that comparison already
    lives in the ML challenger's trend-delta features (CP6); this is
    strictly about the Guardian Queue's own ordering, so it uses the
    system's own past conclusions, not the underlying physiology directly.
    `history` must be ordered oldest-first (EventStore.get_risk_assessment_history's contract)."""
    if len(history) < 2:
        return DeteriorationTrend.UNKNOWN

    previous, latest = history[-2], history[-1]
    if latest.final_acuity < previous.final_acuity:
        return DeteriorationTrend.WORSENING
    if latest.final_acuity > previous.final_acuity:
        return DeteriorationTrend.IMPROVING
    return DeteriorationTrend.STABLE


def time_in_current_band_minutes(history: List[RiskAssessment], as_of: Optional[datetime] = None) -> Optional[float]:
    """Phase 5.2 sort key 4 (fairness within a band): how long has this
    case held its CURRENT final_acuity, i.e. since the most recent point
    its acuity actually changed. Walks backward from the latest assessment
    while the acuity matches; returns None if there is no assessment at
    all yet. `history` must be ordered oldest-first."""
    if not history:
        return None

    now = to_naive_utc(as_of) if as_of is not None else utcnow()
    current_acuity = history[-1].final_acuity

    band_start = history[-1].computed_at
    for assessment in reversed(history):
        if assessment.final_acuity != current_acuity:
            break
        band_start = assessment.computed_at

    return (now - band_start).total_seconds() / 60.0
