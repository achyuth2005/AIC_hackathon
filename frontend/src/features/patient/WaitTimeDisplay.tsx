import React from 'react';
import { WaitTimeEstimate } from '../../types/api';
import { Clock, Users, Info } from 'lucide-react';

export interface WaitTimeDisplayProps {
  estimate: WaitTimeEstimate | null | undefined;
}

export const WaitTimeDisplay: React.FC<WaitTimeDisplayProps> = ({ estimate }) => {
  if (!estimate) {
    return (
      <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 text-left space-y-2">
        <div className="flex items-center gap-2 text-slate-400 text-xs font-bold uppercase tracking-wider">
          <Clock className="w-4 h-4 text-cyan-400" />
          <span>Estimated Wait Time</span>
        </div>
        <div className="text-xl font-bold text-slate-300">
          Being assessed by triage team
        </div>
        <p className="text-xs text-slate-400">
          Your initial clinical assessment is in progress. Wait times will populate once initial vitals are recorded.
        </p>
      </div>
    );
  }

  const { lower_minutes, upper_minutes, patients_ahead, caveat } = estimate;

  return (
    <div className="p-6 rounded-2xl bg-gradient-to-br from-slate-900 via-slate-900 to-slate-950 border border-slate-800 text-left space-y-5 shadow-xl">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-slate-400 text-xs font-bold uppercase tracking-wider">
          <Clock className="w-4 h-4 text-cyan-400" />
          <span>Estimated Time Until Doctor Evaluation</span>
        </div>

        {patients_ahead != null && (
          <span className="px-3 py-1 rounded-full text-xs font-mono font-bold bg-slate-800 text-slate-300 border border-slate-700 flex items-center gap-1.5">
            <Users className="w-3.5 h-3.5 text-cyan-400" />
            <span>{patients_ahead} {patients_ahead === 1 ? 'Patient' : 'Patients'} Ahead</span>
          </span>
        )}
      </div>

      <div className="flex items-baseline gap-3">
        <span className="text-4xl sm:text-5xl font-black font-mono text-white tracking-tight">
          {lower_minutes} – {upper_minutes}
        </span>
        <span className="text-sm sm:text-base font-bold text-slate-400 font-mono uppercase">
          Minutes Estimated
        </span>
      </div>

      {caveat && (
        <div className="p-3 rounded-xl bg-slate-950/80 border border-slate-800/80 text-xs text-slate-400 flex items-start gap-2.5 leading-relaxed">
          <Info className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
          <span>{caveat}</span>
        </div>
      )}
    </div>
  );
};
