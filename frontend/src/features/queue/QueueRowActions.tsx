import React, { useState } from 'react';
import { QueueEntry } from '../../types/api';
import { Button } from '../../components/ui/Button';
import { useOverride } from '../../hooks/useOverride';
import { useMarkReassessed } from '../../hooks/useMarkReassessed';
import { DeEscalateModal } from '../case/DeEscalateModal';
import {
  ArrowUpCircle,
  Clock,
  ExternalLink,
  MoreVertical,
  ArrowDownCircle,
  Activity,
} from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';

export interface QueueRowActionsProps {
  entry: QueueEntry;
}

export const QueueRowActions: React.FC<QueueRowActionsProps> = ({ entry }) => {
  const { case_id, final_acuity, display_name, reassessment } = entry;
  const { mutate: override, isPending: isOverridePending } = useOverride();
  const { mutate: markReassessed, isPending: isReassessPending } = useMarkReassessed();
  const [isDeEscalateOpen, setIsDeEscalateOpen] = useState(false);
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const navigate = useNavigate();

  const handleEscalate = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (final_acuity === 1) return;
    override({
      caseId: case_id,
      body: { action: 'ESCALATE' },
    });
  };

  const handleMarkReassessed = (e: React.MouseEvent) => {
    e.stopPropagation();
    markReassessed(case_id);
  };

  return (
    <div className="flex items-center gap-1.5 justify-end" onClick={(e) => e.stopPropagation()}>
      {/* 1-Tap Reassess Now Action — highest visual priority when overdue */}
      <Button
        variant={reassessment.is_due ? 'danger' : 'secondary'}
        size="sm"
        disabled={isReassessPending}
        isLoading={isReassessPending}
        onClick={handleMarkReassessed}
        leftIcon={<Clock className="w-3.5 h-3.5" />}
        title="Reset Reassessment Clock"
        className="font-semibold text-xs"
      >
        {reassessment.is_due ? 'Reassess Now' : 'Reassessed'}
      </Button>

      {/* 1-Tap Escalate Action */}
      <Button
        variant="warning"
        size="sm"
        disabled={final_acuity === 1 || isOverridePending}
        isLoading={isOverridePending}
        onClick={handleEscalate}
        leftIcon={<ArrowUpCircle className="w-3.5 h-3.5" />}
        title={final_acuity === 1 ? 'Patient already at ESI 1 (Highest Urgency)' : '1-Tap Escalate Urgency (No friction)'}
        className="font-semibold text-xs"
      >
        Escalate
      </Button>

      {/* Record Vitals Quick Link */}
      <Link to={`/cases/${case_id}`}>
        <Button
          variant="outline"
          size="sm"
          leftIcon={<Activity className="w-3.5 h-3.5 text-slate-500" />}
          className="hidden sm:inline-flex"
        >
          Vitals
        </Button>
      </Link>

      {/* Overflow Menu for De-escalate & More */}
      <div className="relative">
        <button
          onClick={() => setIsMenuOpen(!isMenuOpen)}
          className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-white/60 transition-colors"
          aria-label="More actions"
        >
          <MoreVertical className="w-4 h-4" />
        </button>

        {isMenuOpen && (
          <>
            <div className="fixed inset-0 z-20" onClick={() => setIsMenuOpen(false)} />
            <div className="absolute right-0 mt-1 w-52 rounded-2xl bg-white/85 backdrop-blur-2xl border border-white/90 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.9),0_16px_40px_rgba(31,38,135,0.08)] p-1.5 z-30 animate-fade-in text-left">
              <button
                onClick={() => {
                  setIsMenuOpen(false);
                  navigate(`/cases/${case_id}`);
                }}
                className="w-full text-left px-3 py-2 text-xs text-slate-700 hover:bg-white/70 hover:text-slate-900 rounded-xl flex items-center gap-2 transition-colors cursor-pointer"
              >
                <ExternalLink className="w-3.5 h-3.5 text-slate-400" />
                Open Full Case
              </button>

              <button
                onClick={() => {
                  setIsMenuOpen(false);
                  setIsDeEscalateOpen(true);
                }}
                disabled={final_acuity >= 5}
                className="w-full text-left px-3 py-2 text-xs text-rose-800 hover:bg-rose-500/15 hover:text-rose-900 rounded-xl flex items-center gap-2 disabled:opacity-40 transition-colors cursor-pointer"
              >
                <ArrowDownCircle className="w-3.5 h-3.5 text-rose-500" />
                De-escalate (Reason Required)
              </button>
            </div>
          </>
        )}
      </div>

      {/* De-escalate Modal with Reason Friction */}
      {isDeEscalateOpen && (
        <DeEscalateModal
          isOpen={isDeEscalateOpen}
          onClose={() => setIsDeEscalateOpen(false)}
          caseId={case_id}
          patientName={display_name}
          currentAcuity={final_acuity}
        />
      )}
    </div>
  );
};
