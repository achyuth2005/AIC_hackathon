import { http } from '../lib/http';
import {
  CaseResponse,
  CaseDetailResponse,
  CaseCreateRequest,
  OverrideRequest,
  HumanDecisionResponse,
  EventResponse,
  RiskAssessmentResponse,
  ExplanationResult,
  IntakeOutcome,
  IntakeRequest,
  PreAlertView,
  ETARange,
  TransportDelayRequest,
  ProposeIdentityRequest,
  ConfirmIdentityRequest,
  RecordArrivalRequest,
} from '../types/api';
import { CaseStatus } from '../types/enums';

// Bug fix: every one of these calls now requires an authenticated staff
// token on the backend (see app/api/cases.py's audit-fix docstring) except
// the two endpoints deliberately left open by design --
// selfReportWorsening (Phase 8.1's unauthenticated "I feel worse" button)
// and delayAmbulance (no paramedic role/identity is modeled in this
// Auth/RBAC mock). Both are called out below where they diverge.
export const casesApi = {
  createCase: (body: CaseCreateRequest) => http.post<CaseResponse>('/cases', body, { auth: true }),

  listCases: (status?: CaseStatus) =>
    http.get<CaseResponse[]>('/cases', {
      params: { status },
      auth: true,
    }),

  getCase: (caseId: string) => http.get<CaseDetailResponse>(`/cases/${caseId}`, { auth: true }),

  reassessCase: (caseId: string) => http.post<CaseResponse>(`/cases/${caseId}/reassessment`, undefined, { auth: true }),

  overrideCase: (caseId: string, body: OverrideRequest) =>
    http.post<HumanDecisionResponse>(`/cases/${caseId}/override`, body, { auth: true }),

  emergencyBypass: (caseId: string, reason?: string | null) =>
    http.post<CaseResponse>(`/cases/${caseId}/emergency-bypass`, { reason }, { auth: true }),

  getDecisions: (caseId: string) => http.get<HumanDecisionResponse[]>(`/cases/${caseId}/decisions`, { auth: true }),

  getTimeline: (caseId: string) => http.get<EventResponse[]>(`/cases/${caseId}/timeline`, { auth: true }),

  getRiskAssessments: (caseId: string) =>
    http.get<RiskAssessmentResponse[]>(`/cases/${caseId}/risk-assessments`, { auth: true }),

  getExplanation: (caseId: string) => http.get<ExplanationResult>(`/cases/${caseId}/explanation`, { auth: true }),

  processIntake: (caseId: string, body: IntakeRequest) =>
    http.post<IntakeOutcome>(`/cases/${caseId}/intake`, body, { auth: true }),

  // Stays unauthenticated by design (Phase 8.1's zero-friction
  // patient/caregiver "I feel worse" affordance).
  selfReportWorsening: (caseId: string, note?: string | null) =>
    http.post<CaseResponse>(`/cases/${caseId}/self-reported-worsening`, { note }),

  recordArrival: (caseId: string, body?: RecordArrivalRequest) =>
    http.post<CaseResponse>(`/cases/${caseId}/arrival`, body || {}, { auth: true }),

  getEta: (caseId: string) => http.get<ETARange>(`/cases/${caseId}/eta`, { auth: true }),

  // Stays unauthenticated by design (no paramedic role/identity is
  // modeled in this Auth/RBAC mock).
  delayAmbulance: (caseId: string, body: TransportDelayRequest) =>
    http.post<ETARange>(`/cases/${caseId}/ambulance/delay`, body),

  getPreAlert: (caseId: string) => http.get<PreAlertView>(`/cases/${caseId}/pre-alert`, { auth: true }),

  proposeIdentity: (caseId: string, body: ProposeIdentityRequest) =>
    http.post<CaseResponse>(`/cases/${caseId}/identity/propose`, body, { auth: true }),

  confirmIdentity: (caseId: string, body: ConfirmIdentityRequest) =>
    http.post<CaseResponse>(`/cases/${caseId}/identity/confirm`, body, { auth: true }),
};
