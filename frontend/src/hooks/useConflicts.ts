import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { conflictsApi } from '../api/conflicts';
import { ResolveConflictRequest } from '../types/api';
import { useToast } from '../components/ui/Toast';

export function useConflicts(caseId: string | undefined, includeResolved = false) {
  return useQuery({
    queryKey: ['conflicts', caseId, includeResolved],
    queryFn: () => {
      if (!caseId) throw new Error('Case ID is required');
      return conflictsApi.getCaseConflicts(caseId, includeResolved);
    },
    enabled: !!caseId,
    staleTime: 2000,
  });
}

export function useResolveConflict() {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: ({
      conflictId,
      body,
    }: {
      conflictId: string;
      caseId: string;
      body: ResolveConflictRequest;
    }) => conflictsApi.resolveConflict(conflictId, body),
    onSuccess: (_data, variables) => {
      success('Data conflict resolved by clinician selection.', 'Conflict Resolved');
      queryClient.invalidateQueries({ queryKey: ['conflicts', variables.caseId] });
      queryClient.invalidateQueries({ queryKey: ['case', variables.caseId] });
      queryClient.invalidateQueries({ queryKey: ['observations', variables.caseId] });
      queryClient.invalidateQueries({ queryKey: ['risk-assessments', variables.caseId] });
      queryClient.invalidateQueries({ queryKey: ['queue'] });
    },
    onError: (err: unknown) => {
      error(err instanceof Error ? err.message : 'Failed to resolve conflict.');
    },
  });
}
