"""
Layer 4 hard escalation triggers (Phase 3.3): "A small set of
hospital-configured single-parameter triggers that force top acuity
regardless of aggregate score." Evaluated inside the normal scoring
pipeline (app/scoring/engine.py) -- the case is still queued, just forced
to the front of it. NOT the same mechanism as Emergency Bypass
(app/bypass/engine.py), which skips the queue entirely; see
HardTriggerDefinition's docstring for why these are separate.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from app.config.hospital_profile import HardTriggerDefinition
from app.scoring.models import HardTriggerResult, VitalReading
from app.scoring.trigger_conditions import evaluate_condition


def evaluate_hard_triggers(
    readings: Dict[str, Optional[VitalReading]],
    definitions: List[HardTriggerDefinition],
    macro_age_band: str,
) -> List[HardTriggerResult]:
    """`macro_age_band` is the Age Router's PAEDIATRIC/ADULT/GERIATRIC band
    (not PEWS's finer sub-band) -- Layer 4 triggers are scoped at the same
    granularity as Layer 1 routing (Phase 3.3)."""
    fired: List[HardTriggerResult] = []
    for definition in definitions:
        if definition.applies_to_age_bands and macro_age_band not in definition.applies_to_age_bands:
            continue
        reading = readings.get(definition.condition.concept_code)
        if evaluate_condition(reading, definition.condition):
            fired.append(
                HardTriggerResult(
                    trigger_id=definition.trigger_id,
                    label=definition.label,
                    concept_code=definition.condition.concept_code,
                    raw_value=reading.value,
                    target_esi_level=definition.target_esi_level,
                )
            )
    return fired
