import React from 'react';
import { DeterioratingPatientTile } from '../../types/api';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';
import { AcuityBadge } from '../../components/clinical/AcuityBadge';
import { TrendingUp, ArrowRight, CheckCircle2 } from 'lucide-react';
import { Link } from 'react-router-dom';

export interface DeterioratingTileProps {
  data: DeterioratingPatientTile[];
}

export const DeterioratingTile: React.FC<DeterioratingTileProps> = ({ data = [] }) => {
  return (
    <Card className="text-left border-orange-200/80">
      <CardHeader className="pb-3 flex flex-row items-center justify-between">
        <CardTitle className="text-sm flex items-center gap-2 text-orange-800">
          <TrendingUp className="w-4 h-4 text-orange-600" />
          <span>Deteriorating Trajectories</span>
        </CardTitle>
        <span
          className={`text-xs font-mono font-bold tabular-nums px-2 py-0.5 rounded border ${
            data.length > 0
              ? 'bg-orange-50 text-orange-700 border-orange-200'
              : 'bg-slate-100 text-slate-500 border-slate-200'
          }`}
        >
          {data.length} Cases
        </span>
      </CardHeader>

      <CardContent className="space-y-3">
        {data.length === 0 ? (
          <div className="py-8 text-center text-xs text-slate-400 font-mono space-y-1.5">
            <CheckCircle2 className="w-6 h-6 text-emerald-500 mx-auto" />
            <div>No active physiological deterioration detected.</div>
          </div>
        ) : (
          <div className="space-y-2">
            {data.map((p) => (
              <Link
                key={p.case_id}
                to={`/cases/${p.case_id}`}
                className="p-3 rounded-xl bg-orange-50/60 border border-orange-200 hover:border-orange-400 hover:bg-orange-50 flex items-center justify-between transition-colors block group"
              >
                <div className="space-y-0.5">
                  <div className="font-bold text-xs text-slate-900 group-hover:text-orange-800">
                    {p.display_name || `Case ${p.case_id.substring(0, 8)}`}
                  </div>
                  <div className="text-[10px] font-mono text-slate-500">
                    Time Engine Auto-Prioritized
                  </div>
                </div>

                <div className="flex items-center gap-1.5">
                  <AcuityBadge acuity={p.from_acuity} size="xs" showLabel={false} />
                  <ArrowRight className="w-3 h-3 text-orange-500" />
                  <AcuityBadge acuity={p.to_acuity} size="xs" showLabel={false} />
                </div>
              </Link>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
};
