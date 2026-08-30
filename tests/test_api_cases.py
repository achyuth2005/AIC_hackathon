"""
Checkpoint 2 validation: the HTTP surface over EventStore, including the
error-response contract a frontend integrator would actually rely on.

Audit remediation: most of these endpoints now require an authenticated
staff token (see app/auth/deps.py) -- every call below passes
`nurse_headers` accordingly. `GET /cases/{id}` and its sibling read
endpoints also now require auth (see app/api/cases.py's audit-fix
docstring), so reads use it too.
"""
from datetime import datetime, timezone

import pytest


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _create_case(client, headers, **overrides):
    payload = {"display_name": "Test Patient", "age_years": 40, "arrival_mode": "WALK_IN"}
    payload.update(overrides)
    return client.post("/cases", json=payload, headers=headers)


def test_create_walk_in_case(client, nurse_headers):
    resp = _create_case(client, nurse_headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "ACTIVE"
    assert body["identity_link_status"] == "CONFIRMED"
    assert body["arrival_mode"] == "WALK_IN"
    assert "case_id" in body


def test_create_case_requires_authentication(client):
    resp = client.post("/cases", json={"display_name": "Test Patient", "age_years": 40})
    assert resp.status_code == 401


def test_create_ambulance_case_is_pre_arrival_and_unlinked(client, nurse_headers):
    resp = _create_case(client, nurse_headers, arrival_mode="AMBULANCE", display_name=None, age_years=None)
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "PRE_ARRIVAL"
    assert body["identity_link_status"] == "UNLINKED"
    assert body["arrived_at"] is None


def test_get_case_detail_includes_current_observations(client, nurse_headers):
    case_id = _create_case(client, nurse_headers).json()["case_id"]
    resp = client.get(f"/cases/{case_id}", headers=nurse_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["case_id"] == case_id
    assert body["current_observations"] == []


def test_get_case_requires_authentication(client, nurse_headers):
    case_id = _create_case(client, nurse_headers).json()["case_id"]
    resp = client.get(f"/cases/{case_id}")
    assert resp.status_code == 401


def test_get_missing_case_is_404(client, nurse_headers):
    resp = client.get("/cases/does-not-exist", headers=nurse_headers)
    assert resp.status_code == 404
    assert "does-not-exist" in resp.json()["detail"]


def test_add_and_list_observations(client, nurse_headers):
    case_id = _create_case(client, nurse_headers).json()["case_id"]
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
    resp = client.post(f"/cases/{case_id}/observations", json=obs_payload, headers=nurse_headers)
    assert resp.status_code == 201
    obs_body = resp.json()
    assert obs_body["value"] == 97.0
    assert obs_body["is_current"] is True

    listed = client.get(f"/cases/{case_id}/observations", headers=nurse_headers).json()
    assert len(listed) == 1
    assert listed[0]["observation_id"] == obs_body["observation_id"]


def test_add_observation_value_type_mismatch_is_422(client, nurse_headers):
    case_id = _create_case(client, nurse_headers).json()["case_id"]
    obs_payload = {
        "concept_code": "SPO2",
        "value": True,  # bool, but value_type says NUMERIC
        "value_type": "NUMERIC",
        "source_type": "DEVICE",
        "reliability_tier": 1,
        "measurement_status": "MEASURED",
        "observed_at": _now_iso(),
    }
    resp = client.post(f"/cases/{case_id}/observations", json=obs_payload, headers=nurse_headers)
    assert resp.status_code == 422


def test_ai_inferred_without_confidence_is_422(client, nurse_headers):
    case_id = _create_case(client, nurse_headers).json()["case_id"]
    obs_payload = {
        "concept_code": "SYMPTOM_CHEST_PAIN",
        "value": True,
        "value_type": "BOOLEAN",
        "source_type": "AI_INFERRED",
        "reliability_tier": 4,
        "measurement_status": "MEASURED",
        "observed_at": _now_iso(),
    }
    resp = client.post(f"/cases/{case_id}/observations", json=obs_payload, headers=nurse_headers)
    assert resp.status_code == 422
    assert "extraction_confidence" in resp.text


def test_add_observation_rejects_an_unknown_concept_code_with_422(client, nurse_headers):
    case_id = _create_case(client, nurse_headers).json()["case_id"]
    obs_payload = {
        "concept_code": "HEART_RATEE",  # typo -- not in the controlled vocabulary
        "value": 72.0,
        "value_type": "NUMERIC",
        "source_type": "DEVICE",
        "reliability_tier": 1,
        "measurement_status": "MEASURED",
        "observed_at": _now_iso(),
    }
    resp = client.post(f"/cases/{case_id}/observations", json=obs_payload, headers=nurse_headers)
    assert resp.status_code == 422


def test_add_observation_rejects_an_implausible_vital_with_422(client, nurse_headers):
    case_id = _create_case(client, nurse_headers).json()["case_id"]
    obs_payload = {
        "concept_code": "SPO2",
        "value": 980.0,  # a percentage that can never exceed 100
        "value_type": "NUMERIC",
        "source_type": "DEVICE",
        "reliability_tier": 1,
        "measurement_status": "MEASURED",
        "observed_at": _now_iso(),
    }
    resp = client.post(f"/cases/{case_id}/observations", json=obs_payload, headers=nurse_headers)
    assert resp.status_code == 422


def test_add_observation_rejects_a_null_value_when_measured_with_422(client, nurse_headers):
    """Audit fix (Critical, data integrity): measurement_status=MEASURED
    with no value used to return a clean 201 and persist a row that
    permanently broke every future scoring pass over this concept for this
    case. Rejected at the door now, same as every other malformed-payload
    case in this file."""
    case_id = _create_case(client, nurse_headers).json()["case_id"]
    obs_payload = {
        "concept_code": "TEMPERATURE",
        "value_type": "NUMERIC",
        "source_type": "DEVICE",
        "reliability_tier": 1,
        "measurement_status": "MEASURED",
        "observed_at": _now_iso(),
        # "value" deliberately omitted -- defaults to null.
    }
    resp = client.post(f"/cases/{case_id}/observations", json=obs_payload, headers=nurse_headers)
    assert resp.status_code == 422
    assert "measurement_status is MEASURED" in resp.text

    # And nothing was persisted despite the 422.
    listed = client.get(f"/cases/{case_id}/observations", headers=nurse_headers).json()
    assert listed == []


def test_add_observation_rolls_back_entirely_if_rescoring_fails(client, nurse_headers, monkeypatch):
    """Audit fix (Critical, atomicity): the observation write, the
    emergency-bypass check, and the rescore now share exactly one
    transaction (app/api/cases.py's add_observation composes all three
    with commit=False and commits once at the end). Forcing the rescore
    step to blow up here stands in for the real-world failure (a value
    app/scoring/banding.py had no configured band for) that used to leave
    an orphaned, never-scored observation permanently in the store --
    the exact shape of the 863 corrupt rows found in the pre-existing demo
    dataset. If rescoring fails, the observation must not exist either."""
    import app.api.cases as cases_module

    # Created BEFORE the monkeypatch below -- create_case also calls
    # assess_case (its own initial-assessment step) and must not be caught
    # by the same patch as the observation endpoint under test.
    case_id = _create_case(client, nurse_headers).json()["case_id"]

    def _boom(*args, **kwargs):
        raise RuntimeError("simulated scoring engine failure")

    monkeypatch.setattr(cases_module, "assess_case", _boom)

    obs_payload = {
        "concept_code": "SPO2",
        "value": 97.0,
        "value_type": "NUMERIC",
        "source_type": "DEVICE",
        "reliability_tier": 1,
        "measurement_status": "MEASURED",
        "observed_at": _now_iso(),
    }
    with pytest.raises(RuntimeError, match="simulated scoring engine failure"):
        client.post(f"/cases/{case_id}/observations", json=obs_payload, headers=nurse_headers)

    # The observation write happened first and would previously have been
    # committed on its own -- confirm it was rolled back along with the
    # rescore failure, not left behind as an orphaned row.
    monkeypatch.undo()  # restore the real assess_case before the GET below
    listed = client.get(f"/cases/{case_id}/observations", headers=nurse_headers).json()
    assert listed == []


def test_add_observation_to_missing_case_is_404(client, nurse_headers):
    obs_payload = {
        "concept_code": "SPO2",
        "value": 97.0,
        "value_type": "NUMERIC",
        "source_type": "DEVICE",
        "reliability_tier": 1,
        "measurement_status": "MEASURED",
        "observed_at": _now_iso(),
    }
    resp = client.post("/cases/does-not-exist/observations", json=obs_payload, headers=nurse_headers)
    assert resp.status_code == 404


def test_supersede_observation(client, nurse_headers):
    case_id = _create_case(client, nurse_headers).json()["case_id"]
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
        headers=nurse_headers,
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
        headers=nurse_headers,
    )
    assert corrected_resp.status_code == 201
    corrected = corrected_resp.json()
    assert corrected["value"] == 132.0
    assert corrected["concept_code"] == "HEART_RATE"  # carried forward, not client-supplied

    current = client.get(f"/cases/{case_id}/observations", headers=nurse_headers).json()
    assert len(current) == 1
    assert current[0]["observation_id"] == corrected["observation_id"]


def test_supersede_already_superseded_is_409(client, nurse_headers):
    case_id = _create_case(client, nurse_headers).json()["case_id"]
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
        headers=nurse_headers,
    ).json()
    supersede_body = {
        "value": 80.0,
        "value_type": "NUMERIC",
        "source_type": "NURSE",
        "reliability_tier": 2,
        "measurement_status": "MEASURED",
        "observed_at": _now_iso(),
    }
    client.post(f"/observations/{original['observation_id']}/supersede", json=supersede_body, headers=nurse_headers)

    second_attempt = client.post(
        f"/observations/{original['observation_id']}/supersede", json=supersede_body, headers=nurse_headers
    )
    assert second_attempt.status_code == 409


