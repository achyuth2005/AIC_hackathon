import React from 'react';
import { ScoreComponent } from '../../types/api';
import { Table, TableHeader, TableBody, TableHead, TableRow, TableCell } from '../../components/ui/Table';
import { formatRelative } from '../../lib/datetime';
import { StalenessDot } from '../../components/clinical/StalenessDot';
import { AlertCircle, CheckCircle2 } from 'lucide-react';

export interface ComponentBreakdownTableProps {
  components: ScoreComponent[];
}

export const ComponentBreakdownTable: React.FC<ComponentBreakdownTableProps> = ({
  components,
}) => {
  if (!components || components.length === 0) {
    return (
      <div className="p-4 text-center text-xs text-slate-500 font-mono italic">
        No rule component breakdown available.
      </div>
    );
  }

  const formatRawValue = (comp: ScoreComponent) => {
    if (comp.raw_value == null) return '--';
    if (typeof comp.raw_value === 'boolean') return comp.raw_value ? 'Yes (Oxygen)' : 'No (Room Air)';
    return `${comp.raw_value} ${comp.unit || ''}`.trim();
  };

  return (
    <div className="space-y-2">
      <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider px-1">
        Deterministic Scoring Framework Breakdown
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead scope="col">Clinical Parameter</TableHead>
            <TableHead scope="col">Observed Value</TableHead>
            <TableHead scope="col">Measurement Timing & Tier</TableHead>
            <TableHead scope="col" className="text-right">NEWS2 / PEWS Points</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {components.map((comp) => {
            const hasPoints = comp.points != null && comp.points > 0;
            const isExcluded = comp.points === null;

            return (
              <TableRow
                key={comp.concept_code}
                className={
                  comp.is_missing
                    ? 'bg-slate-950/40 opacity-70'
                    : hasPoints
                    ? 'bg-orange-950/20'
                    : ''
                }
              >
                <TableCell className="font-medium text-slate-200">
                  <div className="flex items-center gap-2">
                    {hasPoints ? (
                      <AlertCircle className="w-3.5 h-3.5 text-orange-400 shrink-0" />
                    ) : (
                      <CheckCircle2 className="w-3.5 h-3.5 text-slate-600 shrink-0" />
                    )}
                    <div>
                      <div className="text-xs font-semibold">{comp.label}</div>
                      <div className="text-[10px] font-mono text-slate-500">
                        {comp.concept_code}
                      </div>
                    </div>
                  </div>
                </TableCell>

                <TableCell className="font-mono text-xs">
                  {comp.is_missing ? (
                    <span className="text-amber-400 text-xs italic">
                      Missing: {comp.missing_reason || 'NOT_RECORDED'}
                    </span>
                  ) : (
                    <span className="font-bold text-slate-100">{formatRawValue(comp)}</span>
                  )}
                </TableCell>

                <TableCell className="text-xs font-mono text-slate-400">
                  {comp.observed_at ? (
                    <div className="flex items-center gap-1.5">
                      <StalenessDot observedAt={comp.observed_at} />
                      <span>{formatRelative(comp.observed_at)}</span>
                      {comp.reliability_tier && (
                        <span className="text-[10px] text-slate-500 font-bold px-1 rounded bg-slate-800">
                          T{comp.reliability_tier}
                        </span>
                      )}
                    </div>
                  ) : (
                    <span className="text-slate-600">--</span>
                  )}
                </TableCell>

                <TableCell className="text-right font-mono">
                  {isExcluded ? (
                    <span className="text-xs text-slate-500 bg-slate-800/80 px-2 py-0.5 rounded border border-slate-700 font-medium">
                      Not scored (excluded)
                    </span>
                  ) : (
                    <span
                      className={`text-xs font-bold px-2 py-0.5 rounded ${
                        hasPoints
                          ? 'bg-orange-950 text-orange-300 border border-orange-700/80'
                          : 'bg-emerald-950/60 text-emerald-400 border border-emerald-800/40'
                      }`}
                    >
                      {comp.points} {comp.points === 1 ? 'pt' : 'pts'}
                    </span>
                  )}
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
};
