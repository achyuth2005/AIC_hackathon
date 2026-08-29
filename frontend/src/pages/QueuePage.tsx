import React, { useState, useEffect } from 'react';
import { useQueue } from '../hooks/useQueue';
import { QueueTable } from '../features/queue/QueueTable';
import { QueueLegend } from '../features/queue/QueueLegend';
import { Button } from '../components/ui/Button';
import { Skeleton } from '../components/ui/Skeleton';
import { ErrorState } from '../components/ui/ErrorState';
import { AcuityBadge } from '../components/clinical/AcuityBadge';
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

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12 animate-fade-in">
      {/* Top Header & Fast Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-extrabold tracking-tight text-slate-100 flex items-center gap-2.5">
              <ListOrdered className="w-7 h-7 text-cyan-400" />
              Nurse Guardian Queue
            </h1>
            <span className="text-xs px-2.5 py-0.5 rounded-full font-mono font-bold bg-cyan-950 text-cyan-300 border border-cyan-700/60">
              {totalCases} Active
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Deterministic time-engine reassessment priority with 3s active sweep.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          {/* Polling heartbeat indicator */}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs font-mono text-slate-400">
            <span
              className={`w-2 h-2 rounded-full ${
                isFetching ? 'bg-cyan-400 animate-ping' : 'bg-emerald-400'
              }`}
            />
            <span>{secondsAgo === 0 ? 'Just updated' : `${secondsAgo}s ago`}</span>
            <button
              onClick={() => refetch()}
              disabled={isFetching}
              className="text-slate-400 hover:text-slate-200 cursor-pointer p-0.5"
              aria-label="Refresh now"
            >
              <RefreshCw className={`w-3 h-3 ${isFetching ? 'animate-spin text-cyan-400' : ''}`} />
            </button>
          </div>

          <Link to="/register">
            <Button
              variant="primary"
              size="sm"
              leftIcon={<UserPlus className="w-4 h-4" />}
              className="font-bold shadow-md shadow-cyan-950/40"
            >
              New Walk-In
            </Button>
          </Link>
        </div>
      </div>

      {/* Acuity Band Summary Metric Chips */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
        {/* Total Metric */}
        <div className="p-3 rounded-xl bg-slate-900 border border-slate-800 text-left">
          <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
            Total Active
          </div>
          <div className="text-2xl font-black font-mono text-slate-100 mt-0.5">
            {totalCases}
          </div>
        </div>

        {/* ESI 1 to 5 Metrics */}
        {countsByAcuity.map(({ level, count }) => (
          <div
            key={level}
            className="p-3 rounded-xl bg-slate-900 border border-slate-800 text-left flex items-center justify-between"
          >
            <div>
              <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                ESI {level}
              </div>
              <div className="text-xl font-black font-mono text-slate-100 mt-0.5">
                {count}
              </div>
            </div>
            <AcuityBadge acuity={level} size="xs" showLabel={false} />
          </div>
        ))}

        {/* Overdue Alert Metric */}
        <div
          className={`p-3 rounded-xl border text-left flex items-center justify-between ${
            overdueCount > 0
              ? 'bg-rose-950/40 border-rose-700/60 text-rose-200'
              : 'bg-slate-900 border-slate-800 text-slate-400'
          }`}
        >
          <div>
            <div className="text-[10px] font-bold uppercase tracking-wider">
              Overdue
            </div>
            <div className="text-xl font-black font-mono mt-0.5">
              {overdueCount}
            </div>
          </div>
          <Clock className={`w-4 h-4 ${overdueCount > 0 ? 'text-rose-400 animate-pulse' : 'text-slate-600'}`} />
        </div>
      </div>

      {/* Emergency Bypass Critical Banner if any bypass active */}
      {bypassCount > 0 && (
        <div
          role="alert"
          className="p-4 rounded-xl bg-red-950/80 border-2 border-red-600 text-red-100 flex items-center justify-between gap-4 animate-pulse shadow-lg glow-red"
        >
          <div className="flex items-center gap-3">
            <Zap className="w-6 h-6 text-red-400 fill-red-400 shrink-0" />
            <div>
              <div className="font-extrabold text-sm text-white flex items-center gap-2">
                CRITICAL BYPASS ACTIVE ({bypassCount} {bypassCount === 1 ? 'Patient' : 'Patients'})
              </div>
              <p className="text-xs text-red-200 mt-0.5">
                Immediate resuscitation protocol engaged. Guardian Queue ordered with bypass prioritized.
              </p>
            </div>
          </div>
          <span className="px-3 py-1 rounded-full bg-red-800 border border-red-500 font-mono text-xs font-black">
            ESI 1 PROTOCOL
          </span>
        </div>
      )}

      {/* Queue Table */}
      {isLoading ? (
        <div className="space-y-3 p-6 rounded-xl bg-slate-900/40 border border-slate-800">
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
