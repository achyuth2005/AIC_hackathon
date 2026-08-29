import React from 'react';
import { PrimaryAttentionFlag } from '../../types/enums';
import { cn } from '../../lib/cn';
import {
  TrendingUp,
  Clock,
  HelpCircle,
  GitCompare,
  CheckCircle2,
} from 'lucide-react';

export interface AttentionFlagChipProps {
  flag: PrimaryAttentionFlag | null | undefined;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export const AttentionFlagChip: React.FC<AttentionFlagChipProps> = ({
  flag = 'NONE',
  size = 'md',
  className,
}) => {
  const flagConfig: Record<
    PrimaryAttentionFlag,
    { label: string; bg: string; text: string; border: string; icon: React.ReactNode }
  > = {
    REASSESSMENT_OVERDUE: {
      label: 'REASSESSMENT OVERDUE',
      bg: 'bg-rose-950/80',
      text: 'text-rose-300',
      border: 'border-rose-600/70 animate-pulse',
      icon: <Clock className="w-3.5 h-3.5 text-rose-400 shrink-0" />,
    },
    DETERIORATING: {
      label: 'DETERIORATING',
      bg: 'bg-orange-950/80',
      text: 'text-orange-300',
      border: 'border-orange-600/70',
      icon: <TrendingUp className="w-3.5 h-3.5 text-orange-400 shrink-0" />,
    },
    DATA_CONFLICT: {
      label: 'DATA CONFLICT',
      bg: 'bg-purple-950/80',
      text: 'text-purple-300',
      border: 'border-purple-600/70',
      icon: <GitCompare className="w-3.5 h-3.5 text-purple-400 shrink-0" />,
    },
    UNKNOWN_VITALS: {
      label: 'VITALS INCOMPLETE',
      bg: 'bg-amber-950/80',
      text: 'text-amber-300',
      border: 'border-amber-600/70',
      icon: <HelpCircle className="w-3.5 h-3.5 text-amber-400 shrink-0" />,
    },
    NONE: {
      label: 'STABLE / ROUTINE',
      bg: 'bg-slate-900/60',
      text: 'text-slate-400',
      border: 'border-slate-800',
      icon: <CheckCircle2 className="w-3.5 h-3.5 text-slate-500 shrink-0" />,
    },
  };

  const current = flag && flag in flagConfig ? flagConfig[flag] : flagConfig.NONE;

  return (
    <span
      role="status"
      aria-label={`Attention flag: ${current.label}`}
      className={cn(
        'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-bold border font-mono tracking-tight select-none',
        current.bg,
        current.text,
        current.border,
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
