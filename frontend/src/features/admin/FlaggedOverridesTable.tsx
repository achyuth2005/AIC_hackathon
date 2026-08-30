import React from 'react';
import { HumanDecisionResponse } from '../../types/api';
import { Table, TableHeader, TableBody, TableHead, TableRow, TableCell } from '../../components/ui/Table';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';
import { AcuityBadge } from '../../components/clinical/AcuityBadge';
import { DE_ESCALATION_REASONS } from '../../lib/enums';
import { formatRelative, formatClock } from '../../lib/datetime';
import { Link } from 'react-router-dom';
import { ShieldAlert, ArrowRight, CheckCircle2 } from 'lucide-react';

export interface FlaggedOverridesTableProps {
  overrides: HumanDecisionResponse[];
  isLoading?: boolean;
}

export const FlaggedOverridesTable: React.FC<FlaggedOverridesTableProps> = ({
  overrides = [],
  isLoading = false,
}) => {
  return (
    <Card className="border-amber-200 text-left shadow-card-lg">
      <CardHeader className="pb-3 flex flex-row items-center justify-between">
        <CardTitle className="text-base flex items-center gap-2.5 text-amber-800">
          <ShieldAlert className="w-5 h-5 text-amber-600" />
          <span>Retrospective Review Queue (Flagged De-escalations) ({overrides.length})</span>
        </CardTitle>
        <span className="text-[10px] font-mono font-bold bg-amber-50 text-amber-700 px-2.5 py-0.5 rounded-full border border-amber-200">
          Phase 9.6 Audit Surface
        </span>
      </CardHeader>

      <CardContent>
        {isLoading ? (
          <div className="space-y-2 py-4">
            <div className="h-10 bg-slate-100 rounded animate-pulse" />
            <div className="h-10 bg-slate-100 rounded animate-pulse" />
          </div>
        ) : overrides.length === 0 ? (
          <div className="p-8 rounded-xl bg-slate-50 border border-slate-200 text-center space-y-2">
            <CheckCircle2 className="w-8 h-8 text-emerald-500 mx-auto" />
            <div className="text-sm font-semibold text-slate-700">
              No Flagged De-escalations Pending Review
            </div>
            <p className="text-xs text-slate-500 max-w-sm mx-auto">
              All clinician override actions adhere to standard escalation pathways.
            </p>
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead scope="col">Case & Clinician</TableHead>
                <TableHead scope="col">Timestamp</TableHead>
                <TableHead scope="col">System vs Decided</TableHead>
                <TableHead scope="col">Structured Clinical Justification</TableHead>
                <TableHead scope="col" className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {overrides.map((d) => (
                <TableRow key={d.decision_id} className="bg-amber-50/60">
                  <TableCell>
                    <div className="space-y-0.5">
                      <div className="font-bold text-xs text-slate-900">
                        {d.clinician_id} ({d.role})
                      </div>
                      <div className="text-[10px] font-mono text-slate-400">
                        Case: {d.case_id.substring(0, 8)}...
                      </div>
                    </div>
                  </TableCell>

                  <TableCell className="text-xs font-mono text-slate-600">
                    <div>{formatRelative(d.timestamp)}</div>
                    <div className="text-[10px] text-slate-400">{formatClock(d.timestamp, true)}</div>
                  </TableCell>

                  <TableCell>
                    <div className="flex items-center gap-1.5 font-mono text-xs">
                      <AcuityBadge acuity={d.system_recommendation} size="xs" showLabel={false} />
                      <span className="text-amber-600 font-bold">→</span>
                      <AcuityBadge acuity={d.resulting_acuity} size="xs" showLabel={false} />
                    </div>
                  </TableCell>

                  <TableCell className="text-xs text-slate-600 max-w-sm">
                    <div className="space-y-0.5">
                      <div className="font-semibold text-amber-700">
                        {d.reason_code ? (DE_ESCALATION_REASONS[d.reason_code] || d.reason_code) : 'No reason code'}
                      </div>
                      {d.free_text_reason && (
                        <div className="text-[11px] text-slate-500 italic">
                          "{d.free_text_reason}"
                        </div>
                      )}
                    </div>
                  </TableCell>

                  <TableCell className="text-right">
                    <Link
                      to={`/cases/${d.case_id}`}
                      className="inline-flex items-center gap-1 text-xs text-indigo-600 hover:text-indigo-700 font-mono font-bold"
                    >
                      <span>Workspace</span>
                      <ArrowRight className="w-3 h-3" />
                    </Link>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
};
