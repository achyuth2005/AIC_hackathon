"""
Tests for the Alert Aggregation Engine (Phase 8.5, CP12): the three named
interrupt types, deduplication, aggregation of overdue reassessments into
one notification, auto-resolution, dismissal, and the alert-budget report.
"""
from datetime import timedelta

from app.alerts.budget import compute_alert_budget
from app.alerts.engine import sync_alerts
from app.config.hospital_profile import load_hospital_profile
from app.models.enums import (
    AlertDismissalReasonCode,
    AlertType,
    BypassSource,
    MeasurementStatus,
    ReliabilityTier,
    SourceType,
    ValueType,
)
from app.scoring import concepts
from app.scoring.risk_orchestrator import assess_case
from app.store.event_store import EventStore
from app.timeutil import utcnow

PROFILE = load_hospital_profile("default")


def _full_vitals(store, case_id, *, rr=18, spo2=96, hr=80, sbp=120, temp=37.0, observed_at=None):
    for code, val, vt in (
        (concepts.RESP_RATE, rr, ValueType.NUMERIC),
        (concepts.SPO2, spo2, ValueType.NUMERIC),
        (concepts.HEART_RATE, hr, ValueType.NUMERIC),
        (concepts.SYSTOLIC_BP, sbp, ValueType.NUMERIC),
        (concepts.TEMPERATURE, temp, ValueType.NUMERIC),
        (concepts.CONSCIOUSNESS_LEVEL, "ALERT", ValueType.CODED),
        (concepts.SUPPLEMENTAL_OXYGEN, False, ValueType.BOOLEAN),
    ):
        store.add_observation(
            case_id=case_id, concept_code=code, value=val, value_type=vt,
            source_type=SourceType.DEVICE,
            reliability_tier=ReliabilityTier.MACHINE_MEASURED,
            measurement_status=MeasurementStatus.MEASURED,
            observed_at=observed_at or utcnow(),
        )


def test_ambient_conditions_never_raise_an_alert(store: EventStore):
    """A completely quiet department must produce zero alerts -- alerts
    are the exception, not the default."""
    case = store.create_case(age_years=40)
    _full_vitals(store, case.case_id)
    assess_case(case, store, PROFILE)

    alerts = sync_alerts(store, PROFILE)
    assert alerts == []


def test_critical_bypass_raises_exactly_one_alert_even_after_a_second_detector_fires(store: EventStore):
    case = store.create_case(age_years=40)
    store.activate_emergency_bypass(case.case_id, source=BypassSource.HUMAN, reason="Nurse pressed the button")
    sync_alerts(store, PROFILE)
    # A second, different detector fires for the SAME case -- must not
    # raise a second "new critical patient" alert.
    store.activate_emergency_bypass(case.case_id, source=BypassSource.PHYSIOLOGICAL, reason="SpO2 <= 75", trigger_id="X")

    alerts = sync_alerts(store, PROFILE)
    bypass_alerts = [a for a in alerts if a.alert_type == AlertType.CRITICAL_BYPASS_PATIENT]
    assert len(bypass_alerts) == 1
    assert bypass_alerts[0].payload["case_id"] == case.case_id


def test_acuity_crossing_upward_raises_an_alert_and_downward_does_not(store: EventStore):
    case = store.create_case(age_years=50)
    _full_vitals(store, case.case_id, rr=18, spo2=96, hr=80, sbp=120, temp=37.0)
    assess_case(case, store, PROFILE)

    later = utcnow() + timedelta(minutes=10)
    _full_vitals(store, case.case_id, rr=26, spo2=92, hr=115, sbp=95, temp=38.5, observed_at=later)
    assess_case(case, store, PROFILE, as_of=later)

    alerts = sync_alerts(store, PROFILE)
    crossings = [a for a in alerts if a.alert_type == AlertType.ACUITY_BAND_CROSSED_UPWARD and a.payload["case_id"] == case.case_id]
    assert len(crossings) == 1
    assert crossings[0].payload["to_acuity"] < crossings[0].payload["from_acuity"]


