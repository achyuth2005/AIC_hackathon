import { useMutation, useQueryClient } from '@tanstack/react-query';
import { casesApi } from '../api/cases';
import { useToast } from '../components/ui/Toast';

export function useIntake() {
  const queryClient = useQueryClient();
  const { success, warning, error } = useToast();

  return useMutation({
    mutationFn: ({ caseId, text }: { caseId: string; text: string }) =>
      casesApi.processIntake(caseId, { text }),
    onSuccess: (data, variables) => {
      if (!data.llm_available) {
        warning(
          `LLM Intake unavailable (${data.reason || 'LLM_DISABLED'}). Switched to deterministic vitals capture.`,
          'Intake Engine Fallback'
        );
      } else if (data.parse_succeeded) {
        success(
          `Extracted ${data.observations_created.length} observations from text.`,
          'AI Intake Complete'
        );
      } else {
        warning(
          `Could not extract structured vitals from text (${data.reason}). Please enter vitals manually.`,
          'Manual Capture Required'
        );
      }

      queryClient.invalidateQueries({ queryKey: ['case', variables.caseId] });
      queryClient.invalidateQueries({ queryKey: ['observations', variables.caseId] });
      queryClient.invalidateQueries({ queryKey: ['risk-assessments', variables.caseId] });
      queryClient.invalidateQueries({ queryKey: ['timeline', variables.caseId] });
      queryClient.invalidateQueries({ queryKey: ['explanation', variables.caseId] });
      queryClient.invalidateQueries({ queryKey: ['queue'] });
    },
    onError: (err: unknown) => {
      error(err instanceof Error ? err.message : 'Intake parsing failed.');
    },
  });
}
