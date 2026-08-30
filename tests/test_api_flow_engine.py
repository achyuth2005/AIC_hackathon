"""
API-level tests for resources, diagnostic tests, and the stuck-patients
sweep (Phase 6).

Audit remediation: resource provisioning (POST /resources) is ADMIN-only
(operational/administrative action, least privilege); everything else
below just needs any authenticated staff token.
"""


def _create_case(client, headers, age_years=40):
    return client.post("/cases", json={"age_years": age_years}, headers=headers).json()["case_id"]


def test_create_and_list_resources(client, admin_headers, nurse_headers):
    resp = client.post(
        "/resources", json={"resource_type": "TREATMENT_SPACE", "label": "Bay 7"}, headers=admin_headers
    )
    assert resp.status_code == 201
    resource_id = resp.json()["resource_id"]

    # Least privilege: creating a resource is ADMIN-only.
    forbidden = client.post(
        "/resources", json={"resource_type": "TREATMENT_SPACE", "label": "Bay 7b"}, headers=nurse_headers
    )
    assert forbidden.status_code == 403

    listed = client.get("/resources", params={"resource_type": "TREATMENT_SPACE"}, headers=nurse_headers).json()
    assert any(r["resource_id"] == resource_id for r in listed)


def test_assign_resource_via_case_endpoint(client, admin_headers, nurse_headers):
    client.post("/resources", json={"resource_type": "TREATMENT_SPACE", "label": "Bay 8"}, headers=admin_headers)
    case_id = _create_case(client, nurse_headers)

    resp = client.post(
        f"/cases/{case_id}/assign-resource", json={"resource_type": "TREATMENT_SPACE"}, headers=nurse_headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "OCCUPIED"
    assert body["assigned_case_id"] == case_id


def test_assign_resource_capacity_conflict_returns_409_with_candidate_actions(client, nurse_headers):
    case_id = _create_case(client, nurse_headers)  # no resources registered
    resp = client.post(
        f"/cases/{case_id}/assign-resource", json={"resource_type": "RESUSCITATION_BAY"}, headers=nurse_headers
    )
    assert resp.status_code == 409
    body = resp.json()
    assert body["resource_type"] == "RESUSCITATION_BAY"
    assert len(body["candidate_actions"]) > 0


def test_confirm_occupancy_and_release(client, admin_headers, nurse_headers):
    resource_id = client.post(
        "/resources", json={"resource_type": "TREATMENT_SPACE", "label": "Bay 9"}, headers=admin_headers
    ).json()["resource_id"]
    case_id = _create_case(client, nurse_headers)
    client.post(f"/cases/{case_id}/assign-resource", json={"resource_type": "TREATMENT_SPACE"}, headers=nurse_headers)

    confirmed = client.post(f"/resources/{resource_id}/confirm-occupancy", headers=nurse_headers)
    assert confirmed.status_code == 200

    released = client.post(f"/resources/{resource_id}/release", headers=nurse_headers)
    assert released.status_code == 200
    assert released.json()["status"] == "AVAILABLE"
    assert released.json()["assigned_case_id"] is None


def test_diagnostic_test_lifecycle_via_api(client, nurse_headers):
    case_id = _create_case(client, nurse_headers)
    ordered = client.post(f"/cases/{case_id}/tests", json={"test_type": "CBC"}, headers=nurse_headers)
    assert ordered.status_code == 201
    test_id = ordered.json()["test_id"]
    assert ordered.json()["status"] == "ORDERED"

    collected = client.post(f"/tests/{test_id}/sample-collected", headers=nurse_headers)
    assert collected.json()["status"] == "SAMPLE_COLLECTED"

    available = client.post(f"/tests/{test_id}/result-available", headers=nurse_headers)
    assert available.json()["status"] == "RESULT_AVAILABLE"

    reviewed = client.post(f"/tests/{test_id}/result-reviewed", headers=nurse_headers)
    assert reviewed.json()["status"] == "RESULT_REVIEWED"

    tests = client.get(f"/cases/{case_id}/tests", headers=nurse_headers).json()
    assert len(tests) == 1
    assert tests[0]["test_id"] == test_id


def test_stuck_patients_endpoint_returns_empty_when_nothing_stuck(client, nurse_headers):
    _create_case(client, nurse_headers)
    stuck = client.get("/ops/stuck-patients", headers=nurse_headers).json()
    assert stuck == []


def test_order_test_on_missing_case_is_404(client, nurse_headers):
    resp = client.post("/cases/does-not-exist/tests", json={"test_type": "CBC"}, headers=nurse_headers)
    assert resp.status_code == 404
