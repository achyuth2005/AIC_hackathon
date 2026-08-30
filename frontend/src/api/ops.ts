import { http } from '../lib/http';
import { StuckPatternResult, ControlTowerResponse } from '../types/api';

// Bug fix: both now require an authenticated staff token on the backend
// (see app/api/ops.py / app/api/control_tower.py's audit-fix docstrings).
export const opsApi = {
  getStuckPatients: (hospitalProfileId = 'default') =>
    http.get<StuckPatternResult[]>('/ops/stuck-patients', {
      params: { hospital_profile_id: hospitalProfileId },
      auth: true,
    }),

  getControlTower: (hospitalProfileId = 'default') =>
    http.get<ControlTowerResponse>('/control-tower', {
      params: { hospital_profile_id: hospitalProfileId },
      auth: true,
    }),
};
