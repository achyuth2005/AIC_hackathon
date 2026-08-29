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

export const TimelineList: React.FC<TimelineListProps> = ({ caseId }) => {
  const { data: timeline, isLoading, isError } = useCaseTimeline(caseId);

  if (isLoading) {
    return (
      <Card className="bg-slate-900 border-slate-800">
        <CardHeader>
          <CardTitle className="text-sm">Audit Timeline</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="h-4 bg-slate-800 rounded animate-pulse w-3/4" />
            <div className="h-4 bg-slate-800 rounded animate-pulse w-1/2" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (isError || !timeline || timeline.length === 0) {
    return null;
  }

  const getEventIcon = (type: string) => {
    if (type.includes('BYPASS')) return <Zap className="w-4 h-4 text-red-400" />;
    if (type.includes('ESCALATE') || type.includes('UPWARD')) return <ArrowUpCircle className="w-4 h-4 text-orange-400" />;
    if (type.includes('DE_ESCALATE')) return <ArrowDownCircle className="w-4 h-4 text-cyan-400" />;
    if (type.includes('OBSERVATION')) return <Activity className="w-4 h-4 text-cyan-400" />;
    if (type.includes('TEST')) return <TestTube className="w-4 h-4 text-indigo-400" />;
    if (type.includes('RESOURCE')) return <Layers className="w-4 h-4 text-emerald-400" />;
    if (type.includes('CONFLICT')) return <AlertTriangle className="w-4 h-4 text-purple-400" />;
    if (type.includes('REASSESS')) return <Clock className="w-4 h-4 text-amber-400" />;
    if (type.includes('IDENTITY')) return <UserCheck className="w-4 h-4 text-blue-400" />;
    return <FileCheck className="w-4 h-4 text-slate-400" />;
  };

  const formatEventType = (type: string) => {
    return type
      .replace(/_/g, ' ')
      .toLowerCase()
      .replace(/\b\w/g, (c) => c.toUpperCase());
  };

  return (
    <Card className="bg-slate-900 border-slate-800 text-left">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm flex items-center justify-between">
          <span className="flex items-center gap-2 text-slate-200">
            <History className="w-4 h-4 text-cyan-400" />
            Event Sourced Case Audit Trail ({timeline.length} Events)
          </span>
        </CardTitle>
      </CardHeader>

      <CardContent>
        <div className="relative pl-6 space-y-4 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-px before:bg-slate-800">
          {timeline.map((ev) => (
            <div key={ev.event_id} className="relative flex items-start gap-3 group">
              <div className="absolute -left-6 p-1 rounded-full bg-slate-950 border border-slate-800 shrink-0">
                {getEventIcon(ev.event_type)}
              </div>

              <div className="flex-1 min-w-0 bg-slate-950/40 p-3 rounded-xl border border-slate-800/80">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs font-semibold text-slate-200">
                    {formatEventType(ev.event_type)}
                  </span>
                  <span className="text-[10px] font-mono text-slate-500 shrink-0">
                    {formatRelative(ev.occurred_at)} ({formatClock(ev.occurred_at, true)})
                  </span>
                </div>

                {ev.payload && Object.keys(ev.payload).length > 0 && (
                  <div className="mt-1 text-[11px] font-mono text-slate-400 line-clamp-2">
                    {JSON.stringify(ev.payload).replace(/[{}]/g, '')}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
};
