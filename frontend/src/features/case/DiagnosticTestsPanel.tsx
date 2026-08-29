import React, { useState } from 'react';
import { useCaseTests, useOrderTest, useAdvanceTest } from '../../hooks/useCaseTests';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { formatRelative, formatClock } from '../../lib/datetime';
import { DIAGNOSTIC_STATUS_LABELS } from '../../lib/enums';
import { TestTube, Plus, Clock, CheckCircle2, ArrowRight, AlertCircle } from 'lucide-react';

export interface DiagnosticTestsPanelProps {
  caseId: string;
}

export const DiagnosticTestsPanel: React.FC<DiagnosticTestsPanelProps> = ({ caseId }) => {
  const { data: tests, isLoading } = useCaseTests(caseId);
  const { mutate: orderTest, isPending: isOrderPending } = useOrderTest();
  const { mutate: advanceTest, isPending: isAdvancePending } = useAdvanceTest();

  const [testType, setTestType] = useState('');
  const [showOrderForm, setShowOrderForm] = useState(false);

  const handleOrder = (e: React.FormEvent) => {
    e.preventDefault();
    if (!testType.trim()) return;
    orderTest(
      { caseId, body: { test_type: testType.trim() } },
      {
        onSuccess: () => {
          setTestType('');
          setShowOrderForm(false);
        },
      }
    );
  };

  const stages = ['ORDERED', 'SAMPLE_COLLECTED', 'RESULT_AVAILABLE', 'RESULT_REVIEWED'] as const;

  return (
    <Card className="bg-slate-900 border-slate-800 text-left">
      <CardHeader className="pb-3 flex flex-row items-center justify-between">
        <CardTitle className="text-sm flex items-center gap-2 text-slate-200">
          <TestTube className="w-4 h-4 text-indigo-400" />
          Diagnostic Tests & Labs ({tests?.length || 0})
        </CardTitle>

        <Button
          variant="secondary"
          size="xs"
          onClick={() => setShowOrderForm(!showOrderForm)}
          leftIcon={<Plus className="w-3.5 h-3.5" />}
        >
          {showOrderForm ? 'Cancel' : 'Order Diagnostic Test'}
        </Button>
      </CardHeader>

      <CardContent className="space-y-4">
        {showOrderForm && (
          <form
            onSubmit={handleOrder}
            className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 flex flex-col sm:flex-row items-end gap-3 animate-fade-in"
          >
            <div className="flex-1 w-full">
              <Input
                label="Diagnostic Test Type"
                placeholder="e.g. 12-Lead ECG, Point-of-Care Troponin, Chest X-Ray"
                value={testType}
                onChange={(e) => setTestType(e.target.value)}
              />
            </div>
            <Button
              type="submit"
              variant="primary"
              size="md"
              isLoading={isOrderPending}
              disabled={!testType.trim()}
              className="w-full sm:w-auto font-bold bg-indigo-600 hover:bg-indigo-500"
            >
              Order Test
            </Button>
          </form>
        )}

        {isLoading ? (
          <div className="space-y-2">
            <div className="h-12 bg-slate-800/60 rounded-xl animate-pulse" />
          </div>
        ) : !tests || tests.length === 0 ? (
          <div className="text-xs text-slate-500 font-mono text-center py-4 italic">
            No diagnostic tests ordered for this case.
          </div>
        ) : (
          <div className="space-y-3">
            {tests.map((t) => {
              const currentStageIdx = stages.indexOf(t.status);

              return (
                <div
                  key={t.test_id}
                  className={`p-3.5 rounded-xl border space-y-3 ${
                    t.stuck_flagged
                      ? 'bg-rose-950/20 border-rose-600/70'
                      : 'bg-slate-950/60 border-slate-800'
                  }`}
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <TestTube className="w-4 h-4 text-indigo-400" />
                      <span className="font-bold text-sm text-slate-100">{t.test_type}</span>
                      <span className="text-[10px] font-mono text-slate-400 px-2 py-0.5 rounded bg-slate-900 border border-slate-800">
                        {DIAGNOSTIC_STATUS_LABELS[t.status]}
                      </span>
                      {t.stuck_flagged && (
                        <span className="text-[10px] font-mono font-bold text-rose-300 bg-rose-950 px-2 py-0.5 rounded border border-rose-700/60 flex items-center gap-1 animate-pulse">
                          <AlertCircle className="w-3 h-3 text-rose-400" />
                          STUCK
                        </span>
                      )}
                    </div>

                    <div className="text-[11px] font-mono text-slate-400">
                      Ordered: {formatRelative(t.ordered_at)} ({formatClock(t.ordered_at)})
                    </div>
                  </div>

                  {/* 4-Stage Stepper */}
                  <div className="grid grid-cols-4 gap-1.5 pt-1">
                    {stages.map((stage, idx) => {
                      const isCompleted = idx <= currentStageIdx;
                      const isCurrent = idx === currentStageIdx;

                      return (
                        <div
                          key={stage}
                          className={`p-2 rounded-lg text-center text-[10px] font-mono border transition-all ${
                            isCurrent
                              ? 'bg-indigo-950 text-indigo-200 border-indigo-500 font-bold'
                              : isCompleted
                              ? 'bg-slate-900 text-slate-300 border-slate-700/60'
                              : 'bg-slate-950 text-slate-600 border-slate-800/40'
                          }`}
                        >
                          <div className="flex items-center justify-center gap-1">
                            {isCompleted ? (
                              <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                            ) : (
                              <Clock className="w-3 h-3 text-slate-600" />
                            )}
                            <span className="truncate">{stage.replace(/_/g, ' ')}</span>
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  {/* Lifecycle advance buttons */}
                  <div className="flex justify-end gap-2 pt-1 border-t border-slate-900">
                    {t.status === 'ORDERED' && (
                      <Button
                        size="xs"
                        variant="secondary"
                        disabled={isAdvancePending}
                        onClick={() => advanceTest({ testId: t.test_id, caseId, stage: 'sample' })}
                        rightIcon={<ArrowRight className="w-3 h-3" />}
                      >
                        Mark Sample Collected
                      </Button>
                    )}

                    {t.status === 'SAMPLE_COLLECTED' && (
                      <Button
                        size="xs"
                        variant="secondary"
                        disabled={isAdvancePending}
                        onClick={() => advanceTest({ testId: t.test_id, caseId, stage: 'result' })}
                        rightIcon={<ArrowRight className="w-3 h-3" />}
                      >
                        Mark Result Available
                      </Button>
                    )}

                    {t.status === 'RESULT_AVAILABLE' && (
                      <Button
                        size="xs"
                        variant="primary"
                        disabled={isAdvancePending}
                        onClick={() => advanceTest({ testId: t.test_id, caseId, stage: 'review' })}
                        rightIcon={<CheckCircle2 className="w-3 h-3" />}
                        className="bg-emerald-600 hover:bg-emerald-500"
                      >
                        Mark Result Reviewed (Doctor)
                      </Button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
};
