import React from 'react';
import { useQueue } from '../../hooks/useQueue';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';
import { AcuityBadge } from '../../components/clinical/AcuityBadge';
import { formatMinutes } from '../../lib/datetime';
import { Clock } from 'lucide-react';

export const DwellTimeDistribution: React.FC = () => {
  const { data: queue } = useQueue();

  const entries = queue || [];

  const acuityBands = [1, 2, 3, 4, 5].map((level) => {
    const matching = entries.filter((e) => e.final_acuity === level);
    const avgWait =
      matching.length > 0
        ? Math.round(
            matching.reduce((acc, curr) => acc + curr.waiting_minutes, 0) / matching.length
          )
        : 0;

    // Configured benchmarks (target minutes before doctor evaluation)
    const targets: Record<number, number> = {
      1: 0,
      2: 10,
      3: 30,
      4: 60,
      5: 120,
    };

    return {
      level,
      count: matching.length,
      avgWait,
      target: targets[level],
    };
  });

  return (
    <Card className="text-left">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm flex items-center gap-2">
          <Clock className="w-4 h-4 text-indigo-600" />
          Acuity-Stratified Dwell Times vs Clinical Benchmarks
        </CardTitle>
      </CardHeader>

      <CardContent>
        <div className="space-y-3">
          {acuityBands.map(({ level, count, avgWait, target }) => {
            const isExceeded = avgWait > target && count > 0;

            return (
              <div
                key={level}
                className="p-3 rounded-xl bg-slate-50 border border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs font-mono"
              >
                <div className="flex items-center gap-2.5">
                  <AcuityBadge acuity={level} size="xs" />
                  <span className="text-slate-700 font-bold">
                    {count} Patient{count === 1 ? '' : 's'} Active
                  </span>
                </div>

                <div className="flex items-center gap-4">
                  <div className="text-slate-500">
                    Target: <strong className="text-slate-700">{target}m</strong>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="text-slate-500">Mean Dwell:</span>
                    <span
                      className={`font-bold text-sm ${
                        isExceeded ? 'text-rose-600' : 'text-emerald-600'
                      }`}
                    >
                      {count > 0 ? formatMinutes(avgWait) : '--'}
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
};
