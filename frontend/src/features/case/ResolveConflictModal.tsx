import React, { useState } from 'react';
import { DataConflictResponse, ObservationResponse } from '../../types/api';
import { Modal } from '../../components/ui/Modal';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { useResolveConflict } from '../../hooks/useConflicts';
import { useObservations } from '../../hooks/useObservations';
import { formatClock, formatRelative } from '../../lib/datetime';
import { SOURCE_TYPE_LABELS, RELIABILITY_TIER_LABELS } from '../../lib/enums';
import { AlertTriangle, CheckCircle2, GitCompare } from 'lucide-react';

export interface ResolveConflictModalProps {
  isOpen: boolean;
  onClose: () => void;
  conflict: DataConflictResponse;
}

export const ResolveConflictModal: React.FC<ResolveConflictModalProps> = ({
  isOpen,
  onClose,
  conflict,
}) => {
  const { conflict_id, case_id, concept_code, observation_ids, conservative_observation_id } =
    conflict;

  const { data: allObservations } = useObservations(case_id, concept_code);
  const [selectedObsId, setSelectedObsId] = useState<string>(
    conservative_observation_id || observation_ids[0] || ''
  );
  const [resolutionNote, setResolutionNote] = useState('');
  const { mutate: resolveConflict, isPending } = useResolveConflict();

  const conflictingObs = (allObservations || []).filter((o) =>
    observation_ids.includes(o.observation_id)
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedObsId) return;

    resolveConflict(
      {
        conflictId: conflict_id,
        caseId: case_id,
        body: {
          kept_observation_id: selectedObsId,
          note: resolutionNote.trim() || null,
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
      size="lg"
      title={
        <div className="flex items-center gap-2 text-purple-300">
          <GitCompare className="w-5 h-5 text-purple-400" />
          <span>Resolve Conflicting Clinical Observations</span>
        </div>
      }
      description={
        <span>
          Contradictory readings detected for concept{' '}
          <strong className="text-white font-mono">{concept_code}</strong>. Choose which reading to maintain for scoring.
        </span>
      }
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={isPending}>
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={handleSubmit}
            isLoading={isPending}
            disabled={!selectedObsId}
          >
            Confirm Clinical Resolution
          </Button>
        </>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-4 text-left">
        <div className="p-3 rounded-xl bg-purple-950/40 border border-purple-800/60 text-xs text-purple-200 flex items-start gap-2.5">
          <AlertTriangle className="w-4 h-4 text-purple-400 shrink-0 mt-0.5" />
          <div>
            <span className="font-bold text-purple-300">Conservative Safety Default:</span>{' '}
            The scoring stack currently defaults to the more conservative/abnormal observation until explicitly resolved by clinician review.
          </div>
        </div>

        {/* Side-by-Side Conflicting Observations (Phase 9.3) */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {conflictingObs.map((obs: ObservationResponse) => {
            const isSelected = selectedObsId === obs.observation_id;
            const isConservative = conservative_observation_id === obs.observation_id;

            return (
              <button
                key={obs.observation_id}
                type="button"
                onClick={() => setSelectedObsId(obs.observation_id)}
                className={`p-4 rounded-xl border text-left transition-all cursor-pointer relative ${
                  isSelected
                    ? 'bg-purple-950/60 border-purple-500 ring-2 ring-purple-500'
                    : 'bg-slate-950/60 border-slate-800 hover:border-slate-700'
                }`}
              >
                {isConservative && (
                  <span className="absolute top-2 right-2 px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-950 text-amber-300 border border-amber-700/60">
                    Conservative Default
                  </span>
                )}

                <div className="flex items-center gap-2">
                  <div
                    className={`w-4 h-4 rounded-full border flex items-center justify-center ${
                      isSelected
                        ? 'border-purple-400 bg-purple-400 text-slate-950'
                        : 'border-slate-600'
                    }`}
                  >
                    {isSelected && <CheckCircle2 className="w-3.5 h-3.5" />}
                  </div>
                  <span className="font-mono font-black text-xl text-white">
                    {String(obs.value)} {obs.unit || ''}
                  </span>
                </div>

                <div className="mt-3 space-y-1 text-xs text-slate-400 font-mono">
                  <div>Source: <strong className="text-slate-200">{SOURCE_TYPE_LABELS[obs.source_type]}</strong></div>
                  <div>Reliability: <span className="text-slate-300">{RELIABILITY_TIER_LABELS[obs.reliability_tier]}</span></div>
                  <div>Observed: {formatRelative(obs.observed_at)} ({formatClock(obs.observed_at, true)})</div>
                </div>
              </button>
            );
          })}
        </div>

        <Input
          label="Resolution Note (Optional)"
          placeholder="e.g. Verified with manual blood pressure cuff; device reading was movement artifact."
          value={resolutionNote}
          onChange={(e) => setResolutionNote(e.target.value)}
        />
      </form>
    </Modal>
  );
};
