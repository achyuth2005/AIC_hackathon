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
    xs: 'px-1.5 py-0.2 text-[10px] gap-1 rounded',
    sm: 'px-2.5 py-0.5 text-xs font-medium gap-1.5 rounded-full',
    md: 'px-3 py-1 text-xs font-semibold gap-1.5 rounded-full',
    lg: 'px-3.5 py-1.5 text-sm font-semibold gap-2 rounded-full',
  };

  const variantClasses = {
    default: 'bg-slate-800 text-slate-300 border border-slate-700/80',
    primary: 'bg-cyan-950/70 text-cyan-300 border border-cyan-700/60',
    success: 'bg-emerald-950/70 text-emerald-300 border border-emerald-700/60',
    warning: 'bg-amber-950/70 text-amber-300 border border-amber-700/60',
    danger: 'bg-rose-950/70 text-rose-300 border border-rose-700/60',
    info: 'bg-indigo-950/70 text-indigo-300 border border-indigo-700/60',
    outline: 'bg-transparent text-slate-300 border border-slate-700',
  };

  const dotClasses = {
    default: 'bg-slate-400',
    primary: 'bg-cyan-400',
    success: 'bg-emerald-400',
    warning: 'bg-amber-400',
    danger: 'bg-rose-400',
    info: 'bg-indigo-400',
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
