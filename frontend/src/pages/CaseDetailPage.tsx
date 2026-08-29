import React from 'react';
import { useParams } from 'react-router-dom';
import { useCase } from '../hooks/useCase';
import { CaseHeader } from '../features/case/CaseHeader';
import { RiskAssessmentPanel } from '../features/case/RiskAssessmentPanel';
import { VitalsPanel } from '../features/case/VitalsPanel';
import { ExplanationPanel } from '../features/case/ExplanationPanel';
import { AcuityHistoryChart } from '../features/case/AcuityHistoryChart';
import { IntakeTextPanel } from '../features/case/IntakeTextPanel';
import { TimelineList } from '../features/case/TimelineList';
import { AssignResourcePanel } from '../features/case/AssignResourcePanel';
import { ConflictList } from '../features/case/ConflictList';
import { DiagnosticTestsPanel } from '../features/case/DiagnosticTestsPanel';
import { DecisionHistoryList } from '../features/case/DecisionHistoryList';
import { Skeleton } from '../components/ui/Skeleton';
import { ErrorState } from '../components/ui/ErrorState';

export const CaseDetailPage: React.FC = () => {
  const { caseId } = useParams<{ caseId: string }>();
  const { data: caseData, isLoading, isError, error, refetch } = useCase(caseId);

  if (isLoading) {
    return (
      <div className="space-y-6 max-w-6xl mx-auto p-4">
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-48 w-full" />
        <Skeleton className="h-32 w-full" />
      </div>
    );
  }

  if (isError || !caseData) {
    return (
      <div className="max-w-xl mx-auto py-12">
        <ErrorState
          title="Patient Case Not Found"
          error={error}
          onRetry={() => refetch()}
        />
      </div>
    );
  }

  return (
    <div className="space-y-8 max-w-6xl mx-auto pb-16 animate-fade-in text-left">
      {/* 1. Patient Header & Quick Override Controls */}
      <CaseHeader caseData={caseData} />

      {/* 2. Open Data Conflicts (if any exist) */}
      <ConflictList caseId={caseData.case_id} />

      {/* 3. Primary Clinical Risk Assessment & NEWS2/PEWS Breakdown */}
      <RiskAssessmentPanel
        assessment={caseData.latest_risk_assessment}
        isBypassActive={caseData.emergency_bypass_active}
      />

      {/* 4. Clinical Explanation (AI or Rule-based fallback) */}
      <ExplanationPanel caseId={caseData.case_id} />

      {/* 5. Department Resource Assignment & Capacity Conflicts */}
      <AssignResourcePanel caseId={caseData.case_id} />

      {/* 6. Diagnostic Tests Lifecycle */}
      <DiagnosticTestsPanel caseId={caseData.case_id} />

      {/* 7. Current Observations & Vitals Capture */}
      <VitalsPanel
        caseId={caseData.case_id}
        observations={caseData.current_observations || []}
      />

      {/* 8. Clinician Override Audit History */}
      <DecisionHistoryList caseId={caseData.case_id} />

      {/* 9. Acuity Trend Chart (Inverted Y-axis) */}
      <AcuityHistoryChart caseId={caseData.case_id} />

      {/* 10. AI Intake & Clinical Notes */}
      <IntakeTextPanel caseId={caseData.case_id} />

      {/* 11. Immutable Event-Sourced Timeline Audit */}
      <TimelineList caseId={caseData.case_id} />
    </div>
  );
};
