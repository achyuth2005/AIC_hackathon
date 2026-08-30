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
    <Card className="text-left">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm flex items-center justify-between">
          <span className="flex items-center gap-2 text-slate-900">
            <ShieldAlert className="w-4 h-4 text-indigo-600" />
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
                  ? 'bg-amber-50 border-amber-200'
                  : 'bg-slate-50 border-slate-200/80'
              }`}
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  {isEscalate ? (
                    <ArrowUpCircle className="w-4 h-4 text-amber-600 shrink-0" />
                  ) : isDeEscalate ? (
                    <ArrowDownCircle className="w-4 h-4 text-indigo-600 shrink-0" />
                  ) : (
                    <CheckCircle2 className="w-4 h-4 text-slate-400 shrink-0" />
                  )}

                  <span className="font-bold text-xs text-slate-900 uppercase tracking-wider font-mono">
                    {dec.clinician_action}
                  </span>

                  <span className="text-xs text-slate-500 font-mono">
                    (System Rec: ESI {dec.system_recommendation} → Result: ESI {dec.resulting_acuity})
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  {dec.flagged_for_review && (
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-bold font-mono bg-white text-amber-700 border border-amber-300">
                      FLAGGED FOR REVIEW
                    </span>
                  )}
                  <span className="text-[10px] font-mono text-slate-400">
                    {formatRelative(dec.timestamp)} ({formatClock(dec.timestamp, true)})
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-3 text-xs">
                <span className="text-slate-500 font-mono">
                  Clinician: <strong className="text-slate-700">{dec.clinician_id}</strong> ({dec.role})
                </span>
                <span className="text-slate-300">•</span>
                <div className="flex items-center gap-1.5 font-mono">
                  <span className="text-slate-500">Resulting Acuity:</span>
                  <AcuityBadge acuity={dec.resulting_acuity} size="xs" />
                </div>
              </div>

              {dec.reason_code && (
                <div className="text-xs text-slate-600 bg-white p-2.5 rounded-lg border border-slate-200/80 space-y-1">
                  <div>
                    <span className="font-semibold text-slate-500 text-[11px] block">Structured Reason:</span>
                    <span>{DE_ESCALATION_REASONS[dec.reason_code] || dec.reason_code}</span>
                  </div>
                  {dec.free_text_reason && (
                    <div className="pt-1 border-t border-slate-100 text-slate-500 text-[11px] italic">
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
