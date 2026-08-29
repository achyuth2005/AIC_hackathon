import React from 'react';
import { useBiasMetrics } from '../hooks/useBiasMetrics';
import { useFlaggedOverrides } from '../hooks/useFlaggedOverrides';
import { BiasEquityPanel } from '../features/admin/BiasEquityPanel';
import { FlaggedOverridesTable } from '../features/admin/FlaggedOverridesTable';
import { ShieldCheck, RefreshCw } from 'lucide-react';
import { Skeleton } from '../components/ui/Skeleton';
import { ErrorState } from '../components/ui/ErrorState';

export const AdminPage: React.FC = () => {
  const {
    data: biasReport,
    isLoading: isBiasLoading,
    isError: isBiasError,
    error: biasError,
    refetch: refetchBias,
    isFetching: isBiasFetching,
  } = useBiasMetrics();

  const {
    data: flaggedOverrides,
    isLoading: isOverridesLoading,
    refetch: refetchOverrides,
  } = useFlaggedOverrides();

  const handleRefreshAll = () => {
    refetchBias();
    refetchOverrides();
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-16 animate-fade-in text-left">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-extrabold tracking-tight text-slate-100 flex items-center gap-2.5">
              <ShieldCheck className="w-7 h-7 text-cyan-400" />
              Administrative Governance, Equity & Audit
            </h1>
            <span className="text-xs px-2.5 py-0.5 rounded-full font-mono font-bold bg-cyan-950 text-cyan-300 border border-cyan-700/60">
              Phase 9.6 / 9.7 Standing Oversight
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Standing demographic equity evaluations, override rate monitoring, and retrospective de-escalation audit log.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleRefreshAll}
            disabled={isBiasFetching}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs font-mono text-slate-400 hover:text-slate-200 cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isBiasFetching ? 'animate-spin text-cyan-400' : ''}`} />
            <span>Refresh Audit Data</span>
          </button>
        </div>
      </div>

      {/* 1. Standing Demographic Equity & Override Rate Panel (Phase 9.7) */}
      {isBiasLoading ? (
        <div className="space-y-4">
          <Skeleton className="h-32 w-full rounded-2xl" />
          <Skeleton className="h-64 w-full rounded-2xl" />
        </div>
      ) : isBiasError || !biasReport ? (
        <ErrorState
          title="Failed to load demographic oversight metrics"
          error={biasError}
          onRetry={() => refetchBias()}
        />
      ) : (
        <BiasEquityPanel report={biasReport} />
      )}

      {/* 2. Retrospective Review Audit Queue (Phase 9.6) */}
      <FlaggedOverridesTable
        overrides={flaggedOverrides || []}
        isLoading={isOverridesLoading}
      />
    </div>
  );
};
