import React from 'react';
import { SubgroupStats } from '../../types/api';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';
import { AcuityBadge } from '../../components/clinical/AcuityBadge';
import { BarChart3 } from 'lucide-react';

export interface DisparateImpactChartProps {
  title: string;
  subgroups: SubgroupStats[];
}

export const DisparateImpactChart: React.FC<DisparateImpactChartProps> = ({
  title,
  subgroups = [],
}) => {
  return (
    <Card className="bg-slate-900 border-slate-800 text-left shadow-lg">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm flex items-center gap-2 text-slate-200">
          <BarChart3 className="w-4 h-4 text-cyan-400" />
          <span>{title}</span>
        </CardTitle>
      </CardHeader>

      <CardContent>
        {subgroups.length === 0 ? (
          <div className="text-xs text-slate-500 font-mono py-6 text-center">
            No demographic records evaluated in active window.
          </div>
        ) : (
          <div className="space-y-4">
            {subgroups.map((group) => {
              const overridePercent =
                group.override_rate != null ? Math.round(group.override_rate * 100) : null;

              return (
                <div
                  key={group.subgroup}
                  className="p-4 rounded-xl bg-slate-950/70 border border-slate-800/80 space-y-3"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-sm text-slate-100 uppercase tracking-wide">
                        {group.subgroup}
                      </span>
                      <span className="text-xs font-mono text-slate-400">
                        ({group.case_count} Case{group.case_count === 1 ? '' : 's'})
                      </span>
                    </div>

                    <div className="flex items-center gap-3 text-xs font-mono">
                      <span className="text-slate-400">
                        Override Rate:{' '}
                        <strong className="text-cyan-300">
                          {overridePercent != null ? `${overridePercent}%` : 'N/A'}
                        </strong>
                      </span>
                      <span className="text-slate-500">
                        ({group.escalate_count} Esc / {group.de_escalate_count} De-esc)
                      </span>
                    </div>
                  </div>

                  {/* Acuity Distribution Mini-Bar */}
                  <div className="space-y-1">
                    <div className="text-[10px] font-mono text-slate-500 uppercase">
                      Current Acuity Distribution
                    </div>
                    <div className="flex flex-wrap gap-2 items-center">
                      {[1, 2, 3, 4, 5].map((lvl) => {
                        const count = group.acuity_distribution[lvl] || 0;
                        return (
                          <div
                            key={lvl}
                            className="flex items-center gap-1 text-[11px] font-mono px-2 py-0.5 rounded bg-slate-900 border border-slate-800"
                          >
                            <AcuityBadge acuity={lvl} size="xs" showLabel={false} />
                            <span className="text-slate-300 font-bold">{count}</span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
};
