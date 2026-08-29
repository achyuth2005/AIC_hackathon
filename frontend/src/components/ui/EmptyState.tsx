import React from 'react';
import { cn } from '../../lib/cn';
import { Inbox } from 'lucide-react';
import { Button } from './Button';

export interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: React.ReactNode;
  actionText?: string;
  onAction?: () => void;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon = <Inbox className="w-10 h-10 text-slate-500" />,
  title,
  description,
  actionText,
  onAction,
  className,
}) => {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center p-8 sm:p-12 text-center rounded-2xl border border-dashed border-slate-800 bg-slate-900/30 max-w-lg mx-auto my-6 animate-fade-in',
        className
      )}
    >
      <div className="p-3 rounded-2xl bg-slate-800/60 border border-slate-700/60 mb-4">
        {icon}
      </div>
      <h3 className="text-base font-semibold text-slate-100">{title}</h3>
      {description && (
        <div className="text-xs text-slate-400 mt-1 max-w-sm leading-relaxed">
          {description}
        </div>
      )}
      {actionText && onAction && (
        <Button variant="secondary" size="sm" onClick={onAction} className="mt-5">
          {actionText}
        </Button>
      )}
    </div>
  );
};
