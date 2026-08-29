import { useMutation, useQueryClient } from '@tanstack/react-query';
import { ambulanceApi } from '../api/ambulance';
import {
  TransportDelayRequest,
  ProposeIdentityRequest,
  ConfirmIdentityRequest,
  RecordArrivalRequest,
} from '../types/api';
import { useToast } from '../components/ui/Toast';
import { toBackendUtc } from '../lib/datetime';

export function useDelayTransport() {
  const queryClient = useQueryClient();
  const { warning, error } = useToast();

  return useMutation({
    mutationFn: ({ caseId, body }: { caseId: string; body: TransportDelayRequest }) =>
      ambulanceApi.delayTransport(caseId, body),
    onSuccess: (data, variables) => {
      warning(
        `Transport delay added (+${variables.body.additional_minutes}m). New ETA: ${data.lower_minutes}–${data.upper_minutes} mins.`,
        'Paramedic Delay Reported'
      );
      queryClient.invalidateQueries({ queryKey: ['eta', variables.caseId] });
      queryClient.invalidateQueries({ queryKey: ['pre-alert', variables.caseId] });
      queryClient.invalidateQueries({ queryKey: ['control-tower'] });
    },
    onError: (err: unknown) => {
      error(err instanceof Error ? err.message : 'Failed to report transport delay.');
    },
  });
}

export function useProposeIdentity() {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: ({ caseId, body }: { caseId: string; body: ProposeIdentityRequest }) =>
      ambulanceApi.proposeIdentity(caseId, body),
    onSuccess: (_data, variables) => {
      success('Candidate identity match proposed for clinical confirmation.', 'Match Proposed');
      queryClient.invalidateQueries({ queryKey: ['case', variables.caseId] });
      queryClient.invalidateQueries({ queryKey: ['pre-alert', variables.caseId] });
      queryClient.invalidateQueries({ queryKey: ['timeline', variables.caseId] });
    },
    onError: (err: unknown) => {
      error(err instanceof Error ? err.message : 'Failed to propose candidate identity.');
    },
  });
}

export function useConfirmIdentity() {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: ({ caseId, body }: { caseId: string; body: ConfirmIdentityRequest }) =>
      ambulanceApi.confirmIdentity(caseId, body),
    onSuccess: (data, variables) => {
      success(
        `Identity confirmed: ${data.display_name || 'Patient'} (MRN: ${data.mrn}). Prior medical history linked.`,
        'Identity Confirmed'
      );
      queryClient.invalidateQueries({ queryKey: ['case', variables.caseId] });
      queryClient.invalidateQueries({ queryKey: ['pre-alert', variables.caseId] });
      queryClient.invalidateQueries({ queryKey: ['timeline', variables.caseId] });
      queryClient.invalidateQueries({ queryKey: ['queue'] });
    },
    onError: (err: unknown) => {
      error(err instanceof Error ? err.message : 'Failed to confirm patient identity.');
    },
  });
}

export function useRecordArrival() {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: ({ caseId, body }: { caseId: string; body?: RecordArrivalRequest }) =>
      ambulanceApi.recordArrival(caseId, body || { occurred_at: toBackendUtc(new Date()) }),
    onSuccess: (data, variables) => {
      success(
        `Ambulance patient ${data.display_name || 'Patient'} arrived. Case transitioned to ACTIVE and entered Guardian Queue.`,
        'Patient Arrived at ED'
      );
      queryClient.invalidateQueries({ queryKey: ['case', variables.caseId] });
      queryClient.invalidateQueries({ queryKey: ['pre-alert', variables.caseId] });
      queryClient.invalidateQueries({ queryKey: ['eta', variables.caseId] });
      queryClient.invalidateQueries({ queryKey: ['queue'] });
      queryClient.invalidateQueries({ queryKey: ['control-tower'] });
      queryClient.invalidateQueries({ queryKey: ['ambulance-list'] });
    },
    onError: (err: unknown) => {
      error(err instanceof Error ? err.message : 'Failed to record patient arrival.');
    },
  });
}
