"""
Tests for the Phase 9.5 printable queue snapshot (CP19): the "total
system failure" fallback -- plain text, built from the real queue.
"""
from app.config.hospital_profile import load_hospital_profile
from app.queue.guardian_queue import build_queue
from app.queue.printable import render_printable_snapshot
from app.scoring.risk_orchestrator import assess_case
from app.store.event_store import EventStore

PROFILE = load_hospital_profile("default")


def test_empty_queue_renders_without_error(store: EventStore):
    text = render_printable_snapshot([])
    assert "queue is empty" in text
    assert "PATIENTTRIAGE" in text


def test_snapshot_contains_acuity_arrival_and_reassessment_for_each_case(store: EventStore):
    case = store.create_case(age_years=40, display_name="Test Patient")
    assess_case(case, store, PROFILE)
    entries = build_queue(store, PROFILE)

    text = render_printable_snapshot(entries)
    assert "Test Patient" in text
    assert str(entries[0].final_acuity) in text
    assert "1 active patient" in text


def test_overdue_reassessment_is_visibly_flagged(store: EventStore):
    case = store.create_case(age_years=40)
    assess_case(case, store, PROFILE)
    store.flag_reassessment_overdue(case.case_id)
    entries = build_queue(store, PROFILE)

    text = render_printable_snapshot(entries)
    assert "OVERDUE" in text


def test_bypass_active_case_is_flagged_distinctly(store: EventStore):
    from app.models.enums import BypassSource

    case = store.create_case(age_years=40)
    assess_case(case, store, PROFILE)
    store.activate_emergency_bypass(case.case_id, source=BypassSource.HUMAN, reason="test")
    entries = build_queue(store, PROFILE)

    text = render_printable_snapshot(entries)
    assert "BYPASS-ACTIVE" in text


def test_snapshot_is_plain_text_no_markup(store: EventStore):
    case = store.create_case(age_years=40)
    assess_case(case, store, PROFILE)
    text = render_printable_snapshot(build_queue(store, PROFILE))
    assert "<" not in text and ">" not in text
    assert "{" not in text  # not accidentally JSON either


# ---------------------------------------------------------------------
# HTTP surface
# ---------------------------------------------------------------------
def test_printable_endpoint_returns_plain_text(client):
    client.post("/cases", json={"age_years": 40, "display_name": "Jane Doe"})
    resp = client.get("/queue/printable")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/plain")
    assert "Jane Doe" in resp.text
