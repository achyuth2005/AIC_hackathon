import React from 'react';
import { useRiskAssessments } from '../../hooks/useRiskAssessments';
import { RiskAssessmentResponse } from '../../types/api';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts';
import { formatClock } from '../../lib/datetime';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';
import { TrendingUp } from 'lucide-react';

export interface AcuityHistoryChartProps {
  caseId: string;
}

export const AcuityHistoryChart: React.FC<AcuityHistoryChartProps> = ({ caseId }) => {
  const { data: assessments, isLoading } = useRiskAssessments(caseId);

  if (isLoading || !assessments || assessments.length <= 1) {
    return null;
  }

  const chartData = assessments.map((a: RiskAssessmentResponse, idx: number) => ({
    index: idx + 1,
    time: formatClock(a.computed_at),
    rawTime: a.computed_at,
    acuity: a.final_acuity,
    layer: a.deciding_layer,
    ruleAcuity: a.rule_acuity,
  }));

  return (
    <Card className="bg-slate-900 border-slate-800">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm flex items-center justify-between">
          <span className="flex items-center gap-2 text-slate-200">
            <TrendingUp className="w-4 h-4 text-cyan-400" />
            Acuity Progression Over Time (Inverted Y: ESI 1 on Top)
          </span>
          <span className="text-xs font-mono text-slate-400">
            {assessments.length} Rescore Events
          </span>
        </CardTitle>
      </CardHeader>

      <CardContent>
        <div className="h-48 w-full pt-2">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 10, right: 20, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
              <XAxis
                dataKey="time"
                stroke="#64748b"
                tick={{ fontSize: 11, fill: '#94a3b8' }}
              />
              <YAxis
                reversed={true}
                domain={[1, 5]}
                ticks={[1, 2, 3, 4, 5]}
                stroke="#64748b"
                tick={{ fontSize: 11, fill: '#94a3b8', fontFamily: 'monospace' }}
                tickFormatter={(val) => `ESI ${val}`}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#0f172a',
                  borderColor: '#334155',
                  borderRadius: '0.75rem',
                  fontSize: '12px',
                  color: '#f8fafc',
                }}
                formatter={(val, _name, item) => [
                  `ESI ${val} (${item.payload.layer})`,
                  'Authoritative Acuity',
                ]}
                labelFormatter={(label) => `Time: ${label}`}
              />
              <Line
                type="stepAfter"
                dataKey="acuity"
                stroke="#06b6d4"
                strokeWidth={3}
                dot={{ fill: '#06b6d4', r: 4 }}
                activeDot={{ r: 6, fill: '#38bdf8' }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
};
