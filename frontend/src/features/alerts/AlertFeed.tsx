import React, { useState, useEffect, useRef } from 'react';
import { useAlerts, useAlertBudget } from '../../hooks/useAlerts';
import { AlertCard } from './AlertCard';
import { AudioCuePlayer } from './AudioCuePlayer';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';
import { Bell, Volume2, VolumeX, RefreshCw, CheckCheck, Gauge } from 'lucide-react';
import { Skeleton } from '../../components/ui/Skeleton';
import { ErrorState } from '../../components/ui/ErrorState';

export const AlertFeed: React.FC = () => {
  const { data: alerts, isLoading, isError, error, refetch, isFetching } = useAlerts();
  const { data: budget } = useAlertBudget(2, 60);

  const [showUndismissedOnly, setShowUndismissedOnly] = useState(true);
  const [isAudioEnabled, setIsAudioEnabled] = useState(!AudioCuePlayer.isMuted());
  const prevBypassCount = useRef(0);

  const activeAlerts = alerts || [];
  const bypassCount = activeAlerts.filter((a) => a.alert_type === 'CRITICAL_BYPASS_PATIENT' && !a.dismissed).length;

  // Sound chime when a new undismissed emergency bypass alert arrives
  useEffect(() => {
    if (bypassCount > prevBypassCount.current) {
      AudioCuePlayer.playCriticalAlarm();
    }
    prevBypassCount.current = bypassCount;
  }, [bypassCount]);

  const toggleAudio = () => {
    const next = !isAudioEnabled;
    setIsAudioEnabled(next);
    AudioCuePlayer.setMuted(!next);
  };

  const displayedAlerts = activeAlerts.filter((a) => {
    if (showUndismissedOnly) return !a.dismissed;
    return true;
  });

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-12 animate-fade-in text-left">
      {/* Header & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-extrabold tracking-tight text-slate-100 flex items-center gap-2.5">
              <Bell className="w-7 h-7 text-amber-400" />
              Interruptive Alert Aggregation Feed
            </h1>
            <span className="text-xs px-2.5 py-0.5 rounded-full font-mono font-bold bg-amber-950 text-amber-300 border border-amber-700/60">
              {displayedAlerts.length} Active
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Phase 8.5 Alert Engine — only emergency bypass, upward acuity crossings, and aggregated overdue sets.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Audio Chime Toggle */}
          <button
            type="button"
            onClick={toggleAudio}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-mono font-bold transition-all cursor-pointer ${
              isAudioEnabled
                ? 'bg-amber-950 text-amber-300 border-amber-600'
                : 'bg-slate-900 text-slate-500 border-slate-800'
            }`}
            title="Toggle Web Audio alarm chimes for critical alerts"
          >
            {isAudioEnabled ? (
              <>
                <Volume2 className="w-4 h-4 text-amber-400" />
                <span>Audio Alarms ON</span>
              </>
            ) : (
              <>
                <VolumeX className="w-4 h-4 text-slate-500" />
                <span>Audio Muted</span>
              </>
            )}
          </button>

          {/* Undismissed Toggle */}
          <button
            type="button"
            onClick={() => setShowUndismissedOnly(!showUndismissedOnly)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs font-mono text-slate-300 hover:text-white cursor-pointer"
          >
            <CheckCheck className="w-3.5 h-3.5 text-cyan-400" />
            <span>{showUndismissedOnly ? 'Active (Undismissed)' : 'Showing All'}</span>
          </button>

          <button
            onClick={() => refetch()}
            disabled={isFetching}
            className="p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-slate-200 cursor-pointer"
            title="Refresh alerts"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isFetching ? 'animate-spin text-cyan-400' : ''}`} />
          </button>
        </div>
      </div>

      {/* Alert Fatigue Budget Meter (Phase 8.5) */}
      {budget && (
        <Card className="bg-slate-900 border-slate-800 text-left shadow-lg">
          <CardHeader className="pb-3 flex flex-row items-center justify-between">
            <CardTitle className="text-sm flex items-center gap-2 text-slate-200">
              <Gauge className="w-4 h-4 text-cyan-400" />
              <span>Alert Fatigue Budget Meter (Demonstration Metric)</span>
            </CardTitle>
            <span
              className={`text-xs font-mono font-bold px-2 py-0.5 rounded border ${
                budget.within_budget
                  ? 'bg-emerald-950 text-emerald-300 border-emerald-700'
                  : 'bg-rose-950 text-rose-300 border-rose-700'
              }`}
            >
              {budget.within_budget ? 'WITHIN BUDGET' : 'BUDGET EXCEEDED'}
            </span>
          </CardHeader>

          <CardContent className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
            <div className="p-3 rounded-xl bg-slate-950 border border-slate-800">
              <span className="text-slate-500 block text-[10px] uppercase">Rate</span>
              <span className="text-lg font-black text-white">
                {budget.alerts_per_nurse_per_hour.toFixed(1)}
              </span>
              <span className="text-[10px] text-slate-500 block">alerts/nurse/hr</span>
            </div>

            <div className="p-3 rounded-xl bg-slate-950 border border-slate-800">
              <span className="text-slate-500 block text-[10px] uppercase">Target Cap</span>
              <span className="text-lg font-black text-slate-200">
                {budget.target_alerts_per_nurse_per_hour != null
                  ? `${budget.target_alerts_per_nurse_per_hour}/hr`
                  : 'Uncapped'}
              </span>
              <span className="text-[10px] text-slate-500 block">fatigue ceiling</span>
            </div>

            <div className="p-3 rounded-xl bg-slate-950 border border-slate-800">
              <span className="text-slate-500 block text-[10px] uppercase">Nurses on Shift</span>
              <span className="text-lg font-black text-cyan-300">{budget.nurses_on_shift}</span>
              <span className="text-[10px] text-slate-500 block">simulated roster</span>
            </div>

            <div className="p-3 rounded-xl bg-slate-950 border border-slate-800">
              <span className="text-slate-500 block text-[10px] uppercase">Window</span>
              <span className="text-lg font-black text-slate-200">{budget.window_minutes}m</span>
              <span className="text-[10px] text-slate-500 block">rolling duration</span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Alerts Feed List */}
      {isLoading ? (
        <div className="space-y-3">
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-20 w-full" />
        </div>
      ) : isError ? (
        <ErrorState
          title="Failed to load clinical alerts"
          error={error}
          onRetry={() => refetch()}
        />
      ) : displayedAlerts.length === 0 ? (
        <div className="p-12 text-center text-slate-500 bg-slate-900/40 rounded-2xl border border-dashed border-slate-800">
          No active clinical alerts matching criteria.
        </div>
      ) : (
        <div className="space-y-3">
          {displayedAlerts.map((alert) => (
            <AlertCard key={alert.alert_id} alert={alert} />
          ))}
        </div>
      )}
    </div>
  );
};
