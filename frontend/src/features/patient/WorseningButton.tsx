import React, { useState } from 'react';
import { useReportWorsening } from '../../hooks/usePatientView';
import { Button } from '../../components/ui/Button';
import { Modal } from '../../components/ui/Modal';
import { Input } from '../../components/ui/Input';
import { AlertCircle, HeartHandshake } from 'lucide-react';

export interface WorseningButtonProps {
  caseId: string;
}

export const WorseningButton: React.FC<WorseningButtonProps> = ({ caseId }) => {
  const { mutate: reportWorsening, isPending } = useReportWorsening();
  const [isOpen, setIsOpen] = useState(false);
  const [note, setNote] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    reportWorsening(
      { caseId, note: note.trim() || undefined },
      {
        onSuccess: () => {
          setIsOpen(false);
          setNote('');
        },
      }
    );
  };

  return (
    <>
      <div className="p-6 rounded-2xl bg-amber-50 border-2 border-amber-300 text-left space-y-3 shadow-card">
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2 text-amber-800 font-extrabold text-base">
              <AlertCircle className="w-5 h-5 text-amber-600" />
              <span>Are Your Symptoms Getting Worse?</span>
            </div>
            <p className="text-xs text-amber-800/80 max-w-xl leading-relaxed">
              If you experience increased pain, shortness of breath, dizziness, or feel your condition is worsening while waiting, tap this button immediately to alert the nursing team for reassessment.
            </p>
          </div>

          <Button
            size="lg"
            variant="warning"
            onClick={() => setIsOpen(true)}
            className="shrink-0 font-extrabold text-sm px-6 py-3"
          >
            I Feel Worse
          </Button>
        </div>
      </div>

      {/* Confirmation & Optional Details Modal */}
      {isOpen && (
        <Modal
          isOpen={isOpen}
          onClose={() => setIsOpen(false)}
          size="md"
          title="Notify Triage Nurse Immediately"
          description="A notification will be sent straight to the Nurse Guardian Queue to prioritize an immediate bedside reassessment."
          footer={
            <>
              <Button
                variant="secondary"
                onClick={() => setIsOpen(false)}
                disabled={isPending}
              >
                Cancel
              </Button>
              <Button
                variant="warning"
                onClick={handleSubmit}
                isLoading={isPending}
                className="font-bold"
              >
                Send Nurse Alert
              </Button>
            </>
          }
        >
          <form onSubmit={handleSubmit} className="space-y-4 text-left">
            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 flex items-start gap-2.5 text-xs text-slate-600">
              <HeartHandshake className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
              <span>
                Our staff is here to help. You do not need to wait for your estimated time if you feel unwell.
              </span>
            </div>

            <Input
              label="What changed or what are you feeling? (Optional)"
              placeholder="e.g. Sharp pain in chest, feeling faint, nausea worsening..."
              value={note}
              onChange={(e) => setNote(e.target.value)}
              autoFocus
            />
          </form>
        </Modal>
      )}
    </>
  );
};
