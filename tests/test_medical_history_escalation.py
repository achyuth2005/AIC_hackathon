"""
Medical History feature: tests for the Risk Engine's medical-history
escalation (app/scoring/medical_history.py), both as pure unit tests and
end to end through the real Clinical Scoring Engine (app/scoring/engine.py)
and the full assess_case pipeline (app/scoring/risk_orchestrator.py).

Core assertion this file exists to prove (the feature's own acceptance
criteria): two patients with the EXACT SAME acute vitals and chief
complaint, differing only in medical_history, must not land at the same
acuity -- the one with a high-risk history (COPD, CAD, Heart Failure,
Immunosuppressed) must be assigned a strictly more urgent (lower-numbered)
ESI level than the one with no history, solely because of that history.
"""
from datetime import datetime, timezone

from app.config.hospital_profile import load_hospital_profile
from app.models.enums import MeasurementStatus, ReliabilityTier, SourceType, ValueType
from app.scoring import concepts
from app.scoring.engine import score_case
from app.scoring.medical_history import apply_medical_history_escalation, has_high_risk_history
from app.scoring.models import ClinicalScoreResult
from app.scoring.risk_orchestrator import assess_case
from app.store.event_store import EventStore

PROFILE = load_hospital_profile("default")


def _now():
    return datetime.now(timezone.utc)


def _add(store: EventStore, case_id, concept_code, value, value_type, observed_at=None):
    return store.add_observation(
        case_id=case_id,
        concept_code=concept_code,
        value=value,
        value_type=value_type,
        source_type=SourceType.NURSE,
        reliability_tier=ReliabilityTier.CLINICIAN_OBSERVED,
        measurement_status=MeasurementStatus.MEASURED,
        observed_at=observed_at or _now(),
    )


def _add_abnormal_adult_vitals(store: EventStore, case_id, observed_at=None):
    """Deranged-but-not-hard-triggering vitals (Phase 3.3's aggregate NEWS2
    territory, not Layer 4) -- the "acute vitals" both mocked patients in
    this file's headline test share exactly."""
    _add(store, case_id, concepts.RESP_RATE, 24.0, ValueType.NUMERIC, observed_at)
    _add(store, case_id, concepts.SPO2, 93.0, ValueType.NUMERIC, observed_at)
    _add(store, case_id, concepts.SUPPLEMENTAL_OXYGEN, False, ValueType.BOOLEAN, observed_at)
    _add(store, case_id, concepts.SYSTOLIC_BP, 100.0, ValueType.NUMERIC, observed_at)
    _add(store, case_id, concepts.HEART_RATE, 110.0, ValueType.NUMERIC, observed_at)
    _add(store, case_id, concepts.CONSCIOUSNESS_LEVEL, "ALERT", ValueType.CODED, observed_at)
    _add(store, case_id, concepts.TEMPERATURE, 38.2, ValueType.NUMERIC, observed_at)


def _add_normal_adult_vitals(store: EventStore, case_id, observed_at=None):
    _add(store, case_id, concepts.RESP_RATE, 16.0, ValueType.NUMERIC, observed_at)
    _add(store, case_id, concepts.SPO2, 98.0, ValueType.NUMERIC, observed_at)
    _add(store, case_id, concepts.SUPPLEMENTAL_OXYGEN, False, ValueType.BOOLEAN, observed_at)
    _add(store, case_id, concepts.SYSTOLIC_BP, 120.0, ValueType.NUMERIC, observed_at)
    _add(store, case_id, concepts.HEART_RATE, 75.0, ValueType.NUMERIC, observed_at)
    _add(store, case_id, concepts.CONSCIOUSNESS_LEVEL, "ALERT", ValueType.CODED, observed_at)
    _add(store, case_id, concepts.TEMPERATURE, 37.0, ValueType.NUMERIC, observed_at)


# ---------------------------------------------------------------------
# Pure unit tests: app/scoring/medical_history.py in isolation
# ---------------------------------------------------------------------

def test_has_high_risk_history_matches_each_named_condition_case_insensitively():
    assert has_high_risk_history("COPD") is True
    assert has_high_risk_history("copd") is True
    assert has_high_risk_history("Coronary Artery Disease (CAD)") is True
    assert has_high_risk_history("Congestive Heart Failure") is True
    assert has_high_risk_history("Immunosuppressed (post-transplant)") is True


def test_has_high_risk_history_false_for_none_empty_or_low_risk_history():
    assert has_high_risk_history(None) is False
    assert has_high_risk_history("") is False
    assert has_high_risk_history("Hypertension, Type 2 Diabetes") is False


def _result(rule_acuity: int, aggregate_score) -> ClinicalScoreResult:
    return ClinicalScoreResult(
        framework="NEWS2",
        age_band="ADULT",
        aggregate_score=aggregate_score,
        framework_acuity=rule_acuity,
        rule_acuity=rule_acuity,
        components=[],
        reason="test fixture",
    )


