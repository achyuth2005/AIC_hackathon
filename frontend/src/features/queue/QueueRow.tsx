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
          ? 'bg-rose-500/[0.08] hover:bg-rose-500/[0.12] border-l-4 border-l-rose-500'
          : reassessment.is_due
          ? 'bg-rose-500/[0.05] hover:bg-rose-500/[0.09] border-l-4 border-l-rose-400'
          : 'hover:bg-white/60 border-l-4 border-l-transparent'
      }`}
    >
      {/* Column 1: Acuity & Confidence */}
      <TableCell className="w-48 align-top py-4.5 px-4">
        <div className="space-y-1.5">
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono tabular-nums text-slate-400 w-5 text-right font-bold">
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
      <TableCell className="align-top py-4.5 px-4 max-w-sm">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="font-bold text-slate-900 text-sm group-hover:text-indigo-600 transition-colors">
              {display_name || 'Anonymous Walk-in'}
            </span>
            {mrn && (
              <span className="text-[10px] font-mono tabular-nums text-slate-600 px-1.5 py-0.5 rounded-full bg-slate-500/10 border border-slate-300/30 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.7)]">
                {mrn}
              </span>
            )}
            {emergency_bypass_active && (
              <span className="inline-flex items-center gap-1 text-[10px] font-bold text-rose-800 bg-rose-500/15 px-2 py-0.5 rounded-full border border-rose-300/40 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.7)]">
                <Zap className="w-3 h-3 text-rose-600 fill-rose-600" />
                BYPASS
              </span>
            )}
          </div>

          <p className="text-xs text-slate-600 font-normal leading-relaxed line-clamp-2">
            {one_line_presentation || 'Initial clinical presentation pending.'}
          </p>

          <div className="flex items-center gap-3 text-[11px] text-slate-400 font-mono tabular-nums pt-0.5">
            <span>Arrived: {formatRelative(arrival_time)}</span>
            <span>•</span>
            <span className="text-slate-500 font-medium">Wait: {formatMinutes(waiting_minutes)}</span>
          </div>
        </div>
      </TableCell>

      {/* Column 3: Time in Band & Reassessment Clock */}
      <TableCell className="w-64 align-top py-4.5 px-4">
        <div className="space-y-2">
          {/* Reassessment State */}
          <div className="flex items-center justify-between text-xs font-mono tabular-nums">
            <span className="text-slate-400 flex items-center gap-1 text-[11px]">
              <Clock className="w-3 h-3 text-slate-400" />
              In Band:
            </span>
            <span className="font-bold text-slate-800">
              {formatMinutes(time_in_current_band_minutes)}
            </span>
          </div>

          {reassessment.is_due ? (
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-rose-500/15 border border-rose-300/40 text-rose-800 text-[11px] font-mono font-bold shadow-[inset_0_0_0_1px_rgba(255,255,255,0.7)] backdrop-blur-sm">
              <AlertCircle className="w-3.5 h-3.5 text-rose-600 shrink-0" />
              <span>
                OVERDUE {reassessment.minutes_overdue ? `(+${formatMinutes(reassessment.minutes_overdue)})` : ''}
              </span>
            </div>
          ) : (
            <div className="text-[11px] text-slate-400 font-mono tabular-nums">
              Reassessment due in {formatMinutes(reassessment.interval_minutes ? Math.max(0, reassessment.interval_minutes - reassessment.minutes_since_last_reassessment) : 0)}
            </div>
          )}

          {/* Wait Time Range */}
          <WaitTimeRange estimate={wait_time_estimate} compact={true} />
        </div>
      </TableCell>

      {/* Column 4: Attention Flag, Trend & Actions */}
      <TableCell className="w-72 align-top py-4.5 px-4 text-right">
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
