import React from 'react';
import { OverrideMonitoringReport } from '../../types/api';
import { Card, CardContent } from '../../components/ui/Card';
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
      <div className="p-4 rounded-2xl bg-indigo-950/40 border border-indigo-600/60 flex items-start gap-3 shadow-lg">
        <Scale className="w-5 h-5 text-indigo-400 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <div className="text-xs font-bold text-indigo-200 uppercase tracking-wider">
            Standing Evaluation Mandate (Phase 9.7)
          </div>
          <p className="text-xs text-slate-300 leading-relaxed font-sans">
            {caveat ||
              'A standing measurement, not a fairness audit: a skewed distribution here is a prompt for clinical/statistical review, not evidence of bias by itself.'}
          </p>
        </div>
      </div>

      {/* 2. Key Metrics Summary Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {/* Total Cases & Decisions */}
        <Card className="bg-slate-900 border-slate-800">
          <CardContent className="p-4 space-y-1">
            <div className="flex items-center justify-between text-slate-400">
              <span className="text-[10px] font-bold uppercase tracking-wider">Monitored Cases</span>
              <Users className="w-4 h-4 text-cyan-400" />
            </div>
            <div className="text-2xl font-black font-mono text-slate-100">{total_cases}</div>
            <div className="text-[11px] text-slate-400 font-mono">
              {total_decisions} Clinician Decisions
            </div>
          </CardContent>
        </Card>

        {/* Overall Override Rate */}
        <Card className="bg-slate-900 border-slate-800">
          <CardContent className="p-4 space-y-1">
            <div className="flex items-center justify-between text-slate-400">
              <span className="text-[10px] font-bold uppercase tracking-wider">Override Rate</span>
              <GitCommit className="w-4 h-4 text-amber-400" />
            </div>
            <div className="text-2xl font-black font-mono text-amber-300">{overridePercent}%</div>
            <div className="text-[11px] text-slate-400 font-mono">
              Total Escalate + De-escalate
            </div>
          </CardContent>
        </Card>

        {/* De-escalation Rate */}
        <Card className="bg-slate-900 border-slate-800">
          <CardContent className="p-4 space-y-1">
            <div className="flex items-center justify-between text-slate-400">
              <span className="text-[10px] font-bold uppercase tracking-wider">De-escalation Rate</span>
              <ShieldCheck className="w-4 h-4 text-orange-400" />
            </div>
            <div className="text-2xl font-black font-mono text-orange-300">{deEscalatePercent}%</div>
            <div className="text-[11px] text-slate-400 font-mono">
              Asymmetric Friction Gated
            </div>
          </CardContent>
        </Card>

        {/* Flagged for Retrospective Review */}
        <Card className={`border ${flagged_for_review_count > 0 ? 'bg-rose-950/20 border-rose-600/80' : 'bg-slate-900 border-slate-800'}`}>
          <CardContent className="p-4 space-y-1">
            <div className="flex items-center justify-between text-slate-400">
              <span className="text-[10px] font-bold uppercase tracking-wider">Flagged Reviews</span>
              <AlertTriangle className="w-4 h-4 text-rose-400" />
            </div>
            <div className="text-2xl font-black font-mono text-rose-200">{flagged_for_review_count}</div>
            <div className="text-[11px] text-slate-400 font-mono">
              De-escalations Pending Audit
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 3. Demographic Subgroup Breakdowns (Age Band & Sex) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <DisparateImpactChart title="Equity Monitoring: Age Demographic Bands" subgroups={by_age_band} />
        <DisparateImpactChart title="Equity Monitoring: Sex Disparity Breakdown" subgroups={by_sex} />
      </div>
    </div>
  );
};
