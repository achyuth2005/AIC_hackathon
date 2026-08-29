import { http } from '../lib/http';
import {
  DiagnosticTestResponse,
  DiagnosticTestCreateRequest,
} from '../types/api';

export const diagnosticsApi = {
  getCaseTests: (caseId: string) =>
    http.get<DiagnosticTestResponse[]>(`/cases/${caseId}/tests`),

  orderTest: (caseId: string, body: DiagnosticTestCreateRequest) =>
    http.post<DiagnosticTestResponse>(`/cases/${caseId}/tests`, body),

  collectSample: (testId: string) =>
    http.post<DiagnosticTestResponse>(`/tests/${testId}/sample-collected`),

  markResultAvailable: (testId: string) =>
    http.post<DiagnosticTestResponse>(`/tests/${testId}/result-available`),

  markResultReviewed: (testId: string) =>
    http.post<DiagnosticTestResponse>(`/tests/${testId}/result-reviewed`),
};
