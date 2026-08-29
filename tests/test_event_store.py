"""
Checkpoint 1 validation: the Patient State Store enforces the invariants
Phase 4 and Phase 7.1 require, not just "the API doesn't crash".
"""
from datetime import datetime, timedelta, timezone

import pytest

from app.models.enums import (
    ArrivalMode,
    CaseStatus,
    IdentityLinkStatus,
    MeasurementStatus,
    ReliabilityTier,
    SourceType,
    ValueType,
)
from app.store.event_store import (
    EventStore,
    InvalidArrivalError,
    NotFoundError,
    ObservationAlreadySupersededError,
    UnknownEventTypeError,
)
from app.timeutil import to_naive_utc


def _now():
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------
# Case lifecycle (Phase 1, Phase 7.1)
# ---------------------------------------------------------------------
def test_walk_in_case_is_active_and_identity_confirmed(store: EventStore):
    case = store.create_case(display_name="Test Patient", age_years=40, arrival_mode=ArrivalMode.WALK_IN)
    assert case.status == CaseStatus.ACTIVE
    assert case.identity_link_status == IdentityLinkStatus.CONFIRMED

    timeline = store.get_timeline(case.case_id)
    assert [e.event_type for e in timeline] == ["CASE_CREATED"]


def test_ambulance_case_starts_pre_arrival_and_unlinked(store: EventStore):
    case = store.create_case(age_years=55, arrival_mode=ArrivalMode.AMBULANCE)
    assert case.status == CaseStatus.PRE_ARRIVAL
    assert case.identity_link_status == IdentityLinkStatus.UNLINKED
    assert case.arrived_at is None


def test_patient_arrived_is_an_event_not_a_new_case(store: EventStore):
    """Phase 7.1: 'Arrival is an event (PATIENT_ARRIVED), not a new case.'"""
    case = store.create_case(age_years=55, arrival_mode=ArrivalMode.AMBULANCE)
    original_case_id = case.case_id

    updated = store.record_arrival(case.case_id)

    assert updated.case_id == original_case_id  # same record, no new case
    assert updated.status == CaseStatus.ACTIVE
    assert updated.arrived_at is not None

    event_types = [e.event_type for e in store.get_timeline(case.case_id)]
    assert event_types == ["CASE_CREATED", "PATIENT_ARRIVED"]


def test_record_arrival_rejects_a_case_not_awaiting_arrival(store: EventStore):
    """A walk-in case is ACTIVE from creation; PATIENT_ARRIVED is specifically
    the ambulance PRE_ARRIVAL -> ACTIVE transition (Phase 7.1)."""
    walk_in = store.create_case(age_years=40, arrival_mode=ArrivalMode.WALK_IN)
    with pytest.raises(InvalidArrivalError):
        store.record_arrival(walk_in.case_id)


def test_record_arrival_on_missing_case_raises_not_found(store: EventStore):
    with pytest.raises(NotFoundError):
        store.record_arrival("does-not-exist")


def test_add_observation_on_missing_case_raises_not_found(store: EventStore):
    with pytest.raises(NotFoundError):
        store.add_observation(
            case_id="does-not-exist",
            concept_code="SPO2",
            value=98.0,
            value_type=ValueType.NUMERIC,
            source_type=SourceType.DEVICE,
            reliability_tier=ReliabilityTier.MACHINE_MEASURED,
            measurement_status=MeasurementStatus.MEASURED,
            observed_at=_now(),
        )


# ---------------------------------------------------------------------
# Observations (Phase 4.2)
# ---------------------------------------------------------------------
def test_add_observation_is_current(store: EventStore):
    case = store.create_case(age_years=30)
    obs = store.add_observation(
        case_id=case.case_id,
        concept_code="SPO2",
        value=97.0,
        value_type=ValueType.NUMERIC,
        unit="%",
        source_type=SourceType.DEVICE,
        source_id="pulse-ox-01",
        reliability_tier=ReliabilityTier.MACHINE_MEASURED,
        measurement_status=MeasurementStatus.MEASURED,
        observed_at=_now(),
    )
    assert obs.is_current
    assert obs.value == 97.0

    current = store.get_current_observations(case.case_id, concept_code="SPO2")
    assert len(current) == 1
    assert current[0].observation_id == obs.observation_id


def test_ai_inferred_requires_extraction_confidence(store: EventStore):
    case = store.create_case(age_years=30)
    with pytest.raises(ValueError):
        store.add_observation(
            case_id=case.case_id,
            concept_code="CHEST_PAIN",
            value=True,
            value_type=ValueType.BOOLEAN,
            source_type=SourceType.AI_INFERRED,
            reliability_tier=ReliabilityTier.AI_INFERRED,
            measurement_status=MeasurementStatus.MEASURED,
            observed_at=_now(),
            extraction_confidence=None,
        )


