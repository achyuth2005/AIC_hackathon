import React from 'react';
import { StuckPatternResult } from '../../types/api';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';
import { AlertOctagon, CheckCircle2, ArrowRight, Clock } from 'lucide-react';
import { formatMinutes } from '../../lib/datetime';
import { Link } from 'react-router-dom';

export interface StuckPatientsTileProps {
  data: StuckPatternResult[];
}

export const StuckPatientsTile: React.FC<StuckPatientsTileProps> = ({ data = [] }) => {
  return (
    <Card className="bg-slate-900 border-rose-900/60 text-left shadow-lg">
      <CardHeader className="pb-3 flex flex-row items-center justify-between">
        <CardTitle className="text-sm flex items-center gap-2 text-rose-300">
          <AlertOctagon className="w-4 h-4 text-rose-400" />
          <span>Tile 3: Stuck Patient Bottlenecks</span>
        </CardTitle>
        <span
          className={`text-xs font-mono font-bold px-2 py-0.5 rounded border ${
            data.length > 0
              ? 'bg-rose-950 text-rose-300 border-rose-700/80'
              : 'bg-slate-800 text-slate-400 border-slate-700'
          }`}
        >
          {data.length} Stuck
        </span>
      </CardHeader>

      <CardContent className="space-y-3">
        {data.length === 0 ? (
          <div className="py-8 text-center text-xs text-slate-500 font-mono space-y-1.5">
            <CheckCircle2 className="w-6 h-6 text-emerald-400 mx-auto" />
            <div>No active operational bottlenecks.</div>
          </div>
        ) : (
          <div className="space-y-2">
            {data.map((p, idx) => (
              <Link
                key={`${p.case_id}-${idx}`}
                to={`/cases/${p.case_id}`}
                className="p-3 rounded-xl bg-slate-950/80 border border-rose-900/60 hover:border-rose-500 flex items-center justify-between transition-colors block group"
              >
                <div className="space-y-0.5">
                  <div className="font-bold text-xs text-slate-100 group-hover:text-cyan-300">
                    {p.label}
                  </div>
                  <div className="text-[10px] font-mono text-slate-500">
                    Route: {p.route_to}
                  </div>
                </div>

                <div className="text-right text-xs font-mono text-rose-400 font-bold flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {formatMinutes(p.minutes_overdue)}
                </div>
              </Link>
            ))}
          </div>
        )}

        <div className="pt-1 flex justify-end">
          <Link to="/ops" className="text-xs text-cyan-400 hover:underline font-mono inline-flex items-center gap-1">
            <span>Manage on Ops Board</span>
            <ArrowRight className="w-3 h-3" />
          </Link>
        </div>
      </CardContent>
    </Card>
  );
};
