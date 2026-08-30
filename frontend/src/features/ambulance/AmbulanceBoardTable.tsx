import React from 'react';
import { CaseResponse } from '../../types/api';
import { AcuityBadge } from '../../components/clinical/AcuityBadge';
import { Table, TableHeader, TableBody, TableHead, TableRow, TableCell } from '../../components/ui/Table';
import { Link } from 'react-router-dom';
import { Truck, ArrowRight, Clock, ShieldAlert, CheckCircle2 } from 'lucide-react';
import { formatMinutes } from '../../lib/datetime';
import { usePreAlertView } from '../../hooks/useAmbulanceList';

export interface AmbulanceBoardTableProps {
  entries: CaseResponse[];
}

// Bug fix: predicted acuity isn't on CaseResponse (only a full risk
// assessment carries it, and a freshly-created PRE_ARRIVAL case may not
// have one yet at all -- see build_pre_alert's own null-handling). Reuses
// the existing per-case pre-alert hook rather than adding a second
// N+1-fetch pattern; renders a subtle placeholder until an assessment
// exists.
const PredictedAcuityCell: React.FC<{ caseId: string }> = ({ caseId }) => {
  const { data, isLoading } = usePreAlertView(caseId);
  if (isLoading) {
    return <span className="text-[10px] font-mono text-slate-300">…</span>;
  }
  if (!data?.predicted_acuity_band) {
    return <span className="text-[10px] font-mono text-slate-400">Awaiting vitals</span>;
  }
  return <AcuityBadge acuity={data.predicted_acuity_band} size="xs" />;
};

function minutesSince(isoTimestamp: string): number {
  return (Date.now() - new Date(`${isoTimestamp}Z`).getTime()) / 60000;
}

export const AmbulanceBoardTable: React.FC<AmbulanceBoardTableProps> = ({ entries = [] }) => {
  // Bug fix: entries is now the authoritative GET /cases?arrival_mode=
  // AMBULANCE result (see api/ambulance.ts) -- every ambulance-origin
  // case is already exactly what this board wants, regardless of stage,
  // so no further client-side filtering is needed (the previous filter
  // read `arrival_mode`/`stage` fields that never existed on the old
  // /queue-derived QueueEntry shape, so it silently matched nothing).
  const ambulanceCases = entries.filter((e) => e.status !== 'DISPOSED');

  return (
    <div className="space-y-4 text-left">
      {ambulanceCases.length === 0 ? (
        <div className="p-12 text-center text-slate-500 bg-white rounded-2xl border border-dashed border-slate-300 space-y-2">
          <Truck className="w-8 h-8 text-slate-300 mx-auto" />
          <div className="text-sm font-semibold text-slate-700">No Inbound Ambulances En Route</div>
          <p className="text-xs text-slate-500 max-w-sm mx-auto">
            All registered ambulance transports have arrived or entered active triage.
          </p>
        </div>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead scope="col">Transport & Patient</TableHead>
              <TableHead scope="col">Predicted Acuity</TableHead>
              <TableHead scope="col">Status & Stage</TableHead>
              <TableHead scope="col">Wait / Transit Dwell</TableHead>
              <TableHead scope="col">Identity Link</TableHead>
              <TableHead scope="col" className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {ambulanceCases.map((c) => {
              const isPreArrival = c.status === 'PRE_ARRIVAL';
              const dwellMinutes = minutesSince(c.arrived_at || c.created_at);

              return (
                <TableRow key={c.case_id} className={isPreArrival ? 'bg-indigo-50/40' : ''}>
                  <TableCell>
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <Truck className={`w-4 h-4 ${isPreArrival ? 'text-indigo-600 animate-pulse' : 'text-slate-400'}`} />
                        <span className="font-semibold text-xs text-slate-900">
                          {c.display_name || 'Inbound EMS Transport'}
                        </span>
                      </div>
                      <div className="text-[10px] font-mono text-slate-400">
                        {c.case_id.substring(0, 8)}... {c.mrn ? `• MRN: ${c.mrn}` : '• Unlinked'}
                      </div>
                    </div>
                  </TableCell>

                  <TableCell>
                    <PredictedAcuityCell caseId={c.case_id} />
                  </TableCell>

                  <TableCell>
                    <span
                      className={`px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold border ${
                        isPreArrival
                          ? 'bg-indigo-50 text-indigo-700 border-indigo-200 animate-pulse'
                          : 'bg-emerald-50 text-emerald-700 border-emerald-200'
                      }`}
                    >
                      {isPreArrival ? 'EN ROUTE' : 'ARRIVED (ACTIVE)'}
                    </span>
                  </TableCell>

                  <TableCell className="text-xs font-mono tabular-nums text-slate-600">
                    <div className="flex items-center gap-1">
                      <Clock className="w-3.5 h-3.5 text-slate-400" />
                      <span>{formatMinutes(dwellMinutes)}</span>
                    </div>
                  </TableCell>

                  <TableCell>
                    {c.identity_link_status === 'CONFIRMED' ? (
                      <span className="inline-flex items-center gap-1 text-[10px] font-mono font-bold text-emerald-700">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        Confirmed
                      </span>
                    ) : c.identity_link_status === 'CANDIDATE_PROPOSED' ? (
                      <span className="inline-flex items-center gap-1 text-[10px] font-mono font-bold text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded border border-indigo-200">
                        <ShieldAlert className="w-3.5 h-3.5 text-indigo-600" />
                        Match Proposed
                      </span>
                    ) : (
                      <span className="text-[10px] font-mono text-slate-400">
                        Unlinked
                      </span>
                    )}
                  </TableCell>

                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-2">
                      <Link
                        to={`/ambulance/${c.case_id}`}
                        className="inline-flex items-center gap-1 text-xs text-indigo-600 hover:text-indigo-700 font-mono font-bold"
                      >
                        <span>Pre-Alert & ETA</span>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </Link>
                    </div>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      )}
    </div>
  );
};
