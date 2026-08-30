import React from 'react';
import { cn } from '../../lib/cn';
import { AlertCircle, RefreshCw } from 'lucide-react';
import { Button } from './Button';

export interface ErrorStateProps {
  title?: string;
  message?: string;
  error?: unknown;
  onRetry?: () => void;
  className?: string;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = 'Failed to load data',
  message,
  error,
  onRetry,
  className,
}) => {
  const displayMsg =
    message ||
    (error instanceof Error ? error.message : typeof error === 'string' ? error : 'An unexpected error occurred.');

  return (
    <div
      role="alert"
      className={cn(
        'flex flex-col items-center justify-center p-8 text-center rounded-3xl border border-rose-200/50 bg-rose-500/[0.08] backdrop-blur-xl shadow-[inset_0_0_0_1px_rgba(255,255,255,0.8),0_12px_32px_rgba(244,63,94,0.06)] max-w-lg mx-auto my-6 animate-fade-in',
        className
      )}
    >
      <div className="p-3 rounded-2xl bg-white/70 backdrop-blur-sm border border-white/80 shadow-sm mb-3">
        <AlertCircle className="w-8 h-8 text-rose-600" />
      </div>
      <h3 className="text-base font-semibold text-rose-900">{title}</h3>
      <p className="text-xs text-rose-700 mt-1 max-w-sm leading-relaxed">{displayMsg}</p>
      {onRetry && (
        <Button
          variant="outline"
          size="sm"
          onClick={onRetry}
          leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
          className="mt-4 border-rose-300/60 hover:bg-rose-500/15 text-rose-800"
        >
          Try Again
        </Button>
      )}
    </div>
  );
};
