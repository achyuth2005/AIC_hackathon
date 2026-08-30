import { Zap, TrendingUp, Clock, GitCompare } from 'lucide-react';

export const QueueLegend: React.FC = () => {
  return (
    <div className="flex flex-wrap items-center gap-x-6 gap-y-2 p-3.5 rounded-2xl bg-white/60 backdrop-blur-xl border border-white/80 text-[11px] text-slate-500 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.85),0_8px_32px_rgba(31,38,135,0.04)]">
      <div className="font-semibold text-slate-600 uppercase tracking-wider text-[10px]">
        Guardian Queue Guide:
      </div>

      <div className="flex items-center gap-1.5">
        <span className="w-2 h-2 rounded-full bg-rose-600" />
        <span>ESI 1 Immediate</span>
      </div>

      <div className="flex items-center gap-1.5">
        <span className="w-2 h-2 rounded-full bg-amber-600" />
        <span>ESI 2 Emergent</span>
      </div>

      <div className="flex items-center gap-1.5">
        <span className="w-2 h-2 rounded-full bg-yellow-600" />
        <span>ESI 3 Urgent</span>
      </div>

      <div className="flex items-center gap-1.5">
        <span className="w-2 h-2 rounded-full bg-emerald-600" />
        <span>ESI 4 Less Urgent</span>
      </div>

      <div className="flex items-center gap-1.5">
        <span className="w-2 h-2 rounded-full bg-blue-600" />
        <span>ESI 5 Non-Urgent</span>
      </div>

      <div className="flex items-center gap-1.5 text-red-700">
        <Clock className="w-3 h-3 text-red-600" />
        <span>Reassessment Overdue</span>
      </div>

      <div className="flex items-center gap-1.5 text-orange-700">
        <TrendingUp className="w-3 h-3 text-orange-600" />
        <span>Deteriorating</span>
      </div>

      <div className="flex items-center gap-1.5 text-purple-700">
        <GitCompare className="w-3 h-3 text-purple-600" />
        <span>Conflict</span>
      </div>

      <div className="flex items-center gap-1.5 text-rose-700">
        <Zap className="w-3 h-3 text-rose-600" />
        <span>Bypass Panic</span>
      </div>
    </div>
  );
};
