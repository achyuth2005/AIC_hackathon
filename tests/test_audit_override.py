"""
Tests for the Audit & Override Service (Phase 4.3, 9.6, 9.7 -- CP10):
asymmetric override friction, the HumanDecision audit trail,
DecidingLayer.OVERRIDE actually taking effect, and the monitoring report.
"""
import pytest

from app.config.hospital_profile import load_hospital_profile
from app.models.enums import DeEscalationReasonCode, DecidingLayer, HumanDecisionAction
from app.scoring.risk_orchestrator import assess_case
from app.store.event_store import EventStore

PROFILE = load_hospital_profile("default")


def _case_with_assessment(store, age_years=40):
    case = store.create_case(age_years=age_years)
    assess_case(case, store, PROFILE)
    return case


# ---------------------------------------------------------------------
# EventStore.record_human_override -- the asymmetric friction itself
# ---------------------------------------------------------------------
def test_escalate_requires_no_reason_and_applies_instantly(store: EventStore):
    case = _case_with_assessment(store)
    before = store.get_latest_risk_assessment(case.case_id)

    decision = store.record_human_override(
        case.case_id, clinician_id="demo-nurse-01", role="NURSE", action=HumanDecisionAction.ESCALATE
    )
    assert decision.resulting_acuity == max(1, before.final_acuity - 1)
    assert decision.reason_code is None
    assert decision.flagged_for_review is False

    after = store.get_latest_risk_assessment(case.case_id)
    assert after.final_acuity == decision.resulting_acuity
    assert after.deciding_layer == DecidingLayer.OVERRIDE


def test_de_escalate_without_reason_code_is_rejected(store: EventStore):
    case = _case_with_assessment(store)
    before = store.get_latest_risk_assessment(case.case_id)

    with pytest.raises(ValueError):
        store.record_human_override(
            case.case_id,
            clinician_id="demo-doctor-01",
            role="DOCTOR",
            action=HumanDecisionAction.DE_ESCALATE,
            target_acuity=before.final_acuity + 1,
            # reason_code omitted -- must be rejected
        )

    # Nothing was persisted or applied by the rejected attempt.
    assert store.get_latest_risk_assessment(case.case_id).assessment_id == before.assessment_id
    assert store.get_decision_history(case.case_id) == []


def test_de_escalate_with_reason_code_is_flagged_for_review_and_applies(store: EventStore):
    case = _case_with_assessment(store)
    before = store.get_latest_risk_assessment(case.case_id)

    decision = store.record_human_override(
        case.case_id,
        clinician_id="demo-doctor-01",
        role="DOCTOR",
        action=HumanDecisionAction.DE_ESCALATE,
        target_acuity=before.final_acuity + 1,
        reason_code=DeEscalationReasonCode.VITALS_IMPROVED_SINCE_ASSESSMENT,
    )
    assert decision.flagged_for_review is True
    assert decision.resulting_acuity == before.final_acuity + 1

    after = store.get_latest_risk_assessment(case.case_id)
    assert after.final_acuity == before.final_acuity + 1
    assert after.deciding_layer == DecidingLayer.OVERRIDE

    flagged = store.list_flagged_for_review()
    assert any(d.decision_id == decision.decision_id for d in flagged)


def test_escalate_in_the_wrong_direction_is_rejected(store: EventStore):
    case = _case_with_assessment(store)
    before = store.get_latest_risk_assessment(case.case_id)

    with pytest.raises(ValueError):
        store.record_human_override(
            case.case_id,
            clinician_id="demo-nurse-01",
            role="NURSE",
            action=HumanDecisionAction.ESCALATE,
            target_acuity=before.final_acuity + 1,  # less urgent -- wrong door
        )


def test_accept_does_not_change_acuity_but_resets_reassessment_clock(store: EventStore):
    case = _case_with_assessment(store)
    before = store.get_latest_risk_assessment(case.case_id)
    store.flag_reassessment_overdue(case.case_id)

    decision = store.record_human_override(
        case.case_id, clinician_id="demo-nurse-01", role="NURSE", action=HumanDecisionAction.ACCEPT
    )
    assert decision.resulting_acuity == before.final_acuity
    after = store.get_latest_risk_assessment(case.case_id)
    assert after.assessment_id == before.assessment_id  # no new RiskAssessment created

    refreshed_case = store.get_case(case.case_id)
    assert refreshed_case.reassessment_overdue is False  # accept still counts as "looked at"


