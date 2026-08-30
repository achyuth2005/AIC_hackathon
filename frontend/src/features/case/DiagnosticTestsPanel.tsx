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

  // Diagnostic test lifecycle status -> badge classes
  const statusBadgeClasses: Record<string, string> = {
    ORDERED: 'bg-slate-100 text-slate-600 border border-slate-200',
    SAMPLE_COLLECTED: 'bg-slate-100 text-slate-600 border border-slate-200',
    RESULT_AVAILABLE: 'bg-indigo-50 text-indigo-700 border border-indigo-200',
    RESULT_REVIEWED: 'bg-emerald-50 text-emerald-700 border border-emerald-200',
  };

  // Stepper stage -> current/completed color classes
  const stageClasses = (stage: (typeof stages)[number], isCurrent: boolean, isCompleted: boolean) => {
    if (isCurrent) {
      if (stage === 'RESULT_AVAILABLE') return 'bg-indigo-50 text-indigo-700 border-indigo-200 font-bold';
      if (stage === 'RESULT_REVIEWED') return 'bg-emerald-50 text-emerald-700 border-emerald-200 font-bold';
      return 'bg-slate-100 text-slate-700 border-slate-300 font-bold';
    }
    if (isCompleted) return 'bg-white text-slate-500 border-slate-200';
    return 'bg-slate-50 text-slate-300 border-slate-100';
  };

  return (
    <Card className="text-left">
      <CardHeader className="pb-3 flex flex-row items-center justify-between">
        <CardTitle className="text-sm flex items-center gap-2 text-slate-900">
          <TestTube className="w-4 h-4 text-indigo-600" />
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
            className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/80 flex flex-col sm:flex-row items-end gap-3 animate-fade-in"
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
              className="w-full sm:w-auto font-bold"
            >
              Order Test
            </Button>
          </form>
        )}

        {isLoading ? (
          <div className="space-y-2">
            <div className="h-12 bg-slate-100 rounded-xl animate-pulse" />
          </div>
        ) : !tests || tests.length === 0 ? (
          <div className="text-xs text-slate-400 font-mono text-center py-4 italic">
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
                      ? 'bg-rose-50 border-rose-200'
                      : 'bg-slate-50 border-slate-200/80'
                  }`}
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <TestTube className="w-4 h-4 text-indigo-600" />
                      <span className="font-bold text-sm text-slate-900">{t.test_type}</span>
                      <span
                        className={`text-[10px] font-mono px-2 py-0.5 rounded ${
                          statusBadgeClasses[t.status] || 'bg-slate-100 text-slate-600 border border-slate-200'
                        }`}
                      >
                        {DIAGNOSTIC_STATUS_LABELS[t.status]}
                      </span>
                      {t.stuck_flagged && (
                        <span className="text-[10px] font-mono font-bold text-rose-700 bg-white px-2 py-0.5 rounded border border-rose-300 flex items-center gap-1 animate-pulse">
                          <AlertCircle className="w-3 h-3 text-rose-600" />
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
                          className={`p-2 rounded-lg text-center text-[10px] font-mono border transition-all ${stageClasses(
                            stage,
                            isCurrent,
                            isCompleted
                          )}`}
                        >
                          <div className="flex items-center justify-center gap-1">
                            {isCompleted ? (
                              <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                            ) : (
                              <Clock className="w-3 h-3 text-slate-300" />
                            )}
                            <span className="truncate">{stage.replace(/_/g, ' ')}</span>
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  {/* Lifecycle advance buttons */}
                  <div className="flex justify-end gap-2 pt-1 border-t border-slate-200/70">
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
                        className="bg-emerald-600 hover:bg-emerald-700"
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
