import React, { useState } from 'react';
import { useAddObservation } from '../../hooks/useObservations';
import { ObservationCreateRequest } from '../../types/api';
import { toBackendUtc } from '../../lib/datetime';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { Select } from '../../components/ui/Select';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';
import { Activity, Heart, Wind, Thermometer, Gauge, Sparkles } from 'lucide-react';
import { useToast } from '../../components/ui/Toast';

export interface RecordVitalsFormProps {
  caseId: string;
  onSuccess?: () => void;
}

export const RecordVitalsForm: React.FC<RecordVitalsFormProps> = ({
  caseId,
  onSuccess,
}) => {
  const { mutateAsync: addObservations, isPending } = useAddObservation();
  const { error } = useToast();

  const [respiratoryRate, setRespiratoryRate] = useState<string>('');
  const [spo2, setSpo2] = useState<string>('');
  const [supplementalOxygen, setSupplementalOxygen] = useState<string>('false');
  const [heartRate, setHeartRate] = useState<string>('');
  const [systolicBp, setSystolicBp] = useState<string>('');
  const [temperature, setTemperature] = useState<string>('');
  const [avpu, setAvpu] = useState<string>('ALERT');

  const handleFillT6Scenario = () => {
    // T6 integration test vitals set: RR 26, SpO2 92, HR 118, SBP 104, Temp 38.4, ALERT, O2 false -> ESI 2
    setRespiratoryRate('26');
    setSpo2('92');
    setSupplementalOxygen('false');
    setHeartRate('118');
    setSystolicBp('104');
    setTemperature('38.4');
    setAvpu('ALERT');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const observedAt = toBackendUtc(new Date());
    const obsList: ObservationCreateRequest[] = [];

    if (respiratoryRate.trim()) {
      const val = parseFloat(respiratoryRate);
      if (isNaN(val) || val <= 0) {
        error('Respiratory rate must be a positive number.');
        return;
      }
      obsList.push({
        concept_code: 'RESP_RATE',
        value: val,
        value_type: 'NUMERIC',
        unit: 'breaths/min',
        source_type: 'NURSE',
        reliability_tier: 2,
        measurement_status: 'MEASURED',
        observed_at: observedAt,
      });
    }

    if (spo2.trim()) {
      const val = parseFloat(spo2);
      if (isNaN(val) || val < 0 || val > 100) {
        error('SpO2 must be a percentage between 0 and 100.');
        return;
      }
      obsList.push({
        concept_code: 'SPO2',
        value: val,
        value_type: 'NUMERIC',
        unit: '%',
        source_type: 'NURSE',
        reliability_tier: 2,
        measurement_status: 'MEASURED',
        observed_at: observedAt,
      });
    }

    if (supplementalOxygen) {
      obsList.push({
        concept_code: 'SUPPLEMENTAL_OXYGEN',
        value: supplementalOxygen === 'true',
        value_type: 'BOOLEAN',
        source_type: 'NURSE',
        reliability_tier: 2,
        measurement_status: 'MEASURED',
        observed_at: observedAt,
      });
    }

    if (heartRate.trim()) {
      const val = parseFloat(heartRate);
      if (isNaN(val) || val <= 0) {
        error('Heart rate must be a positive number.');
        return;
      }
      obsList.push({
        concept_code: 'HEART_RATE',
        value: val,
        value_type: 'NUMERIC',
        unit: 'bpm',
        source_type: 'NURSE',
        reliability_tier: 2,
        measurement_status: 'MEASURED',
        observed_at: observedAt,
      });
    }

    if (systolicBp.trim()) {
      const val = parseFloat(systolicBp);
      if (isNaN(val) || val <= 0) {
        error('Systolic BP must be a positive number.');
        return;
      }
      obsList.push({
        concept_code: 'SYSTOLIC_BP',
        value: val,
        value_type: 'NUMERIC',
        unit: 'mmHg',
        source_type: 'NURSE',
        reliability_tier: 2,
        measurement_status: 'MEASURED',
        observed_at: observedAt,
      });
    }

    if (temperature.trim()) {
      const val = parseFloat(temperature);
      if (isNaN(val) || val < 25 || val > 45) {
        error('Temperature must be a valid body temperature in °C.');
        return;
      }
      obsList.push({
        concept_code: 'TEMPERATURE',
        value: val,
        value_type: 'NUMERIC',
        unit: '°C',
        source_type: 'NURSE',
        reliability_tier: 2,
        measurement_status: 'MEASURED',
        observed_at: observedAt,
      });
    }

    if (avpu) {
      obsList.push({
        concept_code: 'CONSCIOUSNESS_LEVEL',
        value: avpu,
        value_type: 'CODED',
        source_type: 'NURSE',
        reliability_tier: 2,
        measurement_status: 'MEASURED',
        observed_at: observedAt,
      });
    }

    if (obsList.length === 0) {
      error('Please enter at least one clinical vital sign.');
      return;
    }

    try {
      await addObservations({ caseId, observations: obsList });
      if (onSuccess) onSuccess();
    } catch {
      // Error handled by mutation hook
    }
  };

  return (
    <Card className="bg-slate-900 border-slate-800">
      <CardHeader className="flex flex-row items-center justify-between pb-3">
        <CardTitle className="text-base">
          <Activity className="w-5 h-5 text-cyan-400" />
          Record Clinical Vitals (NEWS2 / PEWS)
        </CardTitle>
        <button
          type="button"
          onClick={handleFillT6Scenario}
          className="text-xs text-cyan-400 hover:text-cyan-300 font-mono flex items-center gap-1 cursor-pointer bg-cyan-950/60 px-2.5 py-1 rounded border border-cyan-800/60"
        >
          <Sparkles className="w-3.5 h-3.5" />
          Autofill T6 Set (NEWS2 Rescore)
        </button>
      </CardHeader>

      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4 text-left">
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
            <Input
              label="Respiratory Rate (br/min)"
              type="number"
              step="1"
              placeholder="e.g. 18"
              value={respiratoryRate}
              onChange={(e) => setRespiratoryRate(e.target.value)}
              leftIcon={<Wind className="w-4 h-4" />}
            />

            <Input
              label="SpO2 Oxygen Saturation (%)"
              type="number"
              step="1"
              placeholder="e.g. 98"
              value={spo2}
              onChange={(e) => setSpo2(e.target.value)}
              leftIcon={<Activity className="w-4 h-4" />}
            />

            <Select
              label="Supplemental Oxygen"
              value={supplementalOxygen}
              onChange={(e) => setSupplementalOxygen(e.target.value)}
              options={[
                { value: 'false', label: 'Room Air (No Oxygen)' },
                { value: 'true', label: 'On Supplemental Oxygen' },
              ]}
            />

            <Input
              label="Heart Rate (bpm)"
              type="number"
              step="1"
              placeholder="e.g. 76"
              value={heartRate}
              onChange={(e) => setHeartRate(e.target.value)}
              leftIcon={<Heart className="w-4 h-4" />}
            />

            <Input
              label="Systolic BP (mmHg)"
              type="number"
              step="1"
              placeholder="e.g. 120"
              value={systolicBp}
              onChange={(e) => setSystolicBp(e.target.value)}
              leftIcon={<Gauge className="w-4 h-4" />}
            />

            <Input
              label="Temperature (°C)"
              type="number"
              step="0.1"
              placeholder="e.g. 37.0"
              value={temperature}
              onChange={(e) => setTemperature(e.target.value)}
              leftIcon={<Thermometer className="w-4 h-4" />}
            />

            <Select
              label="Consciousness Level (AVPU)"
              value={avpu}
              onChange={(e) => setAvpu(e.target.value)}
              options={[
                { value: 'ALERT', label: 'Alert (A)' },
                { value: 'VOICE', label: 'Voice Responsive (V)' },
                { value: 'PAIN', label: 'Pain Responsive (P)' },
                { value: 'UNRESPONSIVE', label: 'Unresponsive (U)' },
              ]}
            />
          </div>

          <div className="pt-2 flex justify-end">
            <Button
              type="submit"
              variant="primary"
              size="md"
              isLoading={isPending}
              className="font-bold px-6 shadow-md shadow-cyan-950/60"
            >
              Save Vitals & Rescore
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
};
