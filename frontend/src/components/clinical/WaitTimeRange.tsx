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
      <div className={cn('text-xs text-slate-400 font-mono italic', className)}>
        Wait estimate calculating...
      </div>
    );
  }

  const { lower_minutes, upper_minutes, patients_ahead, caveat } = estimate;
  const rangeStr = `${formatMinutes(lower_minutes)} – ${formatMinutes(upper_minutes)}`;

  if (compact) {
    return (
      <div className={cn('flex items-center gap-2', className)}>
        <span className="inline-flex items-center gap-1 text-xs font-mono font-bold tabular-nums text-indigo-900 bg-indigo-500/10 px-2 py-0.5 rounded-full border border-indigo-200/40 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.7)]">
          <Clock className="w-3 h-3 text-indigo-600" />
          {rangeStr}
        </span>
        {patients_ahead != null && (
          <span className="text-[11px] text-slate-500 font-mono tabular-nums">
            ({patients_ahead} ahead)
          </span>
        )}
      </div>
    );
  }

  return (
    <div
      className={cn(
        'p-3.5 rounded-2xl bg-white/60 backdrop-blur-xl border border-white/80 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.85),0_8px_32px_rgba(31,38,135,0.04)] space-y-2 text-left',
        className
      )}
    >
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-slate-500 text-xs font-semibold uppercase tracking-wider">
          <Clock className="w-3.5 h-3.5 text-indigo-600" />
          <span>Estimated Wait Range</span>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-slate-600 font-mono tabular-nums">
          <Users className="w-3.5 h-3.5 text-slate-400" />
          <span>{patients_ahead} ahead</span>
        </div>
      </div>

      <div className="text-xl font-bold font-mono tabular-nums text-indigo-700 tracking-tight">
        {rangeStr}
      </div>

      {caveat && (
        <div className="flex items-start gap-1.5 text-[11px] text-amber-900 bg-amber-500/15 p-2 rounded-xl border border-amber-300/40 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.7)] leading-normal">
          <Info className="w-3.5 h-3.5 text-amber-600 shrink-0 mt-0.5" />
          <span>{caveat}</span>
        </div>
      )}
    </div>
  );
};
