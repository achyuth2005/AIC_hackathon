import React, { useState } from 'react';
import { ObservationResponse } from '../../types/api';
import { VitalValue } from '../../components/clinical/VitalValue';
import { Button } from '../../components/ui/Button';
import { Modal } from '../../components/ui/Modal';
import { RecordVitalsForm } from './RecordVitalsForm';
import { Activity, Plus, FileText } from 'lucide-react';

export interface VitalsPanelProps {
  caseId: string;
  observations: ObservationResponse[];
}

export const VitalsPanel: React.FC<VitalsPanelProps> = ({
  caseId,
  observations = [],
}) => {
  const [isRecordModalOpen, setIsRecordModalOpen] = useState(false);

  const currentObs = observations.filter((o) => o.is_current);

  const conceptOrder = [
    'RESP_RATE',
    'SPO2',
    'SUPPLEMENTAL_OXYGEN',
    'HEART_RATE',
    'SYSTOLIC_BP',
    'TEMPERATURE',
    'CONSCIOUSNESS_LEVEL',
  ];

  const sortedObs = [...currentObs].sort((a, b) => {
    const idxA = conceptOrder.indexOf(a.concept_code);
    const idxB = conceptOrder.indexOf(b.concept_code);
    if (idxA !== -1 && idxB !== -1) return idxA - idxB;
    if (idxA !== -1) return -1;
    if (idxB !== -1) return 1;
    return a.concept_code.localeCompare(b.concept_code);
  });

  const getLabel = (code: string) => {
    const map: Record<string, string> = {
      RESP_RATE: 'Respiratory Rate',
      SPO2: 'Oxygen Saturation (SpO2)',
      SUPPLEMENTAL_OXYGEN: 'Supplemental Oxygen',
      HEART_RATE: 'Heart Rate',
      SYSTOLIC_BP: 'Systolic Blood Pressure',
      TEMPERATURE: 'Body Temperature',
      CONSCIOUSNESS_LEVEL: 'Consciousness (AVPU)',
    };
    return map[code] || code;
  };

  return (
    <div className="space-y-4 text-left">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Activity className="w-5 h-5 text-cyan-400" />
          <h3 className="text-base font-bold text-slate-100">
            Current Physiological Observations ({sortedObs.length})
          </h3>
        </div>

        <Button
          variant="primary"
          size="sm"
          onClick={() => setIsRecordModalOpen(true)}
          leftIcon={<Plus className="w-4 h-4" />}
          className="font-bold shadow-md shadow-cyan-950/40"
        >
          Record Vitals Set
        </Button>
      </div>

      {sortedObs.length === 0 ? (
        <div className="p-8 rounded-2xl bg-slate-900/60 border border-dashed border-slate-800 text-center space-y-3">
          <FileText className="w-8 h-8 text-slate-600 mx-auto" />
          <div className="text-sm font-semibold text-slate-300">
            No observations recorded for this case
          </div>
          <p className="text-xs text-slate-400 max-w-sm mx-auto">
            Record respiratory rate, SpO2, heart rate, blood pressure, temperature, and AVPU to assess the patient.
          </p>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setIsRecordModalOpen(true)}
            leftIcon={<Plus className="w-4 h-4" />}
          >
            Record First Vitals Set
          </Button>
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
          {sortedObs.map((obs) => (
            <VitalValue
              key={obs.observation_id}
              label={getLabel(obs.concept_code)}
              value={obs.value}
              unit={obs.unit}
              observedAt={obs.observed_at}
              reliabilityTier={obs.reliability_tier}
            />
          ))}
        </div>
      )}

      {/* Record Vitals Modal */}
      <Modal
        isOpen={isRecordModalOpen}
        onClose={() => setIsRecordModalOpen(false)}
        size="lg"
        title="Record Clinical Vitals"
        description="Enter physiological readings. Each reading will update the case's risk assessment and trigger bypass checks."
      >
        <RecordVitalsForm
          caseId={caseId}
          onSuccess={() => setIsRecordModalOpen(false)}
        />
      </Modal>
    </div>
  );
};
