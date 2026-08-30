import React, { useState, useEffect, useRef } from 'react';
import { useAlerts, useAlertBudget } from '../../hooks/useAlerts';
import { AlertCard } from './AlertCard';
import { AudioCuePlayer } from './AudioCuePlayer';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';
import { MetricCard } from '../../components/ui/MetricCard';
import { Badge } from '../../components/ui/Badge';
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

  const budgetTone = budget?.within_budget === false ? 'rose' : 'emerald';

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-12 animate-fade-in text-left">
      {/* Header & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight text-slate-900 flex items-center gap-2.5">
              <Bell className="w-7 h-7 text-amber-500" />
              Interruptive Alert Aggregation Feed
            </h1>
            <span className="text-xs px-2.5 py-0.5 rounded-full font-mono font-bold bg-amber-50 text-amber-700 border border-amber-200">
              {displayedAlerts.length} Active
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
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
                ? 'bg-amber-50 text-amber-700 border-amber-200'
                : 'bg-white text-slate-500 border-slate-200'
            }`}
            title="Toggle Web Audio alarm chimes for critical alerts"
          >
            {isAudioEnabled ? (
              <>
                <Volume2 className="w-4 h-4 text-amber-500" />
                <span>Audio Alarms ON</span>
              </>
            ) : (
              <>
                <VolumeX className="w-4 h-4 text-slate-400" />
                <span>Audio Muted</span>
              </>
            )}
          </button>

          {/* Undismissed Toggle */}
          <button
            type="button"
            onClick={() => setShowUndismissedOnly(!showUndismissedOnly)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-xs font-mono text-slate-600 hover:text-slate-900 hover:border-slate-300 cursor-pointer transition-colors"
          >
            <CheckCheck className="w-3.5 h-3.5 text-indigo-600" />
            <span>{showUndismissedOnly ? 'Active (Undismissed)' : 'Showing All'}</span>
          </button>

          <button
            onClick={() => refetch()}
            disabled={isFetching}
            className="p-2 rounded-lg bg-white border border-slate-200 text-slate-400 hover:text-slate-700 hover:border-slate-300 cursor-pointer transition-colors"
            title="Refresh alerts"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isFetching ? 'animate-spin text-indigo-600' : ''}`} />
          </button>
        </div>
      </div>

      {/* Alert Fatigue Budget Meter (Phase 8.5) */}
      {budget && (
        <Card className="text-left">
          <CardHeader className="pb-3 flex flex-row items-center justify-between">
            <CardTitle className="text-sm gap-2">
              <Gauge className="w-4 h-4 text-indigo-600" />
              <span>Alert Fatigue Budget Meter (Demonstration Metric)</span>
            </CardTitle>
            <Badge variant={budget.within_budget === false ? 'danger' : 'success'} size="sm" dot>
              {budget.within_budget === false
                ? 'Budget Exceeded'
                : budget.within_budget === true
                ? 'Within Budget'
                : 'Not Evaluated'}
            </Badge>
          </CardHeader>

          <CardContent className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-0">
            <MetricCard
              label="Rate"
              value={budget.alerts_per_nurse_per_hour.toFixed(1)}
              sublabel="alerts/nurse/hr"
              tone={budgetTone}
              active
            />

            <MetricCard
              label="Target Cap"
              value={
                budget.target_alerts_per_nurse_per_hour != null
                  ? `${budget.target_alerts_per_nurse_per_hour}/hr`
                  : 'Uncapped'
              }
              sublabel="fatigue ceiling"
            />

            <MetricCard
              label="Nurses on Shift"
              value={budget.nurses_on_shift}
              sublabel="simulated roster"
              tone="indigo"
            />

            <MetricCard
              label="Window"
              value={`${budget.window_minutes}m`}
              sublabel="rolling duration"
            />
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
        <div className="p-12 text-center text-slate-500 bg-white rounded-2xl border border-dashed border-slate-200">
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
