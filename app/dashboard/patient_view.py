"""
Phase 8.1 patient view (CP15): "reduce anxiety and reduce reception load.
Not to triage." Hierarchy: where you are in the process -> estimated wait
window -> what happens next -> 'I feel worse' button (built separately at
CP8; POST /cases/{id}/self-reported-worsening).

**Never show: risk score, acuity level, probability, differential
considerations, any clinical interpretation.** This is enforced at the API
boundary, not left to frontend discipline: `PatientCaseView` (see
app/schemas/case.py) has no field that could carry an acuity number or a
confidence band, so there is nothing to accidentally leak even if a future
edit to this module tried to add one carelessly -- a reviewer would have
to deliberately widen the response schema to reintroduce the failure mode
Phase 8.1 calls "catastrophic".
"""
from __future__ import annotations

from typing import Optional

from app.config.hospital_profile import HospitalProfile
from app.models.case import Case
from app.models.enums import CaseStatus, PatientStage
from app.ops.wait_time import WaitTimeEstimate, estimate_wait_time
from app.schemas.case import PatientCaseView
from app.store.event_store import EventStore

_NEXT_STEP_MESSAGES = {
    PatientStage.PRE_ARRIVAL: "You are on your way to the hospital. The team has been told you're coming and is getting ready.",
    PatientStage.WAITING: "You're checked in and waiting to be seen. A nurse will call you when it's your turn.",
    PatientStage.IN_TREATMENT: "You're currently being seen by the care team.",
    PatientStage.DISPOSED: "Your visit is complete.",
}


def _stage_for(case: Case, store: EventStore) -> PatientStage:
    if case.status == CaseStatus.PRE_ARRIVAL:
        return PatientStage.PRE_ARRIVAL
    if case.status == CaseStatus.DISPOSED:
        return PatientStage.DISPOSED
    in_service = bool(store.get_assigned_resources_for_case(case.case_id))
    return PatientStage.IN_TREATMENT if in_service else PatientStage.WAITING


def build_patient_view(case: Case, store: EventStore, profile: HospitalProfile):
    """Returns the fields for PatientCaseView. Only fetches
    `final_acuity` internally to compute a wait-time RANGE (which itself
    carries no acuity number) -- it is never placed on the response."""
    stage = _stage_for(case, store)

    wait_time_estimate: Optional[WaitTimeEstimate] = None
    if stage == PatientStage.WAITING:
        latest = store.get_latest_risk_assessment(case.case_id)
        if latest is not None:
            wait_time_estimate = estimate_wait_time(store, profile, case.case_id, latest.final_acuity)

    return PatientCaseView(
        case_id=case.case_id,
        display_name=case.display_name,
        stage=stage,
        next_step_message=_NEXT_STEP_MESSAGES[stage],
        wait_time_estimate=wait_time_estimate,
    )
