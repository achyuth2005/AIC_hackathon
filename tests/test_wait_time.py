"""
Tests for Waiting-time prediction (Phase 6.4): the queue model itself, and
its presence on the Guardian Queue / case-detail API responses.
"""
from datetime import timedelta

from app.config.hospital_profile import load_hospital_profile
from app.models.enums import ResourceType
from app.ops.wait_time import estimate_wait_time
from app.store.event_store import EventStore
from app.timeutil import utcnow

PROFILE = load_hospital_profile("default")


def test_estimate_is_always_a_widening_range_not_a_single_number(store: EventStore):
    case = store.create_case(age_years=40)
    estimate = estimate_wait_time(store, PROFILE, case.case_id, final_acuity=3)

    assert estimate.lower_minutes <= estimate.upper_minutes
    assert estimate.upper_minutes > estimate.lower_minutes  # a real range, never zero-width
    assert "estimate" in estimate.caveat.lower()
    assert "not a commitment" in estimate.caveat.lower()


def test_no_history_and_no_capacity_falls_back_to_configured_default(store: EventStore):
    case = store.create_case(age_years=40)  # no resources registered at all, no history
    estimate = estimate_wait_time(store, PROFILE, case.case_id, final_acuity=2)

    assert estimate.basis == "CONFIGURED_DEFAULT"
    assert estimate.available_capacity == 0
    assert estimate.sample_size == 0


def test_more_patients_ahead_widens_the_point_estimate(store: EventStore):
    from app.scoring.risk_orchestrator import assess_case

    store.create_resource(resource_type=ResourceType.CLINICIAN, label="Dr. A")
    solo_case = store.create_case(age_years=30)
    assess_case(solo_case, store, PROFILE)  # gives it a real final_acuity to be "ahead" of
    solo_estimate = estimate_wait_time(store, PROFILE, solo_case.case_id, final_acuity=3)

    for _ in range(5):
        waiting_case = store.create_case(age_years=30)
        assess_case(waiting_case, store, PROFILE)
    crowded_case = store.create_case(age_years=30)
    assess_case(crowded_case, store, PROFILE)
    crowded_estimate = estimate_wait_time(store, PROFILE, crowded_case.case_id, final_acuity=3)

    assert crowded_estimate.patients_ahead > solo_estimate.patients_ahead
    assert crowded_estimate.upper_minutes > solo_estimate.upper_minutes


def test_patient_already_in_service_does_not_count_as_ahead(store: EventStore):
    store.create_resource(resource_type=ResourceType.TREATMENT_SPACE, label="Bay 1")
    in_service_case = store.create_case(age_years=40)
    store.assign_resource(in_service_case.case_id, ResourceType.TREATMENT_SPACE, PROFILE)

    waiting_case = store.create_case(age_years=40)
    estimate = estimate_wait_time(store, PROFILE, waiting_case.case_id, final_acuity=3)

    assert estimate.patients_ahead == 0  # the only other case is already being seen


def test_band_history_used_once_enough_samples_exist(store: EventStore):
    from app.scoring.risk_orchestrator import assess_case

    store.create_resource(resource_type=ResourceType.CLINICIAN, label="Dr. B")

    # Manufacture 3 historical same-band samples (identical inputs -> the
    # same resulting acuity every time), each with a real RESOURCE_ASSIGNED
    # event so _band_at_time can classify it. Deliberately let every
    # timestamp default to the store's own real-time clock (rather than a
    # single captured `now` reused across steps) so arrival always precedes
    # assignment -- exactly as it would in production.
    acuity_seen = None
    for _ in range(3):
        case = store.create_case(age_years=50)
        acuity_seen = assess_case(case, store, PROFILE).final_acuity
        resource = store.assign_resource(case.case_id, ResourceType.CLINICIAN, PROFILE)
        store.release_resource(resource.resource_id)  # free "Dr. B" for the next loop iteration

    estimate = estimate_wait_time(store, PROFILE, "irrelevant-case-id-not-in-store", final_acuity=acuity_seen)
    assert estimate.basis == "BAND_HISTORY"
    assert estimate.sample_size >= 3


def test_queue_entries_carry_a_wait_time_estimate(client, nurse_headers):
    resp = client.post("/cases", json={"age_years": 40}, headers=nurse_headers)
    case_id = resp.json()["case_id"]

    queue = client.get("/queue", headers=nurse_headers).json()
    entry = next(e for e in queue if e["case_id"] == case_id)
    assert entry["wait_time_estimate"]["lower_minutes"] <= entry["wait_time_estimate"]["upper_minutes"]
    assert entry["wait_time_estimate"]["caveat"]


def test_case_detail_carries_a_wait_time_estimate_once_active_with_an_assessment(client, nurse_headers):
    resp = client.post("/cases", json={"age_years": 40}, headers=nurse_headers)
    case_id = resp.json()["case_id"]

    # Force an initial assessment via the queue's self-healing backfill.
    client.get("/queue", headers=nurse_headers)

    detail = client.get(f"/cases/{case_id}", headers=nurse_headers).json()
    assert detail["wait_time_estimate"] is not None
    assert detail["wait_time_estimate"]["lower_minutes"] <= detail["wait_time_estimate"]["upper_minutes"]
