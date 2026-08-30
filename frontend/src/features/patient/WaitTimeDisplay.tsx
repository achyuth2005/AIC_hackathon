import React from 'react';
import { WaitTimeEstimate } from '../../types/api';
import { Clock, Users, Info } from 'lucide-react';

export interface WaitTimeDisplayProps {
  estimate: WaitTimeEstimate | null | undefined;
}

export const WaitTimeDisplay: React.FC<WaitTimeDisplayProps> = ({ estimate }) => {
  if (!estimate) {
    return (
      <div className="p-6 rounded-2xl bg-white border border-slate-200/80 text-left space-y-2 shadow-card">
        <div className="flex items-center gap-2 text-slate-500 text-xs font-bold uppercase tracking-wider">
          <Clock className="w-4 h-4 text-emerald-600" />
          <span>Estimated Wait Time</span>
        </div>
        <div className="text-xl font-bold text-slate-700">
          Being assessed by triage team
        </div>
        <p className="text-xs text-slate-500">
          Your initial clinical assessment is in progress. Wait times will populate once initial vitals are recorded.
        </p>
      </div>
    );
  }

  const { lower_minutes, upper_minutes, patients_ahead, caveat } = estimate;

  return (
    <div className="p-6 rounded-2xl bg-white border border-slate-200/80 text-left space-y-5 shadow-card">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-slate-500 text-xs font-bold uppercase tracking-wider">
          <Clock className="w-4 h-4 text-emerald-600" />
          <span>Estimated Time Until Doctor Evaluation</span>
        </div>

        {patients_ahead != null && (
          <span className="px-3 py-1 rounded-full text-xs font-mono font-bold bg-slate-50 text-slate-600 border border-slate-200 flex items-center gap-1.5">
            <Users className="w-3.5 h-3.5 text-emerald-600" />
            <span>{patients_ahead} {patients_ahead === 1 ? 'Patient' : 'Patients'} Ahead</span>
          </span>
        )}
      </div>

      <div className="flex items-baseline gap-3">
        <span className="text-4xl sm:text-5xl font-black font-mono text-slate-900 tracking-tight tabular-nums">
          {lower_minutes} – {upper_minutes}
        </span>
        <span className="text-sm sm:text-base font-bold text-slate-500 font-mono uppercase">
          Minutes Estimated
        </span>
      </div>

      {caveat && (
        <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-500 flex items-start gap-2.5 leading-relaxed">
          <Info className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
          <span>{caveat}</span>
        </div>
      )}
    </div>
  );
};
