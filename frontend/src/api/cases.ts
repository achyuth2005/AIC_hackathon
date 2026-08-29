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

export const casesApi = {
  createCase: (body: CaseCreateRequest) =>
    http.post<CaseResponse>('/cases', body),

  listCases: (status?: CaseStatus) =>
    http.get<CaseResponse[]>('/cases', {
      params: { status },
    }),

  getCase: (caseId: string) =>
    http.get<CaseDetailResponse>(`/cases/${caseId}`),

  reassessCase: (caseId: string) =>
    http.post<CaseResponse>(`/cases/${caseId}/reassessment`),

  overrideCase: (caseId: string, body: OverrideRequest) =>
    http.post<HumanDecisionResponse>(`/cases/${caseId}/override`, body, { auth: true }),

  emergencyBypass: (caseId: string, reason?: string | null) =>
    http.post<CaseResponse>(`/cases/${caseId}/emergency-bypass`, { reason }, { auth: true }),

  getDecisions: (caseId: string) =>
    http.get<HumanDecisionResponse[]>(`/cases/${caseId}/decisions`),

  getTimeline: (caseId: string) =>
    http.get<EventResponse[]>(`/cases/${caseId}/timeline`),

  getRiskAssessments: (caseId: string) =>
    http.get<RiskAssessmentResponse[]>(`/cases/${caseId}/risk-assessments`),

  getExplanation: (caseId: string) =>
    http.get<ExplanationResult>(`/cases/${caseId}/explanation`),

  processIntake: (caseId: string, body: IntakeRequest) =>
    http.post<IntakeOutcome>(`/cases/${caseId}/intake`, body),

  selfReportWorsening: (caseId: string, note?: string | null) =>
    http.post<CaseResponse>(`/cases/${caseId}/self-reported-worsening`, { note }),

  recordArrival: (caseId: string, body?: RecordArrivalRequest) =>
    http.post<CaseResponse>(`/cases/${caseId}/arrival`, body || {}),

  getEta: (caseId: string) =>
    http.get<ETARange>(`/cases/${caseId}/eta`),

  delayAmbulance: (caseId: string, body: TransportDelayRequest) =>
    http.post<ETARange>(`/cases/${caseId}/ambulance/delay`, body),

  getPreAlert: (caseId: string) =>
    http.get<PreAlertView>(`/cases/${caseId}/pre-alert`),

  proposeIdentity: (caseId: string, body: ProposeIdentityRequest) =>
    http.post<CaseResponse>(`/cases/${caseId}/identity/propose`, body),

  confirmIdentity: (caseId: string, body: ConfirmIdentityRequest) =>
    http.post<CaseResponse>(`/cases/${caseId}/identity/confirm`, body, { auth: true }),
};
