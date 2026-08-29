import { Zap, TrendingUp, Clock, GitCompare } from 'lucide-react';

export const QueueLegend: React.FC = () => {
  return (
    <div className="flex flex-wrap items-center gap-x-6 gap-y-2 p-3 rounded-xl bg-slate-900/60 border border-slate-800/80 text-[11px] text-slate-400">
      <div className="font-semibold text-slate-300 uppercase tracking-wider text-[10px]">
        Guardian Queue Guide:
      </div>

      <div className="flex items-center gap-1.5">
        <span className="w-2 h-2 rounded-full bg-red-600" />
        <span>ESI 1 Immediate</span>
      </div>

      <div className="flex items-center gap-1.5">
        <span className="w-2 h-2 rounded-full bg-orange-600" />
        <span>ESI 2 Emergent</span>
      </div>

      <div className="flex items-center gap-1.5">
        <span className="w-2 h-2 rounded-full bg-amber-600" />
        <span>ESI 3 Urgent</span>
      </div>

      <div className="flex items-center gap-1.5">
        <span className="w-2 h-2 rounded-full bg-green-600" />
        <span>ESI 4 Less Urgent</span>
      </div>

      <div className="flex items-center gap-1.5">
        <span className="w-2 h-2 rounded-full bg-blue-600" />
        <span>ESI 5 Non-Urgent</span>
      </div>

      <div className="flex items-center gap-1.5 text-rose-300">
        <Clock className="w-3 h-3 text-rose-400" />
        <span>Reassessment Overdue</span>
      </div>

      <div className="flex items-center gap-1.5 text-orange-300">
        <TrendingUp className="w-3 h-3 text-orange-400" />
        <span>Deteriorating</span>
      </div>

      <div className="flex items-center gap-1.5 text-purple-300">
        <GitCompare className="w-3 h-3 text-purple-400" />
        <span>Conflict</span>
      </div>

      <div className="flex items-center gap-1.5 text-red-400">
        <Zap className="w-3 h-3 text-red-400" />
        <span>Bypass Panic</span>
      </div>
    </div>
  );
};
