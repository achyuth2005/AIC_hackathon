import { SurgeModeToggle } from '../features/ops/SurgeModeToggle';
import { FlowMetricsCards } from '../features/ops/FlowMetricsCards';
import { StuckPatientList } from '../features/ops/StuckPatientList';
import { DwellTimeDistribution } from '../features/ops/DwellTimeDistribution';
import { ResourceManager } from '../features/ops/ResourceManager';
import { Activity } from 'lucide-react';

export const OpsPage: React.FC = () => {
  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-16 animate-fade-in text-left">
      {/* 1. Page Header */}
      <div className="border-b border-slate-800 pb-5">
        <h1 className="text-2xl font-extrabold tracking-tight text-slate-100 flex items-center gap-2.5">
          <Activity className="w-7 h-7 text-cyan-400" />
          Emergency Department Operations & Flow
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          Hospital flow coordination, stuck patient bottleneck surface, and capacity management.
        </p>
      </div>

      {/* 2. Surge Burst Simulation */}
      <SurgeModeToggle />

      {/* 3. Department Flow Metrics Cards */}
      <FlowMetricsCards />

      {/* 3. Operationally Stuck Patients Monitoring List */}
      <StuckPatientList />

      {/* 4. Acuity-Stratified Dwell Times vs Target Benchmarks */}
      <DwellTimeDistribution />

      {/* 5. Department Capacity & Bed Manager */}
      <ResourceManager />
    </div>
  );
};
