import React from 'react';
import { useParams, Link } from 'react-router-dom';
import { useCase } from '../hooks/useCase';
import { usePreAlertView } from '../hooks/usePreAlertView';
import { PreAlertCard } from '../features/ambulance/PreAlertCard';
import { TransportDelayControl } from '../features/ambulance/TransportDelayControl';
import { IdentityMatchPrompt } from '../features/ambulance/IdentityMatchPrompt';
import { ArrivedButton } from '../features/ambulance/ArrivedButton';
import { Truck, ArrowLeft, ArrowRight } from 'lucide-react';
import { Skeleton } from '../components/ui/Skeleton';
import { ErrorState } from '../components/ui/ErrorState';

export const AmbulanceCasePage: React.FC = () => {
  const { caseId } = useParams<{ caseId: string }>();
  const { data: caseItem, isLoading: isCaseLoading, isError: isCaseError, error: caseError } = useCase(caseId);
  const { data: preAlert, isLoading: isPreAlertLoading, isError: isPreAlertError, error: preAlertError } = usePreAlertView(caseId);

  if (isCaseLoading || isPreAlertLoading) {
    return (
      <div className="space-y-6 max-w-5xl mx-auto pb-16 animate-fade-in">
        <Skeleton className="h-20 w-full" />
        <Skeleton className="h-64 w-full" />
        <Skeleton className="h-48 w-full" />
      </div>
    );
  }

  if (isCaseError || isPreAlertError || !caseItem || !preAlert) {
    return (
      <div className="max-w-4xl mx-auto py-12">
        <ErrorState
          title="Failed to load ambulance pre-alert details"
          error={caseError || preAlertError}
        />
        <div className="mt-4 text-center">
          <Link to="/ambulance" className="text-cyan-400 text-xs font-mono hover:underline">
            ← Return to Inbound Ambulance Board
          </Link>
        </div>
      </div>
    );
  }

  const isPreArrival = caseItem.status === 'PRE_ARRIVAL';

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-16 animate-fade-in text-left">
      {/* Top Breadcrumb & Action Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div className="flex items-center gap-3">
          <Link
            to="/ambulance"
            className="p-2 rounded-xl bg-slate-900 border border-slate-800 text-slate-400 hover:text-white"
            title="Back to Inbound Board"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-extrabold text-slate-100 flex items-center gap-2">
                <Truck className="w-5 h-5 text-cyan-400" />
                <span>Pre-Alert: {caseItem.display_name || 'Inbound EMS Patient'}</span>
              </h1>
              <span
                className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${
                  isPreArrival
                    ? 'bg-cyan-950 text-cyan-300 border-cyan-700 animate-pulse'
                    : 'bg-emerald-950 text-emerald-300 border-emerald-700'
                }`}
              >
                {caseItem.status}
              </span>
            </div>
            <p className="text-[11px] font-mono text-slate-500 mt-0.5">
              Case {caseItem.case_id} • Dispatch telemetry streaming
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <ArrivedButton caseId={caseItem.case_id} isPreArrival={isPreArrival} />
          <Link
            to={`/cases/${caseItem.case_id}`}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs font-mono font-bold text-cyan-300 hover:text-cyan-200"
          >
            <span>Full Workspace</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </div>

      {/* 1. Scannable 3-Second Pre-Alert Card with Live ETA Countdown */}
      <PreAlertCard preAlert={preAlert} />

      {/* 2. Patient Identity Matching (Phase 7.1) */}
      <IdentityMatchPrompt
        caseId={caseItem.case_id}
        identityStatus={caseItem.identity_link_status}
        mrn={caseItem.mrn}
        displayName={caseItem.display_name}
        candidateMrn={caseItem.candidate_mrn}
        candidateDisplayName={caseItem.candidate_display_name}
        candidateConfidence={caseItem.candidate_confidence}
      />

      {/* 3. Paramedic Transport Delay Simulation */}
      {isPreArrival && <TransportDelayControl caseId={caseItem.case_id} />}
    </div>
  );
};
