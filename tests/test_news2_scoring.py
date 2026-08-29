"""
Pure unit tests for NEWS2/geriatric scoring math (Phase 3.3 Layer 2, adult
backbone + Layer 1 geriatric adjustment) -- no DB involved, VitalReading
constructed directly.
"""
from datetime import datetime, timezone

import pytest

from app.config.hospital_profile import load_hospital_profile
from app.models.enums import MeasurementStatus, ReliabilityTier
from app.scoring import concepts
from app.scoring.models import VitalReading
from app.scoring.news2 import score_news2

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


def _normal_adult_readings():
    return {
        concepts.RESP_RATE: _reading(16.0),
        concepts.SPO2: _reading(98.0),
        concepts.SUPPLEMENTAL_OXYGEN: _reading(False),
        concepts.SYSTOLIC_BP: _reading(120.0),
        concepts.HEART_RATE: _reading(75.0),
        concepts.CONSCIOUSNESS_LEVEL: _reading("ALERT"),
        concepts.TEMPERATURE: _reading(37.0),
    }


def test_all_normal_adult_vitals_score_zero_and_lowest_acuity():
    result = score_news2(_normal_adult_readings(), PROFILE.news2, PROFILE.news2, "ADULT")
    assert result.aggregate_score == 0
    assert result.rule_acuity == 5
    assert result.single_parameter_escalation is False
    assert result.has_any_missing_or_stale is False


def test_single_red_parameter_escalates_past_its_own_aggregate_band():
    """Respiratory rate <=8 scores 3 (NEWS2's own 'red score' rule). Aggregate
    alone (3) would land in the 1-4 -> ESI4 band, but the single-parameter
    rule must independently force the tighter ESI2, proving NEWS2's own
    escalation logic isn't silently subsumed by the aggregate."""
    readings = _normal_adult_readings()
    readings[concepts.RESP_RATE] = _reading(6.0)  # <=8 -> 3 points
    result = score_news2(readings, PROFILE.news2, PROFILE.news2, "ADULT")

    assert result.aggregate_score == 3
    assert result.single_parameter_escalation is True
    assert result.rule_acuity == 2
    assert "Respiratory rate" in result.single_parameter_escalation_reason


def test_multi_parameter_moderate_derangement_without_single_param_trigger():
    readings = _normal_adult_readings()
    readings[concepts.RESP_RATE] = _reading(22.0)  # 21-24 -> 2
    readings[concepts.HEART_RATE] = _reading(95.0)  # 91-110 -> 1
    readings[concepts.SYSTOLIC_BP] = _reading(95.0)  # 91-100 -> 2
    result = score_news2(readings, PROFILE.news2, PROFILE.news2, "ADULT")

    assert result.aggregate_score == 5  # 2 + 1 + 2
    assert result.single_parameter_escalation is False
    assert result.rule_acuity == 3  # 5-6 band


def test_supplemental_oxygen_adds_points():
    readings = _normal_adult_readings()
    readings[concepts.SUPPLEMENTAL_OXYGEN] = _reading(True)
    result = score_news2(readings, PROFILE.news2, PROFILE.news2, "ADULT")
    assert result.aggregate_score == PROFILE.news2.supplemental_oxygen_points


def test_missing_vital_is_excluded_not_scored_as_normal_and_caps_acuity():
    readings = _normal_adult_readings()
    readings[concepts.TEMPERATURE] = None  # never recorded
    result = score_news2(readings, PROFILE.news2, PROFILE.news2, "ADULT")

    temp_component = next(c for c in result.components if c.concept_code == concepts.TEMPERATURE)
    assert temp_component.is_missing is True
    assert temp_component.points is None
    assert temp_component.missing_reason == "NO_OBSERVATION_RECORDED"

    # Everything else is normal (aggregate 0 among present params), but
    # missing data must cap acuity at the configured cap, not read as "fine".
    assert result.aggregate_score == 0
    assert result.missing_data_cap_applied is True
    assert result.rule_acuity == PROFILE.news2.missing_data_cap_esi_level


def test_stale_vital_is_treated_as_missing():
    readings = _normal_adult_readings()
    readings[concepts.SPO2] = _reading(98.0, stale=True)
    result = score_news2(readings, PROFILE.news2, PROFILE.news2, "ADULT")

    spo2_component = next(c for c in result.components if c.concept_code == concepts.SPO2)
    assert spo2_component.is_missing is True
    assert spo2_component.missing_reason == "STALE"
    assert result.has_any_missing_or_stale is True


def test_not_measured_status_is_treated_as_missing_not_as_a_zero():
    readings = _normal_adult_readings()
    readings[concepts.HEART_RATE] = _reading(None, status=MeasurementStatus.NOT_MEASURED)
    result = score_news2(readings, PROFILE.news2, PROFILE.news2, "ADULT")

    hr_component = next(c for c in result.components if c.concept_code == concepts.HEART_RATE)
    assert hr_component.is_missing is True
    assert hr_component.missing_reason == "NOT_MEASURED"


def test_geriatric_adjustment_escalates_earlier_than_adult_for_identical_vitals():
    """Phase 14.1 patient #6: 'why adult-calibrated thresholds under-triage
    the elderly'. Same physiological readings, scored two ways."""
    readings = _normal_adult_readings()
    # A single 1-point derangement: below NEWS2's own "red" threshold of 3
    # (adult ignores it) but at/above the geriatric adjustment's tightened
    # threshold of 1 (geriatric escalates on it).
    readings[concepts.HEART_RATE] = _reading(45.0)  # 41-50 -> 1 point

    as_adult = score_news2(readings, PROFILE.news2, PROFILE.news2, "ADULT")
    as_geriatric = score_news2(readings, PROFILE.news2, PROFILE.geriatric_adjustment, "GERIATRIC")

    assert as_adult.single_parameter_escalation is False  # adult threshold is 3
    assert as_geriatric.single_parameter_escalation is True  # geriatric threshold is 1
    assert as_geriatric.rule_acuity < as_adult.rule_acuity  # more urgent (lower ESI number)


def test_avpu_non_alert_triggers_single_parameter_escalation():
    readings = _normal_adult_readings()
    readings[concepts.CONSCIOUSNESS_LEVEL] = _reading("PAIN")
    result = score_news2(readings, PROFILE.news2, PROFILE.news2, "ADULT")
    assert result.single_parameter_escalation is True
    assert result.rule_acuity == PROFILE.news2.single_parameter_escalation_esi_level
