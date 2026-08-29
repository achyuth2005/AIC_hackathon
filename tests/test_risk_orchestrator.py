"""
Integration tests for app/scoring/risk_orchestrator.py: the Phase 3.1
min() invariant, assembled from real Case/Observation rows and persisted
as a RiskAssessment (Phase 4.3).
"""
from datetime import datetime, timedelta, timezone

from app.config.hospital_profile import load_hospital_profile
from app.models.enums import DecidingLayer, MeasurementStatus, ReliabilityTier, SourceType, ValueType
from app.scoring import concepts
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


def _add_normal_adult_vitals(store: EventStore, case_id, observed_at=None):
    _add(store, case_id, concepts.RESP_RATE, 16.0, ValueType.NUMERIC, observed_at)
    _add(store, case_id, concepts.SPO2, 98.0, ValueType.NUMERIC, observed_at)
    _add(store, case_id, concepts.SUPPLEMENTAL_OXYGEN, False, ValueType.BOOLEAN, observed_at)
    _add(store, case_id, concepts.SYSTOLIC_BP, 120.0, ValueType.NUMERIC, observed_at)
    _add(store, case_id, concepts.HEART_RATE, 75.0, ValueType.NUMERIC, observed_at)
    _add(store, case_id, concepts.CONSCIOUSNESS_LEVEL, "ALERT", ValueType.CODED, observed_at)
    _add(store, case_id, concepts.TEMPERATURE, 37.0, ValueType.NUMERIC, observed_at)


def test_normal_case_persists_a_complete_risk_assessment(store: EventStore):
    case = store.create_case(age_years=40)
    _add_normal_adult_vitals(store, case.case_id)

    ra = assess_case(case, store, PROFILE)

    assert ra.rule_acuity == 5
    assert ra.ml_model_version is not None
    assert ra.ml_probability is not None
    assert ra.final_acuity == 5
    assert ra.deciding_layer == DecidingLayer.RULES
    assert ra.input_snapshot_hash
    assert len(ra.input_observation_ids) > 0

    event_types = [e.event_type for e in store.get_timeline(case.case_id)]
    assert "RISK_ASSESSMENT_COMPUTED" in event_types


def test_hard_trigger_is_persisted_and_logged_as_events(store: EventStore):
    case = store.create_case(age_years=40)
    _add_normal_adult_vitals(store, case.case_id)
    _add(store, case.case_id, concepts.SPO2, 80.0, ValueType.NUMERIC)  # CRITICAL_HYPOXIA hard trigger

    ra = assess_case(case, store, PROFILE)

    assert ra.final_acuity == 1
    assert len(ra.hard_triggers_fired) == 1
    assert ra.hard_triggers_fired[0]["trigger_id"] == "CRITICAL_HYPOXIA"

    event_types = [e.event_type for e in store.get_timeline(case.case_id)]
    assert "HARD_TRIGGER_FIRED" in event_types


def test_ml_escalates_on_a_worsening_trend_rules_alone_would_miss(store: EventStore):
    """The concrete demonstration Phase 3.3 Layer 3 exists for: vitals that
    are each individually near-normal under NEWS2's own point tables, but
    whose TREND (which NEWS2 cannot see at all) is deteriorating."""
    case = store.create_case(age_years=40)
    earlier = _now() - timedelta(minutes=30)

    _add(store, case.case_id, concepts.RESP_RATE, 14.0, ValueType.NUMERIC, earlier)
    _add(store, case.case_id, concepts.SPO2, 99.0, ValueType.NUMERIC, earlier)
    _add(store, case.case_id, concepts.HEART_RATE, 70.0, ValueType.NUMERIC, earlier)
    _add(store, case.case_id, concepts.SYSTOLIC_BP, 120.0, ValueType.NUMERIC, earlier)
    _add(store, case.case_id, concepts.TEMPERATURE, 37.0, ValueType.NUMERIC, earlier)
    _add(store, case.case_id, concepts.CONSCIOUSNESS_LEVEL, "ALERT", ValueType.CODED, earlier)
    _add(store, case.case_id, concepts.SUPPLEMENTAL_OXYGEN, False, ValueType.BOOLEAN, earlier)

    _add(store, case.case_id, concepts.RESP_RATE, 20.0, ValueType.NUMERIC)
    _add(store, case.case_id, concepts.SPO2, 94.0, ValueType.NUMERIC)
    _add(store, case.case_id, concepts.HEART_RATE, 108.0, ValueType.NUMERIC)
    _add(store, case.case_id, concepts.SYSTOLIC_BP, 105.0, ValueType.NUMERIC)
    _add(store, case.case_id, concepts.TEMPERATURE, 37.0, ValueType.NUMERIC)
    _add(store, case.case_id, concepts.CONSCIOUSNESS_LEVEL, "ALERT", ValueType.CODED)
    _add(store, case.case_id, concepts.SUPPLEMENTAL_OXYGEN, False, ValueType.BOOLEAN)

    ra = assess_case(case, store, PROFILE)

    assert ra.deciding_layer == DecidingLayer.ML
    assert ra.ml_suggested_acuity < ra.rule_acuity
    assert ra.final_acuity == ra.ml_suggested_acuity  # min() picked the more urgent ML term


def test_ml_never_makes_the_result_less_urgent(store: EventStore):
    """Phase 3.1: ML can only raise. A case with a hard trigger (forced
    ESI1) must stay at ESI1 even if the ML challenger, looking at the
    non-trigger features, suggests something less urgent."""
    case = store.create_case(age_years=40)
    _add_normal_adult_vitals(store, case.case_id)
    _add(store, case.case_id, concepts.SPO2, 80.0, ValueType.NUMERIC)  # hard trigger -> rule_acuity forced to 1

    ra = assess_case(case, store, PROFILE)
    assert ra.rule_acuity == 1
    assert ra.final_acuity == 1  # ML's own suggestion, whatever it is, cannot relax this


def test_age_unknown_case_never_invokes_ml_and_abstains(store: EventStore):
    case = store.create_case(age_years=None)
    ra = assess_case(case, store, PROFILE)

    assert ra.ml_model_version is None
    assert ra.ml_probability is None
    assert ra.ml_suggested_acuity is None
    assert ra.should_abstain is True
    assert ra.deciding_layer == DecidingLayer.ABSTENTION
    assert ra.final_acuity == PROFILE.confidence.abstention_minimum_acuity


def test_risk_assessment_history_and_latest(store: EventStore):
    case = store.create_case(age_years=40)
    _add_normal_adult_vitals(store, case.case_id)
    first = assess_case(case, store, PROFILE)

    _add(store, case.case_id, concepts.HEART_RATE, 140.0, ValueType.NUMERIC)  # new reading -> re-assess
    second = assess_case(case, store, PROFILE)

    history = store.get_risk_assessment_history(case.case_id)
    assert [a.assessment_id for a in history] == [first.assessment_id, second.assessment_id]

    latest = store.get_latest_risk_assessment(case.case_id)
    assert latest.assessment_id == second.assessment_id
    assert first.assessment_id != second.assessment_id  # never mutated in place -- a new row each time
