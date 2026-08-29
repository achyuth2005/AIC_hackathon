import React from 'react';
import { useHealth } from '../../hooks/useHealth';
import { AlertCircle, RefreshCw, Printer } from 'lucide-react';
import { Link } from 'react-router-dom';

export const ConnectionBanner: React.FC = () => {
  const { isError, isFetching, refetch } = useHealth();

  if (!isError) {
    return null;
  }

  return (
    <div
      role="alert"
      className="bg-rose-950/90 border-b border-rose-600/80 px-4 py-2.5 text-rose-100 flex flex-wrap items-center justify-between gap-3 text-sm backdrop-blur sticky top-0 z-50 animate-fade-in shadow-lg"
    >
      <div className="flex items-center gap-2.5">
        <AlertCircle className="w-5 h-5 text-rose-400 shrink-0 animate-pulse" />
        <div>
          <span className="font-semibold">Backend Disconnected:</span>{' '}
          Unable to reach FastAPI server at port 8000. Data shown may be stale.
        </div>
      </div>
      <div className="flex items-center gap-3">
        <Link
          to="/queue/printable"
          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-rose-900/60 hover:bg-rose-800 text-rose-200 hover:text-white border border-rose-700/60 text-xs font-medium transition-colors"
        >
          <Printer className="w-3.5 h-3.5" />
          Degraded Paper Queue
        </Link>
        <button
          onClick={() => refetch()}
          disabled={isFetching}
          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-rose-600 hover:bg-rose-500 active:bg-rose-700 text-white text-xs font-medium transition-colors disabled:opacity-50 cursor-pointer"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isFetching ? 'animate-spin' : ''}`} />
          Retry Connection
        </button>
      </div>
    </div>
  );
};
