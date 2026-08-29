import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Input } from '../components/ui/Input';
import { Select } from '../components/ui/Select';
import { Modal } from '../components/ui/Modal';
import { ConfirmDialog } from '../components/ui/ConfirmDialog';
import { AcuityBadge } from '../components/clinical/AcuityBadge';
import { ConfidenceBadge } from '../components/clinical/ConfidenceBadge';
import { AttentionFlagChip } from '../components/clinical/AttentionFlagChip';
import { WaitTimeRange } from '../components/clinical/WaitTimeRange';
import { TrendArrow } from '../components/clinical/TrendArrow';
import { VitalValue } from '../components/clinical/VitalValue';
import { QueryBoundary } from '../components/feedback/QueryBoundary';
import { ACUITY_CONFIG } from '../lib/acuity';
import {
  Palette,
  ShieldAlert,
  Zap,
  Activity,
  Layers,
  Sparkles,
} from 'lucide-react';

export const StyleGuidePage: React.FC = () => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isConfirmOpen, setIsConfirmOpen] = useState(false);

  return (
    <div className="space-y-8 max-w-6xl mx-auto pb-12">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-5">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-2.5">
            <Palette className="w-6 h-6 text-cyan-400" />
            Design System & Clinical Primitives Styleguide
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Authoritative visual tokens, clinical badges, color-blind accessible ramps, and components.
          </p>
        </div>
        <Badge variant="primary" size="md">
          Checkpoint 2 Verified
        </Badge>
      </div>

      {/* 1. Acuity Color Scale (ESI 1-5) */}
      <Card>
        <CardHeader>
          <CardTitle>
            <ShieldAlert className="w-5 h-5 text-rose-400" />
            ESI 1–5 Clinical Acuity Scale & Emergency Bypass
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {Object.values(ACUITY_CONFIG).map((cfg) => (
              <div
                key={cfg.level}
                className={`p-4 rounded-xl border ${cfg.borderClass} ${cfg.lightBg} space-y-2 text-left`}
              >
                <div className="flex items-center justify-between">
                  <AcuityBadge acuity={cfg.level} size="md" />
                  <span className="font-mono text-xs text-slate-400">{cfg.hex}</span>
                </div>
                <div className="font-semibold text-slate-200 text-sm">{cfg.name}</div>
                <div className="text-xs text-slate-400">{cfg.description}</div>
              </div>
            ))}

            {/* Emergency Bypass Mode */}
            <div className="p-4 rounded-xl border border-red-600 bg-red-950/60 space-y-2 text-left animate-pulse">
              <div className="flex items-center justify-between">
                <AcuityBadge acuity={1} size="md" isBypass={true} />
                <span className="font-mono text-xs text-red-400 font-bold">PANIC OVERRIDE</span>
              </div>
              <div className="font-semibold text-white text-sm flex items-center gap-1.5">
                <Zap className="w-4 h-4 text-red-400" />
                Emergency Bypass Active
              </div>
              <div className="text-xs text-red-200">
                Escalation-only panic path triggered via staff tap, critical physiology, or NLP.
              </div>
            </div>
          </div>

          <div className="pt-4 border-t border-slate-800/80 flex flex-wrap items-center gap-3">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Badge Size Scale:
            </span>
            <AcuityBadge acuity={1} size="xs" />
            <AcuityBadge acuity={2} size="sm" />
            <AcuityBadge acuity={3} size="md" />
            <AcuityBadge acuity={4} size="lg" />
            <AcuityBadge acuity={5} size="xl" />
          </div>
        </CardContent>
      </Card>

      {/* 2. Confidence Bands & Attention Flags */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>
              <Sparkles className="w-5 h-5 text-cyan-400" />
              Confidence & Abstention Bands
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <div className="flex items-center justify-between p-3 rounded-lg bg-slate-900 border border-slate-800">
                <span className="text-xs text-slate-300">High Confidence (Score &gt;= 75)</span>
                <ConfidenceBadge band="HIGH" />
              </div>
              <div className="flex items-center justify-between p-3 rounded-lg bg-slate-900 border border-slate-800">
                <span className="text-xs text-slate-300">Medium Confidence (Score 40–74)</span>
                <ConfidenceBadge band="MEDIUM" />
              </div>
              <div className="flex items-center justify-between p-3 rounded-lg bg-slate-900 border border-slate-800">
                <span className="text-xs text-slate-300">Low Confidence (Score &lt; 40)</span>
                <ConfidenceBadge band="LOW" />
              </div>
              <div className="flex items-center justify-between p-3 rounded-lg bg-slate-900 border border-slate-800">
                <span className="text-xs text-slate-300">Confidence Engine Abstaining</span>
                <ConfidenceBadge band={null} shouldAbstain={true} />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>
              <Activity className="w-5 h-5 text-amber-400" />
              Primary Attention Flags
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex items-center justify-between p-2.5 rounded-lg bg-slate-900 border border-slate-800">
              <span className="text-xs text-slate-300">Reassessment Overdue</span>
              <AttentionFlagChip flag="REASSESSMENT_OVERDUE" />
            </div>
            <div className="flex items-center justify-between p-2.5 rounded-lg bg-slate-900 border border-slate-800">
              <span className="text-xs text-slate-300">Deteriorating Trend</span>
              <AttentionFlagChip flag="DETERIORATING" />
            </div>
            <div className="flex items-center justify-between p-2.5 rounded-lg bg-slate-900 border border-slate-800">
              <span className="text-xs text-slate-300">Data Conflict Detected</span>
              <AttentionFlagChip flag="DATA_CONFLICT" />
            </div>
            <div className="flex items-center justify-between p-2.5 rounded-lg bg-slate-900 border border-slate-800">
              <span className="text-xs text-slate-300">Vitals Incomplete</span>
              <AttentionFlagChip flag="UNKNOWN_VITALS" />
            </div>
            <div className="flex items-center justify-between p-2.5 rounded-lg bg-slate-900 border border-slate-800">
              <span className="text-xs text-slate-300">Routine / Stable</span>
              <AttentionFlagChip flag="NONE" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 3. Physiological Vital Values & Trends */}
      <Card>
        <CardHeader>
          <CardTitle>
            <Layers className="w-5 h-5 text-emerald-400" />
            Vitals, Trends & Wait Range Primitives
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <VitalValue
              label="Heart Rate"
              value={118}
              unit="bpm"
              points={1}
              reliabilityTier={1}
              observedAt={new Date().toISOString()}
            />
            <VitalValue
              label="Respiration Rate"
              value={26}
              unit="br/min"
              points={3}
              reliabilityTier={2}
              observedAt={new Date().toISOString()}
            />
            <VitalValue
              label="Oxygen Saturation"
              value={92}
              unit="%"
              points={2}
              reliabilityTier={1}
              observedAt={new Date().toISOString()}
            />
            <VitalValue
              label="Consciousness (AVPU)"
              value="ALERT"
              points={0}
              reliabilityTier={2}
              observedAt={new Date().toISOString()}
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4 border-t border-slate-800">
            <div>
              <div className="text-xs font-semibold text-slate-400 mb-2">Trend Arrows</div>
              <div className="flex flex-wrap gap-2">
                <TrendArrow trend="WORSENING" showLabel={true} />
                <TrendArrow trend="STABLE" showLabel={true} />
                <TrendArrow trend="IMPROVING" showLabel={true} />
              </div>
            </div>

            <div className="md:col-span-2">
              <div className="text-xs font-semibold text-slate-400 mb-2">Wait Time Range with Caveat</div>
              <WaitTimeRange
                estimate={{
                  lower_minutes: 20,
                  upper_minutes: 45,
                  patients_ahead: 4,
                  available_capacity: 2,
                  basis: 'BAND_HISTORY',
                  sample_size: 140,
                  caveat:
                    'Historical range for ESI 2 patients under current department capacity. Subject to incoming ambulances and emergent escalations.',
                }}
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 4. Query Boundary States */}
      <Card>
        <CardHeader>
          <CardTitle>Standardized Query Boundary States</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/40">
            <span className="text-xs font-semibold text-slate-400 block mb-2">Success with Data State:</span>
            <QueryBoundary isLoading={false} isError={false} data={{ name: 'Active Patient', mrn: 'MRN-1092' }}>
              {(d) => (
                <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-200">
                  Patient: <span className="font-bold text-cyan-300">{d.name}</span> ({d.mrn})
                </div>
              )}
            </QueryBoundary>
          </div>
          <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/40">
            <span className="text-xs font-semibold text-slate-400 block mb-2">Empty State:</span>
            <QueryBoundary
              isLoading={false}
              isError={false}
              data={[]}
              isEmpty={(arr) => arr.length === 0}
              emptyTitle="No conflicts found"
              emptyDescription="All clinical observations are congruent."
            >
              {() => null}
            </QueryBoundary>
          </div>
        </CardContent>
      </Card>

      {/* 5. Interactive Dialogs & Buttons */}
      <Card>
        <CardHeader>
          <CardTitle>Interactive UI Controls & Form Primitives</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="flex flex-wrap gap-3">
            <Button variant="primary">Primary Button</Button>
            <Button variant="secondary">Secondary Button</Button>
            <Button variant="danger">Danger Action</Button>
            <Button variant="warning">Warning Action</Button>
            <Button variant="outline">Outline Button</Button>
            <Button variant="ghost">Ghost Button</Button>
            <Button variant="primary" isLoading={true}>
              Loading
            </Button>
            <Button variant="primary" onClick={() => setIsModalOpen(true)}>
              Open Sample Modal
            </Button>
            <Button variant="danger" onClick={() => setIsConfirmOpen(true)}>
              Open Confirm Dialog
            </Button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-xl">
            <Input label="Patient Full Name" placeholder="e.g. Maya Devi" />
            <Select
              label="Arrival Mode"
              options={[
                { value: 'WALK_IN', label: 'Walk-In Registration' },
                { value: 'AMBULANCE', label: 'Inbound Ambulance' },
              ]}
            />
          </div>
        </CardContent>
      </Card>

      {/* Sample Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Sample Clinical Modal"
        description="Structured friction and dialog wrapper for clinical operations."
        footer={
          <>
            <Button variant="secondary" onClick={() => setIsModalOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" onClick={() => setIsModalOpen(false)}>
              Save Changes
            </Button>
          </>
        }
      >
        <p className="text-sm text-slate-300">
          This modal traps keyboard focus, closes on Escape, and displays accessible backdrop blur.
        </p>
      </Modal>

      {/* Sample Confirm Dialog */}
      <ConfirmDialog
        isOpen={isConfirmOpen}
        onClose={() => setIsConfirmOpen(false)}
        onConfirm={() => setIsConfirmOpen(false)}
        title="Confirm Emergency Action"
        message="Are you sure you want to trigger this action? This operation will be recorded in the audit log."
        confirmText="Confirm Action"
        variant="danger"
      />
    </div>
  );
};
