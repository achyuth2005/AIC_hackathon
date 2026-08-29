"""
Result types for the Flow/Operations Engine (Phase 6).
"""
from __future__ import annotations

from pydantic import BaseModel


class StuckPatternResult(BaseModel):
    """Phase 6.3: one instance of 'an expected next event has not occurred
    within its configured window.' Always operational, never a clinical
    acuity signal -- these route to a nurse/doctor ops list, never into
    the scoring stack (contrast with CP7/8's reassessment-overdue pattern,
    which Phase 6.3's own table marks as the one CLINICAL pattern among
    the five, and which is handled entirely separately by
    app/queue/time_engine.py, not this module)."""
    pattern_id: str
    label: str
    case_id: str
    minutes_overdue: float
    route_to: str  # "NURSE_OPS" | "DOCTOR_QUEUE" | "CHARGE_NURSE"
