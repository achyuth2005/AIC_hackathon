"""
Tests for Contradictory Information (Phase 9.3, CP13): conflict detection,
conservative-value scoring, deduplication, human resolution, and the API
surface.
"""
import pytest

from app.config.hospital_profile import load_hospital_profile
from app.models.enums import MeasurementStatus, ReliabilityTier, SourceType, ValueType
from app.scoring import concepts
from app.scoring.risk_orchestrator import assess_case
from app.store.event_store import EventStore
from app.timeutil import utcnow

PROFILE = load_hospital_profile("default")


def _obs(store, case_id, code, value, *, source=SourceType.DEVICE, tier=ReliabilityTier.MACHINE_MEASURED, observed_at=None):
    return store.add_observation(
        case_id=case_id, concept_code=code, value=value, value_type=ValueType.NUMERIC,
        source_type=source, reliability_tier=tier, measurement_status=MeasurementStatus.MEASURED,
        observed_at=observed_at or utcnow(),
    )


def _full_adult_vitals(store, case_id, *, include_heart_rate=True):
    """Every ADULT_REQUIRED_CONCEPT except (optionally) HEART_RATE, which
    the conflict tests below set up explicitly themselves."""
    values = {concepts.RESP_RATE: 17.0, concepts.SPO2: 97.0, concepts.SYSTOLIC_BP: 120.0, concepts.TEMPERATURE: 37.0}
    if include_heart_rate:
        values[concepts.HEART_RATE] = 80.0
    for code, val in values.items():
        _obs(store, case_id, code, val)
    store.add_observation(
        case_id=case_id, concept_code=concepts.CONSCIOUSNESS_LEVEL, value="ALERT", value_type=ValueType.CODED,
        source_type=SourceType.DEVICE, reliability_tier=ReliabilityTier.MACHINE_MEASURED,
        measurement_status=MeasurementStatus.MEASURED, observed_at=utcnow(),
    )
    store.add_observation(
        case_id=case_id, concept_code=concepts.SUPPLEMENTAL_OXYGEN, value=False, value_type=ValueType.BOOLEAN,
        source_type=SourceType.DEVICE, reliability_tier=ReliabilityTier.MACHINE_MEASURED,
        measurement_status=MeasurementStatus.MEASURED, observed_at=utcnow(),
    )


def test_no_conflict_when_only_one_current_reading_exists(store: EventStore):
    case = store.create_case(age_years=40)
    _full_adult_vitals(store, case.case_id)
    assess_case(case, store, PROFILE)
    assert store.list_data_conflicts(case.case_id, include_resolved=True) == []


def test_conflicting_values_are_detected_and_the_conservative_one_scores(store: EventStore):
    case = store.create_case(age_years=40)
    now = utcnow()
    mild = _obs(store, case.case_id, concepts.HEART_RATE, 78.0, source=SourceType.PATIENT,
                tier=ReliabilityTier.PATIENT_REPORTED, observed_at=now)
    from datetime import timedelta
    abnormal = _obs(store, case.case_id, concepts.HEART_RATE, 125.0, observed_at=now - timedelta(minutes=5))
    _full_adult_vitals(store, case.case_id, include_heart_rate=False)

    ra = assess_case(case, store, PROFILE, as_of=now)
    hr_component = next(c for c in ra.rule_component_breakdown if c["concept_code"] == concepts.HEART_RATE)
    assert hr_component["raw_value"] == 125.0  # conservative (higher NEWS2 points) wins, not the milder one

    conflicts = store.list_data_conflicts(case.case_id)
    assert len(conflicts) == 1
    assert conflicts[0].concept_code == concepts.HEART_RATE
    assert conflicts[0].conservative_observation_id == abnormal.observation_id

    event_types = [e.event_type for e in store.get_timeline(case.case_id)]
    assert "DATA_CONFLICT_DETECTED" in event_types


def test_rescoring_the_same_conflict_does_not_duplicate_it(store: EventStore):
    case = store.create_case(age_years=40)
    now = utcnow()
    _obs(store, case.case_id, concepts.HEART_RATE, 78.0, source=SourceType.PATIENT,
         tier=ReliabilityTier.PATIENT_REPORTED, observed_at=now)
    _obs(store, case.case_id, concepts.HEART_RATE, 125.0, observed_at=now)
    _full_adult_vitals(store, case.case_id, include_heart_rate=False)

    assess_case(case, store, PROFILE, as_of=now)
    assess_case(case, store, PROFILE, as_of=now)  # re-score without new data
    conflicts = store.list_data_conflicts(case.case_id, include_resolved=True)
    assert len(conflicts) == 1


def test_resolving_a_conflict_makes_scoring_use_the_kept_value(store: EventStore):
    case = store.create_case(age_years=40)
    now = utcnow()
    mild = _obs(store, case.case_id, concepts.HEART_RATE, 78.0, source=SourceType.PATIENT,
                tier=ReliabilityTier.PATIENT_REPORTED, observed_at=now)
    _obs(store, case.case_id, concepts.HEART_RATE, 125.0, observed_at=now)
    _full_adult_vitals(store, case.case_id, include_heart_rate=False)
    assess_case(case, store, PROFILE, as_of=now)

    conflict = store.list_data_conflicts(case.case_id)[0]
    store.resolve_data_conflict(
        conflict.conflict_id, resolved_by="demo-doctor-01", kept_observation_id=mild.observation_id,
        resolution_note="Device was miscalibrated; patient's own pulse count confirmed manually.",
    )

    ra = assess_case(case, store, PROFILE, as_of=now)
    hr_component = next(c for c in ra.rule_component_breakdown if c["concept_code"] == concepts.HEART_RATE)
    assert hr_component["raw_value"] == 78.0  # human's resolution now wins, not the automatic conservative rule

    resolved = store.list_data_conflicts(case.case_id, include_resolved=True)
    assert resolved[0].resolved is True
    assert resolved[0].kept_observation_id == mild.observation_id
    event_types = [e.event_type for e in store.get_timeline(case.case_id)]
    assert "DATA_CONFLICT_RESOLVED" in event_types


