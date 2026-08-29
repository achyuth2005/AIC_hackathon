import React from 'react';
import { DeteriorationTrend } from '../../types/enums';
import { cn } from '../../lib/cn';
import { TrendingUp, TrendingDown, Minus, HelpCircle } from 'lucide-react';

export interface TrendArrowProps {
  trend: DeteriorationTrend | null | undefined;
  showLabel?: boolean;
  className?: string;
}

export const TrendArrow: React.FC<TrendArrowProps> = ({
  trend = 'UNKNOWN',
  showLabel = false,
  className,
}) => {
  const trendConfig: Record<
    DeteriorationTrend,
    { label: string; icon: React.ReactNode; textClass: string; bgClass: string }
  > = {
    WORSENING: {
      label: 'Worsening',
      icon: <TrendingUp className="w-4 h-4 text-orange-400" />,
      textClass: 'text-orange-400',
      bgClass: 'bg-orange-950/50 border-orange-700/50',
    },
    STABLE: {
      label: 'Stable',
      icon: <Minus className="w-4 h-4 text-slate-400" />,
      textClass: 'text-slate-300',
      bgClass: 'bg-slate-800/60 border-slate-700/50',
    },
    IMPROVING: {
      label: 'Improving',
      icon: <TrendingDown className="w-4 h-4 text-emerald-400" />,
      textClass: 'text-emerald-400',
      bgClass: 'bg-emerald-950/50 border-emerald-700/50',
    },
    UNKNOWN: {
      label: 'Unknown',
      icon: <HelpCircle className="w-3.5 h-3.5 text-slate-500" />,
      textClass: 'text-slate-500',
      bgClass: 'bg-slate-900 border-slate-800',
    },
  };

  const current = trend && trend in trendConfig ? trendConfig[trend] : trendConfig.UNKNOWN;

  return (
    <div
      role="status"
      aria-label={`Deterioration trend: ${current.label}`}
      className={cn(
        'inline-flex items-center gap-1.5 px-2 py-1 rounded-md border text-xs font-mono select-none',
        current.bgClass,
        current.textClass,
        className
      )}
    >
      {current.icon}
      {showLabel && <span className="font-sans font-medium">{current.label}</span>}
    </div>
  );
};
