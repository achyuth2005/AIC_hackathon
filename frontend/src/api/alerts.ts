import { http } from '../lib/http';
import { AlertResponse, AlertDismissRequest, AlertBudgetReport } from '../types/api';

// Bug fix: getAlerts/getAlertBudget now require an authenticated staff
// token too (see app/api/alerts.py's audit-fix docstring) -- dismissAlert
// already had it.
export const alertsApi = {
  getAlerts: (hospitalProfileId = 'default') =>
    http.get<AlertResponse[]>('/alerts', {
      params: { hospital_profile_id: hospitalProfileId },
      auth: true,
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
      auth: true,
    }),
};
