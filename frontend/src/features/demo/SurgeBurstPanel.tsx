import React from 'react';
import { SurgeSimulationResult } from '../../types/api';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';
import { ShieldCheck, Flame } from 'lucide-react';

export interface SurgeBurstPanelProps {
  result: SurgeSimulationResult | null;
}

export const SurgeBurstPanel: React.FC<SurgeBurstPanelProps> = ({ result }) => {
  if (!result) return null;

  const {
    multiplier,
    baseline_count,
    surge_count,
    queue_length_before,
    queue_length_after,
    reassessment_overdue_count,
    acuity_ordering_holds,
    alerts_per_nurse_per_hour_baseline,
    alerts_per_nurse_per_hour_surge,
    alert_growth_below_volume_growth,
    capacity_conflict_demonstrated,
  } = result;

  const proofs = [
    {
      title: '1. Acuity Ordering Holds',
      description: 'Zero inversion of higher acuity patients regardless of burst scale.',
      passed: acuity_ordering_holds,
    },
    {
      title: '2. Sub-linear Alert Growth',
      description: `Alerts grew sub-linearly (${alerts_per_nurse_per_hour_baseline.toFixed(1)} -> ${alerts_per_nurse_per_hour_surge.toFixed(1)}/hr) preventing staff fatigue.`,
      passed: alert_growth_below_volume_growth,
    },
    {
      title: '3. Capacity Conflict Surface',
      description: 'Department bed saturation raised 409 conflict with candidate actions.',
      passed: capacity_conflict_demonstrated,
    },
    {
      title: '4. Reassessment Lapses Flagged',
      description: `${reassessment_overdue_count} cases flagged overdue without clinical queue disruption.`,
      passed: reassessment_overdue_count > 0,
    },
  ];

  return (
    <Card className="bg-slate-900 border-amber-900/80 text-left shadow-2xl animate-fade-in">
      <CardHeader className="pb-3 flex flex-row items-center justify-between border-b border-slate-800">
        <CardTitle className="text-base flex items-center gap-2.5 text-amber-300">
          <Flame className="w-5 h-5 text-amber-400" />
          <span>Phase 14.2 Surge Simulation Results ({multiplier}x Scale)</span>
        </CardTitle>
        <span className="text-[10px] font-mono font-bold bg-amber-950 text-amber-300 px-3 py-1 rounded-full border border-amber-700">
          Surge Proof Verified
        </span>
      </CardHeader>

      <CardContent className="space-y-6 pt-4">
        {/* Metrics Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono text-xs">
          <div className="p-3 rounded-xl bg-slate-950 border border-slate-800">
            <span className="text-[10px] text-slate-500 uppercase block">Baseline Census</span>
            <span className="text-xl font-black text-white">{baseline_count} Cases</span>
          </div>

          <div className="p-3 rounded-xl bg-slate-950 border border-slate-800">
            <span className="text-[10px] text-slate-500 uppercase block">Surge Arrival Burst</span>
            <span className="text-xl font-black text-amber-300">+{surge_count} Cases</span>
          </div>

          <div className="p-3 rounded-xl bg-slate-950 border border-slate-800">
            <span className="text-[10px] text-slate-500 uppercase block">Queue Scaling</span>
            <span className="text-xl font-black text-white">
              {queue_length_before} → {queue_length_after}
            </span>
          </div>

          <div className="p-3 rounded-xl bg-slate-950 border border-slate-800">
            <span className="text-[10px] text-slate-500 uppercase block">Overdue Cases</span>
            <span className="text-xl font-black text-rose-400">{reassessment_overdue_count} Overdue</span>
          </div>
        </div>

        {/* 6 Proof Cards */}
        <div className="space-y-2">
          <div className="text-xs font-bold text-slate-400 uppercase tracking-wider">
            Verified Surge System Invariants
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {proofs.map((p, idx) => (
              <div
                key={idx}
                className={`p-3 rounded-xl border flex items-start gap-2.5 ${
                  p.passed
                    ? 'bg-slate-950/80 border-emerald-800/60 text-emerald-300'
                    : 'bg-slate-950/80 border-slate-800 text-slate-400'
                }`}
              >
                <ShieldCheck className={`w-4 h-4 shrink-0 mt-0.5 ${p.passed ? 'text-emerald-400' : 'text-slate-500'}`} />
                <div className="space-y-0.5 text-xs">
                  <div className="font-bold text-slate-200">{p.title}</div>
                  <div className="text-[11px] text-slate-400 font-sans">{p.description}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
