import React, { useState } from 'react';
import { useSeedDemo, useSurgeSimulation } from '../../hooks/useDemoScenarios';
import { DemoScenario } from '../../types/api';
import { ScenarioCard } from './ScenarioCard';
import { SurgeBurstPanel } from './SurgeBurstPanel';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { Play, Sparkles, Flame } from 'lucide-react';

export interface ScenarioRunnerListProps {
  initialScenarios?: DemoScenario[];
}

export const ScenarioRunnerList: React.FC<ScenarioRunnerListProps> = () => {
  const { mutate: seedDemo, isPending: isSeedPending, data: seededScenarios } = useSeedDemo();
  const { mutate: runSurge, isPending: isSurgePending, data: surgeResult } = useSurgeSimulation();

  const [searchQuery, setSearchQuery] = useState('');
  const [scenarios, setScenarios] = useState<DemoScenario[]>([]);

  // When seed completes, update scenarios list
  React.useEffect(() => {
    if (seededScenarios) {
      setScenarios(seededScenarios);
    }
  }, [seededScenarios]);

  const filteredScenarios = scenarios.filter((s) => {
    const q = searchQuery.toLowerCase();
    return (
      s.title.toLowerCase().includes(q) ||
      s.demonstrates.toLowerCase().includes(q) ||
      String(s.number).includes(q)
    );
  });

  return (
    <div className="space-y-8 text-left">
      {/* 1. Control Action Bar */}
      <div className="p-6 rounded-2xl bg-white border border-slate-200/80 shadow-card-lg flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-indigo-600" />
            <h2 className="text-lg font-bold text-slate-900">
              Phase 14.1 Synthetic Scenario Generator
            </h2>
          </div>
          <p className="text-xs text-slate-500 max-w-xl">
            Seed the full suite of 20 clinical scenarios covering emergency bypass, PEWS, ML challenge, resource conflicts, and diagnostic workflows.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <Button
            variant="primary"
            size="md"
            isLoading={isSeedPending}
            onClick={() => seedDemo()}
            leftIcon={<Play className="w-4 h-4" />}
          >
            Seed 20 Demo Patients
          </Button>

          <Button
            variant="primary"
            size="md"
            isLoading={isSurgePending}
            onClick={() => runSurge({ baseline_count: 10, multiplier: 3 })}
            leftIcon={<Flame className="w-4 h-4" />}
            className="bg-indigo-600 hover:bg-indigo-700 active:bg-indigo-800 focus-visible:ring-indigo-500"
          >
            Run 3x Surge Simulation
          </Button>
        </div>
      </div>

      {/* 2. Surge Simulation Results Surface */}
      {surgeResult && <SurgeBurstPanel result={surgeResult} />}

      {/* 3. Scenarios Catalog */}
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <h3 className="text-base font-bold text-slate-900">
              Interactive Scenario Catalog ({scenarios.length > 0 ? scenarios.length : 20} Scenarios)
            </h3>
          </div>

          <div className="w-full sm:w-72">
            <Input
              placeholder="Search scenarios (e.g. bypass, PEWS, conflict)..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
        </div>

        {scenarios.length === 0 ? (
          <div className="p-12 rounded-xl bg-white border border-dashed border-slate-300 text-center space-y-3">
            <Play className="w-8 h-8 text-indigo-600 mx-auto" />
            <div className="text-sm font-semibold text-slate-900">
              Database Ready for Interactive Seeding
            </div>
            <p className="text-xs text-slate-500 max-w-sm mx-auto">
              Click "Seed 20 Demo Patients" above to instantiate the complete clinical scenario benchmark pipeline.
            </p>
            <Button
              size="sm"
              variant="secondary"
              isLoading={isSeedPending}
              onClick={() => seedDemo()}
            >
              Seed Now
            </Button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredScenarios.map((scenario) => (
              <ScenarioCard key={scenario.number} scenario={scenario} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
