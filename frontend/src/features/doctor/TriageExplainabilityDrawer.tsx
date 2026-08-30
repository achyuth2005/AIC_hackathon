import React, { useEffect, useState } from 'react';
import { cn } from '../../lib/cn';
import { formatRelative } from '../../lib/datetime';
import { useDoctorCaseFull } from '../../hooks/useDoctorCaseFull';
import { useExplanation } from '../../hooks/useExplanation';
import { AcuityBadge } from '../../components/clinical/AcuityBadge';
import { Skeleton } from '../../components/ui/Skeleton';
import { ErrorState } from '../../components/ui/ErrorState';
import { ComponentBreakdownTable } from '../case/ComponentBreakdownTable';
import { ExplanationPanel } from '../case/ExplanationPanel';
import {
  X,
  Sparkles,
  Cpu,
  ScrollText,
  ShieldCheck,
  Gauge,
  History,
  CircleDot,
} from 'lucide-react';
import { DecidingLayer } from '../../types/enums';

export interface TriageExplainabilityDrawerProps {
  caseId: string | null;
  onClose: () => void;
}

const DECIDING_LAYER_STYLES: Record<DecidingLayer, string> = {
  RULES: 'bg-slate-100 text-slate-700 border-slate-200',
  ML: 'bg-indigo-50 text-indigo-700 border-indigo-200',
  OVERRIDE: 'bg-orange-50 text-orange-700 border-orange-200',
  ABSTENTION: 'bg-amber-50 text-amber-800 border-amber-200',
};

const LayerHeader: React.FC<{ n: number; title: string; subtitle: string; icon: React.ReactNode }> = ({
  n,
  title,
  subtitle,
  icon,
}) => (
  <div className="flex items-start gap-3">
    <span className="flex items-center justify-center w-6 h-6 rounded-full bg-slate-900 text-white text-[11px] font-bold font-mono shrink-0 mt-0.5">
      {n}
    </span>
    <div className="min-w-0">
      <h3 className="text-sm font-semibold text-slate-900 flex items-center gap-1.5">
        {icon}
        {title}
      </h3>
      <p className="text-[11px] text-slate-500 mt-0.5">{subtitle}</p>
    </div>
  </div>
);

