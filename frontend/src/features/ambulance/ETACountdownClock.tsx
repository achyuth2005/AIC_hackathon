import React from 'react';
import { ETARange } from '../../types/api';
import { Clock, AlertTriangle, CheckCircle2 } from 'lucide-react';

export interface ETACountdownClockProps {
  etaRange: ETARange | null | undefined;
}

export const ETACountdownClock: React.FC<ETACountdownClockProps> = ({ etaRange }) => {
  if (!etaRange) {
    return (
      <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 text-xs font-mono text-slate-500 text-center">
        No active transport tracking clock for this case.
      </div>
    );
  }

  const { lower_minutes, upper_minutes, arrived, delayed_additional_minutes, caveat } = etaRange;

  if (arrived) {
    return (
      <div className="p-4 rounded-xl bg-emerald-950/50 border border-emerald-600/60 text-emerald-200 flex items-center gap-3">
        <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
        <div>
          <div className="font-bold text-xs uppercase tracking-wider text-emerald-300">
            Patient Arrived at Hospital
          </div>
          <div className="text-xs text-slate-300 font-mono mt-0.5">
            Pre-arrival tracking completed. Case active in emergency department.
          </div>
        </div>
      </div>
    );
  }

  const isDelayed = delayed_additional_minutes > 0;

  return (
    <div
      className={`p-5 rounded-2xl border text-left space-y-3 shadow-lg ${
        isDelayed
          ? 'bg-amber-950/40 border-amber-600/80'
          : 'bg-slate-950/80 border-cyan-800/60'
      }`}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Clock className={`w-5 h-5 ${isDelayed ? 'text-amber-400' : 'text-cyan-400'} animate-pulse`} />
          <span className="text-xs font-bold text-slate-200 uppercase tracking-wider">
            Simulated Inbound ETA Range
          </span>
        </div>

        {isDelayed && (
          <span className="text-[10px] font-mono font-bold bg-amber-950 text-amber-300 px-2 py-0.5 rounded border border-amber-700/80 flex items-center gap-1">
            <AlertTriangle className="w-3 h-3 text-amber-400" />
            +{delayed_additional_minutes}m Delayed
          </span>
        )}
      </div>

      <div className="flex items-baseline gap-3">
        <span className="text-3xl font-black font-mono text-white tracking-tight">
          {lower_minutes} – {upper_minutes}
        </span>
        <span className="text-sm font-bold text-slate-400 font-mono uppercase">
          Minutes to Arrival
        </span>
      </div>

      {caveat && (
        <div className="text-[11px] text-slate-400 font-mono border-t border-slate-800/80 pt-2 leading-relaxed">
          {caveat}
        </div>
      )}
    </div>
  );
};
