import { useQuery } from '@tanstack/react-query';
import { casesApi } from '../api/cases';
import { RiskAssessmentResponse } from '../types/api';

export function useRiskAssessments(caseId: string | undefined) {
  return useQuery<RiskAssessmentResponse[]>({
    queryKey: ['risk-assessments', caseId],
    queryFn: () => {
      if (!caseId) throw new Error('Case ID is required');
      return casesApi.getRiskAssessments(caseId);
    },
    enabled: !!caseId,
    staleTime: 2000,
  });
}