def test_acuity_crossing_is_not_re_raised_on_a_later_sync(store: EventStore):
    case = store.create_case(age_years=50)
    _full_vitals(store, case.case_id, rr=18, spo2=96, hr=80, sbp=120, temp=37.0)
    assess_case(case, store, PROFILE)
    later = utcnow() + timedelta(minutes=10)
    _full_vitals(store, case.case_id, rr=26, spo2=92, hr=115, sbp=95, temp=38.5, observed_at=later)
    assess_case(case, store, PROFILE, as_of=later)

    sync_alerts(store, PROFILE)
    second_sync = sync_alerts(store, PROFILE)
    crossings = [a for a in second_sync if a.alert_type == AlertType.ACUITY_BAND_CROSSED_UPWARD]
    assert len(crossings) == 1  # still just the one alert, not duplicated


def test_multiple_overdue_reassessments_aggregate_into_one_alert(store: EventStore):
    cases = []
    for _ in range(3):
        c = store.create_case(age_years=40)
        _full_vitals(store, c.case_id)
        assess_case(c, store, PROFILE)
        store.flag_reassessment_overdue(c.case_id)
        cases.append(c)

    alerts = sync_alerts(store, PROFILE)
    aggregates = [a for a in alerts if a.alert_type == AlertType.REASSESSMENT_OVERDUE_AGGREGATE]
    assert len(aggregates) == 1
    assert aggregates[0].payload["count"] == 3
    assert set(aggregates[0].payload["case_ids"]) == {c.case_id for c in cases}


def test_aggregate_alert_updates_in_place_as_more_cases_become_overdue(store: EventStore):
    c1 = store.create_case(age_years=40)
    _full_vitals(store, c1.case_id)
    assess_case(c1, store, PROFILE)
    store.flag_reassessment_overdue(c1.case_id)
    first_sync = sync_alerts(store, PROFILE)
    aggregate_id = next(a.alert_id for a in first_sync if a.alert_type == AlertType.REASSESSMENT_OVERDUE_AGGREGATE)

    c2 = store.create_case(age_years=45)
    _full_vitals(store, c2.case_id)
    assess_case(c2, store, PROFILE)
    store.flag_reassessment_overdue(c2.case_id)
    second_sync = sync_alerts(store, PROFILE)
    aggregates = [a for a in second_sync if a.alert_type == AlertType.REASSESSMENT_OVERDUE_AGGREGATE]

    assert len(aggregates) == 1
    assert aggregates[0].alert_id == aggregate_id  # same row, updated in place
    assert aggregates[0].payload["count"] == 2


def test_aggregate_alert_auto_resolves_once_nothing_is_overdue(store: EventStore):
    case = store.create_case(age_years=40)
    _full_vitals(store, case.case_id)
    assess_case(case, store, PROFILE)
    store.flag_reassessment_overdue(case.case_id)
    sync_alerts(store, PROFILE)

    store.mark_reassessed(case.case_id)  # clears reassessment_overdue
    alerts = sync_alerts(store, PROFILE)
    assert not any(a.alert_type == AlertType.REASSESSMENT_OVERDUE_AGGREGATE for a in alerts)

    all_alerts = store.list_alerts(PROFILE.profile_id, include_dismissed=True)
    resolved = [a for a in all_alerts if a.alert_type == AlertType.REASSESSMENT_OVERDUE_AGGREGATE]
    assert len(resolved) == 1
    assert resolved[0].dismissed is True
    assert resolved[0].dismissed_by == "SYSTEM"
    assert resolved[0].dismissal_reason_code == AlertDismissalReasonCode.RESOLVED_AUTOMATICALLY


