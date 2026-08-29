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
      {/* 1-Tap Escalate Action */}
      <Button
        variant="warning"
        size="sm"
        disabled={final_acuity === 1 || isOverridePending}
        isLoading={isOverridePending}
        onClick={handleEscalate}
        leftIcon={<ArrowUpCircle className="w-3.5 h-3.5" />}
        title={final_acuity === 1 ? 'Patient already at ESI 1 (Highest Urgency)' : '1-Tap Escalate Urgency (No friction)'}
        className="font-bold text-xs shadow-sm bg-orange-600 hover:bg-orange-500 active:bg-orange-700 disabled:opacity-40"
      >
        Escalate
      </Button>

      {/* Mark Reassessed Action */}
      <Button
        variant={reassessment.is_due ? 'danger' : 'secondary'}
        size="sm"
        disabled={isReassessPending}
        isLoading={isReassessPending}
        onClick={handleMarkReassessed}
        leftIcon={<Clock className="w-3.5 h-3.5" />}
        title="Reset Reassessment Clock"
        className={reassessment.is_due ? 'animate-pulse' : ''}
      >
        {reassessment.is_due ? 'Reassess Now' : 'Reassessed'}
      </Button>

      {/* Record Vitals Quick Link */}
      <Link to={`/cases/${case_id}`}>
        <Button
          variant="secondary"
          size="sm"
          leftIcon={<Activity className="w-3.5 h-3.5 text-cyan-400" />}
          className="hidden sm:inline-flex"
        >
          Vitals
        </Button>
      </Link>

      {/* Overflow Menu for De-escalate & More */}
      <div className="relative">
        <button
          onClick={() => setIsMenuOpen(!isMenuOpen)}
          className="p-1.5 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition-colors"
          aria-label="More actions"
        >
          <MoreVertical className="w-4 h-4" />
        </button>

        {isMenuOpen && (
          <>
            <div className="fixed inset-0 z-20" onClick={() => setIsMenuOpen(false)} />
            <div className="absolute right-0 mt-1 w-48 rounded-xl bg-slate-900 border border-slate-700 shadow-2xl p-1 z-30 animate-fade-in text-left">
              <button
                onClick={() => {
                  setIsMenuOpen(false);
                  navigate(`/cases/${case_id}`);
                }}
                className="w-full text-left px-3 py-2 text-xs text-slate-200 hover:bg-slate-800 hover:text-white rounded-lg flex items-center gap-2"
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
                className="w-full text-left px-3 py-2 text-xs text-rose-300 hover:bg-rose-950/60 hover:text-rose-100 rounded-lg flex items-center gap-2 disabled:opacity-40"
              >
                <ArrowDownCircle className="w-3.5 h-3.5 text-rose-400" />
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
