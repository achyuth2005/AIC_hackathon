import { useQuery } from '@tanstack/react-query';
import { doctorApi } from '../api/doctor';
import { DoctorCaseDetailResponse } from '../types/api';

export function useDoctorCase(caseId: string | undefined) {
  return useQuery<DoctorCaseDetailResponse>({
    queryKey: ['doctor-view', caseId],
    queryFn: () => {
      if (!caseId) throw new Error('Case ID is required');
      return doctorApi.getDoctorCaseDetail(caseId);
    },
    enabled: !!caseId,
    refetchInterval: 5000,
    staleTime: 0,
  });
}
