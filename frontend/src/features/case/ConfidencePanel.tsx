import React from 'react';
import { ConfidenceBand } from '../../types/enums';
import { ConfidenceBadge } from '../../components/clinical/ConfidenceBadge';
import { ShieldCheck, ShieldAlert, AlertTriangle, CheckCircle2 } from 'lucide-react';

export interface ConfidencePanelProps {
  confidenceBand: ConfidenceBand | null | undefined;
  confidenceReasons: string[];
  shouldAbstain: boolean;
  abstentionMessage: string | null | undefined;
}

export const ConfidencePanel: React.FC<ConfidencePanelProps> = ({
  confidenceBand,
  confidenceReasons,
  shouldAbstain,
  abstentionMessage,
}) => {
  return (
    <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-3 text-left">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {shouldAbstain ? (
            <ShieldAlert className="w-5 h-5 text-amber-400" />
          ) : confidenceBand === 'HIGH' ? (
            <ShieldCheck className="w-5 h-5 text-emerald-400" />
          ) : (
            <ShieldAlert className="w-5 h-5 text-rose-400" />
          )}
          <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
            Clinical Confidence & Abstention Engine
          </span>
        </div>
        <ConfidenceBadge band={confidenceBand} shouldAbstain={shouldAbstain} />
      </div>

      {/* Abstention Callout */}
      {shouldAbstain && (
        <div className="p-3 rounded-xl bg-amber-950/50 border border-amber-600/60 text-xs text-amber-200 flex items-start gap-2.5">
          <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
          <div>
            <div className="font-bold text-amber-300">Confidence Engine Abstaining:</div>
            <div className="mt-0.5 leading-relaxed">
              {abstentionMessage ||
                'Missing or low-reliability data prevents high confidence. The system is holding the patient at a safer clinical acuity level.'}
            </div>
          </div>
        </div>
      )}

      {/* Plain Language Confidence Reasons */}
      {confidenceReasons && confidenceReasons.length > 0 && (
        <div className="space-y-1.5 pt-1">
          <div className="text-[11px] font-semibold text-slate-400">Clinical Signals:</div>
          <ul className="space-y-1">
            {confidenceReasons.map((reason, idx) => (
              <li
                key={idx}
                className="text-xs text-slate-300 flex items-start gap-2 bg-slate-950/40 px-2.5 py-1.5 rounded-lg border border-slate-800/80"
              >
                <CheckCircle2 className="w-3.5 h-3.5 text-cyan-400 shrink-0 mt-0.5" />
                <span className="leading-snug">{reason}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};
