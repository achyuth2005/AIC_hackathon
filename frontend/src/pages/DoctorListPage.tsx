import React, { useState } from 'react';
import { useDoctorList } from '../hooks/useDoctorList';
import { DoctorWorklistTable } from '../features/doctor/DoctorWorklistTable';
import { TriageExplainabilityDrawer } from '../features/doctor/TriageExplainabilityDrawer';
import { Stethoscope, RefreshCw, TestTube, AlertCircle, ShieldAlert } from 'lucide-react';
import { Skeleton } from '../components/ui/Skeleton';
import { ErrorState } from '../components/ui/ErrorState';
import { cn } from '../lib/cn';

type FilterType = 'ALL' | 'UNREVIEWED' | 'STUCK' | 'HIGH_ACUITY';

export const DoctorListPage: React.FC = () => {
  const { data: items, isLoading, isError, error, refetch, isFetching } = useDoctorList();
  const [filter, setFilter] = useState<FilterType>('ALL');
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);

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
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200/50 pb-5">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight text-slate-900 flex items-center gap-2.5">
              <Stethoscope className="w-7 h-7 text-indigo-600" />
              Attending Physician Worklist
            </h1>
            <span className="text-xs px-2.5 py-0.5 rounded-full font-mono font-bold tabular-nums bg-indigo-500/10 text-indigo-700 border border-indigo-200/40 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.7)]">
              {items?.length || 0} Patients
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Clinical worklist with priority sorting, real-time vital trends, and unreviewed diagnostic alerts.
          </p>
        </div>

        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/60 backdrop-blur-md border border-white/80 text-xs font-mono text-slate-500 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.8),0_2px_8px_rgba(31,38,135,0.03)]">
          <span className={`w-2 h-2 rounded-full ${isFetching ? 'bg-indigo-500 animate-ping' : 'bg-emerald-500'}`} />
          <span>Live 5s sweep</span>
          <button
            onClick={() => refetch()}
            disabled={isFetching}
            className="text-slate-400 hover:text-slate-700 cursor-pointer p-0.5"
            aria-label="Refresh list"
            title="Refresh list"
          >
            <RefreshCw className={`w-3 h-3 ${isFetching ? 'animate-spin text-indigo-500' : ''}`} />
          </button>
        </div>
      </div>

      {/* Filter Segmented Control */}
      <div className="inline-flex flex-wrap items-center gap-1.5 bg-white/50 backdrop-blur-md p-1.5 rounded-2xl border border-white/80 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.8),0_2px_8px_rgba(0,0,0,0.02)]">
        <button
          onClick={() => setFilter('ALL')}
          className={cn(
            'px-3 py-1.5 rounded-xl text-xs font-semibold transition-all cursor-pointer',
            filter === 'ALL' ? 'bg-gradient-to-r from-slate-900 to-indigo-950 text-white shadow-sm' : 'text-slate-600 hover:text-slate-900 hover:bg-white/60'
          )}
        >
          All Active Patients ({items?.length || 0})
        </button>

        <button
          onClick={() => setFilter('UNREVIEWED')}
          className={cn(
            'px-3 py-1.5 rounded-xl text-xs font-semibold transition-all cursor-pointer flex items-center gap-1.5',
            filter === 'UNREVIEWED' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-600 hover:text-slate-900 hover:bg-white/60'
          )}
        >
          <TestTube className="w-3.5 h-3.5" />
          Unreviewed Results ({unreviewedTotal})
        </button>

        <button
          onClick={() => setFilter('STUCK')}
          className={cn(
            'px-3 py-1.5 rounded-xl text-xs font-semibold transition-all cursor-pointer flex items-center gap-1.5',
            filter === 'STUCK' ? 'bg-gradient-to-r from-rose-500 to-rose-600 text-white shadow-sm' : 'text-slate-600 hover:text-slate-900 hover:bg-white/60'
          )}
        >
          <AlertCircle className="w-3.5 h-3.5" />
          Stuck Patients ({stuckTotal})
        </button>

        <button
          onClick={() => setFilter('HIGH_ACUITY')}
          className={cn(
            'px-3 py-1.5 rounded-xl text-xs font-semibold transition-all cursor-pointer flex items-center gap-1.5',
            filter === 'HIGH_ACUITY' ? 'bg-gradient-to-r from-amber-500 to-amber-600 text-white shadow-sm' : 'text-slate-600 hover:text-slate-900 hover:bg-white/60'
          )}
        >
          <ShieldAlert className="w-3.5 h-3.5" />
          ESI 1 & 2 Only ({highAcuityTotal})
        </button>
      </div>

      {/* Worklist Table */}
      {isLoading ? (
        <div className="space-y-3 p-6 rounded-2xl bg-white/60 backdrop-blur-xl border border-white/80 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.85),0_8px_32px_rgba(31,38,135,0.04)]">
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
        <DoctorWorklistTable items={filteredItems} onExplain={setSelectedCaseId} />
      )}

      <TriageExplainabilityDrawer caseId={selectedCaseId} onClose={() => setSelectedCaseId(null)} />
    </div>
  );
};
