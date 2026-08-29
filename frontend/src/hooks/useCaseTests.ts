import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { diagnosticsApi } from '../api/tests';
import { DiagnosticTestResponse, DiagnosticTestCreateRequest } from '../types/api';
import { useToast } from '../components/ui/Toast';

export function useCaseTests(caseId: string | undefined) {
  return useQuery<DiagnosticTestResponse[]>({
    queryKey: ['tests', caseId],
    queryFn: () => {
      if (!caseId) throw new Error('Case ID is required');
      return diagnosticsApi.getCaseTests(caseId);
    },
    enabled: !!caseId,
    staleTime: 2000,
  });
}

export function useOrderTest() {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: ({ caseId, body }: { caseId: string; body: DiagnosticTestCreateRequest }) =>
      diagnosticsApi.orderTest(caseId, body),
    onSuccess: (data, variables) => {
      success(`Diagnostic test "${data.test_type}" ordered.`, 'Test Ordered');
      queryClient.invalidateQueries({ queryKey: ['tests', variables.caseId] });
      queryClient.invalidateQueries({ queryKey: ['case', variables.caseId] });
      queryClient.invalidateQueries({ queryKey: ['timeline', variables.caseId] });
      queryClient.invalidateQueries({ queryKey: ['ops'] });
    },
    onError: (err: unknown) => {
      error(err instanceof Error ? err.message : 'Failed to order test.');
    },
  });
}

export function useAdvanceTest() {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: async ({
      testId,
      stage,
    }: {
      testId: string;
      caseId: string;
      stage: 'sample' | 'result' | 'review';
    }) => {
      if (stage === 'sample') return diagnosticsApi.collectSample(testId);
      if (stage === 'result') return diagnosticsApi.markResultAvailable(testId);
      return diagnosticsApi.markResultReviewed(testId);
    },
    onSuccess: (data, variables) => {
      const stageName =
        variables.stage === 'sample'
          ? 'Sample Collected'
          : variables.stage === 'result'
          ? 'Result Available'
          : 'Result Reviewed';

      success(`Test "${data.test_type}" updated to ${stageName}.`, 'Diagnostic Status Updated');
      queryClient.invalidateQueries({ queryKey: ['tests', variables.caseId] });
      queryClient.invalidateQueries({ queryKey: ['case', variables.caseId] });
      queryClient.invalidateQueries({ queryKey: ['timeline', variables.caseId] });
      queryClient.invalidateQueries({ queryKey: ['doctor-view', variables.caseId] });
      queryClient.invalidateQueries({ queryKey: ['ops'] });
      queryClient.invalidateQueries({ queryKey: ['control-tower'] });
    },
    onError: (err: unknown) => {
      error(err instanceof Error ? err.message : 'Failed to advance test lifecycle.');
    },
  });
}
