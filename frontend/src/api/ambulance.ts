import { http } from '../lib/http';
import {
  ETARange,
  TransportDelayRequest,
  PreAlertView,
  ProposeIdentityRequest,
  ConfirmIdentityRequest,
  RecordArrivalRequest,
  CaseResponse,
  QueueEntry,
} from '../types/api';

export const ambulanceApi = {
  getAmbulanceQueue: async (hospitalProfileId = 'default'): Promise<QueueEntry[]> => {
    // Fetches all cases and returns inbound ambulance transports (status PRE_ARRIVAL or arrival_mode AMBULANCE)
    const queue = await http.get<QueueEntry[]>('/queue', {
      params: { hospital_profile_id: hospitalProfileId },
    });
    return queue;
  },

  getETA: (caseId: string) =>
    http.get<ETARange>(`/cases/${caseId}/eta`),

  delayTransport: (caseId: string, body: TransportDelayRequest) =>
    http.post<ETARange>(`/cases/${caseId}/ambulance/delay`, body),

  getPreAlert: (caseId: string) =>
    http.get<PreAlertView>(`/cases/${caseId}/pre-alert`),

  proposeIdentity: (caseId: string, body: ProposeIdentityRequest) =>
    http.post<CaseResponse>(`/cases/${caseId}/identity/propose`, body),

  confirmIdentity: (caseId: string, body: ConfirmIdentityRequest) =>
    http.post<CaseResponse>(`/cases/${caseId}/identity/confirm`, body, {
      auth: true,
    }),

  recordArrival: (caseId: string, body: RecordArrivalRequest = {}) =>
    http.post<CaseResponse>(`/cases/${caseId}/arrival`, body),
};
