export const CONFIG = {
  API_BASE_URL: import.meta.env.VITE_API_BASE_URL || '/api',
  DEFAULT_PROFILE_ID: import.meta.env.VITE_DEFAULT_PROFILE_ID || 'default',
  POLLING: {
    QUEUE: 3000,
    ALERTS: 3000,
    CONTROL_TOWER: 5000,
    CASE_DETAIL: 5000,
    ETA: 3000,
    PATIENT_VIEW: 10000,
    HEALTH: 15000,
    OPS: 10000,
    BUDGET: 10000,
  },
  AUTH_STORAGE_KEY: 'patienttriage_auth',
  PROFILE_STORAGE_KEY: 'patienttriage_profile',
} as const;
