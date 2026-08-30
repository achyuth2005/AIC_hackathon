import React from 'react';
import { cn } from '../../lib/cn';
import { Spinner } from './Spinner';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'warning' | 'outline' | 'ghost';
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant = 'primary',
      size = 'md',
      isLoading = false,
      disabled,
      children,
      leftIcon,
      rightIcon,
      type = 'button',
      ...props
    },
    ref
  ) => {
    const sizeClasses = {
      xs: 'px-2.5 py-1 text-xs gap-1 rounded-lg',
      sm: 'px-3 py-1.5 text-xs font-medium gap-1.5 rounded-xl',
      md: 'px-4 py-2 text-sm font-medium gap-2 rounded-xl',
      lg: 'px-5 py-2.5 text-base font-semibold gap-2 rounded-2xl',
      xl: 'px-6 py-3.5 text-lg font-bold gap-3 rounded-2xl',
    };

    const variantClasses = {
      primary:
        'bg-gradient-to-r from-slate-900 via-slate-800 to-indigo-950 hover:from-slate-800 hover:to-indigo-900 text-white shadow-[0_2px_8px_rgba(15,23,42,0.15)] hover:shadow-[0_4px_12px_rgba(15,23,42,0.2)] active:from-slate-950 active:to-black disabled:bg-slate-100 disabled:text-slate-400 disabled:shadow-none focus-visible:ring-2 focus-visible:ring-indigo-500',
      secondary:
        'bg-white/70 hover:bg-white/95 text-slate-700 border border-white/80 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.8),0_1px_3px_rgba(0,0,0,0.04)] hover:shadow-[0_2px_6px_rgba(0,0,0,0.06)] active:bg-slate-50 disabled:bg-white/40 disabled:text-slate-400 disabled:shadow-none backdrop-blur-sm focus-visible:ring-2 focus-visible:ring-slate-400',
      danger:
        'bg-gradient-to-r from-rose-500 to-rose-600 hover:from-rose-600 hover:to-rose-700 text-white shadow-[0_2px_8px_rgba(225,29,72,0.25)] hover:shadow-[0_4px_12px_rgba(225,29,72,0.35)] active:from-rose-700 active:to-rose-800 disabled:bg-slate-100 disabled:text-slate-400 disabled:shadow-none focus-visible:ring-2 focus-visible:ring-rose-400',
      warning:
        'bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-600 hover:to-amber-700 text-white shadow-[0_2px_8px_rgba(217,119,6,0.22)] hover:shadow-[0_4px_12px_rgba(217,119,6,0.3)] active:from-amber-700 active:to-amber-800 disabled:bg-slate-100 disabled:text-slate-400 disabled:shadow-none focus-visible:ring-2 focus-visible:ring-amber-400',
      outline:
        'bg-white/60 border border-white/80 text-slate-700 hover:bg-white/90 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.7),0_1px_3px_rgba(0,0,0,0.03)] disabled:bg-white/30 disabled:text-slate-400 disabled:shadow-none backdrop-blur-sm focus-visible:ring-2 focus-visible:ring-slate-400',
      ghost:
        'text-slate-600 hover:text-slate-900 hover:bg-white/50 backdrop-blur-sm disabled:text-slate-400 focus-visible:ring-2 focus-visible:ring-slate-400',
    };

    return (
      <button
        ref={ref}
        type={type}
        disabled={disabled || isLoading}
        className={cn(
          'inline-flex items-center justify-center transition-all duration-150 select-none outline-none disabled:cursor-not-allowed cursor-pointer',
          sizeClasses[size],
          variantClasses[variant],
          className
        )}
        {...props}
      >
        {isLoading ? <Spinner size="sm" className="mr-1.5" /> : leftIcon ? <span className="shrink-0">{leftIcon}</span> : null}
        {children}
        {!isLoading && rightIcon && <span className="shrink-0">{rightIcon}</span>}
      </button>
    );
  }
);

Button.displayName = 'Button';
