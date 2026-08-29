import { http } from '../lib/http';
import {
  ResourceResponse,
  ResourceCreateRequest,
  AssignResourceRequest,
} from '../types/api';
import { ResourceType, ResourceStatus } from '../types/enums';

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
    }),

  createResource: (body: ResourceCreateRequest) =>
    http.post<ResourceResponse>('/resources', {
      hospital_profile_id: 'default',
      ...body,
    }),

  assignResource: (caseId: string, body: AssignResourceRequest) =>
    http.post<ResourceResponse>(`/cases/${caseId}/assign-resource`, body),

  confirmOccupancy: (resourceId: string) =>
    http.post<ResourceResponse>(`/resources/${resourceId}/confirm-occupancy`),

  releaseResource: (resourceId: string) =>
    http.post<ResourceResponse>(`/resources/${resourceId}/release`),
};
