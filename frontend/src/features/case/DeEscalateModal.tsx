import React, { useState } from 'react';
import { Modal } from '../../components/ui/Modal';
import { Button } from '../../components/ui/Button';
import { Select } from '../../components/ui/Select';
import { Input } from '../../components/ui/Input';
import { DeEscalationReasonCode } from '../../types/enums';
import { DE_ESCALATION_REASONS } from '../../lib/enums';
import { useOverride } from '../../hooks/useOverride';
import { ShieldAlert, AlertTriangle } from 'lucide-react';
import { AcuityBadge } from '../../components/clinical/AcuityBadge';

export interface DeEscalateModalProps {
  isOpen: boolean;
  onClose: () => void;
  caseId: string;
  patientName: string | null;
  currentAcuity: number;
}

export const DeEscalateModal: React.FC<DeEscalateModalProps> = ({
  isOpen,
  onClose,
  caseId,
  patientName,
  currentAcuity,
}) => {
  const [targetAcuity, setTargetAcuity] = useState<number>(Math.min(5, currentAcuity + 1));
  const [reasonCode, setReasonCode] = useState<DeEscalationReasonCode>(
    'PATIENT_STABLE_ON_CLINICAL_REVIEW'
  );
  const [freeTextReason, setFreeTextReason] = useState('');
  const { mutate: override, isPending } = useOverride();

  // Target acuity options must be strictly greater than current acuity (less urgent)
  const availableAcuities: { value: number; label: string }[] = [];
  for (let a = currentAcuity + 1; a <= 5; a++) {
    availableAcuities.push({
      value: a,
      label: `ESI ${a} (${a === 3 ? 'Urgent' : a === 4 ? 'Less Urgent' : 'Non-Urgent'})`,
    });
  }

  const reasonOptions = Object.entries(DE_ESCALATION_REASONS).map(([code, label]) => ({
    value: code,
    label,
  }));

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (targetAcuity <= currentAcuity) return;

    override(
      {
        caseId,
        body: {
          action: 'DE_ESCALATE',
          target_acuity: targetAcuity,
          reason_code: reasonCode,
          free_text_reason: freeTextReason.trim() || null,
        },
      },
      {
        onSuccess: () => {
          onClose();
        },
      }
    );
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      size="md"
      title={
        <div className="flex items-center gap-2 text-rose-700">
          <ShieldAlert className="w-5 h-5 text-rose-600" />
          <span>Structured Clinical De-escalation</span>
        </div>
      }
      description={
        <span>
          De-escalating <strong className="text-slate-700">{patientName || caseId}</strong> from{' '}
          <strong className="text-amber-700">ESI {currentAcuity}</strong>.
        </span>
      }
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={isPending}>
            Cancel
          </Button>
          <Button
            variant="danger"
            onClick={handleSubmit}
            isLoading={isPending}
            disabled={targetAcuity <= currentAcuity || !reasonCode}
          >
            Apply De-escalation Override
          </Button>
        </>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Asymmetric Friction Banner */}
        <div className="p-3 rounded-xl bg-amber-50 border border-amber-200 text-xs text-amber-800 flex items-start gap-2.5">
          <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
          <div>
            <span className="font-semibold text-amber-800">Permanent Governance Audit:</span>{' '}
            Per Phase 9.6, de-escalating acuity creates an immutable audit record and is flagged for retrospective administrative review.
          </div>
        </div>

        <div className="flex items-center justify-between p-3 rounded-xl bg-slate-50 border border-slate-200/80">
          <div className="space-y-1">
            <span className="text-xs text-slate-500 block font-semibold">Current Acuity:</span>
            <AcuityBadge acuity={currentAcuity} size="sm" />
          </div>
          <div className="text-slate-400 font-mono text-xl">→</div>
          <div className="space-y-1">
            <span className="text-xs text-slate-500 block font-semibold">New Target:</span>
            <AcuityBadge acuity={targetAcuity} size="sm" />
          </div>
        </div>

        <Select
          label="Target Acuity Level (Required)"
          value={targetAcuity}
          onChange={(e) => setTargetAcuity(Number(e.target.value))}
          options={availableAcuities}
        />

        <Select
          label="Clinical Reason Code (Required)"
          value={reasonCode}
          onChange={(e) => setReasonCode(e.target.value as DeEscalationReasonCode)}
          options={reasonOptions}
        />

        <Input
          label="Clinical Justification Note (Optional)"
          placeholder="Additional notes for retrospective review..."
          value={freeTextReason}
          onChange={(e) => setFreeTextReason(e.target.value)}
        />
      </form>
    </Modal>
  );
};
