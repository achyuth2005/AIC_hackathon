import { http } from '../lib/http';
import { QueueEntry } from '../types/api';

export const queueApi = {
  getQueue: (hospitalProfileId = 'default') =>
    http.get<QueueEntry[]>('/queue', {
      params: { hospital_profile_id: hospitalProfileId },
    }),

  getPrintableQueue: (hospitalProfileId = 'default') =>
    http.get<string>('/queue/printable', {
      params: { hospital_profile_id: hospitalProfileId },
      responseType: 'text',
    }),
};
