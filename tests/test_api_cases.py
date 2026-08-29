"""
Checkpoint 2 validation: the HTTP surface over EventStore, including the
error-response contract a frontend integrator would actually rely on.
"""
from datetime import datetime, timezone


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _create_case(client, **overrides):
    payload = {"display_name": "Test Patient", "age_years": 40, "arrival_mode": "WALK_IN"}
    payload.update(overrides)
    return client.post("/cases", json=payload)


def test_create_walk_in_case(client):
    resp = _create_case(client)
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "ACTIVE"
    assert body["identity_link_status"] == "CONFIRMED"
    assert body["arrival_mode"] == "WALK_IN"
    assert "case_id" in body


def test_create_ambulance_case_is_pre_arrival_and_unlinked(client):
    resp = _create_case(client, arrival_mode="AMBULANCE", display_name=None, age_years=None)
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "PRE_ARRIVAL"
    assert body["identity_link_status"] == "UNLINKED"
    assert body["arrived_at"] is None


def test_get_case_detail_includes_current_observations(client):
    case_id = _create_case(client).json()["case_id"]
    resp = client.get(f"/cases/{case_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["case_id"] == case_id
    assert body["current_observations"] == []


def test_get_missing_case_is_404(client):
    resp = client.get("/cases/does-not-exist")
    assert resp.status_code == 404
    assert "does-not-exist" in resp.json()["detail"]


def test_add_and_list_observations(client):
    case_id = _create_case(client).json()["case_id"]
    obs_payload = {
        "concept_code": "SPO2",
        "value": 97.0,
        "value_type": "NUMERIC",
        "unit": "%",
        "source_type": "DEVICE",
        "source_id": "pulse-ox-01",
        "reliability_tier": 1,
        "measurement_status": "MEASURED",
        "observed_at": _now_iso(),
    }
    resp = client.post(f"/cases/{case_id}/observations", json=obs_payload)
    assert resp.status_code == 201
    obs_body = resp.json()
    assert obs_body["value"] == 97.0
    assert obs_body["is_current"] is True

    listed = client.get(f"/cases/{case_id}/observations").json()
    assert len(listed) == 1
    assert listed[0]["observation_id"] == obs_body["observation_id"]


def test_add_observation_value_type_mismatch_is_422(client):
    case_id = _create_case(client).json()["case_id"]
    obs_payload = {
        "concept_code": "SPO2",
        "value": True,  # bool, but value_type says NUMERIC
        "value_type": "NUMERIC",
        "source_type": "DEVICE",
        "reliability_tier": 1,
        "measurement_status": "MEASURED",
        "observed_at": _now_iso(),
    }
    resp = client.post(f"/cases/{case_id}/observations", json=obs_payload)
    assert resp.status_code == 422


def test_ai_inferred_without_confidence_is_422(client):
    case_id = _create_case(client).json()["case_id"]
    obs_payload = {
        "concept_code": "CHEST_PAIN",
        "value": True,
        "value_type": "BOOLEAN",
        "source_type": "AI_INFERRED",
        "reliability_tier": 4,
        "measurement_status": "MEASURED",
        "observed_at": _now_iso(),
    }
    resp = client.post(f"/cases/{case_id}/observations", json=obs_payload)
    assert resp.status_code == 422
    assert "extraction_confidence" in resp.text


def test_add_observation_to_missing_case_is_404(client):
    obs_payload = {
        "concept_code": "SPO2",
        "value": 97.0,
        "value_type": "NUMERIC",
        "source_type": "DEVICE",
        "reliability_tier": 1,
        "measurement_status": "MEASURED",
        "observed_at": _now_iso(),
    }
    resp = client.post("/cases/does-not-exist/observations", json=obs_payload)
    assert resp.status_code == 404


def test_supersede_observation(client):
    case_id = _create_case(client).json()["case_id"]
    original = client.post(
        f"/cases/{case_id}/observations",
        json={
            "concept_code": "HEART_RATE",
            "value": 72.0,
            "value_type": "NUMERIC",
            "source_type": "NURSE",
            "reliability_tier": 2,
            "measurement_status": "MEASURED",
            "observed_at": _now_iso(),
        },
    ).json()

    corrected_resp = client.post(
        f"/observations/{original['observation_id']}/supersede",
        json={
            "value": 132.0,
            "value_type": "NUMERIC",
            "source_type": "NURSE",
            "reliability_tier": 2,
            "measurement_status": "MEASURED",
            "observed_at": _now_iso(),
        },
    )
    assert corrected_resp.status_code == 201
    corrected = corrected_resp.json()
    assert corrected["value"] == 132.0
    assert corrected["concept_code"] == "HEART_RATE"  # carried forward, not client-supplied

    current = client.get(f"/cases/{case_id}/observations").json()
    assert len(current) == 1
    assert current[0]["observation_id"] == corrected["observation_id"]


def test_supersede_already_superseded_is_409(client):
    case_id = _create_case(client).json()["case_id"]
    original = client.post(
        f"/cases/{case_id}/observations",
        json={
            "concept_code": "HEART_RATE",
            "value": 72.0,
            "value_type": "NUMERIC",
            "source_type": "NURSE",
            "reliability_tier": 2,
            "measurement_status": "MEASURED",
            "observed_at": _now_iso(),
        },
    ).json()
    supersede_body = {
        "value": 80.0,
        "value_type": "NUMERIC",
        "source_type": "NURSE",
        "reliability_tier": 2,
        "measurement_status": "MEASURED",
        "observed_at": _now_iso(),
    }
    client.post(f"/observations/{original['observation_id']}/supersede", json=supersede_body)

    second_attempt = client.post(f"/observations/{original['observation_id']}/supersede", json=supersede_body)
    assert second_attempt.status_code == 409


def test_record_arrival_transitions_ambulance_case(client):
    case_id = _create_case(client, arrival_mode="AMBULANCE", display_name=None, age_years=None).json()[
        "case_id"
    ]
    resp = client.post(f"/cases/{case_id}/arrival", json={})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ACTIVE"
    assert body["arrived_at"] is not None

    timeline = client.get(f"/cases/{case_id}/timeline").json()
    # CP7: arrival also triggers the case's first RiskAssessment (Phase 5,
    # a case must be scored the moment it's ACTIVE, not only once vitals
    # arrive) -- RISK_ASSESSMENT_COMPUTED follows PATIENT_ARRIVED.
    assert [e["event_type"] for e in timeline] == [
        "CASE_CREATED",
        "PATIENT_ARRIVED",
        "RISK_ASSESSMENT_COMPUTED",
    ]


def test_record_arrival_on_walk_in_is_409(client):
    case_id = _create_case(client).json()["case_id"]  # WALK_IN -> already ACTIVE
    resp = client.post(f"/cases/{case_id}/arrival", json={})
    assert resp.status_code == 409


def test_list_cases_filters_by_status(client):
    _create_case(client, mrn="A")
    _create_case(client, mrn="B", arrival_mode="AMBULANCE", display_name=None, age_years=None)

    active = client.get("/cases", params={"status": "ACTIVE"}).json()
    pre_arrival = client.get("/cases", params={"status": "PRE_ARRIVAL"}).json()

    assert {c["mrn"] for c in active} == {"A"}
    assert {c["mrn"] for c in pre_arrival} == {"B"}


def test_health_check(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
