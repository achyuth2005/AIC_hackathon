import React, { useState } from 'react';
import { AlertResponse } from '../../types/api';
import { AlertDismissalReasonCode } from '../../types/enums';
import { useDismissAlert } from '../../hooks/useAlerts';
import { Button } from '../../components/ui/Button';
import { Modal } from '../../components/ui/Modal';
import { Select } from '../../components/ui/Select';
import { Input } from '../../components/ui/Input';
import { cn } from '../../lib/cn';
import { formatRelative, formatClock } from '../../lib/datetime';
import { ALERT_DISMISSAL_REASONS, ALERT_TYPE_LABELS } from '../../lib/enums';
import { Link } from 'react-router-dom';
import { Zap, AlertTriangle, Clock, ArrowRight, CheckCircle2 } from 'lucide-react';

export interface AlertCardProps {
  alert: AlertResponse;
}

export const AlertCard: React.FC<AlertCardProps> = ({ alert }) => {
  const { mutate: dismissAlert, isPending: isDismissPending } = useDismissAlert();
  const {
    alert_id,
    alert_type,
    created_at,
    payload,
    dismissed,
    dismissed_by,
    dismissal_reason_code,
    dismissal_free_text,
  } = alert;

  const [isDismissModalOpen, setIsDismissModalOpen] = useState(false);
  const [reasonCode, setReasonCode] = useState<AlertDismissalReasonCode>('ALREADY_ACTIONED');
  const [freeTextReason, setFreeTextReason] = useState('');

  const isBypass = alert_type === 'CRITICAL_BYPASS_PATIENT';
  const isEscalation = alert_type === 'ACUITY_BAND_CROSSED_UPWARD';
  const isOverdueAggregate = alert_type === 'REASSESSMENT_OVERDUE_AGGREGATE';

  const caseId = (payload?.case_id as string) || null;
  const patientName = (payload?.display_name as string) || (payload?.patient_name as string) || null;
  const overdueCount = (payload?.overdue_cases_count as number) || null;

  const getTitle = () => {
    switch (alert_type) {
      case 'CRITICAL_BYPASS_PATIENT':
        return `Emergency Bypass Engaged (${patientName || 'Patient'})`;
      case 'ACUITY_BAND_CROSSED_UPWARD':
        return `Patient Acuity Escalated to ESI ${payload?.to_acuity || 1}`;
      case 'REASSESSMENT_OVERDUE_AGGREGATE':
        return `Reassessment Overdue Threshold (${overdueCount || 'Multiple'} Patients)`;
      default:
        return ALERT_TYPE_LABELS[alert_type] || alert_type;
    }
  };

  const getMessage = () => {
    if (payload?.reason) return String(payload.reason);
    if (payload?.message) return String(payload.message);
    if (isOverdueAggregate)
      return `${overdueCount || 'Several'} patients have exceeded configured reassessment intervals without nurse evaluation.`;
    if (isBypass)
      return `Critical presentation triggered zero-latency emergency bypass protocol. Patient prioritized to ESI 1.`;
    if (isEscalation)
      return `Acuity worsened from ESI ${payload?.from_acuity} to ESI ${payload?.to_acuity}. Guardian queue re-sorted.`;
    return 'Clinical and operational alert requires staff attention.';
  };

  const handleDismissSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    dismissAlert(
      {
        alertId: alert_id,
        body: {
          reason_code: reasonCode,
          free_text_reason: freeTextReason.trim() || null,
        },
      },
      {
        onSuccess: () => {
          setIsDismissModalOpen(false);
        },
      }
    );
  };

  return (
    <div
      role="alert"
      className={cn(
        'p-4 rounded-xl border transition-all text-left flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-card',
        dismissed
          ? 'bg-slate-50 border-slate-200 opacity-70'
          : isBypass
          ? 'bg-rose-50 border-rose-200 border-l-4 border-l-rose-600'
          : isEscalation
          ? 'bg-orange-50 border-orange-200 border-l-4 border-l-orange-500'
          : 'bg-white border-slate-200'
      )}
    >
      <div className="flex items-start gap-3.5">
        <div
          className={cn(
            'p-2.5 rounded-xl shrink-0 mt-0.5',
            isBypass
              ? 'bg-rose-600 text-white'
              : isEscalation
              ? 'bg-orange-500 text-white'
              : 'bg-amber-500 text-white'
          )}
        >
          {isBypass ? (
            <Zap className="w-5 h-5 fill-white" />
          ) : isEscalation ? (
            <AlertTriangle className="w-5 h-5" />
          ) : (
            <Clock className="w-5 h-5" />
          )}
        </div>

        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="font-bold text-sm text-slate-900">{getTitle()}</h3>
            <span
              className={cn(
                'text-[10px] font-mono font-bold px-2 py-0.5 rounded-full border',
                isBypass
                  ? 'bg-white text-rose-700 border-rose-300'
                  : isEscalation
                  ? 'bg-white text-orange-700 border-orange-300'
                  : 'bg-white text-amber-700 border-amber-300'
              )}
            >
              {alert_type}
            </span>
          </div>

          <p className="text-xs text-slate-600 leading-relaxed font-sans">{getMessage()}</p>

          <div className="flex items-center gap-3 text-[11px] font-mono text-slate-400 pt-0.5">
            <span>{formatRelative(created_at)} ({formatClock(created_at, true)})</span>
            {caseId && (
              <Link
                to={`/cases/${caseId}`}
                className="text-indigo-600 hover:underline flex items-center gap-1 font-semibold"
              >
                Case {caseId.substring(0, 8)}
                <ArrowRight className="w-3 h-3" />
              </Link>
            )}
          </div>

          {dismissed && (
            <div className="text-[11px] font-mono text-slate-500 pt-1">
              Dismissed by {dismissed_by || 'Staff'} ({ALERT_DISMISSAL_REASONS[dismissal_reason_code!] || dismissal_reason_code})
              {dismissal_free_text ? ` — "${dismissal_free_text}"` : ''}
            </div>
          )}
        </div>
      </div>

      <div className="shrink-0 flex items-center gap-2">
        {!dismissed ? (
          <Button
            size="xs"
            variant={isBypass ? 'danger' : 'secondary'}
            onClick={() => setIsDismissModalOpen(true)}
            leftIcon={<CheckCircle2 className="w-3.5 h-3.5" />}
            className="text-xs font-bold"
          >
            Dismiss Alert
          </Button>
        ) : (
          <span className="text-[11px] font-mono text-slate-400 italic">
            Dismissed
          </span>
        )}
      </div>

      {/* Structured Dismissal Reason Modal */}
      {isDismissModalOpen && (
        <Modal
          isOpen={isDismissModalOpen}
          onClose={() => setIsDismissModalOpen(false)}
          size="md"
          title="Dismiss Interruptive Alert"
          description="Every interruptive alert requires a structured reason to feed the alert-tuning loop and prevent alert fatigue."
          footer={
            <>
              <Button
                variant="secondary"
                onClick={() => setIsDismissModalOpen(false)}
                disabled={isDismissPending}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                onClick={handleDismissSubmit}
                isLoading={isDismissPending}
              >
                Confirm Dismissal
              </Button>
            </>
          }
        >
          <form onSubmit={handleDismissSubmit} className="space-y-4 text-left">
            <Select
              label="Dismissal Reason Code (Required)"
              value={reasonCode}
              onChange={(e) => setReasonCode(e.target.value as AlertDismissalReasonCode)}
              options={[
                { value: 'ALREADY_ACTIONED', label: 'Already Actioned by Clinician' },
                { value: 'NOT_ACTIONABLE_RIGHT_NOW', label: 'Not Actionable Right Now (Monitoring)' },
                { value: 'FALSE_POSITIVE', label: 'False Positive / Measurement Artifact' },
                { value: 'DUPLICATE', label: 'Duplicate Alert' },
                { value: 'RESOLVED_AUTOMATICALLY', label: 'Resolved Automatically' },
                { value: 'OTHER', label: 'Other Operational Reason' },
              ]}
            />

            <Input
              label="Free Text Note (Optional)"
              placeholder="e.g. Attending physician bedside; airway secured."
              value={freeTextReason}
              onChange={(e) => setFreeTextReason(e.target.value)}
            />
          </form>
        </Modal>
      )}
    </div>
  );
};
