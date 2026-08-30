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
      bg: 'bg-rose-500/15',
      text: 'text-rose-800 font-bold',
      border: 'border-rose-300/40 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.7)] animate-pulse',
      icon: <Clock className="w-3.5 h-3.5 text-rose-600 shrink-0" />,
    },
    DETERIORATING: {
      label: 'DETERIORATING',
      bg: 'bg-orange-500/15',
      text: 'text-orange-800 font-bold',
      border: 'border-orange-300/40 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.7)]',
      icon: <TrendingUp className="w-3.5 h-3.5 text-orange-600 shrink-0" />,
    },
    DATA_CONFLICT: {
      label: 'DATA CONFLICT',
      bg: 'bg-purple-500/15',
      text: 'text-purple-800 font-bold',
      border: 'border-purple-300/40 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.7)]',
      icon: <GitCompare className="w-3.5 h-3.5 text-purple-600 shrink-0" />,
    },
    UNKNOWN_VITALS: {
      label: 'MISSING VITALS',
      bg: 'bg-amber-500/15',
      text: 'text-amber-900 font-bold',
      border: 'border-amber-300/40 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.7)]',
      icon: <HelpCircle className="w-3.5 h-3.5 text-amber-600 shrink-0" />,
    },
    NONE: {
      label: 'STABLE / ROUTINE',
      bg: 'bg-slate-500/10',
      text: 'text-slate-700 font-medium',
      border: 'border-slate-300/30 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.7)]',
      icon: <CheckCircle2 className="w-3.5 h-3.5 text-slate-400 shrink-0" />,
    },
  };

  const current = flag && flag in flagConfig ? flagConfig[flag] : flagConfig.NONE;

  return (
    <span
      role="status"
      aria-label={`Attention flag: ${current.label}`}
      className={cn(
        'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold border backdrop-blur-sm font-mono tracking-tight select-none',
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
