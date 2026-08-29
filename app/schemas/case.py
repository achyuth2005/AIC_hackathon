from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from app.models.enums import ArrivalMode, BypassSource, CaseStatus, IdentityLinkStatus, PatientStage
from app.ops.wait_time import WaitTimeEstimate
from app.schemas.observation import ObservationResponse
from app.schemas.risk_assessment import RiskAssessmentResponse


class CaseCreateRequest(BaseModel):
    hospital_profile_id: str = "default"
    mrn: Optional[str] = None
    display_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    age_years: Optional[int] = None
    sex: Optional[str] = None
    arrival_mode: ArrivalMode = ArrivalMode.WALK_IN
    # Phase 7.2 (CP18): only meaningful when arrival_mode=AMBULANCE. A
    # simulated total transport duration -- see app/ambulance/eta.py's
    # module docstring for why this is simulated rather than derived from
    # a real GPS/routing feed. Ignored for a WALK_IN case.
    estimated_transport_minutes: Optional[float] = None


class ArrivalRequest(BaseModel):
    occurred_at: Optional[datetime] = None


class EmergencyBypassRequest(BaseModel):
    """Phase 3.5 detector #1: the human affordance. No vitals, no
    confirmation step, no reason required -- "a persistent, single-tap
    Immediate Escalation control ... zero latency". `reason` is optional
    free text for the audit trail, not a gate on the action.

    CP9.5 closes a previously-flagged gap here: who triggered this used to
    be accepted as `triggered_by_role`/`triggered_by_id` straight out of
    this body (nothing stopped a client from claiming any identity it
    liked). That identity now comes from the caller's authenticated bearer
    token instead (app/auth/deps.py's `require_role`) -- this schema no
    longer carries it at all."""
    reason: Optional[str] = None


class IdentityMatchProposeRequest(BaseModel):
    """Phase 7.1 identity matching, propose half (CP11). The candidate is
    supplied by the caller (a real deployment's upstream matching search),
    not looked up here -- see EventStore.propose_identity_match's
    docstring for why no search exists in this prototype."""
    candidate_mrn: str
    candidate_display_name: Optional[str] = None
    confidence: Optional[float] = None


class IdentityMatchConfirmRequest(BaseModel):
    """Phase 7.1 identity matching, confirm half (CP11): a human confirms
    a proposed match. `confirmed_by` is redundant with the authenticated
    caller (kept for the audit payload's own readability); mrn/display_name
    are what actually gets attached to the case."""
    mrn: str
    display_name: Optional[str] = None


class PatientWorseningRequest(BaseModel):
    """Phase 8.1: the 'I feel worse' button. One tap; `note` is optional
    free text, never required -- the whole point is that this needs no
    detail to be worth acting on."""
    note: Optional[str] = None


class CaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    case_id: str
    hospital_profile_id: str
    mrn: Optional[str]
    display_name: Optional[str]
    date_of_birth: Optional[date]
    age_years: Optional[int]
    sex: Optional[str]
    arrival_mode: ArrivalMode
    status: CaseStatus
    identity_link_status: IdentityLinkStatus
    created_at: datetime
    arrived_at: Optional[datetime]

    emergency_bypass_active: bool
    emergency_bypass_first_activated_at: Optional[datetime]
    emergency_bypass_last_activated_at: Optional[datetime]
    emergency_bypass_last_reason: Optional[str]
    emergency_bypass_last_source: Optional[BypassSource]
    emergency_bypass_last_trigger_id: Optional[str]

    last_reassessed_at: Optional[datetime]
    reassessment_overdue: bool
    reassessment_overdue_since: Optional[datetime]


class CaseDetailResponse(CaseResponse):
    """CaseResponse plus its current (non-superseded) observations and the
    most recent RiskAssessment -- one call a nurse/doctor view can use to
    render a case (Phase 8.2/8.3)."""
    current_observations: List[ObservationResponse]
    latest_risk_assessment: Optional[RiskAssessmentResponse] = None
    # Phase 6.4: only populated when there's an acuity to estimate against
    # (an ACTIVE case with at least one RiskAssessment) -- absent, not a
    # fabricated zero, for a case still pre-arrival or awaiting its first
    # assessment.
    wait_time_estimate: Optional[WaitTimeEstimate] = None


class PatientCaseView(BaseModel):
    """Phase 8.1 (CP15): the ENTIRE patient-facing surface. No acuity, no
    confidence, no risk assessment of any kind -- see
    app/dashboard/patient_view.py's module docstring for why that is
    enforced by this schema's shape, not merely by convention."""
    case_id: str
    display_name: Optional[str]
    stage: PatientStage
    next_step_message: str
    wait_time_estimate: Optional[WaitTimeEstimate] = None
