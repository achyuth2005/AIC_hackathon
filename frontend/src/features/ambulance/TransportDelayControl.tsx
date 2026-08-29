import React, { useState } from 'react';
import { useDelayTransport } from '../../hooks/useAmbulanceActions';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';
import { Clock, Plus } from 'lucide-react';

export interface TransportDelayControlProps {
  caseId: string;
}

export const TransportDelayControl: React.FC<TransportDelayControlProps> = ({ caseId }) => {
  const [delayMinutes, setDelayMinutes] = useState('10');
  const [reason, setReason] = useState('Traffic congestion / road construction');
  const { mutate: delayTransport, isPending } = useDelayTransport();

  const handleAddDelay = (minutes: number) => {
    delayTransport({
      caseId,
      body: {
        additional_minutes: minutes,
        reason: reason.trim() || 'Paramedic reported transport delay',
      },
    });
  };

  const handleCustomSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const val = parseInt(delayMinutes, 10);
    if (isNaN(val) || val <= 0) return;
    handleAddDelay(val);
  };

  return (
    <Card className="bg-slate-900 border-slate-800 text-left">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm flex items-center gap-2 text-slate-200">
          <Clock className="w-4 h-4 text-amber-400" />
          Paramedic Transport Delay Controls (Simulation)
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-4">
        <div className="space-y-1.5">
          <label className="text-xs font-semibold text-slate-300">
            Quick Delay Preset:
          </label>
          <div className="flex flex-wrap items-center gap-2">
            <Button
              size="xs"
              variant="secondary"
              disabled={isPending}
              onClick={() => handleAddDelay(5)}
              leftIcon={<Plus className="w-3 h-3" />}
            >
              +5 Mins
            </Button>
            <Button
              size="xs"
              variant="secondary"
              disabled={isPending}
              onClick={() => handleAddDelay(10)}
              leftIcon={<Plus className="w-3 h-3" />}
            >
              +10 Mins
            </Button>
            <Button
              size="xs"
              variant="secondary"
              disabled={isPending}
              onClick={() => handleAddDelay(15)}
              leftIcon={<Plus className="w-3 h-3" />}
            >
              +15 Mins
            </Button>
          </div>
        </div>

        <form onSubmit={handleCustomSubmit} className="space-y-3 pt-2 border-t border-slate-800">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Input
              label="Custom Delay Duration (Mins)"
              type="number"
              value={delayMinutes}
              onChange={(e) => setDelayMinutes(e.target.value)}
            />
            <Input
              label="Delay Reason"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="e.g. Inclement weather, roadside stabilization"
            />
          </div>

          <div className="flex justify-end">
            <Button
              type="submit"
              size="sm"
              variant="primary"
              isLoading={isPending}
              className="bg-amber-600 hover:bg-amber-500 text-slate-950 font-bold"
            >
              Apply Transport Delay
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
};