def test_resolving_an_already_resolved_conflict_raises(store: EventStore):
    case = store.create_case(age_years=40)
    now = utcnow()
    mild = _obs(store, case.case_id, concepts.HEART_RATE, 78.0, observed_at=now)
    _obs(store, case.case_id, concepts.HEART_RATE, 125.0, observed_at=now)
    _full_adult_vitals(store, case.case_id, include_heart_rate=False)
    assess_case(case, store, PROFILE, as_of=now)

    conflict = store.list_data_conflicts(case.case_id)[0]
    store.resolve_data_conflict(conflict.conflict_id, resolved_by="x", kept_observation_id=mild.observation_id)
    with pytest.raises(ValueError):
        store.resolve_data_conflict(conflict.conflict_id, resolved_by="x", kept_observation_id=mild.observation_id)


def test_resolving_with_an_observation_id_not_in_the_conflict_raises(store: EventStore):
    case = store.create_case(age_years=40)
    now = utcnow()
    _obs(store, case.case_id, concepts.HEART_RATE, 78.0, observed_at=now)
    _obs(store, case.case_id, concepts.HEART_RATE, 125.0, observed_at=now)
    _full_adult_vitals(store, case.case_id, include_heart_rate=False)
    assess_case(case, store, PROFILE, as_of=now)

    conflict = store.list_data_conflicts(case.case_id)[0]
    with pytest.raises(ValueError):
        store.resolve_data_conflict(conflict.conflict_id, resolved_by="x", kept_observation_id="not-a-real-id")


def test_bypass_and_ml_features_are_unaffected_by_conflict_resolution(store: EventStore):
    """Documented scope boundary: only score_case()'s rules scoring is
    conflict-aware; bypass/ML feature extraction still see plain 'latest'."""
    from app.ml.features import extract_features_from_case

    case = store.create_case(age_years=40)
    now = utcnow()
    _obs(store, case.case_id, concepts.HEART_RATE, 78.0, observed_at=now)  # later/latest
    from datetime import timedelta
    _obs(store, case.case_id, concepts.HEART_RATE, 125.0, observed_at=now - timedelta(minutes=5))
    _full_adult_vitals(store, case.case_id, include_heart_rate=False)

    features = extract_features_from_case(case, store, PROFILE, as_of=now)
    assert features.heart_rate == 78.0  # plain "latest", not conflict-resolved


# ---------------------------------------------------------------------
# HTTP surface
# ---------------------------------------------------------------------
def test_conflicts_endpoint_and_resolve_flow(client):
    case_id = client.post("/cases", json={"age_years": 40}).json()["case_id"]
    client.post(
        f"/cases/{case_id}/observations",
        json={
            "concept_code": "HEART_RATE", "value": 78.0, "value_type": "NUMERIC",
            "source_type": "PATIENT", "reliability_tier": 3, "measurement_status": "MEASURED",
            "observed_at": utcnow().isoformat(),
        },
    )
    client.post(
        f"/cases/{case_id}/observations",
        json={
            "concept_code": "HEART_RATE", "value": 125.0, "value_type": "NUMERIC",
            "source_type": "DEVICE", "reliability_tier": 1, "measurement_status": "MEASURED",
            "observed_at": utcnow().isoformat(),
        },
    )
    for code, val in (("RESP_RATE", 17.0), ("SPO2", 97.0), ("SYSTOLIC_BP", 120.0), ("TEMPERATURE", 37.0)):
        client.post(
            f"/cases/{case_id}/observations",
            json={
                "concept_code": code, "value": val, "value_type": "NUMERIC",
                "source_type": "DEVICE", "reliability_tier": 1, "measurement_status": "MEASURED",
                "observed_at": utcnow().isoformat(),
            },
        )
    client.post(
        f"/cases/{case_id}/observations",
        json={
            "concept_code": "CONSCIOUSNESS_LEVEL", "value": "ALERT", "value_type": "CODED",
            "source_type": "DEVICE", "reliability_tier": 1, "measurement_status": "MEASURED",
            "observed_at": utcnow().isoformat(),
        },
    )
    client.post(
        f"/cases/{case_id}/observations",
        json={
            "concept_code": "SUPPLEMENTAL_OXYGEN", "value": False, "value_type": "BOOLEAN",
            "source_type": "DEVICE", "reliability_tier": 1, "measurement_status": "MEASURED",
            "observed_at": utcnow().isoformat(),
        },
    )
    client.get(f"/cases/{case_id}")  # triggers no scoring by itself; force one via queue read
    client.get("/queue")

    conflicts = client.get(f"/cases/{case_id}/conflicts").json()
    assert len(conflicts) == 1
    conflict_id = conflicts[0]["conflict_id"]
    kept_id = conflicts[0]["observation_ids"][0]

    token = client.post("/auth/login", json={"role": "DOCTOR"}).json()["access_token"]
    resp = client.post(
        f"/conflicts/{conflict_id}/resolve",
        json={"kept_observation_id": kept_id, "resolution_note": "Confirmed manually."},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["resolved"] is True

    assert client.get(f"/cases/{case_id}/conflicts").json() == []
