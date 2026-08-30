import React, { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { casesApi } from '../../api/cases';
import { CaseCreateRequest } from '../../types/api';
import { ArrivalMode } from '../../types/enums';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { Select } from '../../components/ui/Select';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';
import { useNavigate } from 'react-router-dom';
import { useToast } from '../../components/ui/Toast';
import { UserPlus, AlertTriangle, Truck, User } from 'lucide-react';

export const RegisterCaseForm: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  const [displayName, setDisplayName] = useState('');
  const [mrn, setMrn] = useState('');
  const [ageYears, setAgeYears] = useState<string>('');
  const [sex, setSex] = useState('');
  const [medicalHistory, setMedicalHistory] = useState('');
  const [arrivalMode, setArrivalMode] = useState<ArrivalMode>('WALK_IN');
  const [estimatedTransportMinutes, setEstimatedTransportMinutes] = useState<string>('');

  const { mutate: createCase, isPending } = useMutation({
    mutationFn: (body: CaseCreateRequest) => casesApi.createCase(body),
    onSuccess: (data) => {
      success(
        `Case registered for ${data.display_name || 'Patient'} (${data.arrival_mode}). Initial assessment generated.`,
        'Patient Registered'
      );
      queryClient.invalidateQueries({ queryKey: ['queue'] });
      queryClient.invalidateQueries({ queryKey: ['cases'] });
      // Bug fix: the ambulance board's query key is ['ambulance-list', ...]
      // (useAmbulanceList.ts), not ['queue'] -- without this it only
      // picked up a newly-created ambulance case on its next poll tick,
      // never immediately.
      queryClient.invalidateQueries({ queryKey: ['ambulance-list'] });
      // An AMBULANCE registration belongs on the pre-arrival board/detail
      // view, not the generic active-case detail page.
      navigate(data.arrival_mode === 'AMBULANCE' ? `/ambulance/${data.case_id}` : `/cases/${data.case_id}`);
    },
    onError: (err: unknown) => {
      error(err instanceof Error ? err.message : 'Registration failed.');
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    const parsedAge = ageYears.trim() ? parseInt(ageYears, 10) : null;
    if (ageYears.trim() && (isNaN(parsedAge!) || parsedAge! < 0 || parsedAge! > 130)) {
      error('Please enter a valid age in years.');
      return;
    }

    const parsedTransport =
      arrivalMode === 'AMBULANCE' && estimatedTransportMinutes.trim()
        ? parseFloat(estimatedTransportMinutes)
        : null;

    createCase({
      hospital_profile_id: 'default',
      display_name: displayName.trim() || null,
      mrn: mrn.trim() || null,
      age_years: parsedAge,
      sex: sex.trim() || null,
      medical_history: medicalHistory.trim() || null,
      arrival_mode: arrivalMode,
      estimated_transport_minutes: parsedTransport,
    });
  };

  return (
    <Card className="max-w-2xl mx-auto text-left">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <UserPlus className="w-5 h-5 text-indigo-600" />
          Register New Patient (Walk-In or Inbound Ambulance)
        </CardTitle>
      </CardHeader>

      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              label="Patient Display Name"
              placeholder="e.g. Maya Devi"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              leftIcon={<User className="w-4 h-4" />}
            />

            <Input
              label="Medical Record Number (MRN - Optional)"
              placeholder="e.g. MRN-8921"
              value={mrn}
              onChange={(e) => setMrn(e.target.value)}
            />

            <Input
              label="Age (Years)"
              type="number"
              placeholder="e.g. 54"
              value={ageYears}
              onChange={(e) => setAgeYears(e.target.value)}
              helperText={!ageYears ? 'Age is used to route between NEWS2 (adult) and PEWS (paediatric)' : undefined}
            />

            <Select
              label="Sex (Optional, for Equity Reporting)"
              value={sex}
              onChange={(e) => setSex(e.target.value)}
              options={[
                { value: '', label: 'Unspecified' },
                { value: 'FEMALE', label: 'Female' },
                { value: 'MALE', label: 'Male' },
                { value: 'OTHER', label: 'Other' },
              ]}
            />
          </div>

          <Input
            label="Medical History (Optional)"
            placeholder="e.g. COPD, Type 2 Diabetes -- leave blank if none known"
            value={medicalHistory}
            onChange={(e) => setMedicalHistory(e.target.value)}
            helperText="High-risk conditions (COPD, CAD, heart failure, immunosuppressed) escalate acuity when combined with abnormal vitals."
          />

          {!ageYears && (
            <div className="p-3 rounded-xl bg-amber-50 border border-amber-200 text-xs text-amber-800 flex items-start gap-2.5">
              <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold">Age Router Advisory:</span> Without an age, the system cannot pick between adult NEWS2 and paediatric PEWS frameworks, causing confidence abstention floored at ESI 3.
              </div>
            </div>
          )}

          <div className="pt-2 border-t border-slate-100">
            <Select
              label="Arrival Mode"
              value={arrivalMode}
              onChange={(e) => setArrivalMode(e.target.value as ArrivalMode)}
              options={[
                { value: 'WALK_IN', label: 'Walk-In Registration (Enters Active Queue Immediately)' },
                { value: 'AMBULANCE', label: 'Inbound Ambulance Transport (Pre-Arrival Board)' },
              ]}
            />
          </div>

          {arrivalMode === 'AMBULANCE' && (
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-3 animate-fade-in">
              <div className="flex items-center gap-2 text-xs font-semibold text-indigo-700">
                <Truck className="w-4 h-4" />
                Ambulance Pre-Arrival Parameters
              </div>
              <Input
                label="Estimated Transport Duration (Minutes)"
                type="number"
                placeholder="e.g. 15"
                value={estimatedTransportMinutes}
                onChange={(e) => setEstimatedTransportMinutes(e.target.value)}
                helperText="Starts the simulated ETA countdown clock upon creation."
              />
            </div>
          )}

          <div className="pt-4 flex items-center justify-end gap-3">
            <Button
              type="button"
              variant="secondary"
              onClick={() => navigate('/queue')}
              disabled={isPending}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              isLoading={isPending}
              className="font-bold px-6"
            >
              Create Patient Case
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
};
