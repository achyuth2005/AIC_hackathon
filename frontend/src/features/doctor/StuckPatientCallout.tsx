import React from 'react';
import { AlertCircle, ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';

export interface StuckPatientCalloutProps {
  stuckFlagged: boolean;
  stuckReasons?: string[];
  caseId?: string;
}

export const StuckPatientCallout: React.FC<StuckPatientCalloutProps> = ({
  stuckFlagged,
  stuckReasons = [],
  caseId,
}) => {
  if (!stuckFlagged) return null;

  const formatReason = (reason: string) => {
    return reason
      .replace(/_/g, ' ')
      .toLowerCase()
      .replace(/\b\w/g, (c) => c.toUpperCase());
  };

  return (
    <div
      role="alert"
      className="p-4 rounded-xl bg-rose-950/40 border-2 border-rose-600 text-rose-100 space-y-2 text-left animate-fade-in shadow-lg"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <AlertCircle className="w-5 h-5 text-rose-400 shrink-0" />
          <h3 className="font-extrabold text-sm text-rose-200 uppercase tracking-wide">
            Operationally Stuck Patient Detected
          </h3>
        </div>
        <span className="text-[10px] font-mono font-bold bg-rose-900 text-rose-200 px-2 py-0.5 rounded border border-rose-700">
          Flow Bottleneck
        </span>
      </div>

      <p className="text-xs text-rose-200 leading-relaxed">
        This patient's clinical progression has exceeded operational dwell thresholds without advancing to the next stage of care.
      </p>

      {stuckReasons && stuckReasons.length > 0 && (
        <div className="space-y-1 pt-1">
          <div className="text-[11px] font-semibold text-rose-300">Identified Bottlenecks:</div>
          <div className="flex flex-wrap gap-1.5">
            {stuckReasons.map((r, idx) => (
              <span
                key={idx}
                className="px-2 py-0.5 rounded bg-rose-900/60 border border-rose-700/60 text-[11px] font-mono text-white"
              >
                {formatReason(r)}
              </span>
            ))}
          </div>
        </div>
      )}

      {caseId && (
        <div className="pt-2 flex justify-end">
          <Link
            to={`/cases/${caseId}`}
            className="inline-flex items-center gap-1 text-xs text-rose-300 hover:text-white font-semibold underline"
          >
            Open Full Case Workspace
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      )}
    </div>
  );
};
