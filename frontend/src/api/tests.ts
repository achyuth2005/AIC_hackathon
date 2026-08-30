import { http } from '../lib/http';
import {
  DiagnosticTestResponse,
  DiagnosticTestCreateRequest,
} from '../types/api';

// Bug fix: every one of these now requires an authenticated staff token
// on the backend (see app/api/cases.py / app/api/diagnostics.py's
// audit-fix docstrings).
export const diagnosticsApi = {
  getCaseTests: (caseId: string) => http.get<DiagnosticTestResponse[]>(`/cases/${caseId}/tests`, { auth: true }),

  orderTest: (caseId: string, body: DiagnosticTestCreateRequest) =>
    http.post<DiagnosticTestResponse>(`/cases/${caseId}/tests`, body, { auth: true }),

  collectSample: (testId: string) =>
    http.post<DiagnosticTestResponse>(`/tests/${testId}/sample-collected`, undefined, { auth: true }),

  markResultAvailable: (testId: string) =>
    http.post<DiagnosticTestResponse>(`/tests/${testId}/result-available`, undefined, { auth: true }),

  markResultReviewed: (testId: string) =>
    http.post<DiagnosticTestResponse>(`/tests/${testId}/result-reviewed`, undefined, { auth: true }),
};
