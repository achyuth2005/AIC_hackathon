import React from 'react';
import { QueueEntry } from '../../types/api';
import { AcuityBadge } from '../../components/clinical/AcuityBadge';
import { ConfidenceBadge } from '../../components/clinical/ConfidenceBadge';
import { AttentionFlagChip } from '../../components/clinical/AttentionFlagChip';
import { TrendArrow } from '../../components/clinical/TrendArrow';
import { WaitTimeRange } from '../../components/clinical/WaitTimeRange';
import { QueueRowActions } from './QueueRowActions';
import { formatMinutes, formatRelative } from '../../lib/datetime';
import { TableRow, TableCell } from '../../components/ui/Table';
import { useNavigate } from 'react-router-dom';
import { Clock, Zap, AlertCircle } from 'lucide-react';

export interface QueueRowProps {
  entry: QueueEntry;
  index: number;
}

export const QueueRow: React.FC<QueueRowProps> = ({ entry, index }) => {
  const navigate = useNavigate();
  const {
    case_id,
    display_name,
    mrn,
    final_acuity,
    confidence_band,
    should_abstain,
    deterioration_trend,
    time_in_current_band_minutes,
    arrival_time,
    waiting_minutes,
    reassessment,
    emergency_bypass_active,
    wait_time_estimate,
    one_line_presentation,
    primary_attention_flag,
  } = entry;

  return (
    <TableRow
      onClick={() => navigate(`/cases/${case_id}`)}
      className={`cursor-pointer group transition-all duration-150 ${
        emergency_bypass_active
          ? 'bg-red-950/30 hover:bg-red-950/50 border-l-4 border-l-red-600'
          : reassessment.is_due
          ? 'bg-rose-950/15 hover:bg-rose-950/30 border-l-4 border-l-rose-500'
          : 'hover:bg-slate-800/40 border-l-4 border-l-transparent'
      }`}
    >
      {/* Column 1: Acuity & Confidence */}
      <TableCell className="w-48 align-top py-3.5">
        <div className="space-y-1.5">
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono text-slate-500 w-5 text-right font-bold">
              #{index + 1}
            </span>
            <AcuityBadge
              acuity={final_acuity}
              size="md"
              isBypass={emergency_bypass_active}
            />
          </div>
          <div className="pl-7">
            <ConfidenceBadge band={confidence_band} shouldAbstain={should_abstain} size="sm" />
          </div>
        </div>
      </TableCell>

      {/* Column 2: One-Line Presentation & Identity */}
      <TableCell className="align-top py-3.5 max-w-sm">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="font-bold text-slate-100 text-sm group-hover:text-cyan-300 transition-colors">
              {display_name || 'Anonymous Walk-in'}
            </span>
            {mrn && (
              <span className="text-[10px] font-mono text-slate-400 px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700/60">
                {mrn}
              </span>
            )}
            {emergency_bypass_active && (
              <span className="inline-flex items-center gap-1 text-[10px] font-bold text-red-300 bg-red-900/80 px-1.5 py-0.5 rounded border border-red-600 animate-pulse">
                <Zap className="w-3 h-3 text-red-400 fill-red-400" />
                BYPASS
              </span>
            )}
          </div>

          <p className="text-xs text-slate-300 line-clamp-2 leading-relaxed">
            {one_line_presentation || 'Initial clinical presentation pending.'}
          </p>

          <div className="flex items-center gap-3 text-[11px] text-slate-400 font-mono pt-0.5">
            <span>Arrived: {formatRelative(arrival_time)}</span>
            <span>•</span>
            <span className="text-slate-300">Wait: {formatMinutes(waiting_minutes)}</span>
          </div>
        </div>
      </TableCell>

      {/* Column 3: Time in Band & Reassessment Clock */}
      <TableCell className="w-64 align-top py-3.5">
        <div className="space-y-2">
          {/* Reassessment State */}
          <div className="flex items-center justify-between text-xs font-mono">
            <span className="text-slate-400 flex items-center gap-1 text-[11px]">
              <Clock className="w-3 h-3 text-slate-400" />
              In Band:
            </span>
            <span className="font-bold text-slate-200">
              {formatMinutes(time_in_current_band_minutes)}
            </span>
          </div>

          {reassessment.is_due ? (
            <div className="flex items-center gap-1.5 px-2 py-1 rounded bg-rose-950/70 border border-rose-600/70 text-rose-300 text-[11px] font-mono font-bold animate-pulse">
              <AlertCircle className="w-3.5 h-3.5 text-rose-400 shrink-0" />
              <span>
                OVERDUE {reassessment.minutes_overdue ? `(+${formatMinutes(reassessment.minutes_overdue)})` : ''}
              </span>
            </div>
          ) : (
            <div className="text-[11px] text-slate-400 font-mono">
              Reassessment due in {formatMinutes(reassessment.interval_minutes ? Math.max(0, reassessment.interval_minutes - reassessment.minutes_since_last_reassessment) : 0)}
            </div>
          )}

          {/* Wait Time Range */}
          <WaitTimeRange estimate={wait_time_estimate} compact={true} />
        </div>
      </TableCell>

      {/* Column 4: Attention Flag, Trend & Actions */}
      <TableCell className="w-72 align-top py-3.5 text-right">
        <div className="flex flex-col items-end gap-2.5">
          <div className="flex items-center gap-2">
            <TrendArrow trend={deterioration_trend} showLabel={false} />
            <AttentionFlagChip flag={primary_attention_flag} size="sm" />
          </div>

          <QueueRowActions entry={entry} />
        </div>
      </TableCell>
    </TableRow>
  );
};
