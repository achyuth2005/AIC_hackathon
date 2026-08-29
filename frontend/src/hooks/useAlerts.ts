import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { alertsApi } from '../api/alerts';
import { opsApi } from '../api/ops';
import { CONFIG } from '../config';
import { AlertDismissRequest } from '../types/api';
import { useToast } from '../components/ui/Toast';

export function useAlerts(hospitalProfileId = 'default') {
  return useQuery({
    queryKey: ['alerts', hospitalProfileId],
    queryFn: () => alertsApi.getAlerts(hospitalProfileId),
    refetchInterval: CONFIG.POLLING.ALERTS,
    refetchIntervalInBackground: false,
    staleTime: 0,
  });
}

export function useDismissAlert() {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: ({ alertId, body }: { alertId: string; body: AlertDismissRequest }) =>
      alertsApi.dismissAlert(alertId, body),
    onSuccess: () => {
      success('Alert dismissed with clinical reason.', 'Alert Dismissed');
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
      queryClient.invalidateQueries({ queryKey: ['alert-budget'] });
    },
    onError: (err: unknown) => {
      error(err instanceof Error ? err.message : 'Failed to dismiss alert.');
    },
  });
}

export function useAlertBudget(nursesOnShift = 2, windowMinutes = 60) {
  return useQuery({
    queryKey: ['alert-budget', nursesOnShift, windowMinutes],
    queryFn: () => alertsApi.getAlertBudget({ nurses_on_shift: nursesOnShift, window_minutes: windowMinutes }),
    refetchInterval: CONFIG.POLLING.BUDGET,
    refetchIntervalInBackground: false,
    staleTime: 0,
  });
}

export function useControlTower(hospitalProfileId = 'default') {
  return useQuery({
    queryKey: ['control-tower', hospitalProfileId],
    queryFn: () => opsApi.getControlTower(hospitalProfileId),
    refetchInterval: CONFIG.POLLING.CONTROL_TOWER,
    refetchIntervalInBackground: false,
    staleTime: 0,
  });
}
