import React, { useState } from 'react';
import { useIntake } from '../../hooks/useIntake';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Sparkles, MessageSquare } from 'lucide-react';

export interface IntakeTextPanelProps {
  caseId: string;
}

export const IntakeTextPanel: React.FC<IntakeTextPanelProps> = ({ caseId }) => {
  const [text, setText] = useState('');
  const { mutate: processIntake, isPending } = useIntake();

  const handleIntakeSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim()) return;
    processIntake(
      { caseId, text: text.trim() },
      {
        onSuccess: () => {
          setText('');
        },
      }
    );
  };

  return (
    <Card className="bg-slate-900 border-slate-800 text-left">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm flex items-center justify-between">
          <span className="flex items-center gap-2 text-slate-200">
            <Sparkles className="w-4 h-4 text-indigo-400" />
            Natural Language Intake & Clinical Notes (AI Assisted)
          </span>
          <span className="text-[10px] font-mono text-slate-500">
            Tier 4 AI Inference
          </span>
        </CardTitle>
      </CardHeader>

      <CardContent>
        <form onSubmit={handleIntakeSubmit} className="space-y-3">
          <p className="text-xs text-slate-400">
            Paste unstructured triage transcript, symptoms, or spoken notes. The Intake Engine will extract structured vitals into Tier 4 AI observations (or gracefully fall back if offline).
          </p>

          <textarea
            rows={3}
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="e.g. 54-year-old male with severe crushing chest pain radiating to left arm. Sweating profusely, BP 160/95, pulse 112 bpm, SpO2 93% on room air..."
            className="w-full bg-slate-950 border border-slate-700/80 rounded-xl p-3 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-400 font-sans"
          />

          <div className="flex justify-between items-center">
            <span className="text-[11px] text-slate-500 font-mono">
              Privacy redacted before server inference
            </span>
            <Button
              type="submit"
              variant="primary"
              size="sm"
              isLoading={isPending}
              disabled={!text.trim() || isPending}
              leftIcon={<MessageSquare className="w-3.5 h-3.5" />}
              className="bg-indigo-600 hover:bg-indigo-500 text-xs font-bold"
            >
              Parse Clinical Text
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
};
