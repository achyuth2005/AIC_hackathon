import { http } from '../lib/http';
import { AlertResponse, AlertDismissRequest, AlertBudgetReport } from '../types/api';

export const alertsApi = {
  getAlerts: (hospitalProfileId = 'default') =>
    http.get<AlertResponse[]>('/alerts', {
      params: { hospital_profile_id: hospitalProfileId },
    }),

  dismissAlert: (alertId: string, body: AlertDismissRequest) =>
    http.post<AlertResponse>(`/alerts/${alertId}/dismiss`, body, {
      auth: true,
    }),

  getAlertBudget: (params?: {
    hospital_profile_id?: string;
    nurses_on_shift?: number;
    window_minutes?: number;
  }) =>
    http.get<AlertBudgetReport>('/alerts/budget', {
      params: {
        hospital_profile_id: params?.hospital_profile_id || 'default',
        nurses_on_shift: params?.nurses_on_shift || 2,
        window_minutes: params?.window_minutes || 60,
      },
    }),
};
