import React, { useState } from 'react';
import { useAssignResource } from '../../hooks/useResources';
import { ResourceType } from '../../types/enums';
import { CapacityConflictResponse } from '../../types/api';
import { ApiError } from '../../lib/http';
import { Button } from '../../components/ui/Button';
import { Select } from '../../components/ui/Select';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';
import { CapacityConflictPanel } from './CapacityConflictPanel';
import { Layers } from 'lucide-react';

export interface AssignResourcePanelProps {
  caseId: string;
}

export const AssignResourcePanel: React.FC<AssignResourcePanelProps> = ({ caseId }) => {
  const [resourceType, setResourceType] = useState<ResourceType>('TREATMENT_SPACE');
  const [conflictData, setConflictData] = useState<CapacityConflictResponse | null>(null);

  const { mutate: assignResource, isPending } = useAssignResource();

  const handleAssign = (e: React.FormEvent) => {
    e.preventDefault();
    setConflictData(null);

    assignResource(
      { caseId, body: { resource_type: resourceType } },
      {
        onSuccess: () => {
          setConflictData(null);
        },
        onError: (err: unknown) => {
          if (err instanceof ApiError && err.isCapacityConflict && err.capacityConflictData) {
            setConflictData(err.capacityConflictData);
          }
        },
      }
    );
  };

  return (
    <div className="space-y-4">
      <Card className="bg-slate-900 border-slate-800 text-left">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center justify-between">
            <span className="flex items-center gap-2 text-slate-200">
              <Layers className="w-4 h-4 text-emerald-400" />
              Assign Department Resource / Bed
            </span>
          </CardTitle>
        </CardHeader>

        <CardContent>
          <form onSubmit={handleAssign} className="flex flex-col sm:flex-row items-end gap-3">
            <div className="flex-1 w-full">
              <Select
                label="Resource Type"
                value={resourceType}
                onChange={(e) => setResourceType(e.target.value as ResourceType)}
                options={[
                  { value: 'TREATMENT_SPACE', label: 'Treatment Space / Bed' },
                  { value: 'RESUSCITATION_BAY', label: 'Resuscitation Bay (ESI 1)' },
                  { value: 'CLINICIAN', label: 'Primary Attending Clinician' },
                ]}
              />
            </div>
            <Button
              type="submit"
              variant="primary"
              size="md"
              isLoading={isPending}
              className="w-full sm:w-auto font-bold bg-emerald-600 hover:bg-emerald-500 shadow-md shadow-emerald-950/40"
            >
              Assign Resource
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* 409 Capacity Conflict Surface */}
      {conflictData && (
        <CapacityConflictPanel
          conflict={conflictData}
          onDismiss={() => setConflictData(null)}
        />
      )}
    </div>
  );
};
