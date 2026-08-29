import { useQuery } from '@tanstack/react-query';
import { healthApi } from '../api/health';
import { CONFIG } from '../config';

export function useHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: healthApi.check,
    refetchInterval: CONFIG.POLLING.HEALTH,
    refetchIntervalInBackground: false,
    retry: 1,
    staleTime: 5000,
  });
}
