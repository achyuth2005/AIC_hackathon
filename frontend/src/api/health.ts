import { http } from '../lib/http';

export interface HealthResponse {
  status: string;
}

export const healthApi = {
  check: () => http.get<HealthResponse>('/health'),
};
