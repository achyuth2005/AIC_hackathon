import { http } from '../lib/http';
import { QueueEntry } from '../types/api';

// Bug fix: both endpoints now require an authenticated staff token on the
// backend (see app/api/queue.py's audit-fix docstring).
export const queueApi = {
  getQueue: (hospitalProfileId = 'default') =>
    http.get<QueueEntry[]>('/queue', {
      params: { hospital_profile_id: hospitalProfileId },
      auth: true,
    }),

  getPrintableQueue: (hospitalProfileId = 'default') =>
    http.get<string>('/queue/printable', {
      params: { hospital_profile_id: hospitalProfileId },
      responseType: 'text',
      auth: true,
    }),
};
