import { useQuery } from '@tanstack/react-query';
import { casesApi } from '../api/cases';

export function useRiskAssessments(caseId: string | undefined) {
  return useQuery({
    queryKey: ['risk-assessments', caseId],
    queryFn: () => {
      if (!caseId) throw new Error('Case ID is required');
      return casesApi.getRiskAssessments(caseId);
    },
    enabled: !!caseId,
    staleTime: 2000,
  });
}

export function useCaseTimeline(caseId: string | undefined) {
  return useQuery({
    queryKey: ['timeline', caseId],
    queryFn: () => {
      if (!caseId) throw new Error('Case ID is required');
      return casesApi.getTimeline(caseId);
    },
    enabled: !!caseId,
    staleTime: 2000,
  });
}

export function useExplanation(caseId: string | undefined) {
  return useQuery({
    queryKey: ['explanation', caseId],
    queryFn: () => {
      if (!caseId) throw new Error('Case ID is required');
      return casesApi.getExplanation(caseId);
    },
    enabled: !!caseId,
    staleTime: 5000,
    retry: false, // Do not aggressively retry explanation endpoint
  });
}
