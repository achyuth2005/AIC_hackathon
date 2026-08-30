import { http } from '../lib/http';
import { ObservationResponse, ObservationCreateRequest } from '../types/api';

// Bug fix: all three now require an authenticated staff token on the
// backend (see app/api/cases.py / app/api/observations.py's audit-fix
// docstrings).
export const observationsApi = {
  addObservation: (caseId: string, body: ObservationCreateRequest) =>
    http.post<ObservationResponse>(`/cases/${caseId}/observations`, body, { auth: true }),

  getObservations: (caseId: string, conceptCode?: string) =>
    http.get<ObservationResponse[]>(`/cases/${caseId}/observations`, {
      params: { concept_code: conceptCode },
      auth: true,
    }),

  supersedeObservation: (
    observationId: string,
    body: { new_value: number | boolean | string; reason: string }
  ) =>
    http.post<ObservationResponse>(
      `/observations/${observationId}/supersede`,
      body,
      { auth: true }
    ),
};
