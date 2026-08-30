import React from 'react';
import { useCaseTimeline } from '../../hooks/useCaseTimeline';
import { formatClock, formatRelative } from '../../lib/datetime';
import {
  History,
  Activity,
  Zap,
  ArrowUpCircle,
  ArrowDownCircle,
  FileCheck,
  AlertTriangle,
  Clock,
  UserCheck,
  Layers,
  TestTube,
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';

export interface TimelineListProps {
  caseId: string;
}

// Event type -> semantic tint for the icon chip. Light-mode palette.
const eventTint = (type: string): { bg: string; border: string; icon: string } => {
  if (type.includes('BYPASS')) return { bg: 'bg-rose-50', border: 'border-rose-200', icon: 'text-rose-600' };
  if (type.includes('ESCALATE') || type.includes('UPWARD')) return { bg: 'bg-amber-50', border: 'border-amber-200', icon: 'text-amber-600' };
  if (type.includes('DE_ESCALATE')) return { bg: 'bg-indigo-50', border: 'border-indigo-200', icon: 'text-indigo-600' };
  if (type.includes('OBSERVATION')) return { bg: 'bg-blue-50', border: 'border-blue-200', icon: 'text-blue-600' };
  if (type.includes('TEST')) return { bg: 'bg-indigo-50', border: 'border-indigo-200', icon: 'text-indigo-600' };
  if (type.includes('RESOURCE')) return { bg: 'bg-emerald-50', border: 'border-emerald-200', icon: 'text-emerald-600' };
  if (type.includes('CONFLICT')) return { bg: 'bg-purple-50', border: 'border-purple-200', icon: 'text-purple-600' };
  if (type.includes('REASSESS')) return { bg: 'bg-amber-50', border: 'border-amber-200', icon: 'text-amber-600' };
  if (type.includes('IDENTITY')) return { bg: 'bg-blue-50', border: 'border-blue-200', icon: 'text-blue-600' };
  return { bg: 'bg-slate-100', border: 'border-slate-200', icon: 'text-slate-500' };
};

export const TimelineList: React.FC<TimelineListProps> = ({ caseId }) => {
  const { data: timeline, isLoading, isError } = useCaseTimeline(caseId);

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Audit Timeline</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="h-4 bg-slate-100 rounded animate-pulse w-3/4" />
            <div className="h-4 bg-slate-100 rounded animate-pulse w-1/2" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (isError || !timeline || timeline.length === 0) {
    return null;
  }

  const getEventIcon = (type: string) => {
    const { icon } = eventTint(type);
    if (type.includes('BYPASS')) return <Zap className={`w-4 h-4 ${icon}`} />;
    if (type.includes('ESCALATE') || type.includes('UPWARD')) return <ArrowUpCircle className={`w-4 h-4 ${icon}`} />;
    if (type.includes('DE_ESCALATE')) return <ArrowDownCircle className={`w-4 h-4 ${icon}`} />;
    if (type.includes('OBSERVATION')) return <Activity className={`w-4 h-4 ${icon}`} />;
    if (type.includes('TEST')) return <TestTube className={`w-4 h-4 ${icon}`} />;
    if (type.includes('RESOURCE')) return <Layers className={`w-4 h-4 ${icon}`} />;
    if (type.includes('CONFLICT')) return <AlertTriangle className={`w-4 h-4 ${icon}`} />;
    if (type.includes('REASSESS')) return <Clock className={`w-4 h-4 ${icon}`} />;
    if (type.includes('IDENTITY')) return <UserCheck className={`w-4 h-4 ${icon}`} />;
    return <FileCheck className={`w-4 h-4 ${icon}`} />;
  };

  const formatEventType = (type: string) => {
    return type
      .replace(/_/g, ' ')
      .toLowerCase()
      .replace(/\b\w/g, (c) => c.toUpperCase());
  };

  return (
    <Card className="text-left">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm flex items-center justify-between">
          <span className="flex items-center gap-2 text-slate-900">
            <History className="w-4 h-4 text-indigo-600" />
            Event Sourced Case Audit Trail ({timeline.length} Events)
          </span>
        </CardTitle>
      </CardHeader>

      <CardContent>
        <div className="relative pl-6 space-y-4 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-px before:bg-slate-200">
          {timeline.map((ev) => {
            const tint = eventTint(ev.event_type);
            return (
              <div key={ev.event_id} className="relative flex items-start gap-3 group">
                <div className={`absolute -left-6 p-1 rounded-full border shrink-0 ${tint.bg} ${tint.border}`}>
                  {getEventIcon(ev.event_type)}
                </div>

                <div className="flex-1 min-w-0 bg-slate-50 p-3 rounded-xl border border-slate-200/70">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs font-semibold text-slate-900">
                      {formatEventType(ev.event_type)}
                    </span>
                    <span className="text-[10px] font-mono tabular-nums text-slate-400 shrink-0">
                      {formatRelative(ev.occurred_at)} ({formatClock(ev.occurred_at, true)})
                    </span>
                  </div>

                  {ev.payload && Object.keys(ev.payload).length > 0 && (
                    <div className="mt-1 text-[11px] font-mono text-slate-500 line-clamp-2">
                      {JSON.stringify(ev.payload).replace(/[{}]/g, '')}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
};
