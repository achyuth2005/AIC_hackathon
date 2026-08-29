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
    <Card className="bg-slate-900 border-slate-800 text-left hover:border-slate-700 transition-all flex flex-col justify-between shadow-lg">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between gap-2">
          <span className="w-7 h-7 rounded-lg bg-cyan-950 text-cyan-300 border border-cyan-800 flex items-center justify-center font-mono font-bold text-xs">
            #{number}
          </span>
          <span
            className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border flex items-center gap-1 ${
              isFull
                ? 'bg-emerald-950 text-emerald-300 border-emerald-800'
                : 'bg-amber-950 text-amber-300 border-amber-800'
            }`}
          >
            {isFull ? <CheckCircle2 className="w-3 h-3 text-emerald-400" /> : <AlertCircle className="w-3 h-3 text-amber-400" />}
            <span>{fidelity} FIDELITY</span>
          </span>
        </div>

        <CardTitle className="text-sm font-bold text-slate-100 mt-2 line-clamp-2">
          {title}
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-3 pt-0">
        <p className="text-xs text-slate-300 leading-relaxed font-sans line-clamp-3">
          {demonstrates}
        </p>

        {note && (
          <div className="text-[11px] font-mono text-slate-400 bg-slate-950/80 p-2 rounded-lg border border-slate-800">
            {note}
          </div>
        )}

        <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between">
          <span className="text-[10px] font-mono text-slate-500">
            ID: {case_id.substring(0, 8)}...
          </span>

          <Link
            to={`/cases/${case_id}`}
            className="inline-flex items-center gap-1 text-xs text-cyan-400 hover:text-cyan-300 font-mono font-bold"
          >
            <span>Open Case</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </CardContent>
    </Card>
  );
};
