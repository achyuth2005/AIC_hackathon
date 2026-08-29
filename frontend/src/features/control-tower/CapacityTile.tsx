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
    <Card className="bg-slate-900 border-slate-800 text-left shadow-lg">
      <CardHeader className="pb-3 flex flex-row items-center justify-between">
        <CardTitle className="text-sm flex items-center gap-2 text-slate-200">
          <Bed className="w-4 h-4 text-emerald-400" />
          <span>Tile 4: Physical & Clinician Capacity</span>
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-3">
        <div className="space-y-2">
          {data.map((c) => {
            const total = c.available + c.occupied + c.out_of_service;
            const isDeficit = c.available < c.needed_estimate;

            return (
              <div
                key={c.resource_type}
                className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-1.5"
              >
                <div className="flex items-center justify-between text-xs">
                  <span className="font-bold text-slate-200">
                    {RESOURCE_TYPE_LABELS[c.resource_type as ResourceType] || c.resource_type}
                  </span>
                  <span
                    className={`font-mono font-bold text-xs px-2 py-0.5 rounded ${
                      isDeficit
                        ? 'bg-rose-950 text-rose-300 border border-rose-800'
                        : 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                    }`}
                  >
                    {c.available} Free / {c.needed_estimate} Needed
                  </span>
                </div>

                <div className="flex items-center justify-between text-[11px] font-mono text-slate-500">
                  <span>Occupied: {c.occupied}</span>
                  <span>Out of Service: {c.out_of_service}</span>
                  <span>Total Inventory: {total}</span>
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
};
