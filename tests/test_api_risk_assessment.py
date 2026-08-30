"""
API-level tests: RiskAssessment is computed automatically as observations
arrive and is reachable via GET /cases/{id} (latest) and
GET /cases/{id}/risk-assessments (history).
"""
from datetime import datetime, timezone


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _create_case(client, headers, age_years=40):
    return client.post("/cases", json={"age_years": age_years}, headers=headers).json()["case_id"]


def _post_obs(client, headers, case_id, concept_code, value, value_type, reliability_tier=1):
    return client.post(
        f"/cases/{case_id}/observations",
        json={
            "concept_code": concept_code,
            "value": value,
            "value_type": value_type,
            "source_type": "DEVICE",
            "reliability_tier": reliability_tier,
            "measurement_status": "MEASURED",
            "observed_at": _now_iso(),
        },
        headers=headers,
    )


def test_case_detail_has_an_initial_assessment_before_any_observation(client, nurse_headers):
    """CP7: a case gets its first RiskAssessment the moment it's ACTIVE
    (registration for a walk-in), not only once vitals arrive -- Phase 9.2
    abstention applies (no vitals at all yet), holding at a safe default
    rather than leaving the case invisible to the Guardian Queue."""
    case_id = _create_case(client, nurse_headers)
    detail = client.get(f"/cases/{case_id}", headers=nurse_headers).json()
    ra = detail["latest_risk_assessment"]
    assert ra is not None
    assert ra["should_abstain"] is True
    assert ra["deciding_layer"] == "ABSTENTION"


def test_adding_an_observation_produces_a_latest_risk_assessment(client, nurse_headers):
    case_id = _create_case(client, nurse_headers)
    resp = _post_obs(client, nurse_headers, case_id, "SPO2", 98.0, "NUMERIC")
    assert resp.status_code == 201

    detail = client.get(f"/cases/{case_id}", headers=nurse_headers).json()
    ra = detail["latest_risk_assessment"]
    assert ra is not None
    assert ra["case_id"] == case_id
    assert "final_acuity" in ra and 1 <= ra["final_acuity"] <= 5
    assert ra["deciding_layer"] in {"RULES", "ML", "ABSTENTION", "OVERRIDE"}


def test_risk_assessment_history_grows_with_each_observation(client, nurse_headers):
    case_id = _create_case(client, nurse_headers)  # CP7: registration itself produces assessment #1
    _post_obs(client, nurse_headers, case_id, "SPO2", 98.0, "NUMERIC")
    _post_obs(client, nurse_headers, case_id, "HEART_RATE", 75.0, "NUMERIC")

    history = client.get(f"/cases/{case_id}/risk-assessments", headers=nurse_headers).json()
    assert len(history) == 3  # registration + one re-assessment per observation write
    # Ordered oldest-first, never mutated in place.
    ids = [a["assessment_id"] for a in history]
    assert len(set(ids)) == 3


def test_risk_assessments_on_missing_case_is_404(client, nurse_headers):
    resp = client.get("/cases/does-not-exist/risk-assessments", headers=nurse_headers)
    assert resp.status_code == 404


def test_critical_vital_drives_final_acuity_to_1_via_api(client, nurse_headers):
    case_id = _create_case(client, nurse_headers)
    _post_obs(client, nurse_headers, case_id, "SPO2", 80.0, "NUMERIC")  # CRITICAL_HYPOXIA hard trigger

    detail = client.get(f"/cases/{case_id}", headers=nurse_headers).json()
    ra = detail["latest_risk_assessment"]
    assert ra["final_acuity"] == 1
    assert len(ra["hard_triggers_fired"]) == 1