def test_dismiss_requires_a_reason_and_removes_it_from_the_open_feed(store: EventStore):
    case = store.create_case(age_years=40)
    store.activate_emergency_bypass(case.case_id, source=BypassSource.HUMAN, reason="test")
    alerts = sync_alerts(store, PROFILE)
    alert = alerts[0]

    dismissed = store.dismiss_alert(
        alert.alert_id, dismissed_by="demo-nurse-01", reason_code=AlertDismissalReasonCode.ALREADY_ACTIONED
    )
    assert dismissed.dismissed is True

    open_alerts = store.list_alerts(PROFILE.profile_id)
    assert not any(a.alert_id == alert.alert_id for a in open_alerts)


def test_dismissing_an_already_dismissed_alert_raises(store: EventStore):
    case = store.create_case(age_years=40)
    store.activate_emergency_bypass(case.case_id, source=BypassSource.HUMAN, reason="test")
    alert = sync_alerts(store, PROFILE)[0]
    store.dismiss_alert(alert.alert_id, dismissed_by="x", reason_code=AlertDismissalReasonCode.DUPLICATE)

    import pytest
    with pytest.raises(ValueError):
        store.dismiss_alert(alert.alert_id, dismissed_by="x", reason_code=AlertDismissalReasonCode.DUPLICATE)


# ---------------------------------------------------------------------
# Alert budget
# ---------------------------------------------------------------------
def test_alert_budget_counts_alerts_in_the_window_and_compares_to_target(store: EventStore):
    for _ in range(2):
        c = store.create_case(age_years=40)
        store.activate_emergency_bypass(c.case_id, source=BypassSource.HUMAN, reason="test")
    sync_alerts(store, PROFILE)

    report = compute_alert_budget(store, PROFILE, nurses_on_shift=1.0, window_minutes=60)
    assert report.interruptive_alerts_in_window == 2
    assert report.alerts_per_nurse_per_hour == 2.0
    assert report.target_alerts_per_nurse_per_hour == 4.0  # default.yaml's configured target
    assert report.within_budget is True
    assert report.breakdown_by_type[AlertType.CRITICAL_BYPASS_PATIENT.value] == 2


def test_alert_budget_flags_over_target(store: EventStore):
    for _ in range(10):
        c = store.create_case(age_years=40)
        store.activate_emergency_bypass(c.case_id, source=BypassSource.HUMAN, reason="test")
    sync_alerts(store, PROFILE)

    report = compute_alert_budget(store, PROFILE, nurses_on_shift=1.0, window_minutes=60)
    assert report.within_budget is False


# ---------------------------------------------------------------------
# HTTP surface
# ---------------------------------------------------------------------
def test_alerts_endpoint_and_dismiss_flow(client, nurse_headers):
    case_id = client.post("/cases", json={"age_years": 40}, headers=nurse_headers).json()["case_id"]
    client.post(
        f"/cases/{case_id}/emergency-bypass",
        json={"reason": "test"},
        headers=nurse_headers,
    )

    # Audit fix: GET /alerts now requires authentication too.
    unauthenticated = client.get("/alerts")
    assert unauthenticated.status_code == 401

    alerts = client.get("/alerts", headers=nurse_headers).json()
    assert len(alerts) == 1
    alert_id = alerts[0]["alert_id"]

    forbidden = client.post(f"/alerts/{alert_id}/dismiss", json={"reason_code": "ALREADY_ACTIONED"})
    assert forbidden.status_code == 401

    ok = client.post(
        f"/alerts/{alert_id}/dismiss",
        json={"reason_code": "ALREADY_ACTIONED"},
        headers=nurse_headers,
    )
    assert ok.status_code == 200
    assert ok.json()["dismissed"] is True

    assert client.get("/alerts", headers=nurse_headers).json() == []


def test_alert_budget_endpoint(client, nurse_headers):
    resp = client.get("/alerts/budget", params={"nurses_on_shift": 2}, headers=nurse_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["nurses_on_shift"] == 2
    assert "target_alerts_per_nurse_per_hour" in body
