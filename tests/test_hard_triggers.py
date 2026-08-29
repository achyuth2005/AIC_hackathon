"""
Pure unit tests for Layer 4 hard escalation triggers (Phase 3.3) and the
shared TriggerCondition evaluator.
"""
from datetime import datetime, timezone

from app.config.hospital_profile import HardTriggerDefinition, TriggerCondition, load_hospital_profile
from app.models.enums import MeasurementStatus, ReliabilityTier
from app.scoring import concepts
from app.scoring.hard_triggers import evaluate_hard_triggers
from app.scoring.models import VitalReading
from app.scoring.trigger_conditions import evaluate_condition

PROFILE = load_hospital_profile("default")


def _reading(value, status=MeasurementStatus.MEASURED, stale=False, reliability_tier=ReliabilityTier.MACHINE_MEASURED):
    return VitalReading(
        value=value,
        measurement_status=status,
        observed_at=datetime.now(timezone.utc).replace(tzinfo=None),
        observation_id="obs-1",
        is_stale=stale,
        reliability_tier=reliability_tier,
    )


def test_lte_condition_fires_and_does_not_fire():
    condition = TriggerCondition(concept_code=concepts.SPO2, comparison="lte", numeric_threshold=85)
    assert evaluate_condition(_reading(80.0), condition) is True
    assert evaluate_condition(_reading(90.0), condition) is False


def test_condition_never_fires_on_missing_not_measured_or_stale_reading():
    condition = TriggerCondition(concept_code=concepts.SPO2, comparison="lte", numeric_threshold=85)
    assert evaluate_condition(None, condition) is False
    assert evaluate_condition(_reading(70.0, status=MeasurementStatus.NOT_MEASURED), condition) is False
    assert evaluate_condition(_reading(70.0, stale=True), condition) is False


def test_boolean_true_never_satisfies_a_numeric_condition():
    """bool is an int subclass in Python -- must not silently pass a
    numeric lte/gte threshold check."""
    condition = TriggerCondition(concept_code=concepts.SPO2, comparison="lte", numeric_threshold=85)
    assert evaluate_condition(_reading(True), condition) is False


def test_eq_condition_against_coded_value():
    condition = TriggerCondition(concept_code=concepts.CONSCIOUSNESS_LEVEL, comparison="eq", coded_value="UNRESPONSIVE")
    assert evaluate_condition(_reading("UNRESPONSIVE"), condition) is True
    assert evaluate_condition(_reading("ALERT"), condition) is False


def test_default_profile_hard_triggers_force_esi1_regardless_of_age_band():
    readings = {concepts.SPO2: _reading(80.0)}
    fired = evaluate_hard_triggers(readings, PROFILE.hard_trigger_definitions, "ADULT")
    assert any(t.trigger_id == "CRITICAL_HYPOXIA" for t in fired)
    assert all(t.target_esi_level == 1 for t in fired)


def test_age_scoped_trigger_only_fires_for_its_band():
    definitions = [
        HardTriggerDefinition(
            trigger_id="PAED_ONLY",
            label="Paediatric-only test trigger",
            condition=TriggerCondition(concept_code=concepts.SPO2, comparison="lte", numeric_threshold=90),
            applies_to_age_bands=["PAEDIATRIC"],
        )
    ]
    readings = {concepts.SPO2: _reading(85.0)}

    assert evaluate_hard_triggers(readings, definitions, "PAEDIATRIC") != []
    assert evaluate_hard_triggers(readings, definitions, "ADULT") == []


def test_unscoped_trigger_fires_for_every_band():
    definitions = [
        HardTriggerDefinition(
            trigger_id="ALL_BANDS",
            label="Applies everywhere",
            condition=TriggerCondition(concept_code=concepts.HEART_RATE, comparison="lte", numeric_threshold=30),
        )
    ]
    readings = {concepts.HEART_RATE: _reading(25.0)}
    for band in ("PAEDIATRIC", "ADULT", "GERIATRIC"):
        assert evaluate_hard_triggers(readings, definitions, band) != []


# ---------------------------------------------------------------------
# CP11 regression: adult-calibrated RR/HR/SBP hard triggers must not fire
# for values that are entirely normal within a paediatric patient's own
# PEWS reference range (self-discovered while building a demo scenario --
# see default.yaml's CP11 comment on hard_trigger_definitions).
# ---------------------------------------------------------------------
def test_healthy_infant_vitals_do_not_trip_the_adult_calibrated_triggers():
    # 160 bpm and 45 breaths/min sit inside PEWS's own INFANT normal range
    # (heart_rate_normal [100, 160], respiratory_rate_normal [30, 53]), and
    # 70 mmHg is literally that band's systolic-BP floor -- all three used
    # to trip the general, unscoped adult trigger before the CP11 fix.
    readings = {
        concepts.HEART_RATE: _reading(160.0),
        concepts.RESP_RATE: _reading(45.0),
        concepts.SYSTOLIC_BP: _reading(70.0),
    }
    fired = evaluate_hard_triggers(readings, PROFILE.hard_trigger_definitions, "PAEDIATRIC")
    assert fired == []


def test_genuinely_severe_paediatric_vitals_still_fire_the_paediatric_variant():
    readings = {concepts.HEART_RATE: _reading(215.0)}
    fired = evaluate_hard_triggers(readings, PROFILE.hard_trigger_definitions, "PAEDIATRIC")
    assert any(t.trigger_id == "SEVERE_TACHYCARDIA_PAEDIATRIC" for t in fired)


def test_adult_and_geriatric_bands_are_unaffected_by_the_paediatric_split():
    readings = {concepts.HEART_RATE: _reading(165.0)}
    for band in ("ADULT", "GERIATRIC"):
        fired = evaluate_hard_triggers(readings, PROFILE.hard_trigger_definitions, band)
        assert any(t.trigger_id == "SEVERE_TACHYCARDIA" for t in fired)