def test_record_arrival_transitions_ambulance_case(client, nurse_headers):
    case_id = _create_case(
        client, nurse_headers, arrival_mode="AMBULANCE", display_name=None, age_years=None
    ).json()["case_id"]
    resp = client.post(f"/cases/{case_id}/arrival", json={}, headers=nurse_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ACTIVE"
    assert body["arrived_at"] is not None

    timeline = client.get(f"/cases/{case_id}/timeline", headers=nurse_headers).json()
    # CP7: arrival also triggers the case's first RiskAssessment (Phase 5,
    # a case must be scored the moment it's ACTIVE, not only once vitals
    # arrive) -- RISK_ASSESSMENT_COMPUTED follows PATIENT_ARRIVED.
    assert [e["event_type"] for e in timeline] == [
        "CASE_CREATED",
        "PATIENT_ARRIVED",
        "RISK_ASSESSMENT_COMPUTED",
    ]


def test_record_arrival_on_walk_in_is_409(client, nurse_headers):
    case_id = _create_case(client, nurse_headers).json()["case_id"]  # WALK_IN -> already ACTIVE
    resp = client.post(f"/cases/{case_id}/arrival", json={}, headers=nurse_headers)
    assert resp.status_code == 409


def test_list_cases_filters_by_status(client, nurse_headers):
    _create_case(client, nurse_headers, mrn="A")
    _create_case(client, nurse_headers, mrn="B", arrival_mode="AMBULANCE", display_name=None, age_years=None)

    active = client.get("/cases", params={"status": "ACTIVE"}, headers=nurse_headers).json()
    pre_arrival = client.get("/cases", params={"status": "PRE_ARRIVAL"}, headers=nurse_headers).json()

    assert {c["mrn"] for c in active} == {"A"}
    assert {c["mrn"] for c in pre_arrival} == {"B"}


def test_list_cases_filters_by_arrival_mode(client, nurse_headers):
    """Regression: the Guardian Queue (GET /queue) can never surface a
    PRE_ARRIVAL ambulance case (status=ACTIVE only, by design), so the
    ambulance pre-arrival board needs GET /cases?arrival_mode=AMBULANCE to
    find one regardless of stage."""
    _create_case(client, nurse_headers, mrn="WALKIN")
    _create_case(
        client, nurse_headers, mrn="AMB", arrival_mode="AMBULANCE", display_name=None, age_years=None
    )

    ambulances = client.get("/cases", params={"arrival_mode": "AMBULANCE"}, headers=nurse_headers).json()
    assert {c["mrn"] for c in ambulances} == {"AMB"}
    assert all(c["arrival_mode"] == "AMBULANCE" for c in ambulances)


def test_health_check(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