def test_supersede_never_mutates_the_original(store: EventStore):
    """Phase 4.2: 'Corrections create new records. The original stays.'"""
    case = store.create_case(age_years=30)
    original = store.add_observation(
        case_id=case.case_id,
        concept_code="HEART_RATE",
        value=72.0,
        value_type=ValueType.NUMERIC,
        unit="bpm",
        source_type=SourceType.NURSE,
        source_id="nurse-jane",
        reliability_tier=ReliabilityTier.CLINICIAN_OBSERVED,
        measurement_status=MeasurementStatus.MEASURED,
        observed_at=_now(),
    )

    corrected = store.supersede_observation(
        observation_id=original.observation_id,
        value=132.0,  # nurse mis-typed the first reading
        value_type=ValueType.NUMERIC,
        source_type=SourceType.NURSE,
        source_id="nurse-jane",
        reliability_tier=ReliabilityTier.CLINICIAN_OBSERVED,
        measurement_status=MeasurementStatus.MEASURED,
        observed_at=_now(),
    )

    # Original row is retained, unedited, and now points at its replacement.
    assert original.value == 72.0
    assert original.superseded_by == corrected.observation_id
    assert not original.is_current

    # Only the corrected value is "current".
    current = store.get_current_observations(case.case_id, concept_code="HEART_RATE")
    assert len(current) == 1
    assert current[0].observation_id == corrected.observation_id
    assert current[0].value == 132.0

    event_types = [e.event_type for e in store.get_timeline(case.case_id)]
    assert event_types == [
        "CASE_CREATED",
        "OBSERVATION_RECORDED",
        "OBSERVATION_RECORDED",
        "OBSERVATION_SUPERSEDED",
    ]


def test_cannot_supersede_an_already_superseded_observation(store: EventStore):
    case = store.create_case(age_years=30)
    original = store.add_observation(
        case_id=case.case_id,
        concept_code="HEART_RATE",
        value=72.0,
        value_type=ValueType.NUMERIC,
        source_type=SourceType.NURSE,
        reliability_tier=ReliabilityTier.CLINICIAN_OBSERVED,
        measurement_status=MeasurementStatus.MEASURED,
        observed_at=_now(),
    )
    store.supersede_observation(
        observation_id=original.observation_id,
        value=80.0,
        value_type=ValueType.NUMERIC,
        source_type=SourceType.NURSE,
        reliability_tier=ReliabilityTier.CLINICIAN_OBSERVED,
        measurement_status=MeasurementStatus.MEASURED,
        observed_at=_now(),
    )

    with pytest.raises(ObservationAlreadySupersededError):
        store.supersede_observation(
            observation_id=original.observation_id,
            value=999.0,
            value_type=ValueType.NUMERIC,
            source_type=SourceType.NURSE,
            reliability_tier=ReliabilityTier.CLINICIAN_OBSERVED,
            measurement_status=MeasurementStatus.MEASURED,
            observed_at=_now(),
        )


def test_missing_vitals_are_not_imputed_as_normal(store: EventStore):
    """Phase 3.3 'Handling missing data': a NOT_MEASURED status must be
    stored and queryable as-is -- never silently defaulted to a normal
    numeric value."""
    case = store.create_case(age_years=30)
    obs = store.add_observation(
        case_id=case.case_id,
        concept_code="SYSTOLIC_BP",
        value=None,
        value_type=ValueType.NUMERIC,
        source_type=SourceType.NURSE,
        reliability_tier=ReliabilityTier.CLINICIAN_OBSERVED,
        measurement_status=MeasurementStatus.NOT_MEASURED,
        observed_at=_now(),
    )
    assert obs.measurement_status == MeasurementStatus.NOT_MEASURED
    assert obs.value is None


def test_observed_at_and_recorded_at_can_diverge(store: EventStore):
    """Phase 4.2: a vital taken in the ambulance and entered on arrival is
    not a current reading -- the split must be preserved exactly."""
    case = store.create_case(age_years=30, arrival_mode=ArrivalMode.AMBULANCE)
    taken_in_ambulance = _now() - timedelta(minutes=25)

    obs = store.add_observation(
        case_id=case.case_id,
        concept_code="HEART_RATE",
        value=110.0,
        value_type=ValueType.NUMERIC,
        source_type=SourceType.PARAMEDIC,
        reliability_tier=ReliabilityTier.CLINICIAN_OBSERVED,
        measurement_status=MeasurementStatus.MEASURED,
        observed_at=taken_in_ambulance,
    )
    # Stored as naive UTC (app/timeutil.py convention); compare normalized.
    assert obs.observed_at == to_naive_utc(taken_in_ambulance)
    assert obs.recorded_at > obs.observed_at


def test_is_stale_uses_concept_specific_window(store: EventStore):
    case = store.create_case(age_years=30)
    obs = store.add_observation(
        case_id=case.case_id,
        concept_code="SPO2",
        value=98.0,
        value_type=ValueType.NUMERIC,
        source_type=SourceType.DEVICE,
        reliability_tier=ReliabilityTier.MACHINE_MEASURED,
        measurement_status=MeasurementStatus.MEASURED,
        observed_at=_now() - timedelta(minutes=90),
    )
    assert obs.is_stale(timedelta(minutes=30)) is True
    assert obs.is_stale(timedelta(minutes=120)) is False
    assert obs.is_stale(None) is False  # concept explicitly configured to never go stale


# ---------------------------------------------------------------------
# Event stream (Phase 4.4)
# ---------------------------------------------------------------------
def test_unknown_event_type_is_rejected(store: EventStore):
    case = store.create_case(age_years=30)
    with pytest.raises(UnknownEventTypeError):
        store.append_event(case_id=case.case_id, event_type="THIS_IS_NOT_A_REAL_EVENT")


def test_timeline_is_ordered_by_recorded_at(store: EventStore):
    case = store.create_case(age_years=30)
    store.add_observation(
        case_id=case.case_id,
        concept_code="TEMPERATURE",
        value=37.0,
        value_type=ValueType.NUMERIC,
        source_type=SourceType.NURSE,
        reliability_tier=ReliabilityTier.CLINICIAN_OBSERVED,
        measurement_status=MeasurementStatus.MEASURED,
        observed_at=_now(),
    )
    timeline = store.get_timeline(case.case_id)
    recorded_ats = [e.recorded_at for e in timeline]
    assert recorded_ats == sorted(recorded_ats)
