"""
Case endpoints (Phase 4.4, 7.1). Thin HTTP wrapper over EventStore -- no
business logic lives here; that keeps every engine added in later
checkpoints usable both via HTTP and directly in tests/CLI tooling.
"""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status as http_status

from app.api.deps import get_store
from app.auth.deps import get_current_user, require_role
from app.auth.models import AuthenticatedUser
from app.auth.roles import Role
from app.bypass.engine import evaluate_and_activate as evaluate_emergency_bypass
from app.config.hospital_profile import load_hospital_profile
from app.dashboard.doctor_view import build_doctor_view
from app.dashboard.patient_view import build_patient_view
from app.llm.explanation import ExplanationResult, generate_explanation
from app.llm.intake import IntakeOutcome, extract_intake_fields
from app.models.enums import ArrivalMode, BypassSource, CaseStatus
from app.ops.wait_time import estimate_wait_time
from app.schemas.case import (
    IdentityMatchConfirmRequest,
    IdentityMatchProposeRequest,
    ArrivalRequest,
    CaseCreateRequest,
    CaseDetailResponse,
    CaseResponse,
    EmergencyBypassRequest,
    PatientCaseView,
    PatientWorseningRequest,
)
from app.ambulance.eta import ETARange, compute_eta_range
from app.ambulance.prealert import PreAlertView, build_pre_alert
from app.schemas.ambulance import TransportDelayRequest
from app.schemas.data_conflict import DataConflictResponse
from app.schemas.diagnostic_test import DiagnosticTestResponse, OrderTestRequest
from app.schemas.doctor_view import DoctorCaseView
from app.schemas.event import EventResponse
from app.schemas.human_decision import HumanDecisionResponse, OverrideRequest
from app.schemas.llm import IntakeRequest
from app.schemas.observation import ObservationCreateRequest, ObservationResponse
from app.schemas.resource import AssignResourceRequest, CapacityConflictResponse, ResourceResponse
from app.schemas.risk_assessment import RiskAssessmentResponse
from app.scoring.risk_orchestrator import assess_case
from app.store.event_store import CapacityConflictError, EventStore, NotFoundError

router = APIRouter(prefix="/cases", tags=["cases"])


@router.post("", response_model=CaseResponse, status_code=http_status.HTTP_201_CREATED)
def create_case(body: CaseCreateRequest, store: EventStore = Depends(get_store)) -> CaseResponse:
    case = store.create_case(
        hospital_profile_id=body.hospital_profile_id,
        mrn=body.mrn,
        display_name=body.display_name,
        date_of_birth=body.date_of_birth,
        age_years=body.age_years,
        sex=body.sex,
        arrival_mode=body.arrival_mode,
    )

    # A walk-in is ACTIVE (in the department, in the queue) from the
    # moment of registration -- give it an initial RiskAssessment
    # immediately (Phase 9.2 abstention if age/vitals are unknown yet)
    # rather than leaving it invisible to the Guardian Queue until the
    # first observation arrives. An ambulance case is still PRE_ARRIVAL
    # and is assessed for the first time on arrival instead (below).
    if case.status == CaseStatus.ACTIVE:
        profile = load_hospital_profile(case.hospital_profile_id)
        assess_case(case, store, profile)
    elif case.arrival_mode == ArrivalMode.AMBULANCE and body.estimated_transport_minutes is not None:
        # Phase 7.2 (CP18): starts the simulated ETA clock immediately so
        # a pre-alert can show a narrowing range from the moment dispatch
        # creates the case, not only once someone happens to ask.
        store.start_ambulance_transport(case.case_id, estimated_total_minutes=body.estimated_transport_minutes)

    return CaseResponse.model_validate(case)


@router.get("", response_model=List[CaseResponse])
def list_cases(
    status: Optional[CaseStatus] = Query(default=None),
    store: EventStore = Depends(get_store),
) -> List[CaseResponse]:
    cases = store.list_cases(status=status)
    return [CaseResponse.model_validate(c) for c in cases]


