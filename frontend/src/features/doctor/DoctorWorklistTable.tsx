import React from 'react';
import { DoctorQueueItemResponse } from '../../types/api';
import { AcuityBadge } from '../../components/clinical/AcuityBadge';
import { TrendArrow } from '../../components/clinical/TrendArrow';
import { VitalTrendSpark } from './VitalTrendSpark';
import { Table, TableHeader, TableBody, TableHead, TableRow, TableCell } from '../../components/ui/Table';
import { formatMinutes } from '../../lib/datetime';
import { useNavigate } from 'react-router-dom';
import { TestTube, AlertCircle, Bed, User, Sparkles } from 'lucide-react';

export interface DoctorWorklistTableProps {
  items: DoctorQueueItemResponse[];
  /** Opens the Triage Explainability drawer for this case without navigating away. */
  onExplain?: (caseId: string) => void;
}

export const DoctorWorklistTable: React.FC<DoctorWorklistTableProps> = ({ items, onExplain }) => {
  const navigate = useNavigate();

  if (items.length === 0) {
    return (
      <div className="p-12 text-center text-slate-500 bg-white/60 backdrop-blur-xl rounded-3xl border border-white/80 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.85),0_8px_32px_rgba(31,38,135,0.04)]">
        No patients match the current physician worklist filter.
      </div>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead scope="col" className="w-40">Acuity & Trend</TableHead>
          <TableHead scope="col">Patient & Bed Location</TableHead>
          <TableHead scope="col" className="w-44">Time in Care</TableHead>
          <TableHead scope="col">Recent Vital Trends</TableHead>
          <TableHead scope="col" className="w-56 text-right">Physician Attention</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {items.map((item) => {
          const {
            case_id,
            display_name,
            mrn,
            age_years,
            sex,
            final_acuity,
            acuity_trend,
            waiting_minutes,
            time_in_current_band_minutes,
            assigned_resource_label,
            unreviewed_results_count,
            stuck_flagged,
            recent_vital_summary,
          } = item;

          return (
            <TableRow
              key={case_id}
              onClick={() => navigate(`/doctor/${case_id}`)}
              className="cursor-pointer group hover:bg-white/60 transition-colors"
            >
              {/* 1. Acuity & Trend */}
              <TableCell className="py-4 px-4">
                <div className="flex items-center gap-2">
                  <AcuityBadge acuity={final_acuity} size="sm" />
                  <TrendArrow trend={acuity_trend} />
                </div>
              </TableCell>

              {/* 2. Patient & Bed Location */}
              <TableCell className="py-4 px-4">
                <div className="space-y-0.5">
                  <div className="font-bold text-slate-900 text-sm flex items-center gap-2 group-hover:text-indigo-600 transition-colors">
                    <span>{display_name || 'Anonymous Walk-in'}</span>
                    {mrn && (
                      <span className="text-[10px] font-mono tabular-nums text-slate-600 bg-slate-500/10 px-1.5 py-0.5 rounded-full border border-slate-300/30 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.7)]">
                        {mrn}
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-3 text-xs text-slate-500 font-mono">
                    {age_years != null && (
                      <span className="flex items-center gap-1">
                        <User className="w-3 h-3 text-slate-400" />
                        {age_years}y {sex ? `• ${sex}` : ''}
                      </span>
                    )}
                    <span className="flex items-center gap-1 text-indigo-600">
                      <Bed className="w-3 h-3" />
                      {assigned_resource_label || 'Unassigned (Waiting Room)'}
                    </span>
                  </div>
                </div>
              </TableCell>

              {/* 3. Wait Time & Time in Band */}
              <TableCell className="py-4 px-4 text-xs font-mono tabular-nums text-slate-600">
                <div className="space-y-0.5">
                  <div>In Band: <strong className="text-slate-900">{formatMinutes(time_in_current_band_minutes)}</strong></div>
                  <div className="text-[11px] text-slate-400">Total: {formatMinutes(waiting_minutes)}</div>
                </div>
              </TableCell>

              {/* 4. Vitals Trend Sparks */}
              <TableCell className="py-4 px-4">
                <div className="flex flex-wrap items-center gap-1.5">
                  {recent_vital_summary && Object.keys(recent_vital_summary).length > 0 ? (
                    Object.entries(recent_vital_summary).map(([concept, data]) => {
                      const typedData = data as {
                        latest_value?: unknown;
                        previous_value?: unknown;
                        trend_direction?: string;
                        unit?: string | null;
                      };
                      return (
                        <VitalTrendSpark
                          key={concept}
                          concept={concept}
                          latestValue={typedData.latest_value as number | string | boolean | null}
                          previousValue={typedData.previous_value}
                          direction={typedData.trend_direction}
                          unit={typedData.unit}
                        />
                      );
                    })
                  ) : (
                    <span className="text-[11px] text-slate-400 italic font-mono">
                      No vitals recorded
                    </span>
                  )}
                </div>
              </TableCell>

              {/* 5. Physician Attention Chips & Explain Action */}
              <TableCell className="py-4 px-4 text-right">
                <div className="flex items-center justify-end gap-2">
                  <div className="flex flex-col items-end gap-1">
                    {unreviewed_results_count > 0 && (
                      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-indigo-500/15 text-indigo-800 border border-indigo-300/40 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.7)]">
                        <TestTube className="w-3 h-3 text-indigo-600" />
                        {unreviewed_results_count} Result{unreviewed_results_count === 1 ? '' : 's'} Ready
                      </span>
                    )}

                    {stuck_flagged && (
                      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-rose-500/15 text-rose-800 border border-rose-300/40 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.7)]">
                        <AlertCircle className="w-3 h-3 text-rose-600" />
                        Stuck Patient
                      </span>
                    )}

                    {!unreviewed_results_count && !stuck_flagged && (
                      <span className="text-xs text-slate-400 font-mono">Routine Care</span>
                    )}
                  </div>

                  {onExplain && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onExplain(case_id);
                      }}
                      className="shrink-0 p-1.5 rounded-lg text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 border border-transparent hover:border-indigo-200 transition-colors cursor-pointer"
                      aria-label="Explain triage decision"
                      title="Explain triage decision"
                    >
                      <Sparkles className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
};
