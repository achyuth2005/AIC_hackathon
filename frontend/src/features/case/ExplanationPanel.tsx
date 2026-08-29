import React from 'react';
import { useExplanation } from '../../hooks/useExplanation';
import { Sparkles, FileText, AlertTriangle, ShieldCheck } from 'lucide-react';
import { Skeleton } from '../../components/ui/Skeleton';

export interface ExplanationPanelProps {
  caseId: string;
}

export const ExplanationPanel: React.FC<ExplanationPanelProps> = ({ caseId }) => {
  const { data: explanation, isLoading, isError } = useExplanation(caseId);

  if (isLoading) {
    return (
      <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
        <Skeleton className="h-4 w-1/4" />
        <Skeleton className="h-12 w-full" />
      </div>
    );
  }

  if (isError || !explanation) {
    return null;
  }

  const { text, fallback_used, grounded, fallback_reason } = explanation;

  return (
    <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-2.5 text-left animate-fade-in">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {fallback_used ? (
            <FileText className="w-4 h-4 text-cyan-400" />
          ) : (
            <Sparkles className="w-4 h-4 text-indigo-400" />
          )}
          <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
            {fallback_used ? 'Rule-Based Clinical Explanation' : 'LLM Triage Synthesis'}
          </span>
        </div>

        <div className="flex items-center gap-2">
          {fallback_used ? (
            <span className="text-[10px] font-mono text-slate-400 px-2 py-0.5 rounded bg-slate-800 border border-slate-700">
              Deterministic Fallback ({fallback_reason || 'OFFLINE'})
            </span>
          ) : (
            <span className="text-[10px] font-mono text-indigo-300 px-2 py-0.5 rounded bg-indigo-950 border border-indigo-700/60 flex items-center gap-1">
              <ShieldCheck className="w-3 h-3 text-indigo-400" />
              Grounded AI
            </span>
          )}
        </div>
      </div>

      <p className="text-xs text-slate-200 leading-relaxed font-sans bg-slate-950/40 p-3 rounded-lg border border-slate-800">
        {text}
      </p>

      {!grounded && (
        <div className="flex items-center gap-1.5 text-[11px] text-amber-400 font-mono">
          <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
          <span>Clinical note: Unverified against current physiological observations.</span>
        </div>
      )}
    </div>
  );
};
