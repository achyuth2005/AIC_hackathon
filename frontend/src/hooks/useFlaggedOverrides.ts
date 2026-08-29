import { useQuery } from '@tanstack/react-query';
import { adminApi } from '../api/admin';

export function useFlaggedOverrides(hospitalProfileId = 'default') {
  return useQuery({
    queryKey: ['flagged-overrides', hospitalProfileId],
    queryFn: () => adminApi.getFlaggedOverrides(hospitalProfileId),
    refetchInterval: 5000,
    staleTime: 0,
  });
}
