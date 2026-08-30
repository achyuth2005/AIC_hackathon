import React from 'react';
import { useSurgeSimulation } from '../../hooks/useDemoScenarios';
import { Button } from '../../components/ui/Button';
import { Flame } from 'lucide-react';

export const SurgeModeToggle: React.FC = () => {
  const { mutate: triggerSurge, isPending } = useSurgeSimulation();

  return (
    <div className="p-5 rounded-2xl bg-white border border-slate-200/80 text-left flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-card">
      <div className="flex items-start gap-3.5">
        <div className="p-2.5 rounded-xl border shrink-0 bg-orange-50 text-orange-600 border-orange-200">
          <Flame className="w-6 h-6" />
        </div>

        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h3 className="font-bold text-base text-slate-900">
              Department Surge Mode & Mass-Casualty Simulation
            </h3>
            <span className="text-[10px] font-mono font-bold px-2.5 py-0.5 rounded-full border bg-slate-100 text-slate-500 border-slate-200">
              Phase 14.2 Simulation
            </span>
          </div>
          <p className="text-xs text-slate-500 max-w-xl leading-relaxed">
            Trigger a 3x emergency burst arrival with deteriorating patient auto-escalations, bed capacity saturation, and flow bottlenecks.
          </p>
        </div>
      </div>

      <div className="shrink-0">
        <Button
          variant="warning"
          size="md"
          isLoading={isPending}
          onClick={() => triggerSurge({ baseline_count: 10, multiplier: 3 })}
          leftIcon={<Flame className="w-4 h-4" />}
          className="font-bold"
        >
          Simulate Surge Burst (30 Patients)
        </Button>
      </div>
    </div>
  );
};
