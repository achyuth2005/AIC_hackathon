import { http } from '../lib/http';
import { DataConflictResponse, ResolveConflictRequest } from '../types/api';

export const conflictsApi = {
  getCaseConflicts: (caseId: string, includeResolved = false) =>
    http.get<DataConflictResponse[]>(`/cases/${caseId}/conflicts`, {
      params: { include_resolved: includeResolved },
    }),

  resolveConflict: (conflictId: string, body: ResolveConflictRequest) =>
    http.post<DataConflictResponse>(`/conflicts/${conflictId}/resolve`, body, {
      auth: true,
    }),
};
