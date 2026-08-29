import React from 'react';
import { PatientStage } from '../../types/enums';
import { CheckCircle2, Clock, Activity, UserCheck } from 'lucide-react';

export interface StageProgressTrackerProps {
  currentStage: PatientStage;
}

const STAGES: { stage: PatientStage; label: string; description: string; icon: React.FC<{ className?: string }> }[] = [
  {
    stage: 'PRE_ARRIVAL',
    label: 'In Transit',
    description: 'En route to hospital',
    icon: Clock,
  },
  {
    stage: 'WAITING',
    label: 'Triage & Waiting',
    description: 'Vitals taken, awaiting doctor',
    icon: Activity,
  },
  {
    stage: 'IN_TREATMENT',
    label: 'In Treatment Area',
    description: 'Under physician evaluation',
    icon: UserCheck,
  },
  {
    stage: 'DISPOSED',
    label: 'Care Completed',
    description: 'Discharged or admitted',
    icon: CheckCircle2,
  },
];

export const StageProgressTracker: React.FC<StageProgressTrackerProps> = ({ currentStage }) => {
  const currentIndex = STAGES.findIndex((s) => s.stage === currentStage);

  return (
    <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 text-left space-y-6 shadow-xl">
      <div className="space-y-1">
        <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider">
          Care Pathway Progress
        </h3>
        <p className="text-base font-extrabold text-slate-100">
          Where You Are in Your Emergency Care Visit
        </p>
      </div>

      <div className="relative">
        {/* Progress Bar Line */}
        <div className="hidden sm:block absolute top-1/2 left-6 right-6 -translate-y-1/2 h-0.5 bg-slate-800" />

        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 relative z-10">
          {STAGES.map((s, index) => {
            const isCompleted = index < currentIndex || currentStage === 'DISPOSED';
            const isCurrent = index === currentIndex && currentStage !== 'DISPOSED';
            const Icon = s.icon;

            return (
              <div
                key={s.stage}
                className={`p-4 rounded-xl border transition-all text-left space-y-2 ${
                  isCurrent
                    ? 'bg-cyan-950/60 border-cyan-500 shadow-lg shadow-cyan-950/60 ring-2 ring-cyan-500/20'
                    : isCompleted
                    ? 'bg-slate-950/80 border-emerald-800/60'
                    : 'bg-slate-950/30 border-slate-800/80 opacity-50'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div
                    className={`w-8 h-8 rounded-lg flex items-center justify-center font-mono font-bold text-xs ${
                      isCurrent
                        ? 'bg-cyan-500 text-slate-950'
                        : isCompleted
                        ? 'bg-emerald-600 text-white'
                        : 'bg-slate-800 text-slate-400'
                    }`}
                  >
                    {isCompleted ? <CheckCircle2 className="w-4 h-4" /> : <Icon className="w-4 h-4" />}
                  </div>

                  {isCurrent && (
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-cyan-900 text-cyan-200 border border-cyan-700 animate-pulse">
                      Current Step
                    </span>
                  )}
                </div>

                <div>
                  <div className={`font-bold text-sm ${isCurrent ? 'text-cyan-300' : 'text-slate-200'}`}>
                    {s.label}
                  </div>
                  <div className="text-xs text-slate-400 mt-0.5">{s.description}</div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
