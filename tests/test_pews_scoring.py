"""
Pure unit tests for PEWS-style paediatric scoring (Phase 3.3 Layer 2,
paediatric backbone) -- no DB involved.
"""
from datetime import datetime, timezone

from app.config.hospital_profile import load_hospital_profile
from app.scoring import concepts
from app.scoring.models import VitalReading
from app.scoring.pews import score_pews
from app.models.enums import MeasurementStatus, ReliabilityTier

PROFILE = load_hospital_profile("default")


def _reading(value, stale=False, reliability_tier=ReliabilityTier.MACHINE_MEASURED):
    return VitalReading(
        value=value,
        measurement_status=MeasurementStatus.MEASURED,
        observed_at=datetime.now(timezone.utc).replace(tzinfo=None),
        observation_id="obs-1",
        is_stale=stale,
        reliability_tier=reliability_tier,
    )


def _toddler_band():
    return PROFILE.pews.band_for_age(3)  # TODDLER: 1 <= age < 5


def _normal_toddler_readings():
    band = _toddler_band()
    rr_low, rr_high = band.respiratory_rate_normal
    hr_low, hr_high = band.heart_rate_normal
    sbp_low, sbp_high = band.systolic_bp_normal
    return {
        concepts.RESP_RATE: _reading((rr_low + rr_high) / 2),
        concepts.SPO2: _reading(98.0),
        concepts.SUPPLEMENTAL_OXYGEN: _reading(False),
        concepts.SYSTOLIC_BP: _reading((sbp_low + sbp_high) / 2),
        concepts.HEART_RATE: _reading((hr_low + hr_high) / 2),
        concepts.CONSCIOUSNESS_LEVEL: _reading("ALERT"),
        concepts.TEMPERATURE: _reading(37.0),
        concepts.WORK_OF_BREATHING: _reading("NORMAL"),
    }


def test_age_band_resolution():
    assert PROFILE.pews.band_for_age(0.5).name == "INFANT"
    assert PROFILE.pews.band_for_age(3).name == "TODDLER"
    assert PROFILE.pews.band_for_age(8).name == "CHILD"
    assert PROFILE.pews.band_for_age(14).name == "ADOLESCENT"
    assert PROFILE.pews.band_for_age(16) is None  # 16+ routes to ADULT at Layer 1, not PEWS


def test_normal_toddler_vitals_score_zero():
    result = score_pews(_normal_toddler_readings(), PROFILE.pews, _toddler_band())
    assert result.aggregate_score == 0
    assert result.rule_acuity == 5
    assert result.age_band == "TODDLER"
    assert result.framework == "PEWS"


def test_respiratory_rate_far_outside_normal_range_scores_high_deviation():
    band = _toddler_band()
    rr_low, _ = band.respiratory_rate_normal
    readings = _normal_toddler_readings()
    readings[concepts.RESP_RATE] = _reading(rr_low * 0.5)  # 50% below the low bound -> beyond both thresholds
    result = score_pews(readings, PROFILE.pews, band)

    rr_component = next(c for c in result.components if c.concept_code == concepts.RESP_RATE)
    assert rr_component.points == 3  # beyond both [0.15, 0.30] thresholds


def test_mild_deviation_scores_one_point():
    band = _toddler_band()
    rr_low, rr_high = band.respiratory_rate_normal
    readings = _normal_toddler_readings()
    readings[concepts.RESP_RATE] = _reading(rr_high * 1.05)  # 5% above high bound -> within 15% threshold
    result = score_pews(readings, PROFILE.pews, band)

    rr_component = next(c for c in result.components if c.concept_code == concepts.RESP_RATE)
    assert rr_component.points == 1


def test_severe_work_of_breathing_triggers_single_parameter_escalation():
    """Phase 3.3: qualitative signs like work of breathing matter more than
    numbers for paediatrics -- this is the only parameter with no numeric
    equivalent in NEWS2 at all."""
    readings = _normal_toddler_readings()
    readings[concepts.WORK_OF_BREATHING] = _reading("SEVERE")
    result = score_pews(readings, PROFILE.pews, _toddler_band())

    assert result.single_parameter_escalation is True
    assert result.rule_acuity == PROFILE.pews.single_parameter_escalation_esi_level


def test_missing_vital_caps_acuity_even_when_rest_is_normal():
    readings = _normal_toddler_readings()
    readings[concepts.SYSTOLIC_BP] = None
    result = score_pews(readings, PROFILE.pews, _toddler_band())

    assert result.missing_data_cap_applied is True
    assert result.rule_acuity == PROFILE.pews.missing_data_cap_esi_level


def test_zero_observations_at_all_does_not_crash_and_holds_at_cap():
    """Phase 14.1 patient #14 shape: missing vitals entirely."""
    empty_readings = {c: None for c in concepts.PAEDIATRIC_REQUIRED_CONCEPTS}
    result = score_pews(empty_readings, PROFILE.pews, _toddler_band())

    assert result.aggregate_score is None
    assert result.rule_acuity == PROFILE.pews.missing_data_cap_esi_level
    assert all(c.is_missing for c in result.components)