def test_override_without_any_prior_assessment_is_rejected(store: EventStore):
    case = store.create_case(age_years=40)  # no assess_case() call
    with pytest.raises(ValueError):
        store.record_human_override(
            case.case_id, clinician_id="demo-nurse-01", role="NURSE", action=HumanDecisionAction.ESCALATE
        )


def test_first_activated_and_linked_assessment_id_are_recorded(store: EventStore):
    case = _case_with_assessment(store)
    before = store.get_latest_risk_assessment(case.case_id)
    decision = store.record_human_override(
        case.case_id, clinician_id="demo-nurse-01", role="NURSE", action=HumanDecisionAction.ESCALATE
    )
    assert decision.linked_assessment_id == before.assessment_id
    assert decision.system_recommendation == before.final_acuity


# ---------------------------------------------------------------------
# HTTP surface
# ---------------------------------------------------------------------
def _token(client, role):
    return client.post("/auth/login", json={"role": role}).json()["access_token"]


def test_override_endpoint_requires_authentication(client):
    case_id = client.post("/cases", json={"age_years": 40}).json()["case_id"]
    client.get("/queue")  # backfill an initial assessment
    resp = client.post(f"/cases/{case_id}/override", json={"action": "ESCALATE"})
    assert resp.status_code == 401


def test_override_endpoint_escalate_one_tap(client):
    case_id = client.post("/cases", json={"age_years": 40}).json()["case_id"]
    client.get("/queue")
    token = _token(client, "NURSE")

    resp = client.post(
        f"/cases/{case_id}/override",
        json={"action": "ESCALATE"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["clinician_action"] == "ESCALATE"
    assert body["flagged_for_review"] is False
    assert body["resulting_acuity"] < body["system_recommendation"]


def test_override_endpoint_de_escalate_without_reason_is_400(client):
    case_id = client.post("/cases", json={"age_years": 40}).json()["case_id"]
    detail = client.get(f"/cases/{case_id}").json()
    client.get("/queue")
    token = _token(client, "DOCTOR")

    resp = client.post(
        f"/cases/{case_id}/override",
        json={"action": "DE_ESCALATE", "target_acuity": 5},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


def test_override_endpoint_de_escalate_with_reason_is_flagged(client):
    case_id = client.post("/cases", json={"age_years": 40}).json()["case_id"]
    client.get("/queue")
    doctor_token = _token(client, "DOCTOR")
    admin_token = _token(client, "ADMIN")

    current = client.get(f"/cases/{case_id}").json()["latest_risk_assessment"]["final_acuity"]
    resp = client.post(
        f"/cases/{case_id}/override",
        json={
            "action": "DE_ESCALATE",
            "target_acuity": current + 1,
            "reason_code": "SYMPTOM_RESOLVED",
        },
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["flagged_for_review"] is True

    flagged = client.get(
        "/overrides/flagged-for-review", headers={"Authorization": f"Bearer {admin_token}"}
    ).json()
    assert any(d["case_id"] == case_id for d in flagged)

    decisions = client.get(f"/cases/{case_id}/decisions").json()
    assert len(decisions) == 1


def test_monitoring_endpoint_requires_admin(client):
    case_id = client.post("/cases", json={"age_years": 40}).json()["case_id"]
    client.get("/queue")
    nurse_token = _token(client, "NURSE")
    admin_token = _token(client, "ADMIN")

    forbidden = client.get("/overrides/monitoring", headers={"Authorization": f"Bearer {nurse_token}"})
    assert forbidden.status_code == 403

    ok = client.get("/overrides/monitoring", headers={"Authorization": f"Bearer {admin_token}"})
    assert ok.status_code == 200
    body = ok.json()
    assert body["total_cases"] >= 1
    assert "caveat" in body
