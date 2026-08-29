import { useQuery } from '@tanstack/react-query';
import { queueApi } from '../api/queue';
import { useProfile } from '../contexts/ProfileContext';
import { CONFIG } from '../config';

export function useQueue() {
  const { hospitalProfileId } = useProfile();

  return useQuery({
    queryKey: ['queue', hospitalProfileId],
    queryFn: () => queueApi.getQueue(hospitalProfileId),
    refetchInterval: CONFIG.POLLING.QUEUE,
    refetchIntervalInBackground: false,
    staleTime: 0,
    retry: 1,
  });
}
