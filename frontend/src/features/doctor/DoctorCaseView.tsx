import React from 'react';
import { DoctorCaseDetailResponse } from '../../types/api';
import { AcuityBadge } from '../../components/clinical/AcuityBadge';
import { ConfidenceBadge } from '../../components/clinical/ConfidenceBadge';
import { TrendArrow } from '../../components/clinical/TrendArrow';
import { UnreviewedResultsBanner } from './UnreviewedResultsBanner';
import { StuckPatientCallout } from './StuckPatientCallout';
import { DiagnosticTestsPanel } from '../case/DiagnosticTestsPanel';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';
import { formatMinutes } from '../../lib/datetime';
import { Link } from 'react-router-dom';
import {
  ArrowLeft,
  User,
  Bed,
  Activity,
  ExternalLink,
  Clock,
} from 'lucide-react';

export interface DoctorCaseViewProps {
  caseData: DoctorCaseDetailResponse;
}

export const DoctorCaseView: React.FC<DoctorCaseViewProps> = ({ caseData }) => {
  const {
    case_id,
    patient_summary,
    acuity_summary,
    unreviewed_tests,
    vital_trends,
    stuck_status,
  } = caseData;

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-16 text-left animate-fade-in">
      {/* Back and Link to Full Workspace */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <Link
          to="/doctor"
          className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-cyan-400 font-medium transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Physician Worklist
        </Link>

        <Link
          to={`/cases/${case_id}`}
          className="inline-flex items-center gap-1.5 text-xs text-cyan-400 hover:text-cyan-300 font-mono font-semibold bg-cyan-950/60 px-3 py-1.5 rounded-lg border border-cyan-800/60"
        >
          <span>Open Full Triage Workspace</span>
          <ExternalLink className="w-3.5 h-3.5" />
        </Link>
      </div>

      {/* Header Summary */}
      <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="space-y-1.5">
            <div className="flex flex-wrap items-center gap-3">
              <h1 className="text-2xl font-black text-slate-100">
                {patient_summary.display_name || 'Anonymous Walk-in'}
              </h1>
              {patient_summary.mrn && (
                <span className="font-mono text-xs text-slate-300 bg-slate-800 px-2 py-0.5 rounded border border-slate-700">
                  MRN: {patient_summary.mrn}
                </span>
              )}
              <AcuityBadge acuity={acuity_summary.final_acuity} size="md" />
              <ConfidenceBadge band={acuity_summary.confidence_band} size="sm" />
            </div>

            <div className="flex flex-wrap items-center gap-4 text-xs text-slate-400 font-mono">
              {patient_summary.age_years != null && (
                <span className="flex items-center gap-1 text-slate-300">
                  <User className="w-3.5 h-3.5 text-slate-500" />
                  {patient_summary.age_years} yrs {patient_summary.sex ? `• ${patient_summary.sex}` : ''}
                </span>
              )}
              <span className="flex items-center gap-1 text-cyan-300">
                <Bed className="w-3.5 h-3.5" />
                {patient_summary.assigned_resource_label || 'Unassigned Bed'}
              </span>
              <span className="flex items-center gap-1">
                <Clock className="w-3.5 h-3.5 text-slate-500" />
                Waiting {formatMinutes(patient_summary.waiting_minutes)}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-xs font-mono text-right">
              <div className="text-slate-500">Deciding Layer</div>
              <div className="font-bold text-cyan-300">{acuity_summary.deciding_layer}</div>
            </div>
          </div>
        </div>
      </div>

      {/* Unreviewed Results Alert Banner */}
      {unreviewed_tests && unreviewed_tests.length > 0 && (
        <UnreviewedResultsBanner
          caseId={case_id}
          unreviewededTests={unreviewed_tests}
        />
      )}

      {/* Stuck Patient Callout */}
      {stuck_status && stuck_status.stuck_flagged && (
        <StuckPatientCallout
          stuckFlagged={stuck_status.stuck_flagged}
          stuckReasons={stuck_status.stuck_reasons}
          caseId={case_id}
        />
      )}

      {/* Diagnostic Tests Panel */}
      <DiagnosticTestsPanel caseId={case_id} />

      {/* Longitudinal Vital Trends Table */}
      {vital_trends && vital_trends.length > 0 && (
        <Card className="bg-slate-900 border-slate-800">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm flex items-center gap-2 text-slate-200">
              <Activity className="w-4 h-4 text-cyan-400" />
              Longitudinal Vital Signs Trend Summary
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {vital_trends.map((vt) => (
                <div
                  key={vt.concept_code}
                  className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-2"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-200">
                      {vt.concept_code.replace(/_/g, ' ')}
                    </span>
                    <div className="flex items-center gap-1 text-xs font-mono">
                      <span className="text-slate-400">Trend:</span>
                      <TrendArrow trend={vt.trend_direction} />
                    </div>
                  </div>

                  <div className="flex items-baseline justify-between text-xs font-mono">
                    <div>
                      <span className="text-slate-500 text-[11px] block">Current:</span>
                      <span className="text-lg font-black text-white">
                        {String(vt.latest_value)} {vt.unit || ''}
                      </span>
                    </div>

                    {vt.previous_value != null && (
                      <div className="text-right">
                        <span className="text-slate-500 text-[11px] block">Previous:</span>
                        <span className="text-sm text-slate-400 line-through">
                          {String(vt.previous_value)} {vt.unit || ''}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};
