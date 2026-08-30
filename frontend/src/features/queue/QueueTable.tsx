import React, { useEffect, useState } from 'react';
import { QueueEntry } from '../../types/api';
import { Table, TableHeader, TableBody, TableHead, TableRow } from '../../components/ui/Table';
import { Pagination } from '../../components/ui/Pagination';
import { QueueRow } from './QueueRow';
import { EmptyState } from '../../components/ui/EmptyState';
import { ListOrdered } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export interface QueueTableProps {
  entries: QueueEntry[];
}

const PAGE_SIZE = 25;

export const QueueTable: React.FC<QueueTableProps> = ({ entries }) => {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const pageCount = Math.max(1, Math.ceil(entries.length / PAGE_SIZE));

  // Keep the current page in range as the live 3s sweep adds/removes
  // patients underneath us (e.g. a page 4 that no longer exists once the
  // queue shrinks), without resetting the nurse back to page 1 on every
  // poll while it's still valid.
  useEffect(() => {
    setPage((current) => Math.min(current, pageCount));
  }, [pageCount]);

  if (entries.length === 0) {
    return (
      <EmptyState
        icon={<ListOrdered className="w-10 h-10 text-slate-400" />}
        title="No active patients in Guardian Queue"
        description="All emergency department patients have been seen or disposed. Register a new walk-in or seed demo patients."
        actionText="Register Walk-in Patient"
        onAction={() => navigate('/register')}
      />
    );
  }

  const startIndex = (page - 1) * PAGE_SIZE;
  const pageEntries = entries.slice(startIndex, startIndex + PAGE_SIZE);

  return (
    <div className="space-y-3">
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
            DO NOT SORT ON THE CLIENT. Pagination below only slices this pre-sorted array -- it never reorders it.
          */}
          {pageEntries.map((entry, index) => (
            <QueueRow key={entry.case_id} entry={entry} index={startIndex + index} />
          ))}
        </TableBody>
      </Table>

      <Pagination
        page={page}
        pageCount={pageCount}
        onPageChange={setPage}
        totalCount={entries.length}
        pageSize={PAGE_SIZE}
      />
    </div>
  );
};
