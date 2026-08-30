"""
API-level tests for GET /queue and POST /cases/{id}/reassessment.
"""
from datetime import datetime, timezone

from app.models.enums import MeasurementStatus, ReliabilityTier, SourceType, ValueType
from app.scoring import concepts
from app.timeutil import utcnow


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _create_case(client, headers, age_years=40):
    return client.post("/cases", json={"age_years": age_years}, headers=headers).json()["case_id"]


def _post_obs(client, headers, case_id, concept_code, value, value_type):
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
        headers=headers,
    )


def test_queue_lists_cases_in_acuity_order(client, nurse_headers):
    less_urgent = _create_case(client, nurse_headers)
    _post_obs(client, nurse_headers, less_urgent, "SPO2", 98.0, "NUMERIC")  # stays near ESI5/capped

    more_urgent = _create_case(client, nurse_headers)
    _post_obs(client, nurse_headers, more_urgent, "SPO2", 80.0, "NUMERIC")  # hard trigger -> ESI1

    queue = client.get("/queue", headers=nurse_headers).json()
    case_ids = [entry["case_id"] for entry in queue]
    assert case_ids.index(more_urgent) < case_ids.index(less_urgent)


def test_queue_returns_200_and_excludes_one_malformed_case(client, nurse_headers, store):
    """Audit fix (Critical, fault isolation): GET /queue must return 200
    with every valid case even when one *other* active case in the same
    hospital has a data/config problem the scoring engine can't band --
    never take the whole endpoint down for every other patient. This is
    also what GET /queue/printable, the documented total-system-failure
    paper fallback, is built directly on top of."""
    good_case = _create_case(client, nurse_headers)
    _post_obs(client, nurse_headers, good_case, "SPO2", 98.0, "NUMERIC")

    # Built via the store directly, not the API: the atomic-transaction fix
    # means the API itself would now reject-and-roll-back a value the
    # scoring engine can't band, so a case actually reaching this state in
    # production (a future config/data gap of the same shape) is exactly
    # what this simulates.
    bad_case = store.create_case(age_years=40)
    now = utcnow()
    for concept, value, vtype in [
        (concepts.RESP_RATE, 16.0, ValueType.NUMERIC),
        (concepts.SPO2, 98.0, ValueType.NUMERIC),
        (concepts.SUPPLEMENTAL_OXYGEN, False, ValueType.BOOLEAN),
        (concepts.SYSTOLIC_BP, 120.0, ValueType.NUMERIC),
        (concepts.HEART_RATE, 75.0, ValueType.NUMERIC),
        (concepts.CONSCIOUSNESS_LEVEL, "SOMNOLENT", ValueType.CODED),  # no configured band anywhere
        (concepts.TEMPERATURE, 37.0, ValueType.NUMERIC),
    ]:
        store.add_observation(
            case_id=bad_case.case_id,
            concept_code=concept,
            value=value,
            value_type=vtype,
            source_type=SourceType.DEVICE,
            reliability_tier=ReliabilityTier.MACHINE_MEASURED,
            measurement_status=MeasurementStatus.MEASURED,
            observed_at=now,
        )
    # Deliberately no assess_case() call -- build_queue's self-healing
    # backfill performs the first (failing) scoring attempt for this case.

    resp = client.get("/queue", headers=nurse_headers)
    assert resp.status_code == 200

    case_ids = {entry["case_id"] for entry in resp.json()}
    assert good_case in case_ids
    assert bad_case.case_id not in case_ids


def test_queue_requires_authentication(client):
    resp = client.get("/queue")
    assert resp.status_code == 401


def test_queue_entry_shape(client, nurse_headers):
    case_id = _create_case(client, nurse_headers)
    entry = next(e for e in client.get("/queue", headers=nurse_headers).json() if e["case_id"] == case_id)

    for field in [
        "final_acuity", "confidence_band", "should_abstain", "time_critical_pathway_flag",
        "deterioration_trend", "time_in_current_band_minutes", "arrival_time",
        "waiting_minutes", "reassessment", "emergency_bypass_active",
    ]:
        assert field in entry


def test_mark_reassessed_endpoint(client, nurse_headers):
    case_id = _create_case(client, nurse_headers)
    resp = client.post(f"/cases/{case_id}/reassessment", headers=nurse_headers)
    assert resp.status_code == 200

    timeline = client.get(f"/cases/{case_id}/timeline", headers=nurse_headers).json()
    assert "REASSESSMENT_COMPLETED" in [e["event_type"] for e in timeline]


def test_mark_reassessed_on_missing_case_is_404(client, nurse_headers):
    resp = client.post("/cases/does-not-exist/reassessment", headers=nurse_headers)
    assert resp.status_code == 404
