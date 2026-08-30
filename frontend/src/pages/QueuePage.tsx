import React, { useState, useEffect } from 'react';
import { useQueue } from '../hooks/useQueue';
import { QueueTable } from '../features/queue/QueueTable';
import { QueueLegend } from '../features/queue/QueueLegend';
import { Button } from '../components/ui/Button';
import { Skeleton } from '../components/ui/Skeleton';
import { ErrorState } from '../components/ui/ErrorState';
import { MetricCard } from '../components/ui/MetricCard';
import {
  ListOrdered,
  UserPlus,
  RefreshCw,
  Clock,
  Zap,
} from 'lucide-react';
import { Link } from 'react-router-dom';

export const QueuePage: React.FC = () => {
  const { data: queue, isLoading, isError, error, refetch, dataUpdatedAt, isFetching } = useQueue();
  const [secondsAgo, setSecondsAgo] = useState(0);

  // Update "updated Xs ago" counter
  useEffect(() => {
    const timer = setInterval(() => {
      if (dataUpdatedAt) {
        setSecondsAgo(Math.floor((Date.now() - dataUpdatedAt) / 1000));
      }
    }, 1000);
    return () => clearInterval(timer);
  }, [dataUpdatedAt]);

  // Derived counts from current queue data (for presentation only)
  const totalCases = queue?.length || 0;
  const overdueCount = queue?.filter((e) => e.reassessment.is_due).length || 0;
  const bypassCount = queue?.filter((e) => e.emergency_bypass_active).length || 0;
  const countsByAcuity = [1, 2, 3, 4, 5].map((level) => ({
    level,
    count: queue?.filter((e) => e.final_acuity === level).length || 0,
  }));

  const ACUITY_TONE = ['rose', 'amber', 'yellow', 'emerald', 'blue'] as const;

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12 animate-fade-in">
      {/* Top Header & Fast Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200/50 pb-5">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight text-slate-900 flex items-center gap-2.5">
              <ListOrdered className="w-7 h-7 text-indigo-600" />
              Nurse Guardian Queue
            </h1>
            <span className="text-xs px-2.5 py-0.5 rounded-full font-mono font-bold tabular-nums bg-indigo-500/10 text-indigo-700 border border-indigo-200/40 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.7)]">
              {totalCases} Active
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Deterministic time-engine reassessment priority with 3s active sweep.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          {/* Polling heartbeat indicator */}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/60 backdrop-blur-md border border-white/80 text-xs font-mono text-slate-500 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.8),0_2px_8px_rgba(31,38,135,0.03)]">
            <span
              className={`w-2 h-2 rounded-full ${
                isFetching ? 'bg-indigo-500 animate-ping' : 'bg-emerald-500'
              }`}
            />
            <span>{secondsAgo === 0 ? 'Just updated' : `${secondsAgo}s ago`}</span>
            <button
              onClick={() => refetch()}
              disabled={isFetching}
              className="text-slate-400 hover:text-slate-700 cursor-pointer p-0.5"
              aria-label="Refresh now"
            >
              <RefreshCw className={`w-3 h-3 ${isFetching ? 'animate-spin text-indigo-500' : ''}`} />
            </button>
          </div>

          <Link to="/register">
            <Button
              variant="primary"
              size="sm"
              leftIcon={<UserPlus className="w-4 h-4" />}
              className="font-semibold"
            >
              New Walk-In
            </Button>
          </Link>
        </div>
      </div>

      {/* Acuity Band Summary Metric Strip */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
        <MetricCard label="Total Active" value={totalCases} />

        {countsByAcuity.map(({ level, count }) => (
          <MetricCard
            key={level}
            label={`ESI ${level}`}
            value={count}
            tone={ACUITY_TONE[level - 1]}
            active={count > 0}
          />
        ))}

        <MetricCard
          label="Overdue"
          value={overdueCount}
          tone="rose"
          active={overdueCount > 0}
          icon={<Clock className={`w-4 h-4 ${overdueCount > 0 ? 'animate-pulse' : ''}`} />}
        />
      </div>

      {/* Emergency Bypass Critical Banner if any bypass active */}
      {bypassCount > 0 && (
        <div
          role="alert"
          className="p-4 rounded-2xl border-l-4 border-rose-500 bg-gradient-to-r from-rose-500/15 via-rose-50/60 to-white/60 backdrop-blur-xl flex items-center justify-between gap-4 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.8),0_8px_32px_rgba(244,63,94,0.06)]"
        >
          <div className="flex items-center gap-3">
            <Zap className="w-6 h-6 text-rose-600 fill-rose-200 shrink-0" />
            <div>
              <div className="font-bold text-sm text-rose-900 flex items-center gap-2">
                CRITICAL BYPASS ACTIVE ({bypassCount} {bypassCount === 1 ? 'Patient' : 'Patients'})
              </div>
              <p className="text-xs text-rose-700 mt-0.5">
                Immediate resuscitation protocol engaged. Guardian Queue ordered with bypass prioritized.
              </p>
            </div>
          </div>
          <span className="px-3 py-1 rounded-full bg-rose-500 text-white font-mono text-xs font-bold tabular-nums shrink-0 shadow-sm backdrop-blur-sm">
            ESI 1 PROTOCOL
          </span>
        </div>
      )}

      {/* Queue Table */}
      {isLoading ? (
        <div className="space-y-3 p-6 rounded-2xl bg-white/60 backdrop-blur-xl border border-white/80 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.85),0_8px_32px_rgba(31,38,135,0.04)]">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-20 w-full" />
        </div>
      ) : isError ? (
        <ErrorState
          title="Failed to load Guardian Queue"
          error={error}
          onRetry={() => refetch()}
        />
      ) : (
        <QueueTable entries={queue || []} />
      )}

      {/* Legend & Guide */}
      <QueueLegend />
    </div>
  );
};
