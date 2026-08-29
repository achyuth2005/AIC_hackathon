import { useQuery } from '@tanstack/react-query';
import { adminApi } from '../api/admin';

export function useBiasMetrics(hospitalProfileId = 'default') {
  return useQuery({
    queryKey: ['bias-metrics', hospitalProfileId],
    queryFn: () => adminApi.getOverrideMonitoring(hospitalProfileId),
    refetchInterval: 10000,
    staleTime: 0,
  });
}