def test_escalation_applies_one_level_when_high_risk_history_and_abnormal_vitals():
    result = _result(rule_acuity=3, aggregate_score=5)
    escalated = apply_medical_history_escalation(result, "COPD")
    assert escalated.rule_acuity == 2
    assert escalated.medical_history_escalation_applied is True
    assert "MEDICAL HISTORY ESCALATION" in escalated.reason


def test_escalation_never_pushes_below_esi_1():
    result = _result(rule_acuity=1, aggregate_score=9)
    escalated = apply_medical_history_escalation(result, "CAD")
    assert escalated.rule_acuity == 1
    assert escalated.medical_history_escalation_applied is False  # nothing more urgent to escalate to


def test_no_escalation_when_history_absent():
    result = _result(rule_acuity=3, aggregate_score=5)
    escalated = apply_medical_history_escalation(result, None)
    assert escalated.rule_acuity == 3
    assert escalated.medical_history_escalation_applied is False


def test_no_escalation_when_history_present_but_vitals_are_normal():
    """The multiplier requirement is conjunctive: a high-risk history alone,
    on normal vitals, must not force an escalation."""
    result = _result(rule_acuity=5, aggregate_score=0)
    escalated = apply_medical_history_escalation(result, "COPD")
    assert escalated.rule_acuity == 5
    assert escalated.medical_history_escalation_applied is False


def test_no_escalation_when_vitals_could_not_be_scored_at_all():
    """aggregate_score is None (e.g. no observations yet) -- abstain,
    don't guess an escalation on top of an already-abstained result."""
    result = _result(rule_acuity=PROFILE.news2.missing_data_cap_esi_level, aggregate_score=None)
    escalated = apply_medical_history_escalation(result, "Heart Failure")
    assert escalated.medical_history_escalation_applied is False


def test_no_escalation_for_low_risk_history_even_with_abnormal_vitals():
    result = _result(rule_acuity=3, aggregate_score=5)
    escalated = apply_medical_history_escalation(result, "Hypertension, Type 2 Diabetes")
    assert escalated.rule_acuity == 3
    assert escalated.medical_history_escalation_applied is False


# ---------------------------------------------------------------------
# Integration: real Case + Observation rows through the Clinical Scoring
# Engine (score_case) -- Phase 5's actual acceptance test.
# ---------------------------------------------------------------------

def test_high_risk_history_escalates_acuity_above_identical_vitals_with_no_history(store: EventStore):
    """The headline scenario: Patient A (no history) and Patient B (CAD)
    share the exact same acute vitals and age. Patient B must be assigned
    a strictly more urgent (lower ESI number) acuity than Patient A,
    solely because of medical_history."""
    patient_a = store.create_case(age_years=60, medical_history=None)
    patient_b = store.create_case(age_years=60, medical_history="Coronary Artery Disease (CAD)")

    _add_abnormal_adult_vitals(store, patient_a.case_id)
    _add_abnormal_adult_vitals(store, patient_b.case_id)

    result_a = score_case(patient_a, store, PROFILE)
    result_b = score_case(patient_b, store, PROFILE)

    # Same vitals -> identical pre-history-escalation framework acuity.
    assert result_a.aggregate_score == result_b.aggregate_score
    assert result_a.framework_acuity == result_b.framework_acuity

    assert result_b.medical_history_escalation_applied is True
    assert result_a.medical_history_escalation_applied is False
    assert result_b.rule_acuity < result_a.rule_acuity  # strictly more urgent


def test_high_risk_history_does_not_escalate_a_patient_with_normal_vitals(store: EventStore):
    """Guards against the multiplier degenerating into an unconditional
    bump: identical NORMAL vitals must score identically regardless of
    history, since there is no abnormal physiology to multiply."""
    patient_a = store.create_case(age_years=45, medical_history=None)
    patient_b = store.create_case(age_years=45, medical_history="COPD")

    _add_normal_adult_vitals(store, patient_a.case_id)
    _add_normal_adult_vitals(store, patient_b.case_id)

    result_a = score_case(patient_a, store, PROFILE)
    result_b = score_case(patient_b, store, PROFILE)

    assert result_a.rule_acuity == result_b.rule_acuity
    assert result_b.medical_history_escalation_applied is False


def test_full_assess_case_pipeline_assigns_patient_b_a_higher_final_acuity_tier(store: EventStore):
    """End to end through assess_case (Phase 3.1's
    final_acuity = min(rule_acuity, ml_suggested_acuity, ...) invariant),
    not just the rules-engine intermediate result -- confirms the
    escalation survives all the way to what a nurse/doctor actually sees."""
    patient_a = store.create_case(age_years=70, medical_history=None)
    patient_b = store.create_case(age_years=70, medical_history="Congestive Heart Failure")

    _add_abnormal_adult_vitals(store, patient_a.case_id)
    _add_abnormal_adult_vitals(store, patient_b.case_id)

    assessment_a = assess_case(patient_a, store, PROFILE)
    assessment_b = assess_case(patient_b, store, PROFILE)

    assert assessment_b.final_acuity < assessment_a.final_acuity
    assert assessment_b.rule_acuity < assessment_a.rule_acuity
