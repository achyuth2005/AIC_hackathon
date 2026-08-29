import React from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { casesApi } from '../../api/cases';
import { Button } from '../../components/ui/Button';
import { Zap } from 'lucide-react';
import { useToast } from '../../components/ui/Toast';

export interface EmergencyBypassButtonProps {
  caseId: string;
  isActive: boolean;
  className?: string;
}

export const EmergencyBypassButton: React.FC<EmergencyBypassButtonProps> = ({
  caseId,
  isActive,
  className,
}) => {
  const queryClient = useQueryClient();
  const { error, success } = useToast();

  const { mutate: triggerBypass, isPending } = useMutation({
    mutationFn: () => casesApi.emergencyBypass(caseId, 'Human staff immediate trigger'),
    onSuccess: () => {
      success(
        'Emergency bypass engaged immediately. Acuity forced to ESI 1 (Resuscitation).',
        'EMERGENCY BYPASS ACTIVE'
      );
      queryClient.invalidateQueries({ queryKey: ['case', caseId] });
      queryClient.invalidateQueries({ queryKey: ['queue'] });
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
      queryClient.invalidateQueries({ queryKey: ['control-tower'] });
      queryClient.invalidateQueries({ queryKey: ['risk-assessments', caseId] });
    },
    onError: (err: unknown) => {
      error(err instanceof Error ? err.message : 'Emergency bypass trigger failed.');
    },
  });

  if (isActive) {
    return (
      <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-red-600 border border-red-400 text-white font-black text-xs uppercase tracking-wider animate-pulse shadow-lg glow-red select-none ${className || ''}`}>
        <Zap className="w-4 h-4 fill-white" />
        <span>Bypass Engaged (ESI 1)</span>
      </div>
    );
  }

  return (
    <Button
      variant="danger"
      size="md"
      isLoading={isPending}
      onClick={() => triggerBypass()}
      leftIcon={<Zap className="w-4 h-4" />}
      title="Zero-latency Emergency Bypass: Forces case to ESI 1 and sounds critical alert"
      className={`font-extrabold uppercase tracking-wider bg-red-600 hover:bg-red-500 shadow-md shadow-red-950/60 border border-red-500 ${className || ''}`}
    >
      Emergency Bypass
    </Button>
  );
};
