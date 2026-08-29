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
      className="p-4 rounded-xl bg-indigo-950/60 border-2 border-indigo-500 text-indigo-100 space-y-3 animate-fade-in shadow-lg text-left"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <TestTube className="w-5 h-5 text-indigo-400" />
          <h3 className="font-extrabold text-sm text-indigo-200 uppercase tracking-wide">
            Diagnostic Results Available for Physician Review ({unreviewededTests.length})
          </h3>
        </div>
        <span className="text-[10px] font-mono font-bold bg-indigo-900 text-indigo-200 px-2 py-0.5 rounded border border-indigo-700">
          Action Required
        </span>
      </div>

      <div className="space-y-2">
        {unreviewededTests.map((t) => (
          <div
            key={t.test_id}
            className="p-3 rounded-lg bg-slate-950/80 border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3"
          >
            <div className="space-y-0.5">
              <div className="font-bold text-xs text-white">{t.test_type}</div>
              <div className="text-[11px] text-slate-400 font-mono">
                Result ready {formatRelative(t.result_available_at || t.ordered_at)}
              </div>
            </div>

            <Button
              size="xs"
              variant="primary"
              isLoading={isPending}
              onClick={() => markReviewed({ testId: t.test_id, caseId, stage: 'review' })}
              leftIcon={<CheckCircle2 className="w-3.5 h-3.5" />}
              className="bg-emerald-600 hover:bg-emerald-500 text-xs font-bold shrink-0"
            >
              Sign & Mark Result Reviewed
            </Button>
          </div>
        ))}
      </div>
    </div>
  );
};
