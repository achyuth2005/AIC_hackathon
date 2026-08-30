import React, { useState, useEffect, useRef } from 'react';
import { useIntake } from '../../hooks/useIntake';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Sparkles, MessageSquare, Mic, MicOff } from 'lucide-react';
import { Tooltip } from '../../components/ui/Tooltip';

export interface IntakeTextPanelProps {
  caseId: string;
}

const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

export const IntakeTextPanel: React.FC<IntakeTextPanelProps> = ({ caseId }) => {
  const [text, setText] = useState('');
  const [isListening, setIsListening] = useState(false);
  const { mutate: processIntake, isPending } = useIntake();
  
  const recognitionRef = useRef<any>(null);

  useEffect(() => {
    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      
      recognition.onresult = (event: any) => {
        let currentTranscript = '';
        for (let i = event.resultIndex; i < event.results.length; i++) {
          if (event.results[i].isFinal) {
            currentTranscript += event.results[i][0].transcript + ' ';
          }
        }
        if (currentTranscript) {
          setText((prev) => prev + (prev.endsWith(' ') || prev.length === 0 ? '' : ' ') + currentTranscript);
        }
      };

      recognition.onerror = (event: any) => {
        console.error('Speech recognition error', event.error);
        setIsListening(false);
      };

      recognition.onend = () => {
        setIsListening(false);
      };

      recognitionRef.current = recognition;
    }
    
    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
    };
  }, []);

  const toggleDictation = () => {
    if (isListening) {
      recognitionRef.current?.stop();
      setIsListening(false);
    } else {
      recognitionRef.current?.start();
      setIsListening(true);
    }
  };

  const handleIntakeSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim()) return;
    
    if (isListening) {
      recognitionRef.current?.stop();
      setIsListening(false);
    }

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
    <Card className="text-left">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm flex items-center justify-between">
          <span className="flex items-center gap-2 text-slate-900">
            <Sparkles className="w-4 h-4 text-indigo-600" />
            Natural Language Intake & Clinical Notes (AI Assisted)
          </span>
          <span className="text-[10px] font-mono text-slate-400">
            Tier 4 AI Inference
          </span>
        </CardTitle>
      </CardHeader>

      <CardContent>
        <form onSubmit={handleIntakeSubmit} className="space-y-3">
          <p className="text-xs text-slate-500">
            Paste unstructured triage transcript, symptoms, or spoken notes. The Intake Engine will extract structured vitals into Tier 4 AI observations (or gracefully fall back if offline).
          </p>

          <textarea
            rows={3}
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="e.g. 54-year-old male with severe crushing chest pain radiating to left arm. Sweating profusely, BP 160/95, pulse 112 bpm, SpO2 93% on room air..."
            className="w-full bg-white border border-slate-300 rounded-xl p-3 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent font-sans"
          />

          <div className="flex justify-between items-center">
            <div className="flex items-center gap-3">
              <span className="text-[11px] text-slate-400 font-mono">
                Privacy redacted before server inference
              </span>
              <Tooltip
                content={!SpeechRecognition ? "Voice dictation is not supported in this browser." : (isListening ? "Stop Dictation" : "Start Dictation")}
              >
                <button
                  type="button"
                  onClick={toggleDictation}
                  disabled={!SpeechRecognition}
                  className={`flex items-center justify-center p-1.5 rounded-full transition-colors ${
                    !SpeechRecognition
                      ? 'bg-slate-100 text-slate-400 cursor-not-allowed'
                      : isListening
                      ? 'bg-red-100 text-red-600 hover:bg-red-200 animate-pulse'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  {isListening ? <Mic className="w-4 h-4" /> : <MicOff className="w-4 h-4" />}
                </button>
              </Tooltip>
            </div>
            <Button
              type="submit"
              variant="primary"
              size="sm"
              isLoading={isPending}
              disabled={!text.trim() || isPending}
              leftIcon={<MessageSquare className="w-3.5 h-3.5" />}
              className="text-xs font-bold"
            >
              Parse Clinical Text
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
};
