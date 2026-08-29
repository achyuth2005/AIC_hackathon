import React from 'react';
import { WaitTimeEstimate } from '../../types/api';
import { cn } from '../../lib/cn';
import { Clock, Info, Users } from 'lucide-react';
import { formatMinutes } from '../../lib/datetime';

export interface WaitTimeRangeProps {
  estimate: WaitTimeEstimate | null | undefined;
  compact?: boolean;
  className?: string;
}

export const WaitTimeRange: React.FC<WaitTimeRangeProps> = ({
  estimate,
  compact = false,
  className,
}) => {
  if (!estimate) {
    return (
      <div className={cn('text-xs text-slate-500 font-mono italic', className)}>
        Wait estimate calculating...
      </div>
    );
  }

  const { lower_minutes, upper_minutes, patients_ahead, caveat } = estimate;
  const rangeStr = `${formatMinutes(lower_minutes)} – ${formatMinutes(upper_minutes)}`;

  if (compact) {
    return (
      <div className={cn('flex items-center gap-2', className)}>
        <span className="inline-flex items-center gap-1 text-xs font-mono font-bold text-slate-200 bg-slate-800/80 px-2 py-0.5 rounded border border-slate-700">
          <Clock className="w-3 h-3 text-cyan-400" />
          {rangeStr}
        </span>
        {patients_ahead != null && (
          <span className="text-[11px] text-slate-400 font-mono">
            ({patients_ahead} ahead)
          </span>
        )}
      </div>
    );
  }

  return (
    <div
      className={cn(
        'p-3.5 rounded-xl bg-slate-900/80 border border-slate-800 space-y-2 text-left',
        className
      )}
    >
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-slate-400 text-xs font-semibold uppercase tracking-wider">
          <Clock className="w-3.5 h-3.5 text-cyan-400" />
          <span>Estimated Wait Range</span>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-slate-300 font-mono">
          <Users className="w-3.5 h-3.5 text-slate-400" />
          <span>{patients_ahead} ahead</span>
        </div>
      </div>

      <div className="text-xl font-bold font-mono text-cyan-300 tracking-tight">
        {rangeStr}
      </div>

      {caveat && (
        <div className="flex items-start gap-1.5 text-[11px] text-amber-300/80 bg-amber-950/30 p-2 rounded-lg border border-amber-800/30 leading-normal">
          <Info className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
          <span>{caveat}</span>
        </div>
      )}
    </div>
  );
};
