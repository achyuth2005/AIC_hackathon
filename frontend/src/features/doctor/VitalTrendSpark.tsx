import React from 'react';
import { TrendArrow } from '../../components/clinical/TrendArrow';
import { DeteriorationTrend } from '../../types/enums';

export interface VitalTrendSparkProps {
  concept: string;
  latestValue: number | string | boolean | null | undefined;
  previousValue?: unknown;
  direction?: DeteriorationTrend | string;
  unit?: string | null;
}

export const VitalTrendSpark: React.FC<VitalTrendSparkProps> = ({
  concept,
  latestValue,
  previousValue,
  direction,
  unit,
}) => {
  if (latestValue == null) return null;

  const formatConceptLabel = (c: string) => {
    switch (c) {
      case 'RESP_RATE':
        return 'RR';
      case 'SPO2':
        return 'SpO2';
      case 'HEART_RATE':
        return 'HR';
      case 'SYSTOLIC_BP':
        return 'SBP';
      case 'TEMPERATURE':
        return 'Temp';
      default:
        return c;
    }
  };

  const trend = (direction || 'STABLE') as DeteriorationTrend;

  return (
    <div className="inline-flex items-center gap-1.5 bg-slate-950/80 px-2 py-1 rounded-lg border border-slate-800 text-[11px] font-mono">
      <span className="text-slate-500 font-bold">{formatConceptLabel(concept)}:</span>
      <span className="font-bold text-slate-200">
        {String(latestValue)}
        {unit ? <span className="text-[10px] text-slate-500 ml-0.5">{unit}</span> : ''}
      </span>

      {previousValue != null && (
        <span className="text-[10px] text-slate-500 line-through">
          {String(previousValue)}
        </span>
      )}

      <TrendArrow trend={trend} />
    </div>
  );
};
