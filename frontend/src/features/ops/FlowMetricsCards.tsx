import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { opsApi } from '../../api/ops';
import { Card, CardContent } from '../../components/ui/Card';
import { Users, Bed, AlertOctagon, Truck, Clock } from 'lucide-react';

export const FlowMetricsCards: React.FC = () => {
  const { data: ct, isLoading } = useQuery({
    queryKey: ['control-tower'],
    queryFn: () => opsApi.getControlTower('default'),
    refetchInterval: 5000,
  });

  if (isLoading || !ct) {
    return (
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="h-24 bg-slate-900 rounded-xl animate-pulse border border-slate-800" />
        ))}
      </div>
    );
  }

  const {
    patients_by_acuity_band,
    deteriorating_patients,
    stuck_patients,
    capacity,
    incoming_ambulances,
  } = ct;

  const totalPatients = patients_by_acuity_band.reduce((sum, b) => sum + b.case_count, 0);
  const totalOverdue = patients_by_acuity_band.reduce((sum, b) => sum + b.overdue_count, 0);
  const totalBeds = capacity.reduce((sum, c) => sum + c.available + c.occupied + c.out_of_service, 0);
  const freeBeds = capacity.reduce((sum, c) => sum + c.available, 0);

  return (
    <div className="grid grid-cols-2 lg:grid-cols-5 gap-3 text-left">
      {/* Tile 1: Acuity & Overdue */}
      <Card className="bg-slate-900 border-slate-800">
        <CardContent className="p-4 space-y-1">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-[10px] font-bold uppercase tracking-wider">Active ED Census</span>
            <Users className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-black font-mono text-slate-100">{totalPatients}</div>
          <div className="text-[11px] text-slate-400">
            {totalOverdue > 0 ? (
              <span className="text-rose-400 font-bold">{totalOverdue} Overdue Reassessment</span>
            ) : (
              '0 Overdue Reassessments'
            )}
          </div>
        </CardContent>
      </Card>

      {/* Tile 2: Deteriorating */}
      <Card className={`border ${deteriorating_patients.length > 0 ? 'bg-orange-950/20 border-orange-600/70' : 'bg-slate-900 border-slate-800'}`}>
        <CardContent className="p-4 space-y-1">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-[10px] font-bold uppercase tracking-wider">Deteriorating</span>
            <Clock className="w-4 h-4 text-orange-400" />
          </div>
          <div className="text-2xl font-black font-mono text-slate-100">{deteriorating_patients.length}</div>
          <div className="text-[11px] text-slate-400">
            {deteriorating_patients.length > 0 ? 'Prioritized on Guardian Queue' : 'All trajectories stable'}
          </div>
        </CardContent>
      </Card>

      {/* Tile 3: Stuck Patients */}
      <Card className={`border ${stuck_patients.length > 0 ? 'bg-rose-950/30 border-rose-600/80' : 'bg-slate-900 border-slate-800'}`}>
        <CardContent className="p-4 space-y-1">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-[10px] font-bold uppercase tracking-wider">Stuck Patients</span>
            <AlertOctagon className="w-4 h-4 text-rose-400" />
          </div>
          <div className="text-2xl font-black font-mono text-rose-200">{stuck_patients.length}</div>
          <div className="text-[11px] text-slate-400">
            {stuck_patients.length > 0 ? 'Exceeded operational dwell window' : 'No flow bottlenecks'}
          </div>
        </CardContent>
      </Card>

      {/* Tile 4: Free Beds */}
      <Card className="bg-slate-900 border-slate-800">
        <CardContent className="p-4 space-y-1">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-[10px] font-bold uppercase tracking-wider">Available Capacity</span>
            <Bed className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-black font-mono text-emerald-400">{freeBeds}</div>
          <div className="text-[11px] text-slate-400 font-mono">
            {freeBeds} of {totalBeds} total spaces free
          </div>
        </CardContent>
      </Card>

      {/* Tile 5: Inbound Ambulances */}
      <Card className="bg-slate-900 border-slate-800">
        <CardContent className="p-4 space-y-1">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-[10px] font-bold uppercase tracking-wider">Inbound Transports</span>
            <Truck className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-black font-mono text-cyan-300">{incoming_ambulances.length}</div>
          <div className="text-[11px] text-slate-400">
            {incoming_ambulances.length > 0 ? 'Pre-arrival board active' : '0 Inbound ambulances'}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