@router.get("/{case_id}", response_model=CaseDetailResponse)
def get_case(case_id: str, store: EventStore = Depends(get_store)) -> CaseDetailResponse:
    case = store.get_case(case_id)
    if case is None:
        raise NotFoundError(f"No case {case_id}")
    current_obs = store.get_current_observations(case_id)
    latest_assessment = store.get_latest_risk_assessment(case_id)

    wait_time_estimate = None
    if latest_assessment is not None and case.status == CaseStatus.ACTIVE:
        profile = load_hospital_profile(case.hospital_profile_id)
        wait_time_estimate = estimate_wait_time(store, profile, case_id, latest_assessment.final_acuity)

    return CaseDetailResponse(
        **CaseResponse.model_validate(case).model_dump(),
        current_observations=[ObservationResponse.model_validate(o) for o in current_obs],
        latest_risk_assessment=(
            RiskAssessmentResponse.model_validate(latest_assessment) if latest_assessment else None
        ),
        wait_time_estimate=wait_time_estimate,
    )


@router.get("/{case_id}/patient-view", response_model=PatientCaseView)
def get_patient_view(case_id: str, store: EventStore = Depends(get_store)) -> PatientCaseView:
    """Phase 8.1: the entire patient-facing surface. Unauthenticated by
    design, same as the self-reported-worsening endpoint -- Phase 8.1
    requires kiosk mode / caregiver mode to work without a login. Never
    carries acuity, confidence, or any clinical interpretation; see
    app/dashboard/patient_view.py's module docstring."""
    case = store.get_case(case_id)
    if case is None:
        raise NotFoundError(f"No case {case_id}")
    profile = load_hospital_profile(case.hospital_profile_id)
    return build_patient_view(case, store, profile)


