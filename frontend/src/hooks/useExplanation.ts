import { useQuery } from '@tanstack/react-query';
import { casesApi } from '../api/cases';
import { ExplanationResult } from '../types/api';

export function useExplanation(caseId: string | undefined) {
  return useQuery<ExplanationResult>({
    queryKey: ['explanation', caseId],
    queryFn: () => {
      if (!caseId) throw new Error('Case ID is required');
      return casesApi.getExplanation(caseId);
    },
    enabled: !!caseId,
    staleTime: 5000,
    retry: false,
  });
}
