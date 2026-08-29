import React from 'react';
import { useAmbulanceList } from '../hooks/useAmbulanceList';
import { AmbulanceBoardTable } from '../features/ambulance/AmbulanceBoardTable';
import { Truck, RefreshCw } from 'lucide-react';
import { Skeleton } from '../components/ui/Skeleton';
import { ErrorState } from '../components/ui/ErrorState';

export const AmbulancePage: React.FC = () => {
  const { data: queue, isLoading, isError, error, refetch, isFetching } = useAmbulanceList();

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-16 animate-fade-in text-left">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-extrabold tracking-tight text-slate-100 flex items-center gap-2.5">
              <Truck className="w-7 h-7 text-cyan-400" />
              Inbound Ambulance Transports & Pre-Arrival Board
            </h1>
            <span className="text-xs px-2.5 py-0.5 rounded-full font-mono font-bold bg-cyan-950 text-cyan-300 border border-cyan-700/60">
              Phase 7 Pre-Arrival Workflow
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Real-time telemetry, simulated ETA countdowns, identity resolution, and ED arrival transitions.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => refetch()}
            disabled={isFetching}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs font-mono text-slate-400 hover:text-slate-200 cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isFetching ? 'animate-spin text-cyan-400' : ''}`} />
            <span>Refresh Board</span>
          </button>
        </div>
      </div>

      {/* Ambulance Table Content */}
      {isLoading ? (
        <div className="space-y-3">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
        </div>
      ) : isError ? (
        <ErrorState
          title="Failed to load ambulance pre-arrival board"
          error={error}
          onRetry={() => refetch()}
        />
      ) : (
        <AmbulanceBoardTable entries={queue || []} />
      )}
    </div>
  );
};
