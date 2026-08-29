import React from 'react';
import { ConfidenceBand } from '../../types/enums';
import { cn } from '../../lib/cn';
import { ShieldCheck, ShieldAlert, Shield } from 'lucide-react';

export interface ConfidenceBadgeProps {
  band: ConfidenceBand | null | undefined;
  shouldAbstain?: boolean;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export const ConfidenceBadge: React.FC<ConfidenceBadgeProps> = ({
  band,
  shouldAbstain = false,
  size = 'md',
  className,
}) => {
  if (shouldAbstain) {
    return (
      <span
        role="status"
        aria-label="Clinical confidence: Abstaining due to missing or conflicting data"
        className={cn(
          'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-950/80 text-amber-300 border border-amber-600/60 font-mono tracking-tight',
          size === 'sm' ? 'px-2 py-0.5 text-[11px]' : '',
          size === 'lg' ? 'px-3.5 py-1.5 text-sm' : '',
          className
        )}
      >
        <ShieldAlert className="w-3.5 h-3.5 text-amber-400 shrink-0" />
        <span>ABSTAINING (FLOORED)</span>
      </span>
    );
  }

  const bandConfig = {
    HIGH: {
      label: 'HIGH CONFIDENCE',
      classes: 'bg-emerald-950/70 text-emerald-300 border-emerald-600/50',
      icon: <ShieldCheck className="w-3.5 h-3.5 text-emerald-400 shrink-0" />,
    },
    MEDIUM: {
      label: 'MED CONFIDENCE',
      classes: 'bg-amber-950/70 text-amber-300 border-amber-600/50',
      icon: <Shield className="w-3.5 h-3.5 text-amber-400 shrink-0" />,
    },
    LOW: {
      label: 'LOW CONFIDENCE',
      classes: 'bg-rose-950/70 text-rose-300 border-rose-600/50',
      icon: <ShieldAlert className="w-3.5 h-3.5 text-rose-400 shrink-0" />,
    },
  };

  const current = band && band in bandConfig ? bandConfig[band] : null;

  if (!current) {
    return (
      <span
        className={cn(
          'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-slate-800 text-slate-400 border border-slate-700',
          className
        )}
      >
        <Shield className="w-3.5 h-3.5 text-slate-500 shrink-0" />
        <span>NO CONFIDENCE BAND</span>
      </span>
    );
  }

  return (
    <span
      role="status"
      aria-label={`Clinical confidence: ${current.label}`}
      className={cn(
        'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border font-mono tracking-tight select-none',
        current.classes,
        size === 'sm' ? 'px-2 py-0.5 text-[10px]' : '',
        size === 'lg' ? 'px-3.5 py-1.5 text-sm' : '',
        className
      )}
    >
      {current.icon}
      <span>{current.label}</span>
    </span>
  );
};
