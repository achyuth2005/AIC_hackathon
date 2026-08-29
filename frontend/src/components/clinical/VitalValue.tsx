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
        'p-3 rounded-xl border transition-all flex flex-col justify-between text-left',
        isMissing
          ? 'bg-slate-900/40 border-slate-800/80 opacity-70'
          : isAbnormal || (points != null && points > 0)
          ? 'bg-orange-950/20 border-orange-700/60 text-orange-100'
          : 'bg-slate-900/80 border-slate-800 text-slate-100',
        className
      )}
    >
      <div className="flex items-center justify-between gap-2 text-xs">
        <span className="font-semibold text-slate-300 truncate">{label}</span>
        {observedAt && (
          <div className="flex items-center gap-1 text-[10px] text-slate-400 font-mono">
            <StalenessDot observedAt={observedAt} />
            <span>{formatRelative(observedAt)}</span>
          </div>
        )}
      </div>

      <div className="my-1 flex items-baseline gap-1.5">
        <span className="text-xl font-bold font-mono tracking-tight text-slate-100">
          {displayVal}
        </span>
        {unit && <span className="text-xs text-slate-400 font-mono">{unit}</span>}
      </div>

      <div className="flex items-center justify-between text-[10px] pt-1 border-t border-slate-800/60 mt-1">
        {points !== undefined && (
          <span
            className={cn(
              'font-mono font-bold px-1.5 py-0.2 rounded',
              points == null
                ? 'text-slate-500 bg-slate-800'
                : points > 0
                ? 'text-orange-300 bg-orange-950/80 border border-orange-700/60'
                : 'text-emerald-400 bg-emerald-950/40'
            )}
          >
            {points == null ? 'Not scored' : `${points} pts`}
          </span>
        )}

        {isMissing && missingReason ? (
          <span className="text-amber-400 font-mono text-[9px] truncate">
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
