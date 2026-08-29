"""
Result types for the Time Engine and Guardian Queue (Phase 5).
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.enums import ConfidenceBand, DeteriorationTrend, NurseAttentionFlag
from app.ops.wait_time import WaitTimeEstimate


class ReassessmentStatus(BaseModel):
    """Phase 5.3: whether this case has exceeded its acuity band's
    configured reassessment interval."""
    is_due: bool
    interval_minutes: Optional[int]  # None if the acuity level has no configured interval
    minutes_since_last_reassessment: float
    minutes_overdue: Optional[float] = None  # populated only when is_due


class QueueEntry(BaseModel):
    """One row of the Guardian Queue (Phase 5.2). Sort key fields
    (final_acuity, time_critical_pathway, deterioration_trend,
    time_in_current_band, arrival_time) are ALWAYS populated so the
    lexicographic order in build_queue() is total and reproducible; the
    rest are display/context fields for the nurse dashboard (Phase 8.2)."""
    case_id: str
    display_name: Optional[str]
    mrn: Optional[str]

    final_acuity: int
    confidence_band: Optional[ConfidenceBand]
    should_abstain: bool

    # Sort keys, in lexicographic priority order (Phase 5.2):
    time_critical_pathway_flag: bool  # always False until a pathway-flagging engine exists -- see docstring in guardian_queue.py
    deterioration_trend: DeteriorationTrend
    time_in_current_band_minutes: Optional[float]
    arrival_time: datetime

    # Context, not sort keys:
    waiting_minutes: float
    reassessment: ReassessmentStatus
    emergency_bypass_active: bool
    wait_time_estimate: WaitTimeEstimate  # Phase 6.4 -- always a range, never a single number

    # Phase 8.2 nurse-dashboard presentation fields (CP15): computed here,
    # not left for the frontend to re-derive from the raw pieces above.
    one_line_presentation: Optional[str]  # from the latest current SYMPTOM_TEXT, truncated
    primary_attention_flag: NurseAttentionFlag
