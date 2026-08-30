import React from 'react';
import { AcuityBandTile } from '../../types/api';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';
import { AcuityBadge } from '../../components/clinical/AcuityBadge';
import { Users, Clock } from 'lucide-react';
import { Link } from 'react-router-dom';

export interface AcuityTileProps {
  data: AcuityBandTile[];
}

export const AcuityTile: React.FC<AcuityTileProps> = ({ data = [] }) => {
  const totalCases = data.reduce((sum, item) => sum + item.case_count, 0);
  const totalOverdue = data.reduce((sum, item) => sum + item.overdue_count, 0);

  return (
    <Card className="text-left">
      <CardHeader className="pb-3 flex flex-row items-center justify-between">
        <CardTitle className="text-sm flex items-center gap-2 text-slate-900">
          <Users className="w-4 h-4 text-indigo-600" />
          <span>Acuity Distribution</span>
        </CardTitle>
        <span className="text-xs font-mono font-bold tabular-nums text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded border border-indigo-200">
          {totalCases} Active
        </span>
      </CardHeader>

      <CardContent className="space-y-3">
        <div className="space-y-2">
          {data.map((band) => (
            <div
              key={band.acuity}
              className="p-2.5 rounded-xl bg-white/50 border border-white/80 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.7)] flex items-center justify-between text-xs font-mono backdrop-blur-sm"
            >
              <div className="flex items-center gap-2.5">
                <AcuityBadge acuity={band.acuity} size="xs" />
                <span className="font-bold text-slate-700 tabular-nums">
                  {band.case_count} Patient{band.case_count === 1 ? '' : 's'}
                </span>
              </div>

              {band.overdue_count > 0 ? (
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold tabular-nums bg-rose-500/15 text-rose-800 border border-rose-300/40 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.7)] flex items-center gap-1">
                  <Clock className="w-3 h-3 text-rose-600" />
                  {band.overdue_count} Overdue
                </span>
              ) : (
                <span className="text-[10px] text-slate-400 font-medium">On Schedule</span>
              )}
            </div>
          ))}
        </div>

        <div className="pt-1 flex items-center justify-between text-[11px] font-mono tabular-nums text-slate-500">
          <span>Total Overdue: <strong className={totalOverdue > 0 ? 'text-red-600' : 'text-slate-700'}>{totalOverdue}</strong></span>
          <Link to="/queue" className="text-indigo-600 hover:underline font-sans font-medium">
            Open Guardian Queue →
          </Link>
        </div>
      </CardContent>
    </Card>
  );
};
