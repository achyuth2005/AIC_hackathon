import React from 'react';
import { cn } from '../../lib/cn';
import { parseBackendUtc } from '../../lib/datetime';

export interface StalenessDotProps {
  observedAt: string | Date | null | undefined;
  staleMinutesThreshold?: number;
  className?: string;
}

export const StalenessDot: React.FC<StalenessDotProps> = ({
  observedAt,
  staleMinutesThreshold = 60,
  className,
}) => {
  const d = typeof observedAt === 'string' ? parseBackendUtc(observedAt) : observedAt;
  if (!d) return null;

  const now = new Date();
  const diffMinutes = Math.floor((now.getTime() - d.getTime()) / (1000 * 60));
  const isStale = diffMinutes >= staleMinutesThreshold;

  return (
    <span
      title={isStale ? `Reading is stale (${diffMinutes}m old)` : `Recent reading (${diffMinutes}m old)`}
      className={cn(
        'inline-block w-2 h-2 rounded-full ring-2 ring-white',
        isStale ? 'bg-amber-500 animate-pulse' : 'bg-emerald-500',
        className
      )}
    />
  );
};
