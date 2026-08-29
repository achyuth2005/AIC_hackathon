import { useQuery } from '@tanstack/react-query';
import { casesApi } from '../api/cases';
import { CONFIG } from '../config';

export function useCase(caseId: string | undefined) {
  return useQuery({
    queryKey: ['case', caseId],
    queryFn: () => {
      if (!caseId) throw new Error('Case ID is required');
      return casesApi.getCase(caseId);
    },
    enabled: !!caseId,
    refetchInterval: CONFIG.POLLING.CASE_DETAIL,
    refetchIntervalInBackground: false,
    staleTime: 0,
    retry: 1,
  });
}
