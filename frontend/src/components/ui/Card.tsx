import React from 'react';
import { cn } from '../../lib/cn';

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'elevated' | 'bordered' | 'glass';
}

export const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className, variant = 'default', children, ...props }, ref) => {
    const variantClasses = {
      default: 'bg-white/65 backdrop-blur-xl border border-white/80 text-slate-900 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.85),0_8px_32px_rgba(31,38,135,0.04)] rounded-2xl',
      elevated: 'bg-white/75 backdrop-blur-xl border border-white/90 text-slate-900 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.9),0_12px_36px_rgba(31,38,135,0.06)] rounded-2xl',
      bordered: 'bg-white/60 backdrop-blur-xl border border-white/90 text-slate-900 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.8)] rounded-2xl',
      glass: 'bg-white/60 backdrop-blur-xl border border-white/80 text-slate-900 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.85),0_8px_32px_rgba(31,38,135,0.04)] rounded-2xl',
    };

    return (
      <div ref={ref} className={cn(variantClasses[variant], 'p-4 sm:p-6', className)} {...props}>
        {children}
      </div>
    );
  }
);

Card.displayName = 'Card';

export const CardHeader: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({
  className,
  children,
  ...props
}) => (
  <div className={cn('flex flex-col space-y-1.5 pb-4', className)} {...props}>
    {children}
  </div>
);

export const CardTitle: React.FC<React.HTMLAttributes<HTMLHeadingElement>> = ({
  className,
  children,
  ...props
}) => (
  <h3
    className={cn('text-lg font-semibold tracking-tight text-slate-900 flex items-center gap-2', className)}
    {...props}
  >
    {children}
  </h3>
);

export const CardDescription: React.FC<React.HTMLAttributes<HTMLParagraphElement>> = ({
  className,
  children,
  ...props
}) => (
  <p className={cn('text-sm text-slate-500', className)} {...props}>
    {children}
  </p>
);

export const CardContent: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({
  className,
  children,
  ...props
}) => <div className={cn('pt-0', className)} {...props}>{children}</div>;

export const CardFooter: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({
  className,
  children,
  ...props
}) => (
  <div className={cn('flex items-center pt-4 border-t border-slate-100 mt-4', className)} {...props}>
    {children}
  </div>
);
