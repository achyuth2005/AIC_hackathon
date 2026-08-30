import { http } from '../lib/http';
import { DemoScenario, SurgeSimulationResult } from '../types/api';

// Bug fix: both endpoints are ADMIN-only on the backend now (bulk
// data-generation actions -- see app/api/demo.py's audit-fix docstring).
// Requires the signed-in user to actually hold the ADMIN role; a
// non-admin token will get a 403 from the backend.
export const demoApi = {
  seedDemoPatients: (hospitalProfileId = 'default') =>
    http.post<DemoScenario[]>('/demo/seed', {}, {
      params: { hospital_profile_id: hospitalProfileId },
      auth: true,
    }),

  triggerSurgeSimulation: (params?: {
    hospital_profile_id?: string;
    baseline_count?: number;
    multiplier?: number;
  }) =>
    http.post<SurgeSimulationResult>('/demo/surge', {}, {
      params: {
        hospital_profile_id: params?.hospital_profile_id || 'default',
        baseline_count: params?.baseline_count || 10,
        multiplier: params?.multiplier || 3,
      },
      auth: true,
    }),
};
