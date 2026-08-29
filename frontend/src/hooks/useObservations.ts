import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { observationsApi } from '../api/observations';
import { ObservationCreateRequest } from '../types/api';
import { useToast } from '../components/ui/Toast';

export function useObservations(caseId: string | undefined, conceptCode?: string) {
  return useQuery({
    queryKey: ['observations', caseId, conceptCode],
    queryFn: () => {
      if (!caseId) throw new Error('Case ID is required');
      return observationsApi.getObservations(caseId, conceptCode);
    },
    enabled: !!caseId,
    staleTime: 2000,
  });
}

export function useAddObservation() {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: async ({
      caseId,
      observations,
    }: {
      caseId: string;
      observations: ObservationCreateRequest[];
    }) => {
      // Must post observations sequentially to ensure final scoring calculation incorporates all values
      const results = [];
      for (const obs of observations) {
        const res = await observationsApi.addObservation(caseId, obs);
        results.push(res);
      }
      return results;
    },
    onSuccess: (data, variables) => {
      success(
        `Recorded ${data.length} clinical observation${data.length === 1 ? '' : 's'}. Rescore computed.`,
        'Vitals Saved'
      );
      queryClient.invalidateQueries({ queryKey: ['case', variables.caseId] });
      queryClient.invalidateQueries({ queryKey: ['observations', variables.caseId] });
      queryClient.invalidateQueries({ queryKey: ['risk-assessments', variables.caseId] });
      queryClient.invalidateQueries({ queryKey: ['timeline', variables.caseId] });
      queryClient.invalidateQueries({ queryKey: ['explanation', variables.caseId] });
      queryClient.invalidateQueries({ queryKey: ['queue'] });
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
      queryClient.invalidateQueries({ queryKey: ['control-tower'] });
    },
    onError: (err: unknown) => {
      error(err instanceof Error ? err.message : 'Failed to record observations.');
    },
  });
}
