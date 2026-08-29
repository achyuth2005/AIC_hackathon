import { useMutation, useQueryClient } from '@tanstack/react-query';
import { demoApi } from '../api/demo';
import { useToast } from '../components/ui/Toast';

export function useSeedDemo() {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: () => demoApi.seedDemoPatients('default'),
    onSuccess: (data) => {
      success(`Successfully generated ${data.length} synthetic clinical demo patients!`, 'Demo Database Seeded');
      queryClient.invalidateQueries({ queryKey: ['queue'] });
      queryClient.invalidateQueries({ queryKey: ['control-tower'] });
      queryClient.invalidateQueries({ queryKey: ['doctor-list'] });
      queryClient.invalidateQueries({ queryKey: ['ambulance-list'] });
      queryClient.invalidateQueries({ queryKey: ['stuck-patients'] });
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
      queryClient.invalidateQueries({ queryKey: ['bias-metrics'] });
    },
    onError: (err: unknown) => {
      error(err instanceof Error ? err.message : 'Failed to seed demo database.');
    },
  });
}

export function useSurgeSimulation() {
  const queryClient = useQueryClient();
  const { warning, error } = useToast();

  return useMutation({
    mutationFn: (params?: { baseline_count?: number; multiplier?: number }) =>
      demoApi.triggerSurgeSimulation(params),
    onSuccess: (data) => {
      warning(
        `Surge simulation executed: ${data.surge_count} arrival burst generated across ${data.multiplier}x scale.`,
        'Surge Simulation Engaged'
      );
      queryClient.invalidateQueries({ queryKey: ['queue'] });
      queryClient.invalidateQueries({ queryKey: ['control-tower'] });
      queryClient.invalidateQueries({ queryKey: ['stuck-patients'] });
      queryClient.invalidateQueries({ queryKey: ['doctor-list'] });
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
    },
    onError: (err: unknown) => {
      error(err instanceof Error ? err.message : 'Surge simulation failed.');
    },
  });
}
