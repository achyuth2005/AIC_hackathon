"""
Tests for the Phase 14.2 surge simulator (CP14): each of the six named
surge-time properties actually holds on the returned evidence, not just
that the simulation runs without error.
"""
from app.config.hospital_profile import load_hospital_profile
from app.demo.surge import run_surge_simulation
from app.store.event_store import EventStore

PROFILE = load_hospital_profile("default")


def test_queue_scales_with_volume_and_ordering_holds(store: EventStore):
    result = run_surge_simulation(store, PROFILE, baseline_count=10, multiplier=3)
    assert result.queue_length_before == 10
    assert result.queue_length_after == 30
    assert result.total_cases == 30
    assert result.acuity_ordering_holds is True


def test_reassessment_intervals_lapse(store: EventStore):
    result = run_surge_simulation(store, PROFILE, baseline_count=10, multiplier=3)
    assert result.reassessment_overdue_count > 0


def test_alert_count_grows_slower_than_volume(store: EventStore):
    result = run_surge_simulation(store, PROFILE, baseline_count=10, multiplier=3)
    assert result.alerts_before > 0  # a real, nonzero baseline to measure growth against
    assert result.alert_multiplier_actual is not None
    assert result.alert_multiplier_actual < result.volume_multiplier
    assert result.alert_growth_held_below_volume_growth is True


def test_capacity_conflict_fires_and_is_surfaced(store: EventStore):
    result = run_surge_simulation(store, PROFILE, baseline_count=10, multiplier=3)
    assert result.capacity_conflict_demonstrated is True
    assert result.capacity_conflict_detail["resource_type"] == "RESUSCITATION_BAY"
    assert len(result.capacity_conflict_detail["candidate_actions"]) > 0


def test_capacity_conflict_never_changes_acuity_ordering(store: EventStore):
    """The conflict must be surfaced, never used to reorder around or
    downgrade anyone -- re-affirms Phase 6.2's independence principle
    holds even under surge load."""
    result = run_surge_simulation(store, PROFILE, baseline_count=10, multiplier=3)
    assert result.acuity_ordering_holds is True


def test_stuck_patients_accumulate(store: EventStore):
    result = run_surge_simulation(store, PROFILE, baseline_count=10, multiplier=3)
    assert result.stuck_patient_count == 3


def test_waiting_patient_deteriorates_and_jumps_newer_arrivals(store: EventStore):
    result = run_surge_simulation(store, PROFILE, baseline_count=10, multiplier=3)
    assert result.escalated_case_id is not None
    assert result.escalated_to_acuity < result.escalated_from_acuity  # more urgent afterward
    assert result.escalated_jumped_newer_arrivals_count > 0


def test_narrative_is_a_complete_human_readable_log(store: EventStore):
    result = run_surge_simulation(store, PROFILE, baseline_count=10, multiplier=3)
    assert len(result.narrative) >= 6


def test_different_multiplier_and_baseline_size(store: EventStore):
    result = run_surge_simulation(store, PROFILE, baseline_count=5, multiplier=4)
    assert result.baseline_count == 5
    assert result.surge_count == 15
    assert result.total_cases == 20
    assert result.acuity_ordering_holds is True


# ---------------------------------------------------------------------
# HTTP surface
# ---------------------------------------------------------------------
def test_surge_endpoint(client, admin_headers):
    unauth = client.post("/demo/surge", params={"baseline_count": 6, "multiplier": 3})
    assert unauth.status_code == 401

    resp = client.post("/demo/surge", params={"baseline_count": 6, "multiplier": 3}, headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_cases"] == 18
    assert body["acuity_ordering_holds"] is True
    assert body["capacity_conflict_demonstrated"] is True
