"""
API-level tests for GET /queue and POST /cases/{id}/reassessment.
"""
from datetime import datetime, timezone


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _create_case(client, age_years=40):
    return client.post("/cases", json={"age_years": age_years}).json()["case_id"]


def _post_obs(client, case_id, concept_code, value, value_type):
    return client.post(
        f"/cases/{case_id}/observations",
        json={
            "concept_code": concept_code,
            "value": value,
            "value_type": value_type,
            "source_type": "DEVICE",
            "reliability_tier": 1,
            "measurement_status": "MEASURED",
            "observed_at": _now_iso(),
        },
    )


def test_queue_lists_cases_in_acuity_order(client):
    less_urgent = _create_case(client)
    _post_obs(client, less_urgent, "SPO2", 98.0, "NUMERIC")  # stays near ESI5/capped

    more_urgent = _create_case(client)
    _post_obs(client, more_urgent, "SPO2", 80.0, "NUMERIC")  # hard trigger -> ESI1

    queue = client.get("/queue").json()
    case_ids = [entry["case_id"] for entry in queue]
    assert case_ids.index(more_urgent) < case_ids.index(less_urgent)


def test_queue_entry_shape(client):
    case_id = _create_case(client)
    entry = next(e for e in client.get("/queue").json() if e["case_id"] == case_id)

    for field in [
        "final_acuity", "confidence_band", "should_abstain", "time_critical_pathway_flag",
        "deterioration_trend", "time_in_current_band_minutes", "arrival_time",
        "waiting_minutes", "reassessment", "emergency_bypass_active",
    ]:
        assert field in entry


def test_mark_reassessed_endpoint(client):
    case_id = _create_case(client)
    resp = client.post(f"/cases/{case_id}/reassessment")
    assert resp.status_code == 200

    timeline = client.get(f"/cases/{case_id}/timeline").json()
    assert "REASSESSMENT_COMPLETED" in [e["event_type"] for e in timeline]


def test_mark_reassessed_on_missing_case_is_404(client):
    resp = client.post("/cases/does-not-exist/reassessment")
    assert resp.status_code == 404
