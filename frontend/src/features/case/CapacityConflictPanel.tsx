import React from 'react';
import { CapacityConflictResponse } from '../../types/api';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';
import { AlertOctagon, CheckSquare, ShieldCheck, ExternalLink } from 'lucide-react';
import { Link } from 'react-router-dom';

export interface CapacityConflictPanelProps {
  conflict: CapacityConflictResponse;
  onDismiss?: () => void;
}

export const CapacityConflictPanel: React.FC<CapacityConflictPanelProps> = ({ conflict }) => {
  const { detail, resource_type, candidate_actions } = conflict;

  return (
    <Card className="bg-amber-950/30 border-2 border-amber-500/80 text-left animate-fade-in shadow-xl">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm flex items-center justify-between text-amber-300">
          <div className="flex items-center gap-2">
            <AlertOctagon className="w-5 h-5 text-amber-400 shrink-0" />
            <span>Capacity Conflict Surfaced — {resource_type} Unavailable</span>
          </div>
          <span className="text-[10px] font-mono bg-amber-950 text-amber-300 px-2 py-0.5 rounded border border-amber-700/60 font-bold">
            Phase 6.2 Human Friction
          </span>
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-4">
        <p className="text-xs text-amber-200 font-medium leading-relaxed bg-amber-950/60 p-3 rounded-lg border border-amber-800/60">
          {detail || `No ${resource_type} is currently available in the emergency department.`}
        </p>

        {/* Phase 6.2 Invariant Callout */}
        <div className="flex items-start gap-2.5 p-3 rounded-xl bg-slate-950/80 border border-slate-800 text-xs text-slate-300">
          <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
          <div>
            <span className="font-semibold text-emerald-300">Clinical Invariant Upheld:</span>{' '}
            Patient clinical acuity has <strong className="text-white">NOT</strong> been downgraded to fit available hospital capacity.
          </div>
        </div>

        {/* Candidate Actions Checklist */}
        {candidate_actions && candidate_actions.length > 0 && (
          <div className="space-y-2">
            <div className="text-xs font-semibold text-amber-300 uppercase tracking-wider">
              Recommended Hospital Flow Actions:
            </div>
            <div className="space-y-1.5">
              {candidate_actions.map((action, idx) => (
                <div
                  key={idx}
                  className="flex items-start gap-2.5 p-2.5 rounded-lg bg-slate-950/60 border border-slate-800 text-xs text-slate-200"
                >
                  <CheckSquare className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                  <span>{action}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="pt-2 flex items-center justify-between">
          <Link
            to="/ops"
            className="inline-flex items-center gap-1.5 text-xs text-cyan-400 hover:text-cyan-300 font-mono font-semibold"
          >
            <span>Manage Department Capacity on Ops Board</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </Link>
        </div>
      </CardContent>
    </Card>
  );
};
