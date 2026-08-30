import React from 'react';
import { IncomingAmbulanceTile as IncomingAmbulanceTileType } from '../../types/api';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';
import { AcuityBadge } from '../../components/clinical/AcuityBadge';
import { Truck, CheckCircle2, ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';

export interface IncomingAmbulanceTileProps {
  data: IncomingAmbulanceTileType[];
}

export const IncomingAmbulanceTile: React.FC<IncomingAmbulanceTileProps> = ({ data = [] }) => {
  return (
    <Card className="text-left">
      <CardHeader className="pb-3 flex flex-row items-center justify-between">
        <CardTitle className="text-sm flex items-center gap-2 text-slate-900">
          <Truck className="w-4 h-4 text-indigo-600" />
          <span>Inbound Ambulances</span>
        </CardTitle>
        <span
          className={`text-xs font-mono font-bold tabular-nums px-2 py-0.5 rounded border ${
            data.length > 0
              ? 'bg-indigo-50 text-indigo-700 border-indigo-200'
              : 'bg-slate-100 text-slate-500 border-slate-200'
          }`}
        >
          {data.length} En Route
        </span>
      </CardHeader>

      <CardContent className="space-y-3">
        {data.length === 0 ? (
          <div className="py-8 text-center text-xs text-slate-400 font-mono space-y-1.5">
            <CheckCircle2 className="w-6 h-6 text-emerald-500 mx-auto" />
            <div>No inbound ambulance transports actively en route.</div>
          </div>
        ) : (
          <div className="space-y-2">
            {data.map((amb) => (
              <Link
                key={amb.case_id}
                to={`/ambulance/${amb.case_id}`}
                className="p-3 rounded-xl bg-slate-50 border border-slate-200 hover:border-indigo-300 hover:bg-indigo-50/40 flex items-center justify-between transition-colors block group"
              >
                <div className="space-y-0.5">
                  <div className="font-bold text-xs text-slate-900 group-hover:text-indigo-700">
                    {amb.display_name || `Inbound Case ${amb.case_id.substring(0, 8)}`}
                  </div>
                  <div className="text-[10px] font-mono text-indigo-600">
                    Pre-Arrival Assessment Active
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {amb.predicted_acuity != null ? (
                    <AcuityBadge acuity={amb.predicted_acuity} size="xs" />
                  ) : (
                    <span className="text-[10px] font-mono text-slate-400">Unscored</span>
                  )}
                  <ArrowRight className="w-3 h-3 text-slate-400 group-hover:text-indigo-600" />
                </div>
              </Link>
            ))}
          </div>
        )}

        <div className="pt-1 flex justify-end">
          <Link
            to="/ambulance"
            className="text-xs text-indigo-600 hover:underline font-medium inline-flex items-center gap-1"
          >
            <span>Open Pre-Arrival Board</span>
            <ArrowRight className="w-3 h-3" />
          </Link>
        </div>
      </CardContent>
    </Card>
  );
};
