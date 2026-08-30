"""
Tests for the "I feel worse" button (Phase 8.1): EventStore-level,
Guardian-Queue-level, and API-level.
"""
from datetime import timedelta

from app.config.hospital_profile import load_hospital_profile
from app.queue.guardian_queue import build_queue
from app.scoring.risk_orchestrator import assess_case
from app.store.event_store import EventStore
from app.timeutil import utcnow

PROFILE = load_hospital_profile("default")


def test_reports_immediately_flag_overdue_regardless_of_elapsed_time(store: EventStore):
    """A brand-new case (well within its interval) still gets flagged the
    instant the patient taps the button -- Phase 8.1's 'forces a
    reassessment prompt', not 'waits for the timer too'."""
    case = store.create_case(age_years=40)
    assert case.reassessment_overdue is False

    updated = store.report_patient_worsening(case.case_id, note="Feeling much worse now")
    assert updated.reassessment_overdue is True
    assert updated.reassessment_overdue_since is not None

    event_types = [e.event_type for e in store.get_timeline(case.case_id)]
    assert "PATIENT_SELF_REPORTED_WORSENING" in event_types
    assert "REASSESSMENT_DUE" in event_types


def test_does_not_touch_final_acuity(store: EventStore):
    """Phase 9.3: a self-report is not physiology. The case's acuity must
    be unchanged by the tap alone."""
    case = store.create_case(age_years=40)
    assess_case(case, store, PROFILE)  # the API layer does this at registration (CP7); mirrored here explicitly
    before = store.get_latest_risk_assessment(case.case_id)

    store.report_patient_worsening(case.case_id)

    after = store.get_latest_risk_assessment(case.case_id)
    assert after.assessment_id == before.assessment_id  # no new assessment was triggered
    assert after.final_acuity == before.final_acuity


def test_repeated_taps_each_log_an_event_but_reassessment_due_fires_once(store: EventStore):
    case = store.create_case(age_years=40)

    store.report_patient_worsening(case.case_id, note="first tap")
    store.report_patient_worsening(case.case_id, note="second tap, still waiting")

    timeline = store.get_timeline(case.case_id)
    worsening_events = [e for e in timeline if e.event_type == "PATIENT_SELF_REPORTED_WORSENING"]
    due_events = [e for e in timeline if e.event_type == "REASSESSMENT_DUE"]

    assert len(worsening_events) == 2  # every tap is recorded
    assert len(due_events) == 1  # but the overdue flag only fires once until cleared
    assert worsening_events[1].payload["note"] == "second tap, still waiting"


def test_mark_reassessed_clears_it_and_a_new_tap_can_reflag(store: EventStore):
    case = store.create_case(age_years=40)
    store.report_patient_worsening(case.case_id)
    assert store.get_case(case.case_id).reassessment_overdue is True

    store.mark_reassessed(case.case_id)
    assert store.get_case(case.case_id).reassessment_overdue is False

    store.report_patient_worsening(case.case_id, note="worse again")
    assert store.get_case(case.case_id).reassessment_overdue is True

    due_events = [e for e in store.get_timeline(case.case_id) if e.event_type == "REASSESSMENT_DUE"]
    assert len(due_events) == 2  # once per overdue window, and it reopened a new one


def test_report_on_missing_case_raises_not_found(store: EventStore):
    from app.store.event_store import NotFoundError
    import pytest

    with pytest.raises(NotFoundError):
        store.report_patient_worsening("does-not-exist")


def test_guardian_queue_reflects_the_flag_even_though_the_timer_has_not_tripped(store: EventStore):
    now = utcnow()
    case = store.create_case(age_years=40)  # ESI3ish (missing-data cap), 30 min interval
    assess_case(case, store, PROFILE, as_of=now)  # mirrors the API's registration-time initial assessment
    store.report_patient_worsening(case.case_id, occurred_at=now)  # only just registered -- timer alone wouldn't fire

    queue = build_queue(store, PROFILE, as_of=now + timedelta(minutes=1))
    entry = next(e for e in queue if e.case_id == case.case_id)
    assert entry.reassessment.is_due is True


def test_overdue_flag_survives_a_self_healing_backfill_assessment(store: EventStore):
    """Guards the fix in guardian_queue.py: a case with ZERO RiskAssessment
    history (unreachable via the current API, which always assesses at
    registration -- but not guaranteed for every future case-creation
    path) that is nonetheless already flagged overdue must not have that
    flag silently cleared by the queue's self-healing backfill assessment,
    which would otherwise treat its own catch-up scoring as the
    reassessment that resolves the very flag it hasn't actually addressed."""
    now = utcnow()
    case = store.create_case(age_years=40)  # deliberately NOT calling assess_case -- empty history
    store.report_patient_worsening(case.case_id, occurred_at=now)
    assert store.get_case(case.case_id).reassessment_overdue is True

    queue = build_queue(store, PROFILE, as_of=now)
    entry = next(e for e in queue if e.case_id == case.case_id)

    assert store.get_case(case.case_id).reassessment_overdue is True
    assert entry.reassessment.is_due is True


def test_api_endpoint(client, nurse_headers):
    case_id = client.post("/cases", json={"age_years": 40}, headers=nurse_headers).json()["case_id"]

    # Self-reported-worsening stays unauthenticated by design (Phase 8.1's
    # zero-friction patient/caregiver affordance).
    resp = client.post(f"/cases/{case_id}/self-reported-worsening", json={"note": "chest feels tight now"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["reassessment_overdue"] is True

    timeline = client.get(f"/cases/{case_id}/timeline", headers=nurse_headers).json()
    assert "PATIENT_SELF_REPORTED_WORSENING" in [e["event_type"] for e in timeline]

    queue = client.get("/queue", headers=nurse_headers).json()
    entry = next(e for e in queue if e["case_id"] == case_id)
    assert entry["reassessment"]["is_due"] is True


def test_api_endpoint_without_a_note(client, nurse_headers):
    case_id = client.post("/cases", json={"age_years": 40}, headers=nurse_headers).json()["case_id"]
    resp = client.post(f"/cases/{case_id}/self-reported-worsening", json={})
    assert resp.status_code == 200


def test_api_endpoint_on_missing_case_is_404(client):
    resp = client.post("/cases/does-not-exist/self-reported-worsening", json={})
    assert resp.status_code == 404
