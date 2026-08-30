import React from 'react';
import { useControlTower } from '../hooks/useControlTower';
import { AcuityTile } from '../features/control-tower/AcuityTile';
import { DeterioratingTile } from '../features/control-tower/DeterioratingTile';
import { StuckPatientsTile } from '../features/control-tower/StuckPatientsTile';
import { CapacityTile } from '../features/control-tower/CapacityTile';
import { IncomingAmbulanceTile } from '../features/control-tower/IncomingAmbulanceTile';
import { Radio, RefreshCw } from 'lucide-react';
import { Skeleton } from '../components/ui/Skeleton';
import { ErrorState } from '../components/ui/ErrorState';

export const ControlTowerPage: React.FC = () => {
  const { data: ct, isLoading, isError, error, refetch, isFetching } = useControlTower();

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-16 animate-fade-in text-left">
      {/* Header & 5-Tile Philosophy Subtitle */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200/50 pb-5">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight text-slate-900 flex items-center gap-2.5">
              <Radio className="w-7 h-7 text-indigo-600" />
              Executive Control Tower
            </h1>
            <span className="text-xs px-2.5 py-0.5 rounded-full font-mono font-bold bg-indigo-500/10 text-indigo-700 border border-indigo-200/40 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.7)]">
              5 Actionable Tiles
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Anticipatory hospital operations overview — 5 tiles maximum, every tile actionable.
          </p>
        </div>

        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/60 backdrop-blur-md border border-white/80 text-xs font-mono text-slate-500 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.8),0_2px_8px_rgba(31,38,135,0.03)]">
          <span className={`w-2 h-2 rounded-full ${isFetching ? 'bg-indigo-500 animate-ping' : 'bg-emerald-500'}`} />
          <span>Live 5s sweep</span>
          <button
            onClick={() => refetch()}
            disabled={isFetching}
            className="text-slate-400 hover:text-slate-700 cursor-pointer p-0.5"
            title="Refresh Control Tower"
          >
            <RefreshCw className={`w-3 h-3 ${isFetching ? 'animate-spin text-indigo-500' : ''}`} />
          </button>
        </div>
      </div>

      {/* 5 Anticipatory Tiles Layout */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {[1, 2, 3, 4, 5].map((i) => (
            <Skeleton key={i} className="h-64 w-full rounded-2xl" />
          ))}
        </div>
      ) : isError || !ct ? (
        <ErrorState
          title="Failed to load Executive Control Tower"
          error={error}
          onRetry={() => refetch()}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {/* Tile 1: Acuity Band & Overdue Breakdown */}
          <AcuityTile data={ct.patients_by_acuity_band} />

          {/* Tile 2: Deteriorating Trajectories */}
          <DeterioratingTile data={ct.deteriorating_patients} />

          {/* Tile 3: Stuck Patient Bottlenecks */}
          <StuckPatientsTile data={ct.stuck_patients} />

          {/* Tile 4: Capacity: Spaces and Clinicians Free vs Needed */}
          <CapacityTile data={ct.capacity} />

          {/* Tile 5: Incoming Ambulances with Predicted Acuity */}
          <IncomingAmbulanceTile data={ct.incoming_ambulances} />
        </div>
      )}
    </div>
  );
};
