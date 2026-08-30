import React from 'react';
import { DiagnosticTestResponse } from '../../types/api';
import { useAdvanceTest } from '../../hooks/useCaseTests';
import { Button } from '../../components/ui/Button';
import { TestTube, CheckCircle2 } from 'lucide-react';
import { formatRelative } from '../../lib/datetime';

export interface UnreviewedResultsBannerProps {
  caseId: string;
  unreviewededTests: DiagnosticTestResponse[];
}

export const UnreviewedResultsBanner: React.FC<UnreviewedResultsBannerProps> = ({
  caseId,
  unreviewededTests,
}) => {
  const { mutate: markReviewed, isPending } = useAdvanceTest();

  if (!unreviewededTests || unreviewededTests.length === 0) {
    return null;
  }

  return (
    <div
      role="alert"
      className="p-4 rounded-xl bg-indigo-50 border-2 border-indigo-200 text-indigo-900 space-y-3 animate-fade-in shadow-card text-left"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <TestTube className="w-5 h-5 text-indigo-600" />
          <h3 className="font-bold text-sm text-indigo-900 uppercase tracking-wide">
            Diagnostic Results Available for Physician Review ({unreviewededTests.length})
          </h3>
        </div>
        <span className="text-[10px] font-mono font-bold bg-indigo-600 text-white px-2 py-0.5 rounded border border-indigo-700">
          Action Required
        </span>
      </div>

      <div className="space-y-2">
        {unreviewededTests.map((t) => (
          <div
            key={t.test_id}
            className="p-3 rounded-lg bg-white border border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3"
          >
            <div className="space-y-0.5">
              <div className="font-semibold text-xs text-slate-900">{t.test_type}</div>
              <div className="text-[11px] text-slate-500 font-mono">
                Result ready {formatRelative(t.result_available_at || t.ordered_at)}
              </div>
            </div>

            <Button
              size="xs"
              variant="primary"
              isLoading={isPending}
              onClick={() => markReviewed({ testId: t.test_id, caseId, stage: 'review' })}
              leftIcon={<CheckCircle2 className="w-3.5 h-3.5" />}
              className="bg-emerald-600 hover:bg-emerald-700 text-xs font-bold shrink-0"
            >
              Sign & Mark Result Reviewed
            </Button>
          </div>
        ))}
      </div>
    </div>
  );
};
