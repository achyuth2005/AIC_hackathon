import React from 'react';
import { QueueEntry } from '../../types/api';
import { AcuityBadge } from '../../components/clinical/AcuityBadge';
import { Table, TableHeader, TableBody, TableHead, TableRow, TableCell } from '../../components/ui/Table';
import { Link } from 'react-router-dom';
import { Truck, ArrowRight, Clock, ShieldAlert, CheckCircle2 } from 'lucide-react';
import { formatMinutes } from '../../lib/datetime';

export interface AmbulanceBoardTableProps {
  entries: QueueEntry[];
}

export const AmbulanceBoardTable: React.FC<AmbulanceBoardTableProps> = ({ entries = [] }) => {
  // Filter for cases with arrival_mode AMBULANCE or PRE_ARRIVAL status
  const ambulanceCases = entries.filter(
    (e) => e.arrival_mode === 'AMBULANCE' || e.stage === 'PRE_ARRIVAL'
  );

  return (
    <div className="space-y-4 text-left">
      {ambulanceCases.length === 0 ? (
        <div className="p-12 text-center text-slate-500 bg-slate-900/40 rounded-2xl border border-dashed border-slate-800 space-y-2">
          <Truck className="w-8 h-8 text-slate-600 mx-auto" />
          <div className="text-sm font-semibold text-slate-300">No Inbound Ambulances En Route</div>
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
              const isPreArrival = c.stage === 'PRE_ARRIVAL';

              return (
                <TableRow key={c.case_id} className={isPreArrival ? 'bg-cyan-950/20' : ''}>
                  <TableCell>
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <Truck className={`w-4 h-4 ${isPreArrival ? 'text-cyan-400 animate-pulse' : 'text-slate-400'}`} />
                        <span className="font-bold text-xs text-slate-100">
                          {c.display_name || 'Inbound EMS Transport'}
                        </span>
                      </div>
                      <div className="text-[10px] font-mono text-slate-500">
                        {c.case_id.substring(0, 8)}... {c.mrn ? `• MRN: ${c.mrn}` : '• Unlinked'}
                      </div>
                    </div>
                  </TableCell>

                  <TableCell>
                    <AcuityBadge acuity={c.final_acuity} size="xs" />
                  </TableCell>

                  <TableCell>
                    <span
                      className={`px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold border ${
                        isPreArrival
                          ? 'bg-cyan-950 text-cyan-300 border-cyan-700 animate-pulse'
                          : 'bg-emerald-950 text-emerald-300 border-emerald-700'
                      }`}
                    >
                      {isPreArrival ? 'EN ROUTE' : 'ARRIVED (ACTIVE)'}
                    </span>
                  </TableCell>

                  <TableCell className="text-xs font-mono text-slate-300">
                    <div className="flex items-center gap-1">
                      <Clock className="w-3.5 h-3.5 text-slate-500" />
                      <span>{formatMinutes(c.waiting_minutes)}</span>
                    </div>
                  </TableCell>

                  <TableCell>
                    {c.identity_link_status === 'CONFIRMED' ? (
                      <span className="inline-flex items-center gap-1 text-[10px] font-mono font-bold text-emerald-400">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        Confirmed
                      </span>
                    ) : c.identity_link_status === 'CANDIDATE_PROPOSED' ? (
                      <span className="inline-flex items-center gap-1 text-[10px] font-mono font-bold text-indigo-300 bg-indigo-950 px-2 py-0.5 rounded border border-indigo-700">
                        <ShieldAlert className="w-3.5 h-3.5 text-indigo-400" />
                        Match Proposed
                      </span>
                    ) : (
                      <span className="text-[10px] font-mono text-slate-500">
                        Unlinked
                      </span>
                    )}
                  </TableCell>

                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-2">
                      <Link
                        to={`/ambulance/${c.case_id}`}
                        className="inline-flex items-center gap-1 text-xs text-cyan-400 hover:text-cyan-300 font-mono font-bold"
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
