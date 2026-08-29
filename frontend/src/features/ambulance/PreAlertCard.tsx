import React from 'react';
import { PreAlertView } from '../../types/api';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';
import { AcuityBadge } from '../../components/clinical/AcuityBadge';
import { ETACountdownClock } from './ETACountdownClock';
import { Truck, Activity, Stethoscope, Package, AlertCircle } from 'lucide-react';

export interface PreAlertCardProps {
  preAlert: PreAlertView;
}

export const PreAlertCard: React.FC<PreAlertCardProps> = ({ preAlert }) => {
  const {
    predicted_acuity_band,
    one_line_presentation,
    key_abnormal_vitals = [],
    interventions_already_performed = [],
    eta_range,
    what_hospital_should_prepare,
  } = preAlert;

  return (
    <div className="space-y-5 text-left">
      {/* Top Pre-Alert Banner: Acuity + ETA Clock */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="md:col-span-1 p-5 rounded-2xl bg-slate-900 border border-slate-800 space-y-2 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 text-slate-400 text-xs font-bold uppercase tracking-wider">
              <Truck className="w-4 h-4 text-cyan-400" />
              <span>Predicted Pre-Arrival Acuity</span>
            </div>
            <div className="mt-3">
              {predicted_acuity_band != null ? (
                <AcuityBadge acuity={predicted_acuity_band} size="lg" />
              ) : (
                <span className="text-xs font-mono text-slate-500">Uncalculated</span>
              )}
            </div>
          </div>
          <div className="text-[11px] text-slate-400 font-mono">
            Anticipatory scoring from paramedic field observations
          </div>
        </div>

        <div className="md:col-span-2">
          <ETACountdownClock etaRange={eta_range} />
        </div>
      </div>

      {/* 3-Second Clinical Presentation */}
      <Card className="bg-slate-900 border-cyan-900/60 shadow-xl">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-2 text-cyan-300">
            <Activity className="w-4 h-4 text-cyan-400" />
            <span>One-Line Clinical Presentation</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 text-base font-semibold text-slate-100 leading-relaxed">
            {one_line_presentation || 'Inbound transport en route; initial telemetry streaming.'}
          </div>
        </CardContent>
      </Card>

      {/* Grid: Abnormal Field Vitals & En-Route Interventions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Abnormal Vitals */}
        <Card className="bg-slate-900 border-slate-800">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs flex items-center gap-2 text-slate-300 uppercase tracking-wider">
              <AlertCircle className="w-4 h-4 text-rose-400" />
              <span>Key Abnormal Field Vitals</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {key_abnormal_vitals.length === 0 ? (
              <div className="text-xs text-slate-500 font-mono py-3">
                No acute physiological vital abnormalities flagged.
              </div>
            ) : (
              <div className="space-y-2">
                {key_abnormal_vitals.map((v, i) => (
                  <div
                    key={i}
                    className="p-2.5 rounded-xl bg-rose-950/30 border border-rose-800/60 flex items-center justify-between text-xs font-mono"
                  >
                    <span className="font-bold text-slate-200">{v.label || v.concept_code}</span>
                    <span className="text-rose-300 font-black">
                      {String(v.raw_value)} {v.unit || ''} ({v.points} pts)
                    </span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Interventions Already Performed */}
        <Card className="bg-slate-900 border-slate-800">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs flex items-center gap-2 text-slate-300 uppercase tracking-wider">
              <Stethoscope className="w-4 h-4 text-emerald-400" />
              <span>Interventions Already Performed (EMS)</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {interventions_already_performed.length === 0 ? (
              <div className="text-xs text-slate-500 font-mono py-3">
                No pre-hospital invasive interventions recorded.
              </div>
            ) : (
              <ul className="space-y-1.5 text-xs text-slate-200 list-disc list-inside">
                {interventions_already_performed.map((item, idx) => (
                  <li key={idx} className="font-medium text-emerald-300">
                    {item}
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Hospital Preparation Directive */}
      {what_hospital_should_prepare && (
        <div className="p-4 rounded-xl bg-amber-950/40 border border-amber-600/80 text-left space-y-1.5 shadow-md">
          <div className="flex items-center gap-2 text-amber-300 text-xs font-bold uppercase tracking-wider">
            <Package className="w-4 h-4 text-amber-400" />
            <span>ED Preparation Directive</span>
          </div>
          <div className="text-sm font-semibold text-slate-100">
            {what_hospital_should_prepare}
          </div>
        </div>
      )}
    </div>
  );
};
