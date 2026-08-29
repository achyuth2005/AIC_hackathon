import { useMutation, useQueryClient } from '@tanstack/react-query';
import { casesApi } from '../api/cases';
import { useToast } from '../components/ui/Toast';

export function useMarkReassessed() {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: (caseId: string) => casesApi.reassessCase(caseId),
    onSuccess: (data, caseId) => {
      success(
        data.display_name
          ? `Reassessment recorded for ${data.display_name}.`
          : 'Reassessment recorded.',
        'Reassessment Clock Reset'
      );
      queryClient.invalidateQueries({ queryKey: ['queue'] });
      queryClient.invalidateQueries({ queryKey: ['case', caseId] });
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
      queryClient.invalidateQueries({ queryKey: ['control-tower'] });
    },
    onError: (err: unknown) => {
      error(err instanceof Error ? err.message : 'Failed to mark reassessed.');
    },
  });
}
