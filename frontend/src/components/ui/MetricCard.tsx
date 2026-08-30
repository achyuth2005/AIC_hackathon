import React from 'react';
import { cn } from '../../lib/cn';

export interface MetricCardProps {
  label: string;
  value: React.ReactNode;
  icon?: React.ReactNode;
  /** Semantic tone. Only visually applied when `active` is true — otherwise the card stays a
   * neutral white surface so a strip of metric cards reads calmly until something needs attention. */
  tone?: 'neutral' | 'rose' | 'amber' | 'yellow' | 'emerald' | 'blue' | 'orange' | 'indigo';
  /** Switches the card from a neutral surface to its tinted `tone` state (e.g. an overdue count > 0). */
  active?: boolean;
  sublabel?: string;
  /** Small trailing element, e.g. an EsiBadge or a trend arrow. */
  trailing?: React.ReactNode;
  onClick?: () => void;
  className?: string;
}

const TONE_ACTIVE: Record<NonNullable<MetricCardProps['tone']>, string> = {
  neutral: 'bg-slate-500/10 border-slate-300/30 text-slate-900 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.8),0_8px_32px_rgba(31,38,135,0.04)]',
  rose: 'bg-rose-500/15 border-rose-300/40 text-rose-900 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.8),0_8px_32px_rgba(244,63,94,0.06)]',
  amber: 'bg-amber-500/15 border-amber-300/40 text-amber-900 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.8),0_8px_32px_rgba(245,158,11,0.06)]',
  yellow: 'bg-yellow-500/18 border-yellow-300/40 text-yellow-950 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.8),0_8px_32px_rgba(234,179,8,0.06)]',
  emerald: 'bg-emerald-500/15 border-emerald-300/40 text-emerald-900 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.8),0_8px_32px_rgba(16,185,129,0.06)]',
  blue: 'bg-blue-500/15 border-blue-300/40 text-blue-900 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.8),0_8px_32px_rgba(59,130,246,0.06)]',
  orange: 'bg-orange-500/15 border-orange-300/40 text-orange-900 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.8),0_8px_32px_rgba(249,115,22,0.06)]',
  indigo: 'bg-indigo-500/15 border-indigo-300/40 text-indigo-900 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.8),0_8px_32px_rgba(99,102,241,0.06)]',
};

const TONE_ICON: Record<NonNullable<MetricCardProps['tone']>, string> = {
  neutral: 'text-slate-400',
  rose: 'text-rose-600',
  amber: 'text-amber-600',
  yellow: 'text-yellow-600',
  emerald: 'text-emerald-600',
  blue: 'text-blue-600',
  orange: 'text-orange-600',
  indigo: 'text-indigo-600',
};

/**
 * Generic stat tile used for metric summary strips (Guardian Queue), the 5-tile Control Tower
 * grid, and gauge-style cards (Alert Fatigue Budget). Reads as a calm white card until `active`
 * flips it into its tinted `tone`, keeping a scan of the row fast — only the cards that matter
 * pull the eye.
 */
export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  icon,
  tone = 'neutral',
  active = false,
  sublabel,
  trailing,
  onClick,
  className,
}) => {
  const Comp = onClick ? 'button' : 'div';

  return (
    <Comp
      onClick={onClick}
      className={cn(
        'p-3.5 rounded-2xl border text-left w-full transition-all backdrop-blur-xl',
        active ? TONE_ACTIVE[tone] : 'bg-white/60 border-white/80 text-slate-900 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.85),0_8px_32px_rgba(31,38,135,0.04)]',
        onClick && 'hover:bg-white/80 cursor-pointer',
        className
      )}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="min-w-0">
          <div
            className={cn(
              'text-[11px] font-semibold uppercase tracking-wider truncate',
              active ? 'opacity-80' : 'text-slate-500'
            )}
          >
            {label}
          </div>
          <div className="text-2xl font-bold font-mono tabular-nums mt-0.5 leading-none">
            {value}
          </div>
          {sublabel && (
            <div className={cn('text-[11px] mt-1', active ? 'opacity-70' : 'text-slate-400')}>
              {sublabel}
            </div>
          )}
        </div>

        {(icon || trailing) && (
          <div className="shrink-0 flex flex-col items-end gap-1.5">
            {icon && <span className={active ? '' : TONE_ICON[tone]}>{icon}</span>}
            {trailing}
          </div>
        )}
      </div>
    </Comp>
  );
};
