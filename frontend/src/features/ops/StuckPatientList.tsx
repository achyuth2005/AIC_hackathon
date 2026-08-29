import React from 'react';
import { useStuckPatients } from '../../hooks/useStuckPatients';
import { Table, TableHeader, TableBody, TableHead, TableRow, TableCell } from '../../components/ui/Table';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';
import { formatMinutes } from '../../lib/datetime';
import { Link } from 'react-router-dom';
import { AlertOctagon, CheckCircle2, Clock, ArrowRight } from 'lucide-react';

export const StuckPatientList: React.FC = () => {
  const { data: stuckPatients, isLoading } = useStuckPatients();

  const count = stuckPatients?.length || 0;

  return (
    <Card className="bg-slate-900 border-rose-900/60 text-left shadow-xl">
      <CardHeader className="pb-3 flex flex-row items-center justify-between">
        <CardTitle className="text-base flex items-center gap-2.5 text-rose-300">
          <AlertOctagon className="w-5 h-5 text-rose-400" />
          <span>Operationally Stuck Patients ({count})</span>
        </CardTitle>
        <span className="text-[10px] font-mono font-bold bg-rose-950 text-rose-300 px-2.5 py-0.5 rounded-full border border-rose-800">
          Flow Bottleneck Surface
        </span>
      </CardHeader>

      <CardContent>
        {isLoading ? (
          <div className="space-y-2 py-4">
            <div className="h-10 bg-slate-800 rounded animate-pulse" />
            <div className="h-10 bg-slate-800 rounded animate-pulse" />
          </div>
        ) : count === 0 ? (
          <div className="p-8 rounded-xl bg-slate-950/60 border border-slate-800/80 text-center space-y-2">
            <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto" />
            <div className="text-sm font-semibold text-slate-200">
              No Operational Bottlenecks Detected
            </div>
            <p className="text-xs text-slate-400 max-w-sm mx-auto">
              All active patients are progressing within expected clinical dwell thresholds.
            </p>
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead scope="col">Case ID</TableHead>
                <TableHead scope="col">Bottleneck Pattern</TableHead>
                <TableHead scope="col">Time Overdue</TableHead>
                <TableHead scope="col">Routing Queue</TableHead>
                <TableHead scope="col" className="text-right">Case Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {stuckPatients!.map((p, idx) => (
                <TableRow key={`${p.case_id}-${idx}`}>
                  <TableCell className="font-mono text-xs font-bold text-slate-200">
                    Case {p.case_id.substring(0, 8)}...
                  </TableCell>

                  <TableCell className="text-xs font-semibold text-rose-300">
                    {p.label}
                  </TableCell>

                  <TableCell className="text-xs font-mono text-slate-300">
                    <div className="text-rose-400 font-bold flex items-center gap-1">
                      <Clock className="w-3.5 h-3.5" />
                      {formatMinutes(p.minutes_overdue)} overdue
                    </div>
                  </TableCell>

                  <TableCell>
                    <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700 text-[10px] font-mono font-bold">
                      {p.route_to}
                    </span>
                  </TableCell>

                  <TableCell className="text-right">
                    <Link
                      to={`/cases/${p.case_id}`}
                      className="inline-flex items-center gap-1 text-xs text-cyan-400 hover:text-cyan-300 font-mono font-semibold"
                    >
                      <span>Open Workspace</span>
                      <ArrowRight className="w-3.5 h-3.5" />
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
