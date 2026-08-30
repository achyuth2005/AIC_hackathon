import { useParams } from 'react-router-dom';
import { usePatientView } from '../hooks/usePatientView';
import { StageProgressTracker } from '../features/patient/StageProgressTracker';
import { WaitTimeDisplay } from '../features/patient/WaitTimeDisplay';
import { WorseningButton } from '../features/patient/WorseningButton';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card';
import { HeartPulse, MessageSquare, PhoneCall, RefreshCw } from 'lucide-react';
import { Skeleton } from '../components/ui/Skeleton';
import { ErrorState } from '../components/ui/ErrorState';

export const PatientPage: React.FC = () => {
  const { caseId } = useParams<{ caseId: string }>();
  const { data: patientView, isLoading, isError, error, refetch, isFetching } = usePatientView(caseId);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-50 p-6 flex flex-col items-center justify-center max-w-4xl mx-auto space-y-6">
        <Skeleton className="h-24 w-full rounded-2xl" />
        <Skeleton className="h-48 w-full rounded-2xl" />
        <Skeleton className="h-40 w-full rounded-2xl" />
      </div>
    );
  }

  if (isError || !patientView || !caseId) {
    return (
      <div className="min-h-screen bg-slate-50 p-6 flex flex-col items-center justify-center max-w-md mx-auto text-left">
        <ErrorState
          title="Patient Waiting Room Portal"
          error={error || new Error('Invalid or missing case link.')}
          onRetry={() => refetch()}
        />
        <div className="mt-6 text-center">
          <p className="text-xs text-slate-500">
            Please ask the front triage desk for your mobile tracking link or QR code.
          </p>
        </div>
      </div>
    );
  }

  const { display_name, stage, next_step_message, wait_time_estimate } = patientView;

  return (
    <div className="min-h-screen bg-slate-50 py-8 px-4 sm:px-6 flex flex-col justify-between">
      <div className="max-w-4xl w-full mx-auto space-y-6 text-left animate-fade-in pb-12">
        {/* Header */}
        <div className="p-6 rounded-3xl bg-white border border-slate-200/80 flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-card">
          <div className="flex items-center gap-3.5">
            <div className="p-3 rounded-2xl bg-emerald-50 text-emerald-600 border border-emerald-200">
              <HeartPulse className="w-8 h-8" />
            </div>
            <div>
              <div className="text-xs font-bold font-mono text-emerald-700 uppercase tracking-wider">
                Emergency Department Care Portal
              </div>
              <h1 className="text-2xl font-black text-slate-900">
                Welcome, {display_name || 'Patient'}
              </h1>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => refetch()}
              disabled={isFetching}
              className="p-2.5 rounded-xl bg-slate-50 border border-slate-200 text-slate-500 hover:text-slate-900 cursor-pointer transition-colors"
              title="Refresh status"
            >
              <RefreshCw className={`w-4 h-4 ${isFetching ? 'animate-spin text-emerald-600' : ''}`} />
            </button>
            <div className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-slate-50 border border-slate-200 text-xs font-mono text-slate-600">
              <PhoneCall className="w-3.5 h-3.5 text-emerald-600" />
              <span>Desk Ext: 4100</span>
            </div>
          </div>
        </div>

        {/* 1. Care Pathway Progress Tracker */}
        <StageProgressTracker currentStage={stage} />

        {/* 2. Transparent Estimated Wait Time Interval */}
        <WaitTimeDisplay estimate={wait_time_estimate} />

        {/* 3. Next Step & Clinical Instructions Message */}
        <Card className="text-left">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2 text-slate-600">
              <MessageSquare className="w-4 h-4 text-emerald-600" />
              <span>What to Expect Next</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-sm font-medium text-slate-700 leading-relaxed">
              {next_step_message || 'Please remain seated in the waiting area. A clinical team member will call your name for physician examination.'}
            </div>
          </CardContent>
        </Card>

        {/* 4. "I Feel Worse" Single-Tap Reassessment Button */}
        <WorseningButton caseId={caseId} />
      </div>

      {/* Footer Disclaimer */}
      <footer className="text-center py-4 text-xs font-mono text-slate-400 border-t border-slate-200 max-w-4xl mx-auto w-full">
        PatientTriage.ai Waiting Room System • Patient Data Strictly Isolated
      </footer>
    </div>
  );
};
