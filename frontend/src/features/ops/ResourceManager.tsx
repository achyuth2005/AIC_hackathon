import React, { useState } from 'react';
import {
  useResources,
  useCreateResource,
  useReleaseResource,
  useConfirmOccupancy,
} from '../../hooks/useResources';
import { ResourceType } from '../../types/enums';
import { RESOURCE_TYPE_LABELS, RESOURCE_STATUS_LABELS } from '../../lib/enums';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { Select } from '../../components/ui/Select';
import { Table, TableHeader, TableBody, TableHead, TableRow, TableCell } from '../../components/ui/Table';
import { formatRelative } from '../../lib/datetime';
import { Layers, Plus, CheckCircle2, RefreshCw, Unlock } from 'lucide-react';
import { Link } from 'react-router-dom';

export const ResourceManager: React.FC = () => {
  const { data: resources, isLoading, refetch } = useResources();
  const { mutate: createResource, isPending: isCreatePending } = useCreateResource();
  const { mutate: releaseResource, isPending: isReleasePending } = useReleaseResource();
  const { mutate: confirmOccupancy, isPending: isConfirmPending } = useConfirmOccupancy();

  const [label, setLabel] = useState('');
  const [resourceType, setResourceType] = useState<ResourceType>('TREATMENT_SPACE');
  const [showCreateForm, setShowCreateForm] = useState(false);

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!label.trim()) return;
    createResource(
      { resource_type: resourceType, label: label.trim(), hospital_profile_id: 'default' },
      {
        onSuccess: () => {
          setLabel('');
          setShowCreateForm(false);
        },
      }
    );
  };

  const handleQuickSeedDefaults = () => {
    // Helper to quickly populate default hospital beds if database is fresh
    const defaults: { type: ResourceType; label: string }[] = [
      { type: 'TREATMENT_SPACE', label: 'Bed 01 (Acute)' },
      { type: 'TREATMENT_SPACE', label: 'Bed 02 (Acute)' },
      { type: 'TREATMENT_SPACE', label: 'Bed 03 (Subacute)' },
      { type: 'RESUSCITATION_BAY', label: 'Resus Bay 1 (Trauma)' },
      { type: 'RESUSCITATION_BAY', label: 'Resus Bay 2 (Cardiac)' },
      { type: 'CLINICIAN', label: 'Attending Physician 1' },
      { type: 'CLINICIAN', label: 'Triage Nurse 1' },
    ];

    defaults.forEach((item) => {
      createResource({ resource_type: item.type, label: item.label, hospital_profile_id: 'default' });
    });
  };

  const totalCount = resources?.length || 0;
  const availableCount = resources?.filter((r) => r.status === 'AVAILABLE').length || 0;
  const occupiedCount = resources?.filter((r) => r.status === 'OCCUPIED').length || 0;

  return (
    <div className="space-y-6 text-left">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2.5">
            <Layers className="w-6 h-6 text-indigo-600" />
            Department Capacity & Bed Manager
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Manage physical treatment bays, resus suites, and staff assignments.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {totalCount === 0 && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleQuickSeedDefaults}
              className="text-xs border-indigo-200 text-indigo-700"
            >
              Seed Default Beds & Staff
            </Button>
          )}

          <Button
            variant="primary"
            size="sm"
            onClick={() => setShowCreateForm(!showCreateForm)}
            leftIcon={<Plus className="w-4 h-4" />}
          >
            {showCreateForm ? 'Cancel' : 'New Resource'}
          </Button>
        </div>
      </div>

      {/* Summary metric tiles */}
      <div className="grid grid-cols-3 gap-3">
        <div className="p-3.5 rounded-xl bg-white border border-slate-200/80 shadow-card">
          <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">
            Total Capacity
          </span>
          <span className="text-2xl font-bold font-mono tabular-nums text-slate-900 mt-1 block">
            {totalCount}
          </span>
        </div>

        <div className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 shadow-card">
          <span className="text-[10px] font-bold text-emerald-700 uppercase tracking-wider block">
            Available
          </span>
          <span className="text-2xl font-bold font-mono tabular-nums text-emerald-700 mt-1 block">
            {availableCount}
          </span>
        </div>

        <div className="p-3.5 rounded-xl bg-amber-50 border border-amber-200 shadow-card">
          <span className="text-[10px] font-bold text-amber-700 uppercase tracking-wider block">
            Occupied
          </span>
          <span className="text-2xl font-bold font-mono tabular-nums text-amber-700 mt-1 block">
            {occupiedCount}
          </span>
        </div>
      </div>

      {/* Create form */}
      {showCreateForm && (
        <Card className="animate-fade-in">
          <CardHeader>
            <CardTitle className="text-sm">Register Department Resource</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleCreate} className="grid grid-cols-1 sm:grid-cols-3 gap-4 items-end">
              <Input
                label="Resource Label / Name"
                placeholder="e.g. Bay 04 (Acute Treatment)"
                value={label}
                onChange={(e) => setLabel(e.target.value)}
              />

              <Select
                label="Resource Type"
                value={resourceType}
                onChange={(e) => setResourceType(e.target.value as ResourceType)}
                options={[
                  { value: 'TREATMENT_SPACE', label: 'Treatment Space / Bed' },
                  { value: 'RESUSCITATION_BAY', label: 'Resuscitation Bay' },
                  { value: 'CLINICIAN', label: 'Clinician' },
                ]}
              />

              <Button
                type="submit"
                variant="primary"
                size="md"
                isLoading={isCreatePending}
                disabled={!label.trim()}
                className="font-bold"
              >
                Create Resource
              </Button>
            </form>
          </CardContent>
        </Card>
      )}

      {/* Resources Table */}
      <Card>
        <CardHeader className="pb-3 flex flex-row items-center justify-between">
          <CardTitle className="text-sm">
            Registered Department Resources
          </CardTitle>
          <button
            onClick={() => refetch()}
            className="text-slate-400 hover:text-slate-700 p-1 rounded hover:bg-slate-100"
            title="Refresh resources list"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </CardHeader>

        <CardContent>
          {isLoading ? (
            <div className="space-y-2 py-4">
              <div className="h-8 bg-slate-100 rounded animate-pulse" />
              <div className="h-8 bg-slate-100 rounded animate-pulse" />
            </div>
          ) : !resources || resources.length === 0 ? (
            <div className="text-center py-8 text-xs text-slate-500 font-mono space-y-2">
              <p>No resources configured yet. All capacity tiles currently read zero.</p>
              <Button size="sm" variant="outline" onClick={handleQuickSeedDefaults}>
                Seed Default Beds & Staff
              </Button>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead scope="col">Resource Label</TableHead>
                  <TableHead scope="col">Type</TableHead>
                  <TableHead scope="col">Status</TableHead>
                  <TableHead scope="col">Assigned Case</TableHead>
                  <TableHead scope="col" className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {resources.map((r) => {
                  const isOccupied = r.status === 'OCCUPIED';
                  const isAvailable = r.status === 'AVAILABLE';

                  return (
                    <TableRow key={r.resource_id}>
                      <TableCell className="font-bold text-slate-900 text-xs font-mono">
                        {r.label}
                      </TableCell>

                      <TableCell className="text-xs text-slate-600">
                        {RESOURCE_TYPE_LABELS[r.resource_type] || r.resource_type}
                      </TableCell>

                      <TableCell>
                        <span
                          className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-mono font-bold border ${
                            isAvailable
                              ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                              : isOccupied
                              ? 'bg-amber-50 text-amber-700 border-amber-200'
                              : 'bg-slate-100 text-slate-500 border-slate-200'
                          }`}
                        >
                          <span
                            className={`w-1.5 h-1.5 rounded-full ${
                              isAvailable ? 'bg-emerald-500' : isOccupied ? 'bg-amber-500' : 'bg-slate-400'
                            }`}
                          />
                          {RESOURCE_STATUS_LABELS[r.status] || r.status}
                        </span>
                        {r.occupancy_stuck_flagged && (
                          <span className="ml-2 text-[10px] font-mono font-bold text-rose-700 bg-rose-50 px-1.5 py-0.2 rounded border border-rose-200">
                            STUCK
                          </span>
                        )}
                      </TableCell>

                      <TableCell className="text-xs font-mono text-slate-500">
                        {r.assigned_case_id ? (
                          <Link
                            to={`/cases/${r.assigned_case_id}`}
                            className="text-indigo-600 hover:underline flex items-center gap-1"
                          >
                            Case {r.assigned_case_id.substring(0, 8)}
                            {r.assigned_at && (
                              <span className="text-[10px] text-slate-400">
                                ({formatRelative(r.assigned_at)})
                              </span>
                            )}
                          </Link>
                        ) : (
                          <span className="text-slate-300">--</span>
                        )}
                      </TableCell>

                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-2">
                          {r.assigned_case_id && !isOccupied && (
                            <Button
                              size="xs"
                              variant="primary"
                              disabled={isConfirmPending}
                              onClick={() => confirmOccupancy(r.resource_id)}
                              leftIcon={<CheckCircle2 className="w-3 h-3" />}
                              className="text-[10px] bg-emerald-600 hover:bg-emerald-700"
                            >
                              Confirm Occupancy
                            </Button>
                          )}

                          {(isOccupied || r.assigned_case_id) && (
                            <Button
                              size="xs"
                              variant="secondary"
                              disabled={isReleasePending}
                              onClick={() => releaseResource(r.resource_id)}
                              leftIcon={<Unlock className="w-3 h-3" />}
                              className="text-[10px]"
                            >
                              Release
                            </Button>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
};
