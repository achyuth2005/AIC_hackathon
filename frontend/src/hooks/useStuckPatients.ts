import { useQuery } from '@tanstack/react-query';
import { opsApi } from '../api/ops';
import { CONFIG } from '../config';

export function useStuckPatients(hospitalProfileId = 'default') {
  return useQuery({
    queryKey: ['stuck-patients', hospitalProfileId],
    queryFn: () => opsApi.getStuckPatients(hospitalProfileId),
    refetchInterval: CONFIG.POLLING.OPS,
    refetchIntervalInBackground: false,
    staleTime: 0,
  });
}
