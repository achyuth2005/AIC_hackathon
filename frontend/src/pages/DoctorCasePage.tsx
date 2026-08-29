import React from 'react';
import { useParams } from 'react-router-dom';
import { useDoctorCase } from '../hooks/useDoctorCase';
import { DoctorCaseView } from '../features/doctor/DoctorCaseView';
import { Skeleton } from '../components/ui/Skeleton';
import { ErrorState } from '../components/ui/ErrorState';

export const DoctorCasePage: React.FC = () => {
  const { caseId } = useParams<{ caseId: string }>();
  const { data: caseData, isLoading, isError, error, refetch } = useDoctorCase(caseId);

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

  return <DoctorCaseView caseData={caseData} />;
};
