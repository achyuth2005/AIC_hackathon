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
      className="p-4 rounded-xl bg-rose-50 border-2 border-rose-200 text-rose-900 space-y-2 text-left animate-fade-in shadow-card"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <AlertCircle className="w-5 h-5 text-rose-600 shrink-0" />
          <h3 className="font-bold text-sm text-rose-900 uppercase tracking-wide">
            Operationally Stuck Patient Detected
          </h3>
        </div>
        <span className="text-[10px] font-mono font-bold bg-rose-600 text-white px-2 py-0.5 rounded border border-rose-700">
          Flow Bottleneck
        </span>
      </div>

      <p className="text-xs text-rose-800 leading-relaxed">
        This patient's clinical progression has exceeded operational dwell thresholds without advancing to the next stage of care.
      </p>

      {stuckReasons && stuckReasons.length > 0 && (
        <div className="space-y-1 pt-1">
          <div className="text-[11px] font-semibold text-rose-700">Identified Bottlenecks:</div>
          <div className="flex flex-wrap gap-1.5">
            {stuckReasons.map((r, idx) => (
              <span
                key={idx}
                className="px-2 py-0.5 rounded bg-white border border-rose-200 text-[11px] font-mono text-rose-800"
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
            className="inline-flex items-center gap-1 text-xs text-rose-700 hover:text-rose-900 font-semibold underline"
          >
            Open Full Case Workspace
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      )}
    </div>
  );
};
