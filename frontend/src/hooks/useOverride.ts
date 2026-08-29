import { useMutation, useQueryClient } from '@tanstack/react-query';
import { casesApi } from '../api/cases';
import { OverrideRequest } from '../types/api';
import { useToast } from '../components/ui/Toast';

export function useOverride() {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: ({ caseId, body }: { caseId: string; body: OverrideRequest }) =>
      casesApi.overrideCase(caseId, body),
    onSuccess: (data, variables) => {
      const actionText =
        variables.body.action === 'ESCALATE'
          ? `Escalated to ESI ${data.resulting_acuity}`
          : `De-escalated to ESI ${data.resulting_acuity} (Flagged for Review)`;

      success(actionText, 'Override Applied');
      queryClient.invalidateQueries({ queryKey: ['queue'] });
      queryClient.invalidateQueries({ queryKey: ['case', variables.caseId] });
      queryClient.invalidateQueries({ queryKey: ['decisions', variables.caseId] });
      queryClient.invalidateQueries({ queryKey: ['risk-assessments', variables.caseId] });
      queryClient.invalidateQueries({ queryKey: ['flagged-for-review'] });
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
      queryClient.invalidateQueries({ queryKey: ['control-tower'] });
    },
    onError: (err: unknown) => {
      error(err instanceof Error ? err.message : 'Override failed.');
    },
  });
}
