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
      xs: 'px-2 py-1 text-xs gap-1 rounded',
      sm: 'px-3 py-1.5 text-xs font-medium gap-1.5 rounded-md',
      md: 'px-4 py-2 text-sm font-medium gap-2 rounded-lg',
      lg: 'px-5 py-2.5 text-base font-semibold gap-2 rounded-lg',
      xl: 'px-6 py-3.5 text-lg font-bold gap-3 rounded-xl',
    };

    const variantClasses = {
      primary:
        'bg-cyan-600 hover:bg-cyan-500 text-white shadow-sm hover:shadow active:bg-cyan-700 disabled:bg-slate-700 disabled:text-slate-400 focus-visible:ring-2 focus-visible:ring-cyan-400',
      secondary:
        'bg-slate-800 hover:bg-slate-700 text-slate-100 border border-slate-700 hover:border-slate-600 disabled:bg-slate-900 disabled:text-slate-500 focus-visible:ring-2 focus-visible:ring-slate-400',
      danger:
        'bg-red-600 hover:bg-red-500 text-white shadow-sm hover:shadow active:bg-red-700 disabled:bg-slate-700 disabled:text-slate-400 focus-visible:ring-2 focus-visible:ring-red-400',
      warning:
        'bg-amber-600 hover:bg-amber-500 text-white shadow-sm active:bg-amber-700 disabled:bg-slate-700 disabled:text-slate-400 focus-visible:ring-2 focus-visible:ring-amber-400',
      outline:
        'border border-slate-600 text-slate-200 hover:bg-slate-800/80 hover:border-slate-500 disabled:border-slate-800 disabled:text-slate-600 focus-visible:ring-2 focus-visible:ring-slate-400',
      ghost:
        'text-slate-300 hover:text-white hover:bg-slate-800/60 disabled:text-slate-600 focus-visible:ring-2 focus-visible:ring-slate-400',
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
