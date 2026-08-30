import React, { useState } from 'react';
import { CaseDetailResponse } from '../../types/api';
import { AcuityBadge } from '../../components/clinical/AcuityBadge';
import { ConfidenceBadge } from '../../components/clinical/ConfidenceBadge';
import { EmergencyBypassButton } from './EmergencyBypassButton';
import { DeEscalateModal } from './DeEscalateModal';
import { Button } from '../../components/ui/Button';
import { useOverride } from '../../hooks/useOverride';
import { useMarkReassessed } from '../../hooks/useMarkReassessed';
import {
  ArrowLeft,
  ArrowUpCircle,
  ArrowDownCircle,
  Clock,
  User,
  Calendar,
  Truck,
  Activity,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { formatRelative } from '../../lib/datetime';

export interface CaseHeaderProps {
  caseData: CaseDetailResponse;
}

export const CaseHeader: React.FC<CaseHeaderProps> = ({ caseData }) => {
  const {
    case_id,
    display_name,
    mrn,
    age_years,
    sex,
    status,
    arrival_mode,
    created_at,
    emergency_bypass_active,
    latest_risk_assessment,
    reassessment_overdue,
  } = caseData;

  const currentAcuity = latest_risk_assessment?.final_acuity || 3;
  const { mutate: override, isPending: isOverridePending } = useOverride();
  const { mutate: markReassessed, isPending: isReassessPending } = useMarkReassessed();
  const [isDeEscalateOpen, setIsDeEscalateOpen] = useState(false);

  const handleEscalate = () => {
    if (currentAcuity === 1) return;
    override({
      caseId: case_id,
      body: { action: 'ESCALATE' },
    });
  };

  return (
    <div className="space-y-4 border-b border-slate-200/50 pb-5 text-left">
      {/* Back button & quick navigation */}
      <div className="flex items-center justify-between">
        <Link
          to="/queue"
          className="inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-indigo-600 font-medium transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Guardian Queue
        </Link>

        <div className="flex items-center gap-2 font-mono text-xs text-slate-500">
          <span>Case ID:</span>
          <span className="text-slate-700 font-bold bg-slate-500/10 px-2 py-0.5 rounded-full border border-slate-300/30 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.7)]">
            {case_id.substring(0, 8)}...
          </span>
        </div>
      </div>

      {/* Hero patient title and action buttons */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
              {display_name || 'Anonymous Patient'}
            </h1>

            {mrn && (
              <span className="font-mono text-xs font-bold text-slate-700 bg-slate-500/10 px-2 py-0.5 rounded-full border border-slate-300/30 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.7)]">
                MRN: {mrn}
              </span>
            )}

            <AcuityBadge
              acuity={currentAcuity}
              size="md"
              isBypass={emergency_bypass_active}
            />

            <ConfidenceBadge
              band={latest_risk_assessment?.confidence_band}
              shouldAbstain={latest_risk_assessment?.should_abstain}
              size="sm"
            />
          </div>

          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500 font-mono">
            {age_years != null && (
              <span className="flex items-center gap-1 text-slate-700">
                <User className="w-3.5 h-3.5 text-slate-400" />
                {age_years} yrs {sex ? `• ${sex}` : ''}
              </span>
            )}

            <span className="flex items-center gap-1">
              <Calendar className="w-3.5 h-3.5 text-slate-400" />
              Arrived {formatRelative(created_at)}
            </span>

            <span className="flex items-center gap-1 text-indigo-600">
              {arrival_mode === 'AMBULANCE' ? (
                <Truck className="w-3.5 h-3.5" />
              ) : (
                <Activity className="w-3.5 h-3.5" />
              )}
              {arrival_mode}
            </span>

            <span className="px-2 py-0.5 rounded-full bg-slate-500/10 text-slate-700 font-bold border border-slate-300/30 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.7)]">
              {status}
            </span>
          </div>

        </div>

        {/* Action buttons */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Emergency Bypass Panic Button */}
          <EmergencyBypassButton
            caseId={case_id}
            isActive={emergency_bypass_active}
          />

          {/* 1-Tap Escalate Action */}
          <Button
            variant="warning"
            size="md"
            disabled={currentAcuity === 1 || isOverridePending}
            isLoading={isOverridePending}
            onClick={handleEscalate}
            leftIcon={<ArrowUpCircle className="w-4 h-4" />}
            className="font-bold text-xs"
            title={
              currentAcuity === 1
                ? 'Patient already at ESI 1 (Highest Urgency)'
                : '1-Tap Escalate (No friction)'
            }
          >
            Escalate Acuity
          </Button>

          {/* De-escalate Action (Reason Gated) */}
          <Button
            variant="secondary"
            size="md"
            onClick={() => setIsDeEscalateOpen(true)}
            leftIcon={<ArrowDownCircle className="w-4 h-4 text-indigo-600" />}
            disabled={currentAcuity >= 5}
            className="text-xs font-semibold"
          >
            De-escalate
          </Button>

          {/* Mark Reassessed Action */}
          <Button
            variant={reassessment_overdue ? 'danger' : 'secondary'}
            size="md"
            onClick={() => markReassessed(case_id)}
            isLoading={isReassessPending}
            leftIcon={<Clock className="w-4 h-4" />}
            className={`text-xs font-semibold ${reassessment_overdue ? 'animate-pulse' : ''}`}
          >
            {reassessment_overdue ? 'Reassess Overdue' : 'Mark Reassessed'}
          </Button>
        </div>
      </div>

      {/* De-escalation Modal */}
      {isDeEscalateOpen && (
        <DeEscalateModal
          isOpen={isDeEscalateOpen}
          onClose={() => setIsDeEscalateOpen(false)}
          caseId={case_id}
          patientName={display_name}
          currentAcuity={currentAcuity}
        />
      )}
    </div>
  );
};
