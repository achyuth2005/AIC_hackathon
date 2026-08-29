import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { resourcesApi } from '../api/resources';
import { ResourceType, ResourceStatus } from '../types/enums';
import { ResourceCreateRequest, AssignResourceRequest } from '../types/api';
import { useToast } from '../components/ui/Toast';

export function useResources(params?: {
  resource_type?: ResourceType;
  status?: ResourceStatus;
}) {
  return useQuery({
    queryKey: ['resources', params?.resource_type, params?.status],
    queryFn: () => resourcesApi.listResources(params),
    staleTime: 3000,
  });
}

export function useCreateResource() {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: (body: ResourceCreateRequest) => resourcesApi.createResource(body),
    onSuccess: (data) => {
      success(`Resource "${data.label}" created.`, 'Resource Created');
      queryClient.invalidateQueries({ queryKey: ['resources'] });
      queryClient.invalidateQueries({ queryKey: ['control-tower'] });
    },
    onError: (err: unknown) => {
      error(err instanceof Error ? err.message : 'Failed to create resource.');
    },
  });
}

export function useAssignResource() {
  const queryClient = useQueryClient();
  const { success } = useToast();

  return useMutation({
    mutationFn: ({ caseId, body }: { caseId: string; body: AssignResourceRequest }) =>
      resourcesApi.assignResource(caseId, body),
    onSuccess: (data, variables) => {
      success(`Assigned ${data.label} (${data.resource_type}) to patient.`, 'Resource Assigned');
      queryClient.invalidateQueries({ queryKey: ['case', variables.caseId] });
      queryClient.invalidateQueries({ queryKey: ['resources'] });
      queryClient.invalidateQueries({ queryKey: ['control-tower'] });
      queryClient.invalidateQueries({ queryKey: ['queue'] });
    },
    // On 409 capacity conflict, we do NOT toast error — the component renders CapacityConflictPanel
  });
}

export function useReleaseResource() {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: (resourceId: string) => resourcesApi.releaseResource(resourceId),
    onSuccess: (data) => {
      success(`Resource "${data.label}" released to Available status.`, 'Resource Released');
      queryClient.invalidateQueries({ queryKey: ['resources'] });
      queryClient.invalidateQueries({ queryKey: ['control-tower'] });
      queryClient.invalidateQueries({ queryKey: ['case'] });
    },
    onError: (err: unknown) => {
      error(err instanceof Error ? err.message : 'Failed to release resource.');
    },
  });
}

export function useConfirmOccupancy() {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: (resourceId: string) => resourcesApi.confirmOccupancy(resourceId),
    onSuccess: (data) => {
      success(`Occupancy confirmed for ${data.label}.`, 'Occupancy Confirmed');
      queryClient.invalidateQueries({ queryKey: ['resources'] });
      queryClient.invalidateQueries({ queryKey: ['control-tower'] });
      queryClient.invalidateQueries({ queryKey: ['ops'] });
    },
    onError: (err: unknown) => {
      error(err instanceof Error ? err.message : 'Failed to confirm occupancy.');
    },
  });
}
