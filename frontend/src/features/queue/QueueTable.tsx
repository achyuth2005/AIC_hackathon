import React from 'react';
import { QueueEntry } from '../../types/api';
import { Table, TableHeader, TableBody, TableHead, TableRow } from '../../components/ui/Table';
import { QueueRow } from './QueueRow';
import { EmptyState } from '../../components/ui/EmptyState';
import { ListOrdered } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export interface QueueTableProps {
  entries: QueueEntry[];
}

export const QueueTable: React.FC<QueueTableProps> = ({ entries }) => {
  const navigate = useNavigate();

  if (entries.length === 0) {
    return (
      <EmptyState
        icon={<ListOrdered className="w-10 h-10 text-slate-500" />}
        title="No active patients in Guardian Queue"
        description="All emergency department patients have been seen or disposed. Register a new walk-in or seed demo patients."
        actionText="Register Walk-in Patient"
        onAction={() => navigate('/register')}
      />
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead scope="col" className="w-48">Acuity & Confidence</TableHead>
          <TableHead scope="col">Patient & One-Line Presentation</TableHead>
          <TableHead scope="col" className="w-64">Time in Band & Reassessment</TableHead>
          <TableHead scope="col" className="w-72 text-right">Attention Flag & Actions</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {/*
          CRITICAL CLINICAL INVARIANT:
          The array returned by GET /queue is already pre-sorted by the backend Guardian Queue engine
          using (final_acuity ASC, time_critical_pathway DESC, deterioration_trend DESC, time_in_current_band DESC, arrival_time ASC).
          DO NOT SORT ON THE CLIENT.
        */}
        {entries.map((entry, index) => (
          <QueueRow key={entry.case_id} entry={entry} index={index} />
        ))}
      </TableBody>
    </Table>
  );
};
