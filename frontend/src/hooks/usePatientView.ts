import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { patientApi } from '../api/patient';
import { CONFIG } from '../config';
import { useToast } from '../components/ui/Toast';

export function usePatientView(caseId: string | undefined) {
  return useQuery({
    queryKey: ['patient-view', caseId],
    queryFn: () => {
      if (!caseId) throw new Error('Case ID is required');
      return patientApi.getPatientView(caseId);
    },
    enabled: !!caseId,
    refetchInterval: CONFIG.POLLING.PATIENT_VIEW,
    refetchIntervalInBackground: false,
    staleTime: 0,
  });
}

export function useReportWorsening() {
  const queryClient = useQueryClient();
  const { warning, error } = useToast();

  return useMutation({
    mutationFn: ({ caseId, note }: { caseId: string; note?: string }) =>
      patientApi.reportWorsening(caseId, note),
    onSuccess: (_data, variables) => {
      warning(
        'Staff have been immediately notified that you feel worse. A triage nurse will check on you shortly.',
        'Nurse Alert Sent'
      );
      queryClient.invalidateQueries({ queryKey: ['patient-view', variables.caseId] });
      queryClient.invalidateQueries({ queryKey: ['queue'] });
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
    },
    onError: (err: unknown) => {
      error(err instanceof Error ? err.message : 'Unable to send nurse notification. Please alert the front desk directly.');
    },
  });
}
