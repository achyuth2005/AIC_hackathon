import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { queueApi } from '../api/queue';
import { useProfile } from '../contexts/ProfileContext';
import { Skeleton } from '../components/ui/Skeleton';
import { ErrorState } from '../components/ui/ErrorState';
import { Button } from '../components/ui/Button';
import { Printer, ArrowLeft } from 'lucide-react';

/**
 * Phase 9.5 "degraded mode" paper snapshot, rendered inside the app.
 *
 * The backend's GET /queue/printable requires the same staff bearer token
 * every other PHI view does, so this can't just be a plain <a href> --
 * a raw browser navigation wouldn't carry the Authorization header and
 * would 401. Instead we fetch it with the authenticated http client (same
 * as the rest of the app) and render the resulting plain-text snapshot
 * verbatim, monospaced, so it prints exactly as the fallback form is meant
 * to look with nothing else on the page.
 */
export const PrintableQueuePage: React.FC = () => {
  const { hospitalProfileId } = useProfile();

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['queue-printable', hospitalProfileId],
    queryFn: () => queueApi.getPrintableQueue(hospitalProfileId),
    staleTime: 0,
    retry: 1,
  });

  return (
    <div className="max-w-4xl mx-auto space-y-4 pb-12 animate-fade-in">
      <div className="flex items-center justify-between gap-3 print:hidden">
        <Link
          to="/queue"
          className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-800 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Guardian Queue
        </Link>

        <Button
          variant="primary"
          size="sm"
          leftIcon={<Printer className="w-4 h-4" />}
          onClick={() => window.print()}
          disabled={isLoading || isError}
        >
          Print
        </Button>
      </div>

      {isLoading ? (
        <div className="space-y-3 p-6 rounded-xl bg-white border border-slate-200 shadow-card">
          <Skeleton className="h-6 w-full" />
          <Skeleton className="h-40 w-full" />
        </div>
      ) : isError ? (
        <ErrorState
          title="Failed to load printable snapshot"
          error={error}
          onRetry={() => refetch()}
        />
      ) : (
        <pre className="whitespace-pre overflow-x-auto rounded-xl border border-slate-200 bg-white p-6 text-xs leading-relaxed font-mono text-slate-800 print:border-none print:p-0 print:text-black">
          {data}
        </pre>
      )}
    </div>
  );
};