export const TriageExplainabilityDrawer: React.FC<TriageExplainabilityDrawerProps> = ({
  caseId,
  onClose,
}) => {
  const isOpen = caseId != null;

  // Keep rendering the last non-null case id while the panel animates closed, so the
  // slide-out transition doesn't flash empty/loading content.
  const [activeCaseId, setActiveCaseId] = useState<string | null>(null);
  useEffect(() => {
    if (caseId != null) setActiveCaseId(caseId);
  }, [caseId]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    }
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, onClose]);

  const { data, isLoading, isError, error, refetch } = useDoctorCaseFull(activeCaseId);
  useExplanation(activeCaseId ?? undefined);

  const assessment = data?.latest_risk_assessment ?? null;

  return (
    <>
      {/* Backdrop */}
      <div
        className={cn(
          'fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-40 transition-opacity duration-200',
          isOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'
        )}
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Panel */}
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Triage Explainability"
        aria-hidden={!isOpen}
        className={cn(
          'fixed inset-y-0 right-0 z-50 w-full max-w-md lg:max-w-lg bg-white shadow-2xl border-l border-slate-200',
          'flex flex-col h-full transition-transform duration-300 ease-out',
          isOpen ? 'translate-x-0' : 'translate-x-full pointer-events-none'
        )}
      >
        {/* Header */}
        <div className="px-5 py-4 border-b border-slate-100 flex items-start justify-between gap-4 shrink-0">
          <div className="min-w-0">
            <h2 className="text-base font-semibold text-slate-900 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-indigo-600" />
              Triage Explainability
            </h2>
            <p className="text-xs text-slate-500 mt-0.5 truncate">
              {data?.display_name || 'Anonymous Walk-in'}
              {activeCaseId && (
                <span className="font-mono text-slate-400"> &middot; {activeCaseId.slice(0, 8)}</span>
              )}
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 p-1.5 rounded-lg hover:bg-slate-100 transition-colors shrink-0"
            aria-label="Close explainability drawer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-5 py-5 space-y-6">
          {isLoading ? (
            <div className="space-y-3">
              <Skeleton className="h-5 w-1/3" />
              <Skeleton className="h-24 w-full" />
              <Skeleton className="h-5 w-1/3" />
              <Skeleton className="h-24 w-full" />
            </div>
          ) : isError || !data ? (
            <ErrorState
              title="Failed to load triage explainability"
              error={error}
              onRetry={() => refetch()}
            />
          ) : (
            <>
              {/* Layer 1 — Deterministic Scoring */}
              <section className="space-y-3">
                <LayerHeader
                  n={1}
                  title="Deterministic Scoring"
                  subtitle="NEWS2 / PEWS rule-engine component breakdown."
                  icon={<Gauge className="w-3.5 h-3.5 text-slate-500" />}
                />
                {assessment ? (
                  <div className="pl-9 space-y-3">
                    <div className="flex items-center gap-2">
                      <span className="text-[11px] font-medium text-slate-500 uppercase tracking-wider">
                        Rule Acuity
                      </span>
                      <AcuityBadge acuity={assessment.rule_acuity} size="sm" />
                    </div>
                    <ComponentBreakdownTable components={assessment.rule_component_breakdown} />
                  </div>
                ) : (
                  <div className="pl-9 p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-500 italic">
                    No risk assessment has been computed for this case yet.
                  </div>
                )}
              </section>

              <div className="border-t border-slate-100" />

              {/* Layer 2 — ML Challenger */}
              <section className="space-y-3">
                <LayerHeader
                  n={2}
                  title="ML Challenger"
                  subtitle="Machine-learning second opinion layered over the deterministic score."
                  icon={<Cpu className="w-3.5 h-3.5 text-slate-500" />}
                />
                {assessment && assessment.ml_model_version ? (
                  <div className="pl-9 space-y-3">
                    <div className="grid grid-cols-2 gap-3 text-xs">
                      <div className="p-3 rounded-xl bg-white border border-slate-200/80 shadow-[0_1px_3px_rgba(0,0,0,0.05),0_1px_2px_rgba(0,0,0,0.02)]">
                        <div className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
                          Model Version
                        </div>
                        <div className="font-mono font-semibold text-slate-800 mt-0.5">
                          {assessment.ml_model_version}
                        </div>
                      </div>
                      <div className="p-3 rounded-xl bg-white border border-slate-200/80 shadow-[0_1px_3px_rgba(0,0,0,0.05),0_1px_2px_rgba(0,0,0,0.02)]">
                        <div className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
                          ML Probability
                        </div>
                        <div className="font-mono font-semibold text-slate-800 mt-0.5 tabular-nums">
                          {assessment.ml_probability != null
                            ? `${Math.round(assessment.ml_probability * 100)}%`
                            : '--'}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center flex-wrap gap-3">
                      <div className="flex items-center gap-2">
                        <span className="text-[11px] font-medium text-slate-500 uppercase tracking-wider">
                          Suggested
                        </span>
                        <AcuityBadge acuity={assessment.ml_suggested_acuity} size="sm" />
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-[11px] font-medium text-slate-500 uppercase tracking-wider">
                          Deciding Layer
                        </span>
                        <span
                          className={cn(
                            'inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-mono font-semibold border',
                            DECIDING_LAYER_STYLES[assessment.deciding_layer]
                          )}
                        >
                          {assessment.deciding_layer}
                        </span>
                      </div>
                    </div>

                    <div className="flex items-start gap-2 p-3 rounded-lg bg-slate-50 border border-slate-200 text-slate-600 text-xs leading-relaxed">
                      <ShieldCheck className="w-3.5 h-3.5 text-slate-400 shrink-0 mt-0.5" />
                      <span>
                        ML challenger can only agree with the deterministic level or escalate it — the
                        min() invariant guarantees it can never silently downgrade a patient.
                      </span>
                    </div>
                  </div>
                ) : (
                  <div className="pl-9 p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-500 italic">
                    ML challenger did not run for this assessment.
                  </div>
                )}
              </section>

              <div className="border-t border-slate-100" />

              {/* Layer 3 — Evidence Synthesis & What Changed */}
              <section className="space-y-3">
                <LayerHeader
                  n={3}
                  title="Evidence Synthesis & What Changed"
                  subtitle="Narrative synthesis plus what's new since your last review."
                  icon={<ScrollText className="w-3.5 h-3.5 text-slate-500" />}
                />
                <div className="pl-9 space-y-4">
                  {activeCaseId && <ExplanationPanel caseId={activeCaseId} />}

                  <div className="space-y-2">
                    <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                      <History className="w-3.5 h-3.5" />
                      Changed Since Last Review
                    </div>

                    {data.is_first_review ? (
                      <div className="p-3 rounded-lg bg-indigo-50 border border-indigo-200 text-indigo-800 text-xs">
                        First physician review of this case.
                      </div>
                    ) : data.changed_since_last_review.length === 0 ? (
                      <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 text-slate-500 text-xs">
                        No changes since your last review.
                      </div>
                    ) : (
                      <ul className="space-y-1.5">
                        {data.changed_since_last_review.map((evt) => (
                          <li
                            key={evt.event_id}
                            className="flex items-center justify-between gap-3 px-3 py-2 rounded-lg bg-white border border-slate-200/80 text-xs"
                          >
                            <span className="flex items-center gap-2 font-medium text-slate-700 min-w-0">
                              <CircleDot className="w-3 h-3 text-indigo-500 shrink-0" />
                              <span className="truncate">{evt.event_type.replace(/_/g, ' ')}</span>
                            </span>
                            <span className="text-slate-400 font-mono tabular-nums shrink-0">
                              {formatRelative(evt.occurred_at)}
                            </span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                </div>
              </section>
            </>
          )}
        </div>
      </div>
    </>
  );
};
