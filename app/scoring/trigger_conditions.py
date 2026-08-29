"""
Evaluates a single TriggerCondition (app/config/hospital_profile.py) against
a VitalReading. Shared by Layer 4 hard triggers (app/scoring/hard_triggers.py)
and Emergency Bypass's physiological detector (app/bypass/engine.py) --
one evaluation rule, two independently-configured trigger lists consuming it.
"""
from __future__ import annotations

from typing import Optional

from app.config.hospital_profile import TriggerCondition
from app.models.enums import MeasurementStatus
from app.scoring.models import VitalReading


def evaluate_condition(reading: Optional[VitalReading], condition: TriggerCondition) -> bool:
    """A trigger only fires on positive evidence: missing, not-measured, or
    stale readings never fire (Phase 3.3 'missing is not normal' cuts both
    ways -- absence of a reading is not evidence of a crisis either).
    Handled instead by the missing-data cap in news2.py/pews.py."""
    if reading is None:
        return False
    if reading.measurement_status != MeasurementStatus.MEASURED:
        return False
    if reading.is_stale:
        return False

    if condition.comparison == "lte":
        return _is_plain_number(reading.value) and reading.value <= condition.numeric_threshold
    if condition.comparison == "gte":
        return _is_plain_number(reading.value) and reading.value >= condition.numeric_threshold
    if condition.comparison == "eq":
        if condition.coded_value is not None:
            return reading.value == condition.coded_value
        if condition.boolean_value is not None:
            return isinstance(reading.value, bool) and reading.value == condition.boolean_value
        return False
    return False  # pragma: no cover - exhaustive by Literal type


def _is_plain_number(value) -> bool:
    # bool is a subclass of int in Python; a boolean value must never
    # satisfy a numeric lte/gte comparison.
    return isinstance(value, (int, float)) and not isinstance(value, bool)
