import { http } from '../lib/http';
import {
  ETARange,
  TransportDelayRequest,
  PreAlertView,
  ProposeIdentityRequest,
  ConfirmIdentityRequest,
  RecordArrivalRequest,
  CaseResponse,
} from '../types/api';

export const ambulanceApi = {
  // Bug fix: this used to call GET /queue and filter the result for
  // arrival_mode==='AMBULANCE' || stage==='PRE_ARRIVAL' -- but /queue
  // (the Guardian Queue) only ever returns ACTIVE cases by construction
  // (app/queue/guardian_queue.py), so a PRE_ARRIVAL ambulance transport
  // could never appear there, and its response shape (QueueEntry) never
  // actually carried `arrival_mode`/`stage` in the first place, so the
  // filter matched nothing even for ACTIVE ambulance-origin cases either.
  // GET /cases?arrival_mode=AMBULANCE is the real, authoritative source:
  // every ambulance-origin case regardless of PRE_ARRIVAL/ACTIVE stage.
  getAmbulanceQueue: (hospitalProfileId = 'default'): Promise<CaseResponse[]> =>
    http.get<CaseResponse[]>('/cases', {
      params: { arrival_mode: 'AMBULANCE', hospital_profile_id: hospitalProfileId },
      auth: true,
    }),

  getETA: (caseId: string) => http.get<ETARange>(`/cases/${caseId}/eta`, { auth: true }),

  // Stays unauthenticated by design -- no paramedic role/identity exists
  // in this Auth/RBAC mock (see TransportDelayRequest's backend docstring).
  delayTransport: (caseId: string, body: TransportDelayRequest) =>
    http.post<ETARange>(`/cases/${caseId}/ambulance/delay`, body),

  getPreAlert: (caseId: string) => http.get<PreAlertView>(`/cases/${caseId}/pre-alert`, { auth: true }),

  proposeIdentity: (caseId: string, body: ProposeIdentityRequest) =>
    http.post<CaseResponse>(`/cases/${caseId}/identity/propose`, body, { auth: true }),

  confirmIdentity: (caseId: string, body: ConfirmIdentityRequest) =>
    http.post<CaseResponse>(`/cases/${caseId}/identity/confirm`, body, {
      auth: true,
    }),

  recordArrival: (caseId: string, body: RecordArrivalRequest = {}) =>
    http.post<CaseResponse>(`/cases/${caseId}/arrival`, body, { auth: true }),
};
