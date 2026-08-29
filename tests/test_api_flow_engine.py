"""
API-level tests for resources, diagnostic tests, and the stuck-patients
sweep (Phase 6).
"""


def _create_case(client, age_years=40):
    return client.post("/cases", json={"age_years": age_years}).json()["case_id"]


def test_create_and_list_resources(client):
    resp = client.post("/resources", json={"resource_type": "TREATMENT_SPACE", "label": "Bay 7"})
    assert resp.status_code == 201
    resource_id = resp.json()["resource_id"]

    listed = client.get("/resources", params={"resource_type": "TREATMENT_SPACE"}).json()
    assert any(r["resource_id"] == resource_id for r in listed)


def test_assign_resource_via_case_endpoint(client):
    client.post("/resources", json={"resource_type": "TREATMENT_SPACE", "label": "Bay 8"})
    case_id = _create_case(client)

    resp = client.post(f"/cases/{case_id}/assign-resource", json={"resource_type": "TREATMENT_SPACE"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "OCCUPIED"
    assert body["assigned_case_id"] == case_id


def test_assign_resource_capacity_conflict_returns_409_with_candidate_actions(client):
    case_id = _create_case(client)  # no resources registered
    resp = client.post(f"/cases/{case_id}/assign-resource", json={"resource_type": "RESUSCITATION_BAY"})
    assert resp.status_code == 409
    body = resp.json()
    assert body["resource_type"] == "RESUSCITATION_BAY"
    assert len(body["candidate_actions"]) > 0


def test_confirm_occupancy_and_release(client):
    resource_id = client.post(
        "/resources", json={"resource_type": "TREATMENT_SPACE", "label": "Bay 9"}
    ).json()["resource_id"]
    case_id = _create_case(client)
    client.post(f"/cases/{case_id}/assign-resource", json={"resource_type": "TREATMENT_SPACE"})

    confirmed = client.post(f"/resources/{resource_id}/confirm-occupancy")
    assert confirmed.status_code == 200

    released = client.post(f"/resources/{resource_id}/release")
    assert released.status_code == 200
    assert released.json()["status"] == "AVAILABLE"
    assert released.json()["assigned_case_id"] is None


def test_diagnostic_test_lifecycle_via_api(client):
    case_id = _create_case(client)
    ordered = client.post(f"/cases/{case_id}/tests", json={"test_type": "CBC"})
    assert ordered.status_code == 201
    test_id = ordered.json()["test_id"]
    assert ordered.json()["status"] == "ORDERED"

    collected = client.post(f"/tests/{test_id}/sample-collected")
    assert collected.json()["status"] == "SAMPLE_COLLECTED"

    available = client.post(f"/tests/{test_id}/result-available")
    assert available.json()["status"] == "RESULT_AVAILABLE"

    reviewed = client.post(f"/tests/{test_id}/result-reviewed")
    assert reviewed.json()["status"] == "RESULT_REVIEWED"

    tests = client.get(f"/cases/{case_id}/tests").json()
    assert len(tests) == 1
    assert tests[0]["test_id"] == test_id


def test_stuck_patients_endpoint_returns_empty_when_nothing_stuck(client):
    _create_case(client)
    stuck = client.get("/ops/stuck-patients").json()
    assert stuck == []


def test_order_test_on_missing_case_is_404(client):
    resp = client.post("/cases/does-not-exist/tests", json={"test_type": "CBC"})
    assert resp.status_code == 404
