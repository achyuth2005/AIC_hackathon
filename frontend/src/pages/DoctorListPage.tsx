import React, { useState } from 'react';
import { useDoctorList } from '../hooks/useDoctorList';
import { DoctorWorklistTable } from '../features/doctor/DoctorWorklistTable';
import { Stethoscope, RefreshCw, TestTube, AlertCircle, ShieldAlert } from 'lucide-react';
import { Skeleton } from '../components/ui/Skeleton';
import { ErrorState } from '../components/ui/ErrorState';

type FilterType = 'ALL' | 'UNREVIEWED' | 'STUCK' | 'HIGH_ACUITY';

export const DoctorListPage: React.FC = () => {
  const { data: items, isLoading, isError, error, refetch, isFetching } = useDoctorList();
  const [filter, setFilter] = useState<FilterType>('ALL');

  const unreviewedTotal = items?.filter((i) => i.unreviewed_results_count > 0).length || 0;
  const stuckTotal = items?.filter((i) => i.stuck_flagged).length || 0;
  const highAcuityTotal = items?.filter((i) => i.final_acuity <= 2).length || 0;

  const filteredItems = (items || []).filter((item) => {
    if (filter === 'UNREVIEWED') return item.unreviewed_results_count > 0;
    if (filter === 'STUCK') return item.stuck_flagged;
    if (filter === 'HIGH_ACUITY') return item.final_acuity <= 2;
    return true;
  });

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12 animate-fade-in text-left">
      {/* Header & Status Indicator */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-extrabold tracking-tight text-slate-100 flex items-center gap-2.5">
              <Stethoscope className="w-7 h-7 text-indigo-400" />
              Attending Physician Worklist
            </h1>
            <span className="text-xs px-2.5 py-0.5 rounded-full font-mono font-bold bg-indigo-950 text-indigo-300 border border-indigo-700/60">
              {items?.length || 0} Patients
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Clinical worklist with priority sorting, real-time vital trends, and unreviewed diagnostic alerts.
          </p>
        </div>

        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs font-mono text-slate-400">
          <span className={`w-2 h-2 rounded-full ${isFetching ? 'bg-indigo-400 animate-ping' : 'bg-emerald-400'}`} />
          <span>Live 5s sweep</span>
          <button
            onClick={() => refetch()}
            disabled={isFetching}
            className="text-slate-400 hover:text-slate-200 cursor-pointer p-0.5"
            title="Refresh list"
          >
            <RefreshCw className={`w-3 h-3 ${isFetching ? 'animate-spin text-indigo-400' : ''}`} />
          </button>
        </div>
      </div>

      {/* Filter Tabs / Pills */}
      <div className="flex flex-wrap items-center gap-2">
        <button
          onClick={() => setFilter('ALL')}
          className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
            filter === 'ALL'
              ? 'bg-indigo-600 text-white shadow-md'
              : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
          }`}
        >
          All Active Patients ({items?.length || 0})
        </button>

        <button
          onClick={() => setFilter('UNREVIEWED')}
          className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer flex items-center gap-1.5 ${
            filter === 'UNREVIEWED'
              ? 'bg-indigo-600 text-white shadow-md'
              : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
          } ${unreviewedTotal > 0 ? 'text-indigo-300' : ''}`}
        >
          <TestTube className="w-3.5 h-3.5" />
          Unreviewed Results ({unreviewedTotal})
        </button>

        <button
          onClick={() => setFilter('STUCK')}
          className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer flex items-center gap-1.5 ${
            filter === 'STUCK'
              ? 'bg-rose-700 text-white shadow-md'
              : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
          } ${stuckTotal > 0 ? 'text-rose-300' : ''}`}
        >
          <AlertCircle className="w-3.5 h-3.5" />
          Stuck Patients ({stuckTotal})
        </button>

        <button
          onClick={() => setFilter('HIGH_ACUITY')}
          className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer flex items-center gap-1.5 ${
            filter === 'HIGH_ACUITY'
              ? 'bg-orange-600 text-white shadow-md'
              : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
          }`}
        >
          <ShieldAlert className="w-3.5 h-3.5" />
          ESI 1 & 2 Only ({highAcuityTotal})
        </button>
      </div>

      {/* Worklist Table */}
      {isLoading ? (
        <div className="space-y-3 p-6 rounded-xl bg-slate-900/40 border border-slate-800">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-20 w-full" />
        </div>
      ) : isError ? (
        <ErrorState
          title="Failed to load physician worklist"
          error={error}
          onRetry={() => refetch()}
        />
      ) : (
        <DoctorWorklistTable items={filteredItems} />
      )}
    </div>
  );
};
