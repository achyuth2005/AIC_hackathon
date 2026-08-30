import { http } from '../lib/http';
import {
  ResourceResponse,
  ResourceCreateRequest,
  AssignResourceRequest,
} from '../types/api';
import { ResourceType, ResourceStatus } from '../types/enums';

// Bug fix: every one of these now requires an authenticated staff token
// on the backend (see app/api/resources.py's audit-fix docstring).
// createResource specifically requires the ADMIN role -- provisioning a
// bed/resource is an operational action, least privilege.
export const resourcesApi = {
  listResources: (params?: {
    hospital_profile_id?: string;
    resource_type?: ResourceType;
    status?: ResourceStatus;
  }) =>
    http.get<ResourceResponse[]>('/resources', {
      params: {
        hospital_profile_id: params?.hospital_profile_id || 'default',
        resource_type: params?.resource_type,
        status: params?.status,
      },
      auth: true,
    }),

  createResource: (body: ResourceCreateRequest) =>
    http.post<ResourceResponse>(
      '/resources',
      { hospital_profile_id: 'default', ...body },
      { auth: true }
    ),

  assignResource: (caseId: string, body: AssignResourceRequest) =>
    http.post<ResourceResponse>(`/cases/${caseId}/assign-resource`, body, { auth: true }),

  confirmOccupancy: (resourceId: string) =>
    http.post<ResourceResponse>(`/resources/${resourceId}/confirm-occupancy`, undefined, { auth: true }),

  releaseResource: (resourceId: string) =>
    http.post<ResourceResponse>(`/resources/${resourceId}/release`, undefined, { auth: true }),
};
