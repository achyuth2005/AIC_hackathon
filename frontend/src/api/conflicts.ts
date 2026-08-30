import { http } from '../lib/http';
import { DataConflictResponse, ResolveConflictRequest } from '../types/api';

// Bug fix: getCaseConflicts now requires an authenticated staff token too
// (see app/api/cases.py's audit-fix docstring) -- resolveConflict already
// had it.
export const conflictsApi = {
  getCaseConflicts: (caseId: string, includeResolved = false) =>
    http.get<DataConflictResponse[]>(`/cases/${caseId}/conflicts`, {
      params: { include_resolved: includeResolved },
      auth: true,
    }),

  resolveConflict: (conflictId: string, body: ResolveConflictRequest) =>
    http.post<DataConflictResponse>(`/conflicts/${conflictId}/resolve`, body, {
      auth: true,
    }),
};
