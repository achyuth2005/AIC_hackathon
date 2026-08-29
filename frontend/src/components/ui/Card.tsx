import React from 'react';
import { cn } from '../../lib/cn';

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'elevated' | 'bordered' | 'glass';
}

export const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className, variant = 'default', children, ...props }, ref) => {
    const variantClasses = {
      default: 'bg-slate-900 border border-slate-800 text-slate-100 shadow-sm rounded-xl',
      elevated: 'bg-slate-900 border border-slate-800/80 text-slate-100 shadow-lg shadow-black/40 rounded-xl',
      bordered: 'bg-slate-950 border-2 border-slate-700/80 text-slate-100 rounded-xl',
      glass: 'bg-slate-900/80 backdrop-blur-md border border-slate-700/50 text-slate-100 shadow-xl rounded-xl',
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
    className={cn('text-lg font-semibold tracking-tight text-slate-100 flex items-center gap-2', className)}
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
  <p className={cn('text-sm text-slate-400', className)} {...props}>
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
  <div className={cn('flex items-center pt-4 border-t border-slate-800/80 mt-4', className)} {...props}>
    {children}
  </div>
);
