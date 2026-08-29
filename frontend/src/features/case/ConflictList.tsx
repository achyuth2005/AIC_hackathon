import React, { useState } from 'react';
import { useConflicts } from '../../hooks/useConflicts';
import { DataConflictResponse } from '../../types/api';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { ResolveConflictModal } from './ResolveConflictModal';
import { GitCompare, AlertTriangle } from 'lucide-react';
import { formatRelative } from '../../lib/datetime';

export interface ConflictListProps {
  caseId: string;
}

export const ConflictList: React.FC<ConflictListProps> = ({ caseId }) => {
  const { data: conflicts, isLoading, isError } = useConflicts(caseId);
  const [selectedConflict, setSelectedConflict] = useState<DataConflictResponse | null>(null);

  if (isLoading || isError || !conflicts || conflicts.length === 0) {
    return null;
  }

  const openConflicts = conflicts.filter((c) => !c.resolved);

  if (openConflicts.length === 0) {
    return null;
  }

  return (
    <Card className="bg-slate-900 border-purple-900/60 text-left">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm flex items-center justify-between text-purple-300">
          <span className="flex items-center gap-2">
            <GitCompare className="w-4 h-4 text-purple-400" />
            Unresolved Data Conflicts ({openConflicts.length})
          </span>
          <span className="text-[10px] font-mono bg-purple-950 text-purple-300 px-2 py-0.5 rounded border border-purple-800">
            Phase 9.3 Asymmetric Safety
          </span>
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-3">
        {openConflicts.map((c) => (
          <div
            key={c.conflict_id}
            className="p-3.5 rounded-xl bg-purple-950/30 border border-purple-800/60 flex flex-col sm:flex-row sm:items-center justify-between gap-3"
          >
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-purple-400" />
                <span className="font-mono font-bold text-xs text-white">
                  {c.concept_code}
                </span>
                <span className="text-xs text-purple-200">
                  — {c.observation_ids.length} conflicting measurements
                </span>
              </div>
              <div className="text-[11px] text-slate-400 font-mono">
                Detected: {formatRelative(c.detected_at)} • Conservative reading active
              </div>
            </div>

            <Button
              variant="outline"
              size="sm"
              onClick={() => setSelectedConflict(c)}
              className="border-purple-600/70 text-purple-200 hover:bg-purple-900/40 text-xs font-semibold shrink-0"
            >
              Resolve Conflict
            </Button>
          </div>
        ))}

        {selectedConflict && (
          <ResolveConflictModal
            isOpen={!!selectedConflict}
            onClose={() => setSelectedConflict(null)}
            conflict={selectedConflict}
          />
        )}
      </CardContent>
    </Card>
  );
};
