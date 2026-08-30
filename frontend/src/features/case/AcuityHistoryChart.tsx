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
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm flex items-center justify-between">
          <span className="flex items-center gap-2 text-slate-900">
            <TrendingUp className="w-4 h-4 text-indigo-600" />
            Acuity Progression Over Time (Inverted Y: ESI 1 on Top)
          </span>
          <span className="text-xs font-mono text-slate-500">
            {assessments.length} Rescore Events
          </span>
        </CardTitle>
      </CardHeader>

      <CardContent>
        <div className="h-48 w-full pt-2">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 10, right: 20, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" opacity={0.8} />
              <XAxis
                dataKey="time"
                stroke="#cbd5e1"
                tick={{ fontSize: 11, fill: '#64748b' }}
              />
              <YAxis
                reversed={true}
                domain={[1, 5]}
                ticks={[1, 2, 3, 4, 5]}
                stroke="#cbd5e1"
                tick={{ fontSize: 11, fill: '#64748b', fontFamily: 'monospace' }}
                tickFormatter={(val) => `ESI ${val}`}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#ffffff',
                  borderColor: '#e2e8f0',
                  borderRadius: '0.75rem',
                  fontSize: '12px',
                  color: '#0f172a',
                  boxShadow: '0 4px 12px rgba(0,0,0,0.06), 0 2px 4px rgba(0,0,0,0.03)',
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
                stroke="#4f46e5"
                strokeWidth={3}
                dot={{ fill: '#4f46e5', r: 4 }}
                activeDot={{ r: 6, fill: '#6366f1' }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
};
