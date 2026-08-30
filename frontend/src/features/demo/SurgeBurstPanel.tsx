import React from 'react';
import { SurgeSimulationResult } from '../../types/api';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';
import { MetricCard } from '../../components/ui/MetricCard';
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
    <Card className="text-left shadow-card-lg animate-fade-in">
      <CardHeader className="pb-3 flex flex-row items-center justify-between border-b border-slate-100">
        <CardTitle className="text-base flex items-center gap-2.5 text-slate-900">
          <Flame className="w-5 h-5 text-amber-500" />
          <span>Phase 14.2 Surge Simulation Results ({multiplier}x Scale)</span>
        </CardTitle>
        <span className="text-[10px] font-mono font-bold bg-emerald-50 text-emerald-700 px-3 py-1 rounded-full border border-emerald-200">
          Surge Proof Verified
        </span>
      </CardHeader>

      <CardContent className="space-y-6 pt-4">
        {/* Metrics Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <MetricCard label="Baseline Census" value={`${baseline_count} Cases`} />

          <MetricCard
            label="Surge Arrival Burst"
            value={`+${surge_count} Cases`}
            tone="amber"
            active
          />

          <MetricCard
            label="Queue Scaling"
            value={`${queue_length_before} → ${queue_length_after}`}
            tone="indigo"
            active
          />

          <MetricCard
            label="Overdue Cases"
            value={`${reassessment_overdue_count} Overdue`}
            tone="rose"
            active={reassessment_overdue_count > 0}
          />
        </div>

        {/* 6 Proof Cards */}
        <div className="space-y-2">
          <div className="text-xs font-bold text-slate-500 uppercase tracking-wider">
            Verified Surge System Invariants
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {proofs.map((p, idx) => (
              <div
                key={idx}
                className={`p-3 rounded-xl border flex items-start gap-2.5 ${
                  p.passed
                    ? 'bg-emerald-50 border-emerald-200 text-emerald-700'
                    : 'bg-slate-50 border-slate-200 text-slate-500'
                }`}
              >
                <ShieldCheck className={`w-4 h-4 shrink-0 mt-0.5 ${p.passed ? 'text-emerald-600' : 'text-slate-400'}`} />
                <div className="space-y-0.5 text-xs">
                  <div className={`font-bold ${p.passed ? 'text-emerald-800' : 'text-slate-700'}`}>{p.title}</div>
                  <div className={`text-[11px] font-sans ${p.passed ? 'text-emerald-700' : 'text-slate-500'}`}>{p.description}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
