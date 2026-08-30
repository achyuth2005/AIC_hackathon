import React from 'react';
import { cn } from '../../lib/cn';

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'default' | 'primary' | 'success' | 'warning' | 'danger' | 'info' | 'outline';
  size?: 'xs' | 'sm' | 'md' | 'lg';
  dot?: boolean;
}

export const Badge: React.FC<BadgeProps> = ({
  className,
  variant = 'default',
  size = 'sm',
  dot = false,
  children,
  ...props
}) => {
  const sizeClasses = {
    xs: 'px-2 py-0.5 text-[10px] gap-1 rounded-full',
    sm: 'px-2.5 py-0.5 text-xs font-medium gap-1.5 rounded-full',
    md: 'px-3 py-1 text-xs font-semibold gap-1.5 rounded-full',
    lg: 'px-3.5 py-1.5 text-sm font-semibold gap-2 rounded-full',
  };

  const variantClasses = {
    default: 'bg-slate-500/10 text-slate-700 border border-slate-300/30 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.7)] backdrop-blur-sm',
    primary: 'bg-indigo-500/15 text-indigo-800 border border-indigo-300/40 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.7)] backdrop-blur-sm',
    success: 'bg-emerald-500/15 text-emerald-800 border border-emerald-300/40 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.7)] backdrop-blur-sm',
    warning: 'bg-amber-500/15 text-amber-900 border border-amber-300/40 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.7)] backdrop-blur-sm',
    danger: 'bg-rose-500/15 text-rose-800 border border-rose-300/40 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.7)] backdrop-blur-sm',
    info: 'bg-blue-500/15 text-blue-800 border border-blue-300/40 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.7)] backdrop-blur-sm',
    outline: 'bg-white/60 text-slate-700 border border-white/80 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.7)] backdrop-blur-sm',
  };

  const dotClasses = {
    default: 'bg-slate-400',
    primary: 'bg-indigo-500',
    success: 'bg-emerald-500',
    warning: 'bg-amber-500',
    danger: 'bg-rose-500',
    info: 'bg-blue-500',
    outline: 'bg-slate-400',
  };

  return (
    <span
      className={cn(
        'inline-flex items-center justify-center transition-colors select-none font-mono tracking-tight',
        sizeClasses[size],
        variantClasses[variant],
        className
      )}
      {...props}
    >
      {dot && <span className={cn('w-1.5 h-1.5 rounded-full shrink-0', dotClasses[variant])} />}
      {children}
    </span>
  );
};
