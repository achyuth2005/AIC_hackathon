import React from 'react';
import { ScenarioRunnerList } from '../features/demo/ScenarioRunnerList';
import { Sparkles } from 'lucide-react';

export const DemoPage: React.FC = () => {
  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-16 animate-fade-in text-left">
      {/* Header */}
      <div className="border-b border-slate-200 pb-5">
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 flex items-center gap-2.5">
          <Sparkles className="w-7 h-7 text-indigo-600" />
          Interactive Scenario Benchmark & Surge Runner
        </h1>
        <p className="text-xs text-slate-500 mt-1">
          Explore the 20 scripted clinical teaching scenarios and trigger mass-casualty surge simulations.
        </p>
      </div>

      {/* Scenario Runner & Surge Simulation Suite */}
      <ScenarioRunnerList />
    </div>
  );
};
