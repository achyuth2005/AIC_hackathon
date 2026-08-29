import React, { useState } from 'react';
import { useConfirmIdentity, useProposeIdentity } from '../../hooks/useAmbulanceActions';
import { IdentityLinkStatus } from '../../types/enums';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { UserCheck, ShieldAlert, UserPlus, AlertTriangle } from 'lucide-react';

export interface IdentityMatchPromptProps {
  caseId: string;
  identityStatus: IdentityLinkStatus;
  mrn?: string | null;
  displayName?: string | null;
  candidateMrn?: string | null;
  candidateDisplayName?: string | null;
  candidateConfidence?: number | null;
}

export const IdentityMatchPrompt: React.FC<IdentityMatchPromptProps> = ({
  caseId,
  identityStatus,
  mrn,
  displayName,
  candidateMrn,
  candidateDisplayName,
  candidateConfidence,
}) => {
  const { mutate: confirmIdentity, isPending: isConfirmPending } = useConfirmIdentity();
  const { mutate: proposeIdentity, isPending: isProposePending } = useProposeIdentity();

  const [propMrn, setPropMrn] = useState('MRN-4421');
  const [propName, setPropName] = useState('Ramesh Sharma');
  const [showProposeForm, setShowProposeForm] = useState(false);

  const handleConfirm = () => {
    if (!candidateMrn) return;
    confirmIdentity({
      caseId,
      body: {
        mrn: candidateMrn,
        display_name: candidateDisplayName || displayName || 'Confirmed Patient',
      },
    });
  };

  const handleProposeSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!propMrn.trim()) return;

    proposeIdentity(
      {
        caseId,
        body: {
          candidate_mrn: propMrn.trim(),
          candidate_display_name: propName.trim() || null,
          confidence: 0.88,
        },
      },
      {
        onSuccess: () => {
          setShowProposeForm(false);
        },
      }
    );
  };

  if (identityStatus === 'CONFIRMED') {
    return (
      <div className="p-4 rounded-xl bg-emerald-950/40 border border-emerald-600/60 text-xs text-emerald-200 flex items-center justify-between text-left">
        <div className="flex items-center gap-2.5">
          <UserCheck className="w-5 h-5 text-emerald-400 shrink-0" />
          <div>
            <div className="font-bold text-emerald-300">Identity Confirmed & EHR Linked</div>
            <div className="text-slate-300 font-mono mt-0.5">
              {displayName || 'Patient'} • MRN: {mrn || 'CONFIRMED'}
            </div>
          </div>
        </div>
        <span className="text-[10px] font-mono font-bold bg-emerald-900 text-emerald-200 px-2 py-0.5 rounded border border-emerald-700">
          LINKED
        </span>
      </div>
    );
  }

  return (
    <Card className="bg-slate-900 border-indigo-900/60 text-left shadow-lg">
      <CardHeader className="pb-3 flex flex-row items-center justify-between">
        <CardTitle className="text-sm flex items-center gap-2 text-indigo-300">
          <UserCheck className="w-4 h-4 text-indigo-400" />
          <span>Ambulance Patient Identity Matching (Phase 7.1)</span>
        </CardTitle>
        <span className="text-[10px] font-mono font-bold bg-indigo-950 text-indigo-300 px-2 py-0.5 rounded border border-indigo-700">
          {identityStatus}
        </span>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Candidate Match Alert Box */}
        {identityStatus === 'CANDIDATE_PROPOSED' ? (
          <div className="p-4 rounded-xl bg-indigo-950/40 border border-indigo-600/80 space-y-3">
            <div className="flex items-start gap-2.5">
              <ShieldAlert className="w-5 h-5 text-indigo-400 shrink-0 mt-0.5" />
              <div>
                <div className="font-extrabold text-sm text-indigo-200">
                  Candidate Patient Record Found
                </div>
                <p className="text-xs text-slate-300 mt-1 leading-relaxed">
                  The demographic matcher identified candidate <strong className="text-white">{candidateDisplayName || 'Patient'}</strong> ({candidateMrn}) with {candidateConfidence ? `${Math.round(candidateConfidence * 100)}% match confidence` : 'high probability'}.
                </p>
              </div>
            </div>

            {/* Invariant callout */}
            <div className="p-2.5 rounded-lg bg-slate-950/80 border border-slate-800 text-[11px] text-amber-300 flex items-start gap-2">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
              <span>
                Safety Rule: The system never automatically merges patient EHR records. A human clinician must explicitly verify and confirm.
              </span>
            </div>

            <div className="flex justify-end gap-2 pt-1">
              <Button
                variant="primary"
                size="sm"
                isLoading={isConfirmPending}
                onClick={handleConfirm}
                leftIcon={<UserCheck className="w-4 h-4" />}
                className="bg-indigo-600 hover:bg-indigo-500 font-bold text-xs"
              >
                Confirm Identity Link
              </Button>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            <p className="text-xs text-slate-400 leading-relaxed">
              Patient is currently unlinked. Prior medical history will not be attached until candidate match is proposed and confirmed by clinical staff.
            </p>

            {!showProposeForm ? (
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setShowProposeForm(true)}
                leftIcon={<UserPlus className="w-3.5 h-3.5" />}
                className="text-xs"
              >
                Propose Candidate EHR Record (Demo)
              </Button>
            ) : (
              <form onSubmit={handleProposeSubmit} className="p-3 rounded-xl bg-slate-950 border border-slate-800 space-y-3 animate-fade-in">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <Input
                    label="Candidate MRN"
                    value={propMrn}
                    onChange={(e) => setPropMrn(e.target.value)}
                  />
                  <Input
                    label="Candidate Display Name"
                    value={propName}
                    onChange={(e) => setPropName(e.target.value)}
                  />
                </div>
                <div className="flex justify-end gap-2">
                  <Button
                    type="button"
                    variant="secondary"
                    size="xs"
                    onClick={() => setShowProposeForm(false)}
                  >
                    Cancel
                  </Button>
                  <Button
                    type="submit"
                    variant="primary"
                    size="xs"
                    isLoading={isProposePending}
                  >
                    Submit Candidate Proposal
                  </Button>
                </div>
              </form>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
};
