import React from 'react';
import { useCaseDecisions } from '../../hooks/useCaseDecisions';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';
import { AcuityBadge } from '../../components/clinical/AcuityBadge';
import { formatClock, formatRelative } from '../../lib/datetime';
import { DE_ESCALATION_REASONS } from '../../lib/enums';
import { ShieldAlert, ArrowUpCircle, ArrowDownCircle, CheckCircle2 } from 'lucide-react';

export interface DecisionHistoryListProps {
  caseId: string;
}

export const DecisionHistoryList: React.FC<DecisionHistoryListProps> = ({ caseId }) => {
  const { data: decisions, isLoading, isError } = useCaseDecisions(caseId);

  if (isLoading || isError || !decisions || decisions.length === 0) {
    return null;
  }

  return (
    <Card className="bg-slate-900 border-slate-800 text-left">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm flex items-center justify-between">
          <span className="flex items-center gap-2 text-slate-200">
            <ShieldAlert className="w-4 h-4 text-cyan-400" />
            Clinician Override Audit Records ({decisions.length})
          </span>
          <span className="text-[10px] font-mono text-slate-400">
            Permanent Governance Trail
          </span>
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-3">
        {decisions.map((dec) => {
          const isEscalate = dec.clinician_action === 'ESCALATE';
          const isDeEscalate = dec.clinician_action === 'DE_ESCALATE';

          return (
            <div
              key={dec.decision_id}
              className={`p-4 rounded-xl border space-y-2.5 ${
                dec.flagged_for_review
                  ? 'bg-amber-950/20 border-amber-600/60'
                  : 'bg-slate-950/60 border-slate-800'
              }`}
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  {isEscalate ? (
                    <ArrowUpCircle className="w-4 h-4 text-orange-400 shrink-0" />
                  ) : isDeEscalate ? (
                    <ArrowDownCircle className="w-4 h-4 text-cyan-400 shrink-0" />
                  ) : (
                    <CheckCircle2 className="w-4 h-4 text-slate-400 shrink-0" />
                  )}

                  <span className="font-bold text-xs text-slate-100 uppercase tracking-wider font-mono">
                    {dec.clinician_action}
                  </span>

                  <span className="text-xs text-slate-400 font-mono">
                    (System Rec: ESI {dec.system_recommendation} → Result: ESI {dec.resulting_acuity})
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  {dec.flagged_for_review && (
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-bold font-mono bg-amber-950 text-amber-300 border border-amber-600/70">
                      FLAGGED FOR REVIEW
                    </span>
                  )}
                  <span className="text-[10px] font-mono text-slate-400">
                    {formatRelative(dec.timestamp)} ({formatClock(dec.timestamp, true)})
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-3 text-xs">
                <span className="text-slate-400 font-mono">
                  Clinician: <strong className="text-slate-200">{dec.clinician_id}</strong> ({dec.role})
                </span>
                <span className="text-slate-600">•</span>
                <div className="flex items-center gap-1.5 font-mono">
                  <span className="text-slate-400">Resulting Acuity:</span>
                  <AcuityBadge acuity={dec.resulting_acuity} size="xs" />
                </div>
              </div>

              {dec.reason_code && (
                <div className="text-xs text-slate-300 bg-slate-900/90 p-2.5 rounded-lg border border-slate-800 space-y-1">
                  <div>
                    <span className="font-semibold text-slate-400 text-[11px] block">Structured Reason:</span>
                    <span>{DE_ESCALATION_REASONS[dec.reason_code] || dec.reason_code}</span>
                  </div>
                  {dec.free_text_reason && (
                    <div className="pt-1 border-t border-slate-800/60 text-slate-400 text-[11px] italic">
                      "{dec.free_text_reason}"
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
};
