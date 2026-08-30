import React from 'react';
import { ETARange } from '../../types/api';
import { Clock, AlertTriangle, CheckCircle2 } from 'lucide-react';

export interface ETACountdownClockProps {
  etaRange: ETARange | null | undefined;
}

export const ETACountdownClock: React.FC<ETACountdownClockProps> = ({ etaRange }) => {
  if (!etaRange) {
    return (
      <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs font-mono text-slate-500 text-center">
        No active transport tracking clock for this case.
      </div>
    );
  }

  const { lower_minutes, upper_minutes, arrived, delayed_additional_minutes, caveat } = etaRange;

  if (arrived) {
    return (
      <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-700 flex items-center gap-3">
        <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
        <div>
          <div className="font-bold text-xs uppercase tracking-wider text-emerald-800">
            Patient Arrived at Hospital
          </div>
          <div className="text-xs text-emerald-700/90 font-mono mt-0.5">
            Pre-arrival tracking completed. Case active in emergency department.
          </div>
        </div>
      </div>
    );
  }

  const isDelayed = delayed_additional_minutes > 0;

  return (
    <div
      className={`p-5 rounded-2xl border text-left space-y-3 shadow-card ${
        isDelayed
          ? 'bg-amber-50 border-amber-300 text-amber-800'
          : 'bg-slate-50 border-indigo-200 text-indigo-700'
      }`}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Clock className={`w-5 h-5 ${isDelayed ? 'text-amber-600' : 'text-indigo-600'} animate-pulse`} />
          <span className={`text-xs font-bold uppercase tracking-wider ${isDelayed ? 'text-amber-800' : 'text-slate-700'}`}>
            Simulated Inbound ETA Range
          </span>
        </div>

        {isDelayed && (
          <span className="text-[10px] font-mono font-bold bg-amber-100 text-amber-800 px-2 py-0.5 rounded border border-amber-300 flex items-center gap-1">
            <AlertTriangle className="w-3 h-3 text-amber-600" />
            +{delayed_additional_minutes}m Delayed
          </span>
        )}
      </div>

      <div className="flex items-baseline gap-3">
        <span className={`text-3xl font-black font-mono tabular-nums tracking-tight ${isDelayed ? 'text-amber-900' : 'text-slate-900'}`}>
          {lower_minutes} – {upper_minutes}
        </span>
        <span className={`text-sm font-bold font-mono uppercase ${isDelayed ? 'text-amber-700' : 'text-slate-500'}`}>
          Minutes to Arrival
        </span>
      </div>

      {caveat && (
        <div className={`text-[11px] font-mono border-t pt-2 leading-relaxed ${isDelayed ? 'border-amber-200 text-amber-700' : 'border-slate-200 text-slate-500'}`}>
          {caveat}
        </div>
      )}
    </div>
  );
};
