import React from 'react';
import { DoctorCaseDetailResponse } from '../../types/api';
import { AcuityBadge } from '../../components/clinical/AcuityBadge';
import { ConfidenceBadge } from '../../components/clinical/ConfidenceBadge';
import { TrendArrow } from '../../components/clinical/TrendArrow';
import { UnreviewedResultsBanner } from './UnreviewedResultsBanner';
import { StuckPatientCallout } from './StuckPatientCallout';
import { DiagnosticTestsPanel } from '../case/DiagnosticTestsPanel';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { formatMinutes } from '../../lib/datetime';
import { Link } from 'react-router-dom';
import {
  ArrowLeft,
  User,
  Bed,
  Activity,
  ExternalLink,
  Clock,
  Stethoscope,
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
      <div className="flex items-center justify-between border-b border-slate-200 pb-4">
        <Link
          to="/doctor"
          className="inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-indigo-700 font-medium transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Physician Worklist
        </Link>

        <Link
          to={`/cases/${case_id}`}
          className="inline-flex items-center gap-1.5 text-xs text-indigo-700 hover:text-indigo-800 font-mono font-semibold bg-indigo-50 px-3 py-1.5 rounded-lg border border-indigo-200"
        >
          <span>Open Full Triage Workspace</span>
          <ExternalLink className="w-3.5 h-3.5" />
        </Link>
      </div>

      {/* Header Summary */}
      <div className="p-6 rounded-2xl bg-white border border-slate-200/80 shadow-card space-y-4">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="space-y-1.5">
            <div className="flex flex-wrap items-center gap-3">
              <h1 className="text-2xl font-bold text-slate-900">
                {patient_summary.display_name || 'Anonymous Walk-in'}
              </h1>
              {patient_summary.mrn && (
                <span className="font-mono text-xs text-slate-600 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                  MRN: {patient_summary.mrn}
                </span>
              )}
              <AcuityBadge acuity={acuity_summary.final_acuity} size="md" />
              <ConfidenceBadge band={acuity_summary.confidence_band} size="sm" />
            </div>

            <div className="flex flex-wrap items-center gap-4 text-xs text-slate-500 font-mono">
              {patient_summary.age_years != null && (
                <span className="flex items-center gap-1 text-slate-600">
                  <User className="w-3.5 h-3.5 text-slate-400" />
                  {patient_summary.age_years} yrs {patient_summary.sex ? `• ${patient_summary.sex}` : ''}
                </span>
              )}
              <span className="flex items-center gap-1 text-indigo-600">
                <Bed className="w-3.5 h-3.5" />
                {patient_summary.assigned_resource_label || 'Unassigned Bed'}
              </span>
              <span className="flex items-center gap-1">
                <Clock className="w-3.5 h-3.5 text-slate-400" />
                Waiting {formatMinutes(patient_summary.waiting_minutes)}
              </span>
            </div>

            {/* Medical History (Medical History feature): prominently
                displayed with an explicit safe empty state. */}
            <div className="flex items-start gap-2 pt-1">
              <Stethoscope className="w-3.5 h-3.5 text-slate-400 mt-0.5 shrink-0" />
              {patient_summary.medical_history && patient_summary.medical_history.trim().length > 0 ? (
                <Badge variant="warning" size="sm" className="font-sans normal-case tracking-normal whitespace-normal text-left">
                  {patient_summary.medical_history}
                </Badge>
              ) : (
                <span className="text-xs italic text-slate-400">No known medical history</span>
              )}
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 text-xs font-mono text-right">
              <div className="text-slate-400">Deciding Layer</div>
              <div className="font-bold text-indigo-700">{acuity_summary.deciding_layer}</div>
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
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm flex items-center gap-2">
              <Activity className="w-4 h-4 text-indigo-600" />
              Longitudinal Vital Signs Trend Summary
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {vital_trends.map((vt) => (
                <div
                  key={vt.concept_code}
                  className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 space-y-2"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-700 capitalize">
                      {vt.concept_code.replace(/_/g, ' ').toLowerCase()}
                    </span>
                    <div className="flex items-center gap-1 text-xs font-mono">
                      <span className="text-slate-400">Trend:</span>
                      <TrendArrow trend={vt.trend_direction} />
                    </div>
                  </div>

                  <div className="flex items-baseline justify-between text-xs font-mono">
                    <div>
                      <span className="text-slate-400 text-[11px] block">Current:</span>
                      <span className="text-lg font-bold text-slate-900 tabular-nums">
                        {String(vt.latest_value)} {vt.unit || ''}
                      </span>
                    </div>

                    {vt.previous_value != null && (
                      <div className="text-right">
                        <span className="text-slate-400 text-[11px] block">Previous:</span>
                        <span className="text-sm text-slate-400 line-through tabular-nums">
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
