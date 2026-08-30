import { useQuery } from '@tanstack/react-query';
import { doctorApi } from '../api/doctor';
import { DoctorCaseView } from '../types/api';

export function useDoctorCaseFull(caseId: string | null | undefined) {
  return useQuery<DoctorCaseView>({
    queryKey: ['doctor-case-full', caseId],
    queryFn: () => {
      if (!caseId) throw new Error('Case ID is required');
      return doctorApi.getDoctorCaseView(caseId);
    },
    enabled: !!caseId,
    staleTime: 3000,
  });
}
