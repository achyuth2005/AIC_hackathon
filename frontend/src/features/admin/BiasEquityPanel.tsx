import React from 'react';
import { OverrideMonitoringReport } from '../../types/api';
import { MetricCard } from '../../components/ui/MetricCard';
import { DisparateImpactChart } from './DisparateImpactChart';
import { ShieldCheck, Scale, AlertTriangle, Users, GitCommit } from 'lucide-react';

export interface BiasEquityPanelProps {
  report: OverrideMonitoringReport;
}

export const BiasEquityPanel: React.FC<BiasEquityPanelProps> = ({ report }) => {
  const {
    total_cases,
    total_decisions,
    overall_override_rate,
    overall_de_escalation_rate,
    flagged_for_review_count,
    by_age_band = [],
    by_sex = [],
    caveat,
  } = report;

  const overridePercent =
    overall_override_rate != null ? Math.round(overall_override_rate * 100) : 0;
  const deEscalatePercent =
    overall_de_escalation_rate != null ? Math.round(overall_de_escalation_rate * 100) : 0;

  return (
    <div className="space-y-6 text-left">
      {/* 1. Standing Evaluation Philosophy Alert (Phase 9.7 requirement) */}
      <div className="p-4 rounded-2xl bg-indigo-50 border border-indigo-200 flex items-start gap-3 shadow-card">
        <Scale className="w-5 h-5 text-indigo-600 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <div className="text-xs font-bold text-indigo-800 uppercase tracking-wider">
            Standing Evaluation Mandate (Phase 9.7)
          </div>
          <p className="text-xs text-slate-600 leading-relaxed font-sans">
            {caveat ||
              'A standing measurement, not a fairness audit: a skewed distribution here is a prompt for clinical/statistical review, not evidence of bias by itself.'}
          </p>
        </div>
      </div>

      {/* 2. Key Metrics Summary Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <MetricCard
          label="Monitored Cases"
          value={total_cases}
          sublabel={`${total_decisions} Clinician Decisions`}
          icon={<Users className="w-4 h-4" />}
        />

        <MetricCard
          label="Override Rate"
          value={`${overridePercent}%`}
          sublabel="Total Escalate + De-escalate"
          icon={<GitCommit className="w-4 h-4" />}
          tone="amber"
          active
        />

        <MetricCard
          label="De-escalation Rate"
          value={`${deEscalatePercent}%`}
          sublabel="Asymmetric Friction Gated"
          icon={<ShieldCheck className="w-4 h-4" />}
          tone="orange"
          active
        />

        <MetricCard
          label="Flagged Reviews"
          value={flagged_for_review_count}
          sublabel="De-escalations Pending Audit"
          icon={<AlertTriangle className="w-4 h-4" />}
          tone="rose"
          active={flagged_for_review_count > 0}
        />
      </div>

      {/* 3. Demographic Subgroup Breakdowns (Age Band & Sex) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <DisparateImpactChart title="Equity Monitoring: Age Demographic Bands" subgroups={by_age_band} />
        <DisparateImpactChart title="Equity Monitoring: Sex Disparity Breakdown" subgroups={by_sex} />
      </div>
    </div>
  );
};
