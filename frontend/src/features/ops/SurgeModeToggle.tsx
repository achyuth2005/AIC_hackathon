import React from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { http } from '../../lib/http';
import { Button } from '../../components/ui/Button';
import { Flame } from 'lucide-react';
import { useToast } from '../../components/ui/Toast';

export const SurgeModeToggle: React.FC = () => {
  const queryClient = useQueryClient();
  const { warning, error } = useToast();

  const { mutate: triggerSurge, isPending } = useMutation({
    mutationFn: () => http.post('/demo/surge?hospital_profile_id=default&baseline_count=10&multiplier=3'),
    onSuccess: () => {
      warning(
        'Surge simulation executed: 30 burst arrivals generated with capacity load and alert aggregation.',
        'SURGE BURST SIMULATION ENGAGED'
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

  return (
    <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 text-left flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-lg">
      <div className="flex items-start gap-3.5">
        <div className="p-2.5 rounded-xl border shrink-0 bg-slate-800 text-slate-400 border-slate-700">
          <Flame className="w-6 h-6 text-amber-400" />
        </div>

        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h3 className="font-extrabold text-base text-slate-100">
              Department Surge Mode & Mass-Casualty Simulation
            </h3>
            <span className="text-[10px] font-mono font-bold px-2.5 py-0.5 rounded-full border bg-slate-800 text-slate-400 border-slate-700">
              Phase 14.2 Simulation
            </span>
          </div>
          <p className="text-xs text-slate-400 max-w-xl leading-relaxed">
            Trigger a 3x emergency burst arrival with deteriorating patient auto-escalations, bed capacity saturation, and flow bottlenecks.
          </p>
        </div>
      </div>

      <div className="shrink-0">
        <Button
          variant="warning"
          size="md"
          isLoading={isPending}
          onClick={() => triggerSurge()}
          leftIcon={<Flame className="w-4 h-4" />}
          className="font-bold bg-amber-600 hover:bg-amber-500 text-slate-950 shadow-md shadow-amber-950/60"
        >
          Simulate Surge Burst (30 Patients)
        </Button>
      </div>
    </div>
  );
};
