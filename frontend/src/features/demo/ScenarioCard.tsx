import React from 'react';
import { DemoScenario } from '../../types/api';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';
import { Link } from 'react-router-dom';
import { ArrowRight, CheckCircle2, AlertCircle } from 'lucide-react';

export interface ScenarioCardProps {
  scenario: DemoScenario;
}

export const ScenarioCard: React.FC<ScenarioCardProps> = ({ scenario }) => {
  const { number, title, demonstrates, case_id, fidelity, note } = scenario;
  const isFull = fidelity === 'FULL';

  return (
    <Card className="text-left hover:border-slate-300 hover:shadow-card-lg transition-all flex flex-col justify-between">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between gap-2">
          <span className="w-7 h-7 rounded-lg bg-indigo-50 text-indigo-700 border border-indigo-200 flex items-center justify-center font-mono font-bold text-xs">
            #{number}
          </span>
          <span
            className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border flex items-center gap-1 ${
              isFull
                ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                : 'bg-amber-50 text-amber-800 border-amber-200'
            }`}
          >
            {isFull ? <CheckCircle2 className="w-3 h-3 text-emerald-600" /> : <AlertCircle className="w-3 h-3 text-amber-600" />}
            <span>{fidelity} FIDELITY</span>
          </span>
        </div>

        <CardTitle className="text-sm font-bold text-slate-900 mt-2 line-clamp-2">
          {title}
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-3 pt-0">
        <p className="text-xs text-slate-600 leading-relaxed font-sans line-clamp-3">
          {demonstrates}
        </p>

        {note && (
          <div className="text-[11px] font-mono text-slate-500 bg-slate-50 p-2 rounded-lg border border-slate-200">
            {note}
          </div>
        )}

        <div className="pt-2 border-t border-slate-100 flex items-center justify-between">
          <span className="text-[10px] font-mono text-slate-400">
            ID: {case_id.substring(0, 8)}...
          </span>

          <Link
            to={`/cases/${case_id}`}
            className="inline-flex items-center gap-1 text-xs text-indigo-600 hover:text-indigo-700 font-mono font-bold"
          >
            <span>Open Case</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </CardContent>
    </Card>
  );
};
