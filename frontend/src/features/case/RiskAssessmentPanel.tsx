import React, { useState } from 'react';
import { RiskAssessmentResponse } from '../../types/api';
import { AcuityBadge } from '../../components/clinical/AcuityBadge';
import { ComponentBreakdownTable } from './ComponentBreakdownTable';
import { ConfidencePanel } from './ConfidencePanel';
import { DECIDING_LAYER_LABELS } from '../../lib/enums';
import { formatClock, formatRelative } from '../../lib/datetime';
import {
  ChevronDown,
  ChevronUp,
  Cpu,
  Zap,
  Activity,
} from 'lucide-react';

export interface RiskAssessmentPanelProps {
  assessment: RiskAssessmentResponse | null | undefined;
  isBypassActive?: boolean;
}

export const RiskAssessmentPanel: React.FC<RiskAssessmentPanelProps> = ({
  assessment,
  isBypassActive = false,
}) => {
  const [showTechnicalDetails, setShowTechnicalDetails] = useState(false);

  if (!assessment) {
    return (
      <div className="p-6 rounded-2xl bg-white border border-slate-200/80 shadow-card text-center space-y-2">
        <Activity className="w-8 h-8 text-slate-300 mx-auto animate-pulse" />
        <h3 className="text-sm font-semibold text-slate-700">
          No Risk Assessment Computed Yet
        </h3>
        <p className="text-xs text-slate-500 max-w-sm mx-auto">
          Enter physiological vitals to trigger the deterministic NEWS2/PEWS scoring pipeline.
        </p>
      </div>
    );
  }

  const {
    final_acuity,
    deciding_layer,
    rule_acuity,
    ml_suggested_acuity,
    ml_probability,
    confidence_band,
    confidence_score,
    confidence_reasons,
    should_abstain,
    abstention_message,
    hard_triggers_fired,
    rule_component_breakdown,
    computed_at,
    rule_engine_version,
  } = assessment;

  // ML Refusal Min() Invariant Moment (Demo scenario #20)
  const isMlRefused =
    ml_suggested_acuity != null &&
    ml_suggested_acuity > final_acuity &&
    deciding_layer === 'RULES';

  return (
    <div className="space-y-6">
      {/* Hero Acuity & Deciding Layer Header */}
      <div className="p-6 rounded-2xl bg-white border border-slate-200/80 shadow-card-lg space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-1">
              Active Authoritative Acuity
            </div>
            <div className="flex items-center gap-3">
              <AcuityBadge
                acuity={final_acuity}
                size="hero"
                isBypass={isBypassActive}
              />
            </div>
          </div>

          <div className="sm:text-right space-y-1 font-mono text-xs text-slate-500">
            <div className="flex sm:justify-end items-center gap-1.5">
              <span className="text-slate-500">Deciding Layer:</span>
              <span className="font-bold text-indigo-700 px-2 py-0.5 rounded bg-indigo-50 border border-indigo-200">
                {DECIDING_LAYER_LABELS[deciding_layer] || deciding_layer}
              </span>
            </div>
            <div>Scored: {formatRelative(computed_at)} ({formatClock(computed_at, true)})</div>
            <div className="text-[10px] text-slate-400">{rule_engine_version}</div>
          </div>
        </div>

        {/* ML Refusal / Min() Invariant Callout */}
        {isMlRefused && (
          <div
            role="alert"
            className="p-4 rounded-xl bg-indigo-50 border-2 border-indigo-300 text-indigo-900 flex items-start gap-3 shadow-card animate-fade-in"
          >
            <Cpu className="w-5 h-5 text-indigo-600 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <div className="font-extrabold text-sm text-indigo-900">
                ML Challenger De-escalation Blocked (Phase 13 Invariant)
              </div>
              <p className="text-xs text-indigo-800 leading-relaxed">
                The ML model suggested a lower urgency level (<strong className="text-slate-900">ESI {ml_suggested_acuity}</strong>), but the governing <code className="bg-white/80 border border-indigo-200 px-1 py-0.5 rounded">min(rules, ml)</code> invariant refused the de-escalation and held the patient at <strong className="text-slate-900">ESI {final_acuity}</strong>.
              </p>
            </div>
          </div>
        )}

        {/* Hard Triggers Fired Banner */}
        {hard_triggers_fired && hard_triggers_fired.length > 0 && (
          <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-300 text-rose-900 space-y-2">
            <div className="flex items-center gap-2 font-bold text-xs text-rose-700 uppercase tracking-wider">
              <Zap className="w-4 h-4 text-rose-600" />
              Layer 4 Hard Triggers Engaged
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {hard_triggers_fired.map((trig) => (
                <div
                  key={trig.trigger_id}
                  className="p-2 rounded-lg bg-rose-100/60 border border-rose-200 text-xs font-mono flex items-center justify-between"
                >
                  <span>{trig.label}</span>
                  <span className="font-bold text-rose-900">Target ESI {trig.target_esi_level}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Technical Detail Collapsible Disclosure */}
        <div className="pt-2 border-t border-slate-200">
          <button
            type="button"
            onClick={() => setShowTechnicalDetails(!showTechnicalDetails)}
            className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-900 transition-colors font-mono cursor-pointer"
          >
            {showTechnicalDetails ? (
              <ChevronUp className="w-4 h-4 text-slate-400" />
            ) : (
              <ChevronDown className="w-4 h-4 text-slate-400" />
            )}
            <span>
              {showTechnicalDetails
                ? 'Hide Technical Model Scores'
                : 'View Technical Model Scores & ML Probabilities (Secondary Details)'}
            </span>
          </button>

          {showTechnicalDetails && (
            <div className="mt-3 p-3 rounded-xl bg-slate-50 border border-slate-200/80 text-xs font-mono grid grid-cols-2 sm:grid-cols-4 gap-3 text-left animate-fade-in">
              <div>
                <span className="text-slate-500 block text-[10px]">Rule Acuity:</span>
                <span className="font-bold text-slate-900">ESI {rule_acuity}</span>
              </div>
              <div>
                <span className="text-slate-500 block text-[10px]">ML Suggested:</span>
                <span className="font-bold text-slate-900">
                  {ml_suggested_acuity != null ? `ESI ${ml_suggested_acuity}` : 'N/A'}
                </span>
              </div>
              <div>
                <span className="text-slate-500 block text-[10px]">ML Prob (Raw):</span>
                <span className="font-bold text-slate-900">
                  {ml_probability != null ? (ml_probability * 100).toFixed(1) + '%' : 'N/A'}
                </span>
              </div>
              <div>
                <span className="text-slate-500 block text-[10px]">Confidence Score:</span>
                <span className="font-bold text-slate-900">{confidence_score}/100</span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Component Breakdown Table & Confidence Panel */}
      <div className="grid grid-cols-1 gap-6">
        <ComponentBreakdownTable components={rule_component_breakdown || []} />
        <ConfidencePanel
          confidenceBand={confidence_band}
          confidenceReasons={confidence_reasons || []}
          shouldAbstain={should_abstain}
          abstentionMessage={abstention_message}
        />
      </div>
    </div>
  );
};
