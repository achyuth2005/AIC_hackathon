import { http } from '../lib/http';
import { StuckPatternResult, ControlTowerResponse } from '../types/api';

export const opsApi = {
  getStuckPatients: (hospitalProfileId = 'default') =>
    http.get<StuckPatternResult[]>('/ops/stuck-patients', {
      params: { hospital_profile_id: hospitalProfileId },
    }),

  getControlTower: (hospitalProfileId = 'default') =>
    http.get<ControlTowerResponse>('/control-tower', {
      params: { hospital_profile_id: hospitalProfileId },
    }),
};
