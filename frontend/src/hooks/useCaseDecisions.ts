import { useQuery } from '@tanstack/react-query';
import { casesApi } from '../api/cases';
import { HumanDecisionResponse } from '../types/api';

export function useCaseDecisions(caseId: string | undefined) {
  return useQuery<HumanDecisionResponse[]>({
    queryKey: ['decisions', caseId],
    queryFn: () => {
      if (!caseId) throw new Error('Case ID is required');
      return casesApi.getDecisions(caseId);
    },
    enabled: !!caseId,
    staleTime: 2000,
  });
}
