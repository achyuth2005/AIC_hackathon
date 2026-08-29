import { http } from '../lib/http';
import { ObservationResponse, ObservationCreateRequest } from '../types/api';

export const observationsApi = {
  addObservation: (caseId: string, body: ObservationCreateRequest) =>
    http.post<ObservationResponse>(`/cases/${caseId}/observations`, body),

  getObservations: (caseId: string, conceptCode?: string) =>
    http.get<ObservationResponse[]>(`/cases/${caseId}/observations`, {
      params: { concept_code: conceptCode },
    }),

  supersedeObservation: (
    observationId: string,
    body: { new_value: number | boolean | string; reason: string }
  ) =>
    http.post<ObservationResponse>(
      `/observations/${observationId}/supersede`,
      body
    ),
};
