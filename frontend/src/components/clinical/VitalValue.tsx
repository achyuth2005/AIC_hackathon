import React from 'react';
import { cn } from '../../lib/cn';
import { StalenessDot } from './StalenessDot';
import { formatRelative } from '../../lib/datetime';
import { ReliabilityTier } from '../../types/enums';

export interface VitalValueProps {
  label: string;
  value: number | boolean | string | null | undefined;
  unit?: string | null;
  observedAt?: string | null;
  points?: number | null;
  reliabilityTier?: ReliabilityTier | null;
  isAbnormal?: boolean;
  isMissing?: boolean;
  missingReason?: string | null;
  className?: string;
}

export const VitalValue: React.FC<VitalValueProps> = ({
  label,
  value,
  unit,
  observedAt,
  points,
  reliabilityTier,
  isAbnormal = false,
  isMissing = false,
  missingReason,
  className,
}) => {
  const displayVal =
    value == null
      ? '--'
      : typeof value === 'boolean'
      ? value
        ? 'Yes'
        : 'No'
      : typeof value === 'number'
      ? Number.isInteger(value)
        ? value.toString()
        : value.toFixed(1)
      : String(value);

  const tierLabels = {
    1: 'Tier 1 (Device)',
    2: 'Tier 2 (Clinician)',
    3: 'Tier 3 (Patient)',
    4: 'Tier 4 (AI Inferred)',
  };

  return (
    <div
      className={cn(
        'p-3.5 rounded-2xl border transition-all flex flex-col justify-between text-left',
        isMissing
          ? 'bg-slate-500/5 border-slate-300/20 opacity-70 text-slate-400 backdrop-blur-sm shadow-[inset_0_0_0_1px_rgba(255,255,255,0.7)]'
          : isAbnormal || (points != null && points > 0)
          ? 'bg-orange-500/15 border-orange-300/40 text-orange-950 backdrop-blur-sm shadow-[inset_0_0_0_1px_rgba(255,255,255,0.7),0_4px_16px_rgba(249,115,22,0.06)]'
          : 'bg-white/60 border-white/80 text-slate-900 backdrop-blur-xl shadow-[inset_0_0_0_1px_rgba(255,255,255,0.85),0_8px_32px_rgba(31,38,135,0.04)]',
        className
      )}
    >
      <div className="flex items-center justify-between gap-2 text-xs">
        <span className="font-semibold text-slate-500 truncate">{label}</span>
        {observedAt && (
          <div className="flex items-center gap-1 text-[10px] text-slate-400 font-mono">
            <StalenessDot observedAt={observedAt} />
            <span>{formatRelative(observedAt)}</span>
          </div>
        )}
      </div>

      <div className="my-1 flex items-baseline gap-1.5">
        <span className="text-xl font-bold font-mono tabular-nums tracking-tight text-slate-900">
          {displayVal}
        </span>
        {unit && <span className="text-xs text-slate-400 font-mono">{unit}</span>}
      </div>

      <div className="flex items-center justify-between text-[10px] pt-1.5 border-t border-slate-100/60 mt-1">
        {points !== undefined && (
          <span
            className={cn(
              'font-mono font-bold px-2 py-0.5 rounded-full text-[10px]',
              points == null
                ? 'text-slate-400 bg-slate-500/10'
                : points > 0
                ? 'text-orange-800 bg-orange-500/20 border border-orange-300/40'
                : 'text-emerald-800 bg-emerald-500/20 border border-emerald-300/40'
            )}
          >
            {points == null ? 'Not scored' : `${points} pts`}
          </span>
        )}

        {isMissing && missingReason ? (
          <span className="text-amber-900 font-mono text-[9px] truncate">
            {missingReason}
          </span>
        ) : reliabilityTier ? (
          <span className="text-slate-400 font-mono" title={tierLabels[reliabilityTier]}>
            T{reliabilityTier}
          </span>
        ) : null}
      </div>
    </div>
  );
};
