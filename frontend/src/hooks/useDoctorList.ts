import { useQuery } from '@tanstack/react-query';
import { doctorApi } from '../api/doctor';
import { CONFIG } from '../config';

export function useDoctorList(hospitalProfileId = 'default') {
  return useQuery({
    queryKey: ['doctor-list', hospitalProfileId],
    queryFn: () => doctorApi.getDoctorQueue(hospitalProfileId),
    refetchInterval: CONFIG.POLLING.QUEUE,
    refetchIntervalInBackground: false,
    staleTime: 0,
  });
}
