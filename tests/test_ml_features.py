"""
Tests for app/ml/features.py: DB-backed extraction of the ML feature
vector (Phase 16.2), including missingness handling and trend deltas.
"""
from datetime import datetime, timedelta, timezone

import pytest

from app.config.hospital_profile import load_hospital_profile
from app.models.enums import ArrivalMode, MeasurementStatus, ReliabilityTier, SourceType, ValueType
from app.ml.features import POPULATION_DEFAULTS, extract_features_from_case
from app.scoring import concepts
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


def test_requires_known_age(store: EventStore):
    case = store.create_case(age_years=None)
    with pytest.raises(ValueError):
        extract_features_from_case(case, store, PROFILE)


def test_all_present_vitals_have_no_missing_flags(store: EventStore):
    case = store.create_case(age_years=40)
    _add(store, case.case_id, concepts.RESP_RATE, 16.0, ValueType.NUMERIC)
    _add(store, case.case_id, concepts.SPO2, 98.0, ValueType.NUMERIC)
    _add(store, case.case_id, concepts.HEART_RATE, 75.0, ValueType.NUMERIC)
    _add(store, case.case_id, concepts.SYSTOLIC_BP, 120.0, ValueType.NUMERIC)
    _add(store, case.case_id, concepts.TEMPERATURE, 37.0, ValueType.NUMERIC)

    features = extract_features_from_case(case, store, PROFILE)
    assert features.resp_rate == 16.0
    assert features.resp_rate_missing == 0.0
    assert features.spo2 == 98.0
    assert features.spo2_missing == 0.0


def test_missing_vital_uses_population_default_and_sets_flag(store: EventStore):
    case = store.create_case(age_years=40)  # no observations recorded at all
    features = extract_features_from_case(case, store, PROFILE)

    assert features.resp_rate == POPULATION_DEFAULTS[concepts.RESP_RATE]
    assert features.resp_rate_missing == 1.0
    assert features.spo2 == POPULATION_DEFAULTS[concepts.SPO2]
    assert features.spo2_missing == 1.0


def test_trend_delta_computed_from_two_readings(store: EventStore):
    case = store.create_case(age_years=40)
    earlier = _now() - timedelta(minutes=30)
    _add(store, case.case_id, concepts.HEART_RATE, 70.0, ValueType.NUMERIC, observed_at=earlier)
    _add(store, case.case_id, concepts.HEART_RATE, 100.0, ValueType.NUMERIC, observed_at=_now())

    features = extract_features_from_case(case, store, PROFILE)
    assert features.heart_rate == 100.0  # latest value used as the point-in-time reading
    assert features.heart_rate_delta == pytest.approx(30.0)
    assert features.heart_rate_delta_missing == 0.0


def test_trend_delta_missing_with_only_one_reading(store: EventStore):
    case = store.create_case(age_years=40)
    _add(store, case.case_id, concepts.HEART_RATE, 75.0, ValueType.NUMERIC)

    features = extract_features_from_case(case, store, PROFILE)
    assert features.heart_rate_delta == 0.0
    assert features.heart_rate_delta_missing == 1.0


def test_history_and_symptom_flags(store: EventStore):
    case = store.create_case(age_years=40)
    _add(store, case.case_id, concepts.HISTORY_CARDIAC, True, ValueType.BOOLEAN)
    _add(store, case.case_id, concepts.SYMPTOM_CHEST_PAIN, False, ValueType.BOOLEAN)

    features = extract_features_from_case(case, store, PROFILE)
    assert features.history_cardiac == 1.0
    assert features.history_cardiac_missing == 0.0
    assert features.symptom_chest_pain == 0.0
    assert features.symptom_chest_pain_missing == 0.0
    # Never recorded at all -> defaults to 0 (absent), flagged missing.
    assert features.history_diabetes == 0.0
    assert features.history_diabetes_missing == 1.0


def test_arrival_mode_ambulance_flag(store: EventStore):
    case = store.create_case(age_years=40, arrival_mode=ArrivalMode.AMBULANCE)
    features = extract_features_from_case(case, store, PROFILE)
    assert features.arrival_mode_ambulance == 1.0


def test_onset_band_and_missingness(store: EventStore):
    case = store.create_case(age_years=40)
    _add(store, case.case_id, concepts.SYMPTOM_ONSET_MINUTES, 45.0, ValueType.NUMERIC)  # <60 -> band 0
    features = extract_features_from_case(case, store, PROFILE)
    assert features.onset_band == 0.0
    assert features.onset_missing == 0.0

    case2 = store.create_case(age_years=40)
    features2 = extract_features_from_case(case2, store, PROFILE)
    assert features2.onset_missing == 1.0


def test_to_vector_matches_feature_names_length(store: EventStore):
    from app.ml.features import FEATURE_NAMES

    case = store.create_case(age_years=40)
    features = extract_features_from_case(case, store, PROFILE)
    assert len(features.to_vector()) == len(FEATURE_NAMES)