@router.get("/{case_id}/doctor-view", response_model=DoctorCaseView)
def get_doctor_view(
    case_id: str,
    store: EventStore = Depends(get_store),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> DoctorCaseView:
    """Phase 8.3. Authenticated (unlike most other read endpoints in this
    API) because the response itself is identity-relative -- "what changed
    since YOU last looked" needs to know who's asking, not just what the
    case looks like; a query-param reviewer_id would let a caller claim
    any identity's review history."""
    case = store.get_case(case_id)
    if case is None:
        raise NotFoundError(f"No case {case_id}")
    profile = load_hospital_profile(case.hospital_profile_id)
    return build_doctor_view(case, store, profile, current_user.user_id)


@router.post("/{case_id}/mark-reviewed", response_model=CaseResponse)
def mark_case_reviewed(
    case_id: str,
    store: EventStore = Depends(get_store),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> CaseResponse:
    """Advances this doctor's own review cursor (see CaseReview's module
    docstring) so their next GET .../doctor-view starts its
    'changed since' window from now."""
    case = store.get_case(case_id)
    if case is None:
        raise NotFoundError(f"No case {case_id}")
    store.mark_case_reviewed(case_id, current_user.user_id)
    return CaseResponse.model_validate(store.get_case(case_id))


@router.post("/{case_id}/intake", response_model=IntakeOutcome)
def run_intake_extraction(
    case_id: str, body: IntakeRequest, store: EventStore = Depends(get_store)
) -> IntakeOutcome:
    """Phase 3.2 LLM Intake Engine (CP17): schema-constrained entity
    extraction from free text, deterministically validated (controlled
    vocabulary + range checks) before anything is persisted. Never
    triggers scoring itself -- extracted facts flow through the ordinary,
    unchanged deterministic pipeline on the next read/reassessment, same
    as any other observation."""
    case = store.get_case(case_id)
    if case is None:
        raise NotFoundError(f"No case {case_id}")
    profile = load_hospital_profile(case.hospital_profile_id)
    return extract_intake_fields(case, store, profile, body.text)


@router.get("/{case_id}/explanation", response_model=ExplanationResult)
def get_case_explanation(case_id: str, store: EventStore = Depends(get_store)) -> ExplanationResult:
    """Phase 3.2/3.6 LLM Explanation Engine (CP17): narrates the EXISTING
    RiskAssessment's structured facts; never computes or changes acuity.
    Deterministically grounding-checked -- an ungrounded LLM response is
    discarded and replaced with a deterministic, rule-component-breakdown
    explanation, the same fallback used when the LLM is disabled or
    unavailable (Phase 9.5)."""
    case = store.get_case(case_id)
    if case is None:
        raise NotFoundError(f"No case {case_id}")
    profile = load_hospital_profile(case.hospital_profile_id)
    return generate_explanation(case, store, profile)


@router.get("/{case_id}/eta", response_model=ETARange)
def get_ambulance_eta(case_id: str, store: EventStore = Depends(get_store)) -> ETARange:
    """Phase 7.2: the simulated, narrowing ETA range. 404s if this case
    has no ambulance transport recorded (a WALK_IN case, or an ambulance
    case created without estimated_transport_minutes)."""
    case = store.get_case(case_id)
    if case is None:
        raise NotFoundError(f"No case {case_id}")
    transport = store.get_ambulance_transport(case_id)
    if transport is None:
        raise NotFoundError(f"No ambulance transport recorded for case {case_id}")
    return compute_eta_range(transport)


@router.post("/{case_id}/ambulance/delay", response_model=ETARange)
def delay_ambulance_transport(
    case_id: str, body: TransportDelayRequest, store: EventStore = Depends(get_store)
) -> ETARange:
    """Phase 7.2: 'a paramedic-controlled delayed flag.' See
    TransportDelayRequest's docstring for why this is unauthenticated."""
    case = store.get_case(case_id)
    if case is None:
        raise NotFoundError(f"No case {case_id}")
    transport = store.mark_transport_delayed(
        case_id, additional_minutes=body.additional_minutes, reason=body.reason
    )
    return compute_eta_range(transport)


@router.get("/{case_id}/pre-alert", response_model=PreAlertView)
def get_ambulance_pre_alert(case_id: str, store: EventStore = Depends(get_store)) -> PreAlertView:
    """Phase 7.3: the scannable-in-three-seconds pre-alert. Works for any
    case (not just PRE_ARRIVAL) -- a pre-alert is most useful before
    arrival, but nothing here breaks once PATIENT_ARRIVED has fired."""
    case = store.get_case(case_id)
    if case is None:
        raise NotFoundError(f"No case {case_id}")
    profile = load_hospital_profile(case.hospital_profile_id)
    return build_pre_alert(case, store, profile)


@router.get("/{case_id}/risk-assessments", response_model=List[RiskAssessmentResponse])
def list_risk_assessments(case_id: str, store: EventStore = Depends(get_store)) -> List[RiskAssessmentResponse]:
    case = store.get_case(case_id)
    if case is None:
        raise NotFoundError(f"No case {case_id}")
    history = store.get_risk_assessment_history(case_id)
    return [RiskAssessmentResponse.model_validate(a) for a in history]


@router.post("/{case_id}/override", response_model=HumanDecisionResponse)
def override_risk_assessment(
    case_id: str,
    body: OverrideRequest,
    store: EventStore = Depends(get_store),
    current_user: AuthenticatedUser = Depends(require_role(Role.NURSE, Role.DOCTOR, Role.ADMIN)),
) -> HumanDecisionResponse:
    """Phase 9.6's asymmetric override: ESCALATE/ACCEPT are applied
    instantly with no reason required; DE_ESCALATE requires
    `target_acuity` + a structured `reason_code` and is flagged for
    retrospective review (see GET /overrides/flagged-for-review). Raises
    404 if the case doesn't exist or has no assessment to override yet,
    400 if the requested direction doesn't match the action or a required
    field is missing (EventStore.record_human_override's own checks,
    mapped by the generic ValueError -> 400 handler in app/main.py)."""
    case = store.get_case(case_id)
    if case is None:
        raise NotFoundError(f"No case {case_id}")

    decision = store.record_human_override(
        case_id,
        clinician_id=current_user.user_id,
        role=current_user.role.value,
        action=body.action,
        target_acuity=body.target_acuity,
        reason_code=body.reason_code,
        free_text_reason=body.free_text_reason,
    )
    return HumanDecisionResponse.model_validate(decision)


@router.get("/{case_id}/decisions", response_model=List[HumanDecisionResponse])
def list_case_decisions(case_id: str, store: EventStore = Depends(get_store)) -> List[HumanDecisionResponse]:
    case = store.get_case(case_id)
    if case is None:
        raise NotFoundError(f"No case {case_id}")
    return [HumanDecisionResponse.model_validate(d) for d in store.get_decision_history(case_id)]


@router.get("/{case_id}/conflicts", response_model=List[DataConflictResponse])
def list_case_conflicts(
    case_id: str,
    include_resolved: bool = Query(default=False),
    store: EventStore = Depends(get_store),
) -> List[DataConflictResponse]:
    """Phase 9.3: 'flag both values with their sources and times ... both
    appear on screen.' This is that display surface -- open conflicts by
    default; pass include_resolved=true to also see resolved history."""
    case = store.get_case(case_id)
    if case is None:
        raise NotFoundError(f"No case {case_id}")
    return [
        DataConflictResponse.model_validate(c)
        for c in store.list_data_conflicts(case_id, include_resolved=include_resolved)
    ]


@router.post("/{case_id}/arrival", response_model=CaseResponse)
def record_arrival(
    case_id: str, body: ArrivalRequest, store: EventStore = Depends(get_store)
) -> CaseResponse:
    case = store.record_arrival(case_id, occurred_at=body.occurred_at)

    # Now ACTIVE for the first time -- same reasoning as create_case above.
    profile = load_hospital_profile(case.hospital_profile_id)
    assess_case(case, store, profile)

    return CaseResponse.model_validate(case)


@router.post("/{case_id}/reassessment", response_model=CaseResponse)
def mark_reassessed(case_id: str, store: EventStore = Depends(get_store)) -> CaseResponse:
    """Phase 8.2 nurse one-tap action: 'mark reassessed'. Resets the Phase
    5.3 reassessment clock even without a new observation -- pair this
    with recording fresh vitals in the UI when there are any, but the
    action itself doesn't require one (a nurse can look at a patient and
    confirm nothing has changed)."""
    case = store.mark_reassessed(case_id)
    return CaseResponse.model_validate(case)


@router.post("/{case_id}/self-reported-worsening", response_model=CaseResponse)
def report_patient_worsening(
    case_id: str, body: PatientWorseningRequest, store: EventStore = Depends(get_store)
) -> CaseResponse:
    """Phase 8.1: the patient/caregiver-facing 'I feel worse' button --
    'more valuable than the entire chat interface and takes an afternoon
    to build.' One tap, forces this case onto the nurse's overdue list
    immediately regardless of the elapsed-time clock. Does not change
    final_acuity by itself (Phase 9.3: a self-report is not physiology) --
    only the nurse's subsequent reassessment, if it finds something, does."""
    case = store.report_patient_worsening(case_id, note=body.note)
    return CaseResponse.model_validate(case)


@router.get("/{case_id}/timeline", response_model=List[EventResponse])
def get_timeline(case_id: str, store: EventStore = Depends(get_store)) -> List[EventResponse]:
    case = store.get_case(case_id)
    if case is None:
        raise NotFoundError(f"No case {case_id}")
    return [EventResponse.model_validate(e) for e in store.get_timeline(case_id)]


@router.get("/{case_id}/observations", response_model=List[ObservationResponse])
def list_observations(
    case_id: str,
    concept_code: Optional[str] = Query(default=None),
    store: EventStore = Depends(get_store),
) -> List[ObservationResponse]:
    case = store.get_case(case_id)
    if case is None:
        raise NotFoundError(f"No case {case_id}")
    obs = store.get_current_observations(case_id, concept_code=concept_code)
    return [ObservationResponse.model_validate(o) for o in obs]


@router.post(
    "/{case_id}/observations", response_model=ObservationResponse, status_code=http_status.HTTP_201_CREATED
)
def add_observation(
    case_id: str, body: ObservationCreateRequest, store: EventStore = Depends(get_store)
) -> ObservationResponse:
    obs = store.add_observation(
        case_id=case_id,
        concept_code=body.concept_code,
        value=body.value,
        value_type=body.value_type,
        source_type=body.source_type,
        reliability_tier=body.reliability_tier,
        measurement_status=body.measurement_status,
        observed_at=body.observed_at,
        unit=body.unit,
        source_id=body.source_id,
        extraction_confidence=body.extraction_confidence,
    )

    # Phase 3.5: "evaluated the instant any vital arrives". Runs detectors
    # #2 (physiological) and #3 (text pattern) right after every write;
    # never blocks or delays the observation itself (already committed
    # above) and never lowers anything -- escalation-only, by construction.
    case = store.get_case(case_id)
    profile = load_hospital_profile(case.hospital_profile_id)
    evaluate_emergency_bypass(case, store, profile)

    # Phase 11.C/H: "vitals captured -> ... -> ML challenger runs ->
    # acuity + confidence appear on nurse queue". Every new observation
    # re-runs the full scoring stack and persists a fresh RiskAssessment --
    # this is the CP7 Guardian Queue's re-scoring behaviour, arriving here
    # ahead of schedule because there is no reason to wait for it: nothing
    # about "re-score on new data" depends on the queue/timer machinery
    # CP7 actually owns.
    assess_case(case, store, profile)

    return ObservationResponse.model_validate(obs)


@router.post("/{case_id}/emergency-bypass", response_model=CaseResponse)
def trigger_emergency_bypass(
    case_id: str,
    body: EmergencyBypassRequest,
    store: EventStore = Depends(get_store),
    current_user: AuthenticatedUser = Depends(require_role(Role.NURSE, Role.DOCTOR, Role.ADMIN)),
) -> CaseResponse:
    """Phase 3.5 detector #1: the human affordance. One tap, no vitals, no
    confirmation required. This endpoint has zero clinical logic -- it is
    the direct API-layer equivalent of a physical panic button.

    CP9.5: who triggered it now comes from the authenticated bearer token
    (any of the three staff roles may fire this), not from the body -- see
    EmergencyBypassRequest's docstring for the gap this closes."""
    case = store.get_case(case_id)
    if case is None:
        raise NotFoundError(f"No case {case_id}")

    who = f"{current_user.role.value} ({current_user.display_name})"
    reason = body.reason or f"Manual emergency escalation by {who}."

    updated = store.activate_emergency_bypass(
        case_id,
        source=BypassSource.HUMAN,
        reason=reason,
    )
    return CaseResponse.model_validate(updated)


@router.post("/{case_id}/identity/propose", response_model=CaseResponse)
def propose_identity_match(
    case_id: str, body: IdentityMatchProposeRequest, store: EventStore = Depends(get_store)
) -> CaseResponse:
    """Phase 7.1 identity matching, propose half (CP11) -- see
    EventStore.propose_identity_match's docstring for what this
    deliberately does not include (candidate search)."""
    case = store.get_case(case_id)
    if case is None:
        raise NotFoundError(f"No case {case_id}")
    updated = store.propose_identity_match(
        case_id,
        candidate_mrn=body.candidate_mrn,
        candidate_display_name=body.candidate_display_name,
        confidence=body.confidence,
    )
    return CaseResponse.model_validate(updated)


@router.post("/{case_id}/identity/confirm", response_model=CaseResponse)
def confirm_identity_match(
    case_id: str,
    body: IdentityMatchConfirmRequest,
    store: EventStore = Depends(get_store),
    current_user: AuthenticatedUser = Depends(require_role(Role.NURSE, Role.DOCTOR, Role.ADMIN)),
) -> CaseResponse:
    """Phase 7.1 identity matching, confirm half (CP11): 'a human confirms,
    the confirmation is logged.' Requires staff authentication -- the
    confirming identity comes from the verified token, same pattern as
    every other CP10-era audit-relevant action."""
    case = store.get_case(case_id)
    if case is None:
        raise NotFoundError(f"No case {case_id}")
    updated = store.confirm_identity_match(
        case_id,
        mrn=body.mrn,
        display_name=body.display_name,
        confirmed_by=current_user.user_id,
    )
    return CaseResponse.model_validate(updated)


@router.post(
    "/{case_id}/assign-resource",
    response_model=ResourceResponse,
    responses={409: {"model": CapacityConflictResponse}},
)
def assign_resource(
    case_id: str, body: AssignResourceRequest, store: EventStore = Depends(get_store)
) -> ResourceResponse:
    """Phase 6.2: assigns an AVAILABLE resource of the requested type to
    this case, or raises a 409 carrying the hospital's configured
    candidate actions if none is free. Acuity is never touched by this
    call in either outcome -- see CapacityConflictError's docstring."""
    case = store.get_case(case_id)
    if case is None:
        raise NotFoundError(f"No case {case_id}")
    profile = load_hospital_profile(case.hospital_profile_id)
    resource = store.assign_resource(case_id, body.resource_type, profile)
    return ResourceResponse.model_validate(resource)


@router.post("/{case_id}/tests", response_model=DiagnosticTestResponse, status_code=http_status.HTTP_201_CREATED)
def order_test(
    case_id: str, body: OrderTestRequest, store: EventStore = Depends(get_store)
) -> DiagnosticTestResponse:
    test = store.order_test(case_id, body.test_type)
    return DiagnosticTestResponse.model_validate(test)


@router.get("/{case_id}/tests", response_model=List[DiagnosticTestResponse])
def list_tests(case_id: str, store: EventStore = Depends(get_store)) -> List[DiagnosticTestResponse]:
    case = store.get_case(case_id)
    if case is None:
        raise NotFoundError(f"No case {case_id}")
    return [DiagnosticTestResponse.model_validate(t) for t in store.get_diagnostic_tests_for_case(case_id)]
