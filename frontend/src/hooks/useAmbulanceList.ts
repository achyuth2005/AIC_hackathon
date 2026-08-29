import { useQuery } from '@tanstack/react-query';
import { ambulanceApi } from '../api/ambulance';
import { CONFIG } from '../config';

export function useAmbulanceList(hospitalProfileId = 'default') {
  return useQuery({
    queryKey: ['ambulance-list', hospitalProfileId],
    queryFn: () => ambulanceApi.getAmbulanceQueue(hospitalProfileId),
    refetchInterval: CONFIG.POLLING.ETA,
    refetchIntervalInBackground: false,
    staleTime: 0,
  });
}

export function usePreAlertView(caseId: string | undefined) {
  return useQuery({
    queryKey: ['pre-alert', caseId],
    queryFn: () => {
      if (!caseId) throw new Error('Case ID is required');
      return ambulanceApi.getPreAlert(caseId);
    },
    enabled: !!caseId,
    refetchInterval: 3000,
    staleTime: 0,
  });
}

export function useAmbulanceETA(caseId: string | undefined) {
  return useQuery({
    queryKey: ['eta', caseId],
    queryFn: () => {
      if (!caseId) throw new Error('Case ID is required');
      return ambulanceApi.getETA(caseId);
    },
    enabled: !!caseId,
    refetchInterval: CONFIG.POLLING.ETA,
    staleTime: 0,
  });
}
