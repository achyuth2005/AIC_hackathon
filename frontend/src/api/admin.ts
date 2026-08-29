import { http } from '../lib/http';
import { HumanDecisionResponse, OverrideMonitoringReport } from '../types/api';

export const adminApi = {
  getFlaggedOverrides: (hospitalProfileId = 'default') =>
    http.get<HumanDecisionResponse[]>('/overrides/flagged-for-review', {
      params: { hospital_profile_id: hospitalProfileId },
      auth: true,
    }),

  getOverrideMonitoring: (hospitalProfileId = 'default') =>
    http.get<OverrideMonitoringReport>('/overrides/monitoring', {
      params: { hospital_profile_id: hospitalProfileId },
      auth: true,
    }),
};
