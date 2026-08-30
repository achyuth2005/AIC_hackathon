import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';
import { Bed } from 'lucide-react';
import { RESOURCE_TYPE_LABELS } from '../../lib/enums';
import { ResourceType } from '../../types/enums';

export interface CapacityItem {
  resource_type: string;
  available: number;
  occupied: number;
  out_of_service: number;
  needed_estimate: number;
}

export interface CapacityTileProps {
  data: CapacityItem[];
}

export const CapacityTile: React.FC<CapacityTileProps> = ({ data = [] }) => {
  return (
    <Card className="text-left">
      <CardHeader className="pb-3 flex flex-row items-center justify-between">
        <CardTitle className="text-sm flex items-center gap-2 text-slate-900">
          <Bed className="w-4 h-4 text-emerald-600" />
          <span>Physical & Staff Capacity</span>
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-3">
        <div className="space-y-2">
          {data.map((c) => {
            const total = c.available + c.occupied + c.out_of_service;
            const isDeficit = c.available < c.needed_estimate;
            const pctOccupied = total > 0 ? Math.round((c.occupied / total) * 100) : 0;

            return (
              <div
                key={c.resource_type}
                className="p-3 rounded-xl bg-slate-50 border border-slate-200/80 space-y-2"
              >
                <div className="flex items-center justify-between text-xs">
                  <span className="font-bold text-slate-700">
                    {RESOURCE_TYPE_LABELS[c.resource_type as ResourceType] || c.resource_type}
                  </span>
                  <span
                    className={`font-mono font-bold text-xs tabular-nums px-2 py-0.5 rounded ${
                      isDeficit
                        ? 'bg-red-50 text-red-700 border border-red-200'
                        : 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                    }`}
                  >
                    {c.available} Free / {c.needed_estimate} Needed
                  </span>
                </div>

                {/* Occupied vs available progress bar */}
                <div className="h-1.5 rounded-full bg-slate-200 overflow-hidden">
                  <div
                    className={`h-full rounded-full ${isDeficit ? 'bg-red-500' : 'bg-emerald-500'}`}
                    style={{ width: `${pctOccupied}%` }}
                  />
                </div>

                <div className="flex items-center justify-between text-[11px] font-mono tabular-nums text-slate-400">
                  <span>Occupied: {c.occupied}</span>
                  <span>Out of Service: {c.out_of_service}</span>
                  <span>Total: {total}</span>
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
};
