"""
Integration tests for app/scoring/engine.py: real Case + Observation rows
through EventStore, end to end through age routing + framework dispatch.
"""
from datetime import datetime, timedelta, timezone

from app.config.hospital_profile import load_hospital_profile
from app.models.enums import ConfidenceBand, MeasurementStatus, ReliabilityTier, SourceType, ValueType
from app.scoring import concepts
from app.scoring.confidence import compute_confidence
from app.scoring.engine import score_case
from app.store.event_store import EventStore

PROFILE = load_hospital_profile("default")


def _now():
    return datetime.now(timezone.utc)


def _add(store: EventStore, case_id, concept_code, value, value_type, observed_at=None, unit=None):
    return store.add_observation(
        case_id=case_id,
        concept_code=concept_code,
        value=value,
        value_type=value_type,
        unit=unit,
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


def test_adult_case_scores_via_news2(store: EventStore):
    case = store.create_case(age_years=40)
    _add_normal_adult_vitals(store, case.case_id)

    result = score_case(case, store, PROFILE)
    assert result.framework == "NEWS2"
    assert result.age_band == "ADULT"
    assert result.rule_acuity == 5
    assert result.age_unknown is False


def test_paediatric_case_scores_via_pews(store: EventStore):
    case = store.create_case(age_years=3)  # TODDLER sub-band
    band = PROFILE.pews.band_for_age(3)
    rr_low, rr_high = band.respiratory_rate_normal
    hr_low, hr_high = band.heart_rate_normal
    sbp_low, sbp_high = band.systolic_bp_normal

    _add(store, case.case_id, concepts.RESP_RATE, (rr_low + rr_high) / 2, ValueType.NUMERIC)
    _add(store, case.case_id, concepts.SPO2, 98.0, ValueType.NUMERIC)
    _add(store, case.case_id, concepts.SUPPLEMENTAL_OXYGEN, False, ValueType.BOOLEAN)
    _add(store, case.case_id, concepts.SYSTOLIC_BP, (sbp_low + sbp_high) / 2, ValueType.NUMERIC)
    _add(store, case.case_id, concepts.HEART_RATE, (hr_low + hr_high) / 2, ValueType.NUMERIC)
    _add(store, case.case_id, concepts.CONSCIOUSNESS_LEVEL, "ALERT", ValueType.CODED)
    _add(store, case.case_id, concepts.TEMPERATURE, 37.0, ValueType.NUMERIC)
    _add(store, case.case_id, concepts.WORK_OF_BREATHING, "NORMAL", ValueType.CODED)

    result = score_case(case, store, PROFILE)
    assert result.framework == "PEWS"
    assert result.age_band == "TODDLER"
    assert result.rule_acuity == 5


def test_geriatric_case_escalates_earlier_than_adult_would_for_same_vitals(store: EventStore):
    """Phase 14.1 patient #6, at the engine/integration level."""
    adult_case = store.create_case(age_years=40)
    geriatric_case = store.create_case(age_years=78)

    for case_id in (adult_case.case_id, geriatric_case.case_id):
        _add_normal_adult_vitals(store, case_id)
        _add(store, case_id, concepts.HEART_RATE, 45.0, ValueType.NUMERIC)  # overrides the 75.0 above via a later reading

    adult_result = score_case(adult_case, store, PROFILE)
    geriatric_result = score_case(geriatric_case, store, PROFILE)

    assert adult_result.age_band == "ADULT"
    assert geriatric_result.age_band == "GERIATRIC"
    assert adult_result.single_parameter_escalation is False
    assert geriatric_result.single_parameter_escalation is True
    assert geriatric_result.rule_acuity < adult_result.rule_acuity


def test_case_with_no_age_recorded_abstains_to_the_configured_default(store: EventStore):
    case = store.create_case(age_years=None)
    result = score_case(case, store, PROFILE)

    assert result.age_unknown is True
    assert result.framework == "NONE"
    assert result.rule_acuity == PROFILE.unknown_age_default_esi_level


def test_zero_history_patient_with_no_vitals_at_all_does_not_crash(store: EventStore):
    """Phase 14.1 patient #7: first-time patient, no record, and here also
    no vitals yet recorded -- the engine must still return a safe result."""
    case = store.create_case(age_years=50)
    result = score_case(case, store, PROFILE)

    assert result.aggregate_score is None
    assert result.missing_data_cap_applied is True
    assert result.rule_acuity == PROFILE.news2.missing_data_cap_esi_level
    assert all(c.is_missing for c in result.components)


def test_stale_reading_is_excluded_from_scoring(store: EventStore):
    case = store.create_case(age_years=40)
    stale_time = _now() - timedelta(minutes=90)  # staleness window for SPO2 is 30 min
    _add_normal_adult_vitals(store, case.case_id, observed_at=stale_time)

    result = score_case(case, store, PROFILE)
    spo2_component = next(c for c in result.components if c.concept_code == concepts.SPO2)
    assert spo2_component.is_missing is True
    assert spo2_component.missing_reason == "STALE"
    assert result.missing_data_cap_applied is True


def test_hard_trigger_forces_top_acuity_despite_low_aggregate(store: EventStore):
    """Phase 3.3 Layer 4: an otherwise near-normal patient with one
    critical single parameter must be forced to the top of the queue, not
    left at whatever the aggregate NEWS2 score would otherwise say."""
    case = store.create_case(age_years=40)
    _add_normal_adult_vitals(store, case.case_id)
    # Override SpO2 with a critical reading (hard trigger: SpO2 <= 85).
    _add(store, case.case_id, concepts.SPO2, 80.0, ValueType.NUMERIC)

    result = score_case(case, store, PROFILE)
    assert any(t.trigger_id == "CRITICAL_HYPOXIA" for t in result.hard_triggers_fired)
    assert result.rule_acuity == 1
    assert "HARD TRIGGER" in result.reason


def test_hard_trigger_never_makes_acuity_less_urgent(store: EventStore):
    """The override is min(computed, trigger_level): if the aggregate score
    was already more urgent than the trigger's target, the trigger must not
    pull it back down."""
    case = store.create_case(age_years=40)
    _add_normal_adult_vitals(store, case.case_id)
    # Multiple deranged parameters already pushing the aggregate acuity to
    # ESI2's territory via the single-parameter red-score rule (RR<=8), plus
    # a hard trigger whose target is also 1 -- acuity should land at 1
    # either way, never regress to something less urgent than the framework
    # score alone would produce.
    _add(store, case.case_id, concepts.RESP_RATE, 6.0, ValueType.NUMERIC)  # NEWS2 red score -> ESI2
    _add(store, case.case_id, concepts.SPO2, 80.0, ValueType.NUMERIC)  # hard trigger -> ESI1

    result = score_case(case, store, PROFILE)
    assert result.rule_acuity == 1  # min(2, 1) == 1, still the more urgent of the two


def test_engine_picks_latest_reading_per_concept_not_the_first(store: EventStore):
    """Trend data: repeated vitals over time are new readings, not
    corrections (Phase 4.2) -- the engine must score the latest one."""
    case = store.create_case(age_years=40)
    earlier = _now() - timedelta(minutes=20)
    _add_normal_adult_vitals(store, case.case_id, observed_at=earlier)
    # A later, deranged heart rate reading for the same concept:
    _add(store, case.case_id, concepts.HEART_RATE, 140.0, ValueType.NUMERIC, observed_at=_now())

    result = score_case(case, store, PROFILE)
    hr_component = next(c for c in result.components if c.concept_code == concepts.HEART_RATE)
    assert hr_component.raw_value == 140.0
    assert hr_component.points == 3


def test_confidence_engine_abstains_end_to_end_on_age_unknown_case(store: EventStore):
    """CP5 wired to CP3's real engine output, not a hand-built fixture."""
    case = store.create_case(age_years=None)
    result = score_case(case, store, PROFILE)
    confidence = compute_confidence(result, PROFILE)

    assert confidence.should_abstain is True
    assert confidence.band == ConfidenceBand.LOW
    assert confidence.final_acuity == min(result.rule_acuity, PROFILE.confidence.abstention_minimum_acuity)


def test_confidence_engine_high_band_on_a_complete_normal_case(store: EventStore):
    case = store.create_case(age_years=40)
    _add_normal_adult_vitals(store, case.case_id)
    result = score_case(case, store, PROFILE)
    confidence = compute_confidence(result, PROFILE, ml_suggested_acuity=result.framework_acuity)

    assert confidence.band == ConfidenceBand.HIGH
    assert confidence.should_abstain is False
    assert confidence.final_acuity == result.rule_acuity
