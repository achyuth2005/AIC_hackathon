import React from 'react';
import { DoctorQueueItemResponse } from '../../types/api';
import { AcuityBadge } from '../../components/clinical/AcuityBadge';
import { TrendArrow } from '../../components/clinical/TrendArrow';
import { VitalTrendSpark } from './VitalTrendSpark';
import { Table, TableHeader, TableBody, TableHead, TableRow, TableCell } from '../../components/ui/Table';
import { formatMinutes } from '../../lib/datetime';
import { useNavigate } from 'react-router-dom';
import { TestTube, AlertCircle, Bed, User } from 'lucide-react';

export interface DoctorWorklistTableProps {
  items: DoctorQueueItemResponse[];
}

export const DoctorWorklistTable: React.FC<DoctorWorklistTableProps> = ({ items }) => {
  const navigate = useNavigate();

  if (items.length === 0) {
    return (
      <div className="p-12 text-center text-slate-500 bg-slate-900/40 rounded-2xl border border-dashed border-slate-800">
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
          <TableHead scope="col" className="w-52 text-right">Physician Attention</TableHead>
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
              onClick={() => navigate(`/doctor/cases/${case_id}`)}
              className="cursor-pointer hover:bg-slate-800/60 transition-colors"
            >
              {/* 1. Acuity & Trend */}
              <TableCell>
                <div className="flex items-center gap-2">
                  <AcuityBadge acuity={final_acuity} size="sm" />
                  <TrendArrow trend={acuity_trend} />
                </div>
              </TableCell>

              {/* 2. Patient & Bed Location */}
              <TableCell>
                <div className="space-y-0.5">
                  <div className="font-bold text-slate-100 text-sm flex items-center gap-2">
                    <span>{display_name || 'Anonymous Walk-in'}</span>
                    {mrn && (
                      <span className="text-[10px] font-mono text-slate-400 bg-slate-800 px-1.5 py-0.2 rounded border border-slate-700">
                        {mrn}
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-3 text-xs text-slate-400 font-mono">
                    {age_years != null && (
                      <span className="flex items-center gap-1">
                        <User className="w-3 h-3 text-slate-500" />
                        {age_years}y {sex ? `• ${sex}` : ''}
                      </span>
                    )}
                    <span className="flex items-center gap-1 text-cyan-300">
                      <Bed className="w-3 h-3" />
                      {assigned_resource_label || 'Unassigned (Waiting Room)'}
                    </span>
                  </div>
                </div>
              </TableCell>

              {/* 3. Wait Time & Time in Band */}
              <TableCell className="text-xs font-mono text-slate-300">
                <div className="space-y-0.5">
                  <div>In Band: <strong className="text-white">{formatMinutes(time_in_current_band_minutes)}</strong></div>
                  <div className="text-[11px] text-slate-400">Total: {formatMinutes(waiting_minutes)}</div>
                </div>
              </TableCell>

              {/* 4. Vitals Trend Sparks */}
              <TableCell>
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
                    <span className="text-[11px] text-slate-600 italic font-mono">
                      No vitals recorded
                    </span>
                  )}
                </div>
              </TableCell>

              {/* 5. Physician Attention Chips */}
              <TableCell className="text-right">
                <div className="flex flex-col items-end gap-1">
                  {unreviewed_results_count > 0 && (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-indigo-950 text-indigo-300 border border-indigo-600/80 animate-pulse">
                      <TestTube className="w-3 h-3 text-indigo-400" />
                      {unreviewed_results_count} Result{unreviewed_results_count === 1 ? '' : 's'} Ready
                    </span>
                  )}

                  {stuck_flagged && (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-rose-950 text-rose-300 border border-rose-700/80">
                      <AlertCircle className="w-3 h-3 text-rose-400" />
                      Stuck Patient
                    </span>
                  )}

                  {!unreviewed_results_count && !stuck_flagged && (
                    <span className="text-xs text-slate-500 font-mono">Routine Care</span>
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
