"""
Emergency Bypass orchestration (Phase 3.5): "Three independent paths, any of
which can fire, none of which can cancel another."

  1. Human affordance -- has no detection logic at all by design. It is
     just app/api/cases.py's POST /cases/{id}/emergency-bypass endpoint
     calling EventStore.activate_emergency_bypass directly.
  2. Deterministic physiological trigger -- implemented here, reusing the
     same TriggerCondition evaluator as Layer 4 hard triggers
     (app/scoring/trigger_conditions.py) against a SEPARATE, independently
     configured trigger list (`emergency_bypass_physiological_triggers`).
  3. Constrained critical-phrase text detector -- implemented here via
     app/bypass/text_patterns.py, scanning the case's latest SYMPTOM_TEXT
     observation.

This is NOT the same mechanism as Phase 3.3 Layer 4 hard triggers
(app/scoring/hard_triggers.py, run inside app/scoring/engine.py). Hard
triggers force a high acuity *within* the normal scoring/queue pipeline;
Emergency Bypass skips the pipeline and queue entirely. The same
physiological state (e.g. unresponsive) firing both is expected and
correct, not a bug -- Phase 3.5 explicitly wants redundant paths to the
same safety outcome.

Call `evaluate_and_activate` right after any new observation is recorded
for a case (Phase 3.5: "evaluated the instant any vital arrives") -- see
the hook in app/api/cases.py's add_observation route.
"""
from __future__ import annotations

from typing import Optional

from app.config.hospital_profile import HospitalProfile
from app.models.case import Case
from app.models.enums import BypassSource
from app.bypass.text_patterns import detect_critical_phrase
from app.scoring import concepts
from app.scoring.readings import fetch_readings
from app.scoring.trigger_conditions import evaluate_condition
from app.store.event_store import EventStore


def evaluate_and_activate(case: Case, store: EventStore, profile: HospitalProfile) -> Optional[Case]:
    """Runs both automatic detectors (#2 physiological, #3 text) against
    the case's current observations. Returns the updated Case if bypass was
    (newly or again) activated, else None. Never raises on missing data --
    like the hard triggers, an absent/stale reading simply does not fire
    (Phase 3.3's 'missing is not normal' cuts both ways: absence is not
    evidence of crisis either)."""
    physiological_hit = _evaluate_physiological(case, store, profile)
    if physiological_hit is not None:
        trigger_id, label, raw_value = physiological_hit
        return store.activate_emergency_bypass(
            case.case_id,
            source=BypassSource.PHYSIOLOGICAL,
            reason=f"{label} (value={raw_value})",
            trigger_id=trigger_id,
        )

    text_hit = _evaluate_text(case, store, profile)
    if text_hit is not None:
        return store.activate_emergency_bypass(
            case.case_id,
            source=BypassSource.TEXT_PATTERN,
            reason=f"Critical phrase matched: '{text_hit}'",
            trigger_id=None,
        )

    return None


def _evaluate_physiological(case: Case, store: EventStore, profile: HospitalProfile):
    triggers = profile.emergency_bypass_physiological_triggers
    if not triggers:
        return None

    concept_codes = list({t.condition.concept_code for t in triggers})
    readings = fetch_readings(store, case.case_id, concept_codes, profile)

    for trigger in triggers:
        reading = readings.get(trigger.condition.concept_code)
        if evaluate_condition(reading, trigger.condition):
            return trigger.trigger_id, trigger.label, reading.value
    return None


def _evaluate_text(case: Case, store: EventStore, profile: HospitalProfile) -> Optional[str]:
    if not profile.emergency_bypass_critical_phrases:
        return None
    text_obs = store.get_latest_current_observation(case.case_id, concepts.SYMPTOM_TEXT)
    if text_obs is None or text_obs.value_text is None:
        return None
    return detect_critical_phrase(text_obs.value_text, profile.emergency_bypass_critical_phrases)
