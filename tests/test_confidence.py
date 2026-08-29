"""
Pure unit tests for the Confidence & Abstention Engine (Phase 9.1, 9.2).
Builds ClinicalScoreResult fixtures via the real NEWS2/PEWS scorers (CP3)
rather than hand-constructing them, so these tests exercise the real
integration shape, not a mock.
"""
from datetime import datetime, timezone

from app.config.hospital_profile import load_hospital_profile
from app.models.enums import ConfidenceBand, MeasurementStatus, ReliabilityTier
from app.scoring import concepts
from app.scoring.confidence import compute_confidence
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


def _normal_adult_readings(**overrides):
    readings = {
        concepts.RESP_RATE: _reading(16.0),
        concepts.SPO2: _reading(98.0),
        concepts.SUPPLEMENTAL_OXYGEN: _reading(False),
        concepts.SYSTOLIC_BP: _reading(120.0),
        concepts.HEART_RATE: _reading(75.0),
        concepts.CONSCIOUSNESS_LEVEL: _reading("ALERT"),
        concepts.TEMPERATURE: _reading(37.0),
    }
    readings.update(overrides)
    return readings


def _score(readings):
    return score_news2(readings, PROFILE.news2, PROFILE.news2, "ADULT")


def test_all_normal_machine_measured_no_ml_is_high_confidence():
    result = _score(_normal_adult_readings())
    confidence = compute_confidence(result, PROFILE, ml_suggested_acuity=None)

    assert confidence.band == ConfidenceBand.HIGH
    assert confidence.should_abstain is False
    assert confidence.final_acuity == result.rule_acuity
    assert confidence.ml_considered is False
    assert any("ML" in r for r in confidence.reasons)  # still disclosed even though it doesn't tank confidence


def test_zero_width_band_is_not_flagged_as_borderline():
    """Regression guard: a perfectly normal aggregate of 0 sits in NEWS2's
    zero-width [0,0] band. Every healthy patient must not be flagged
    'borderline' just because that band has no interior."""
    result = _score(_normal_adult_readings())
    confidence = compute_confidence(result, PROFILE, ml_suggested_acuity=result.framework_acuity)
    assert not any("borderline" in r.lower() for r in confidence.reasons)


def test_missing_vitals_lower_confidence_and_are_named_in_reasons():
    readings = _normal_adult_readings()
    readings[concepts.TEMPERATURE] = None
    readings[concepts.HEART_RATE] = None
    result = _score(readings)

    confidence = compute_confidence(result, PROFILE, ml_suggested_acuity=result.framework_acuity)
    assert confidence.band != ConfidenceBand.HIGH
    combined_reasons = " ".join(confidence.reasons)
    assert "Temperature" in combined_reasons
    assert "Pulse" in combined_reasons  # NEWS2's label for HEART_RATE
    # Missing data never lowers acuity -- it's already floored by CP3/4's own cap.
    assert confidence.final_acuity <= result.rule_acuity


def test_patient_reported_only_vitals_lower_confidence():
    readings = _normal_adult_readings(
        **{
            concepts.RESP_RATE: _reading(16.0, reliability_tier=ReliabilityTier.PATIENT_REPORTED),
            concepts.HEART_RATE: _reading(75.0, reliability_tier=ReliabilityTier.PATIENT_REPORTED),
        }
    )
    result = _score(readings)

    all_machine = compute_confidence(_score(_normal_adult_readings()), PROFILE, ml_suggested_acuity=5)
    self_reported = compute_confidence(result, PROFILE, ml_suggested_acuity=5)

    assert self_reported.score < all_machine.score
    assert any("lower-reliability" in r for r in self_reported.reasons)


def test_ml_agreement_scores_higher_than_ml_disagreement():
    result = _score(_normal_adult_readings())  # framework_acuity == 5

    agree = compute_confidence(result, PROFILE, ml_suggested_acuity=5)
    disagree = compute_confidence(result, PROFILE, ml_suggested_acuity=2)  # ML wants to escalate hard

    assert agree.ml_considered is True
    assert disagree.ml_considered is True
    assert agree.score > disagree.score
    assert any("ESI 2" in r for r in disagree.reasons)


def test_borderline_aggregate_near_a_real_band_edge_lowers_confidence():
    # Band 1-4 (ESI4): aggregate exactly at the lower edge (1 point) is
    # borderline against the healthier 0-point band.
    readings = _normal_adult_readings()
    readings[concepts.HEART_RATE] = _reading(45.0)  # 41-50 -> 1 point
    result = _score(readings)
    assert result.aggregate_score == 1

    confidence = compute_confidence(result, PROFILE, ml_suggested_acuity=result.framework_acuity)
    assert any("borderline" in r.lower() for r in confidence.reasons)


def test_no_vitals_at_all_forces_abstention_not_just_low_confidence():
    """Phase 9.2: a total data void must abstain outright, with the
    explicit 'insufficient information ... nurse assessment required'
    message, and must never fall back to a default low (safe-looking)
    level."""
    empty_readings = {c: None for c in concepts.ADULT_REQUIRED_CONCEPTS}
    result = _score(empty_readings)

    confidence = compute_confidence(result, PROFILE, ml_suggested_acuity=None)
    assert confidence.should_abstain is True
    assert "nurse assessment required" in confidence.abstention_message.lower()
    assert confidence.final_acuity == min(result.rule_acuity, PROFILE.confidence.abstention_minimum_acuity)
    assert confidence.band == ConfidenceBand.LOW


def test_confidence_never_makes_acuity_less_urgent():
    """The core Phase 9.1 invariant: whatever confidence computes, it can
    only hold the final acuity at the same level or a MORE urgent one,
    never relax it."""
    readings = _normal_adult_readings()
    readings[concepts.TEMPERATURE] = None
    result = _score(readings)

    confidence = compute_confidence(result, PROFILE, ml_suggested_acuity=None)
    assert confidence.final_acuity <= result.rule_acuity
