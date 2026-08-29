import { http } from '../lib/http';
import { DemoScenario, SurgeSimulationResult } from '../types/api';

export const demoApi = {
  seedDemoPatients: (hospitalProfileId = 'default') =>
    http.post<DemoScenario[]>('/demo/seed', {}, {
      params: { hospital_profile_id: hospitalProfileId },
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
    }),
};
