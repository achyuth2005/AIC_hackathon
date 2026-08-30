import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { opsApi } from '../../api/ops';
import { MetricCard } from '../../components/ui/MetricCard';
import { Skeleton } from '../../components/ui/Skeleton';
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
          <Skeleton key={i} className="h-24 w-full rounded-xl" />
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
      <MetricCard
        label="Active ED Census"
        value={totalPatients}
        icon={<Users className="w-4 h-4" />}
        sublabel={totalOverdue > 0 ? `${totalOverdue} Overdue Reassessment` : '0 Overdue Reassessments'}
        tone={totalOverdue > 0 ? 'rose' : 'neutral'}
      />

      {/* Tile 2: Deteriorating */}
      <MetricCard
        label="Deteriorating"
        value={deteriorating_patients.length}
        icon={<Clock className="w-4 h-4" />}
        sublabel={deteriorating_patients.length > 0 ? 'Prioritized on Guardian Queue' : 'All trajectories stable'}
        tone="orange"
        active={deteriorating_patients.length > 0}
      />

      {/* Tile 3: Stuck Patients */}
      <MetricCard
        label="Stuck Patients"
        value={stuck_patients.length}
        icon={<AlertOctagon className="w-4 h-4" />}
        sublabel={stuck_patients.length > 0 ? 'Exceeded operational dwell window' : 'No flow bottlenecks'}
        tone="rose"
        active={stuck_patients.length > 0}
      />

      {/* Tile 4: Free Beds */}
      <MetricCard
        label="Available Capacity"
        value={freeBeds}
        icon={<Bed className="w-4 h-4" />}
        sublabel={`${freeBeds} of ${totalBeds} total spaces free`}
        tone="emerald"
        active={freeBeds > 0}
      />

      {/* Tile 5: Inbound Ambulances */}
      <MetricCard
        label="Inbound Transports"
        value={incoming_ambulances.length}
        icon={<Truck className="w-4 h-4" />}
        sublabel={incoming_ambulances.length > 0 ? 'Pre-arrival board active' : '0 Inbound ambulances'}
        tone="indigo"
        active={incoming_ambulances.length > 0}
      />
    </div>
  );
};
