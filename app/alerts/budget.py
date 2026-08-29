"""
Alert budget measurement (Phase 8.5): "Set a target for interruptive
alerts per nurse per hour, measure it in the demo, and show it on a
slide." The target itself lives in HospitalProfile.alert_budget_targets
(already configured since CP1's default.yaml); this module is the
measurement side that target was always waiting on.

[Assumption]: this prototype has no staff-roster/shift concept, so
`nurses_on_shift` is supplied by the caller (a fixed number for a demo, or
whatever a future roster integration would provide) rather than derived
from anything stored here.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
from typing import Dict, Optional

from pydantic import BaseModel

from app.config.hospital_profile import HospitalProfile
from app.store.event_store import EventStore
from app.timeutil import to_naive_utc, utcnow

_TARGET_KEY = "interruptive_alerts_per_nurse_per_hour"


class AlertBudgetReport(BaseModel):
    window_minutes: int
    nurses_on_shift: float
    interruptive_alerts_in_window: int
    alerts_per_nurse_per_hour: float
    target_alerts_per_nurse_per_hour: Optional[float]
    within_budget: Optional[bool]
    breakdown_by_type: Dict[str, int]


def compute_alert_budget(
    store: EventStore,
    profile: HospitalProfile,
    *,
    nurses_on_shift: float = 1.0,
    window_minutes: int = 60,
    as_of: Optional[datetime] = None,
) -> AlertBudgetReport:
    now = to_naive_utc(as_of) if as_of is not None else utcnow()
    since = now - timedelta(minutes=window_minutes)

    # Every alert raised in the window counts, dismissed or not -- it
    # still interrupted someone at the moment it fired (Phase 8.5 measures
    # interruptions, not a live backlog; that's what GET /alerts is for).
    alerts_in_window = store.list_alerts_since(profile.profile_id, since)
    count = len(alerts_in_window)
    hours = window_minutes / 60.0

    rate = (count / (nurses_on_shift * hours)) if nurses_on_shift > 0 and hours > 0 else 0.0
    target = profile.alert_budget_targets.get(_TARGET_KEY)
    within_budget = (rate <= target) if target is not None else None

    breakdown = Counter(a.alert_type.value for a in alerts_in_window)

    return AlertBudgetReport(
        window_minutes=window_minutes,
        nurses_on_shift=nurses_on_shift,
        interruptive_alerts_in_window=count,
        alerts_per_nurse_per_hour=round(rate, 2),
        target_alerts_per_nurse_per_hour=target,
        within_budget=within_budget,
        breakdown_by_type=dict(breakdown),
    )
