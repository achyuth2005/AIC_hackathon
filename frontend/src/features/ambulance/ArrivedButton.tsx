import React from 'react';
import { useRecordArrival } from '../../hooks/useAmbulanceActions';
import { Button } from '../../components/ui/Button';
import { Truck } from 'lucide-react';

export interface ArrivedButtonProps {
  caseId: string;
  isPreArrival: boolean;
  size?: 'sm' | 'md' | 'lg';
}

export const ArrivedButton: React.FC<ArrivedButtonProps> = ({
  caseId,
  isPreArrival,
  size = 'md',
}) => {
  const { mutate: recordArrival, isPending } = useRecordArrival();

  if (!isPreArrival) {
    return null;
  }

  return (
    <Button
      variant="primary"
      size={size}
      isLoading={isPending}
      onClick={() => recordArrival({ caseId })}
      leftIcon={<Truck className="w-4 h-4" />}
      className="bg-emerald-600 hover:bg-emerald-700 font-bold text-white shadow-sm"
    >
      Record Patient Arrival (Enter ED)
    </Button>
  );
};
