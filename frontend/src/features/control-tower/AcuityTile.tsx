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
    <Card className="bg-slate-900 border-slate-800 text-left shadow-lg">
      <CardHeader className="pb-3 flex flex-row items-center justify-between">
        <CardTitle className="text-sm flex items-center gap-2 text-slate-200">
          <Users className="w-4 h-4 text-cyan-400" />
          <span>Tile 1: Patients by Acuity Band</span>
        </CardTitle>
        <span className="text-xs font-mono font-bold text-cyan-300 bg-cyan-950 px-2 py-0.5 rounded border border-cyan-800/60">
          {totalCases} Active
        </span>
      </CardHeader>

      <CardContent className="space-y-3">
        <div className="space-y-2">
          {data.map((band) => (
            <div
              key={band.acuity}
              className="p-2.5 rounded-xl bg-slate-950/60 border border-slate-800/80 flex items-center justify-between text-xs font-mono"
            >
              <div className="flex items-center gap-2.5">
                <AcuityBadge acuity={band.acuity} size="xs" />
                <span className="font-bold text-slate-200">
                  {band.case_count} Patient{band.case_count === 1 ? '' : 's'}
                </span>
              </div>

              {band.overdue_count > 0 ? (
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-950 text-rose-300 border border-rose-700/80 flex items-center gap-1 animate-pulse">
                  <Clock className="w-3 h-3 text-rose-400" />
                  {band.overdue_count} Overdue
                </span>
              ) : (
                <span className="text-[10px] text-slate-500 font-medium">On Schedule</span>
              )}
            </div>
          ))}
        </div>

        <div className="pt-1 flex items-center justify-between text-[11px] font-mono text-slate-400">
          <span>Total Overdue: <strong className={totalOverdue > 0 ? 'text-rose-400' : 'text-slate-300'}>{totalOverdue}</strong></span>
          <Link to="/queue" className="text-cyan-400 hover:underline">
            Open Guardian Queue →
          </Link>
        </div>
      </CardContent>
    </Card>
  );
};
