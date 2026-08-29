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
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-extrabold tracking-tight text-slate-100 flex items-center gap-2.5">
              <Radio className="w-7 h-7 text-cyan-400" />
              Executive Control Tower
            </h1>
            <span className="text-xs px-2.5 py-0.5 rounded-full font-mono font-bold bg-cyan-950 text-cyan-300 border border-cyan-700/60">
              5 Actionable Tiles
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Anticipatory hospital operations overview — 5 tiles maximum, every tile actionable.
          </p>
        </div>

        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs font-mono text-slate-400">
          <span className={`w-2 h-2 rounded-full ${isFetching ? 'bg-cyan-400 animate-ping' : 'bg-emerald-400'}`} />
          <span>Live 5s sweep</span>
          <button
            onClick={() => refetch()}
            disabled={isFetching}
            className="text-slate-400 hover:text-slate-200 cursor-pointer p-0.5"
            title="Refresh Control Tower"
          >
            <RefreshCw className={`w-3 h-3 ${isFetching ? 'animate-spin text-cyan-400' : ''}`} />
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
