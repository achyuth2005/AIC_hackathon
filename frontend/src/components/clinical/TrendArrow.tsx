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
      icon: <TrendingUp className="w-3.5 h-3.5 text-orange-600" />,
      textClass: 'text-orange-800 font-semibold',
      bgClass: 'bg-orange-500/15 border-orange-300/40 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.7)] backdrop-blur-sm',
    },
    STABLE: {
      label: 'Stable',
      icon: <Minus className="w-3.5 h-3.5 text-slate-500" />,
      textClass: 'text-slate-700 font-medium',
      bgClass: 'bg-slate-500/10 border-slate-300/30 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.7)] backdrop-blur-sm',
    },
    IMPROVING: {
      label: 'Improving',
      icon: <TrendingDown className="w-3.5 h-3.5 text-emerald-600" />,
      textClass: 'text-emerald-800 font-semibold',
      bgClass: 'bg-emerald-500/15 border-emerald-300/40 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.7)] backdrop-blur-sm',
    },
    UNKNOWN: {
      label: 'Unknown',
      icon: <HelpCircle className="w-3.5 h-3.5 text-slate-400" />,
      textClass: 'text-slate-500',
      bgClass: 'bg-slate-500/10 border-slate-300/30 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.7)] backdrop-blur-sm',
    },
  };

  const current = trend && trend in trendConfig ? trendConfig[trend] : trendConfig.UNKNOWN;

  return (
    <div
      role="status"
      aria-label={`Deterioration trend: ${current.label}`}
      className={cn(
        'inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full border text-xs font-mono select-none',
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
