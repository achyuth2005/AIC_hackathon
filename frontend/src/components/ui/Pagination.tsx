import React from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { cn } from '../../lib/cn';

export interface PaginationProps {
  page: number;
  pageCount: number;
  onPageChange: (page: number) => void;
  totalCount: number;
  pageSize: number;
  className?: string;
}

/** Builds a compact page list like [1, '…', 4, 5, 6, '…', 12]. */
function buildPageList(page: number, pageCount: number): (number | '…')[] {
  const delta = 1;
  const pages: (number | '…')[] = [];
  const range: number[] = [];

  for (let i = Math.max(2, page - delta); i <= Math.min(pageCount - 1, page + delta); i++) {
    range.push(i);
  }

  pages.push(1);
  if (range[0] > 2) pages.push('…');
  pages.push(...range);
  if (range[range.length - 1] < pageCount - 1) pages.push('…');
  if (pageCount > 1) pages.push(pageCount);

  return pages;
}

export const Pagination: React.FC<PaginationProps> = ({
  page,
  pageCount,
  onPageChange,
  totalCount,
  pageSize,
  className,
}) => {
  if (pageCount <= 1) return null;

  const rangeStart = (page - 1) * pageSize + 1;
  const rangeEnd = Math.min(page * pageSize, totalCount);
  const pages = buildPageList(page, pageCount);

  return (
    <nav
      aria-label="Guardian Queue pagination"
      className={cn(
        'flex flex-col sm:flex-row items-center justify-between gap-3 px-2 py-1',
        className
      )}
    >
      <p className="text-xs text-slate-500 font-mono tabular-nums">
        Showing <span className="font-semibold text-slate-700">{rangeStart}-{rangeEnd}</span> of{' '}
        <span className="font-semibold text-slate-700">{totalCount}</span> patients
      </p>

      <div className="flex items-center gap-1">
        <button
          type="button"
          onClick={() => onPageChange(page - 1)}
          disabled={page === 1}
          aria-label="Previous page"
          className="p-1.5 rounded-xl bg-white/60 hover:bg-white/90 border border-white/80 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.8),0_1px_3px_rgba(0,0,0,0.02)] text-slate-600 disabled:opacity-40 disabled:hover:bg-white/60 backdrop-blur-sm cursor-pointer transition-all"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>

        {pages.map((p, i) =>
          p === '…' ? (
            <span key={`ellipsis-${i}`} className="px-1.5 text-xs text-slate-400 select-none">
              …
            </span>
          ) : (
            <button
              key={p}
              type="button"
              onClick={() => onPageChange(p)}
              aria-label={`Page ${p}`}
              aria-current={p === page ? 'page' : undefined}
              className={cn(
                'min-w-[2rem] h-8 px-2 rounded-xl text-xs font-mono font-semibold tabular-nums transition-all cursor-pointer',
                p === page
                  ? 'bg-gradient-to-r from-slate-900 to-indigo-950 text-white shadow-[0_2px_8px_rgba(15,23,42,0.15)]'
                  : 'text-slate-600 bg-white/50 hover:bg-white/80 border border-white/80 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.7)] backdrop-blur-sm'
              )}
            >
              {p}
            </button>
          )
        )}

        <button
          type="button"
          onClick={() => onPageChange(page + 1)}
          disabled={page === pageCount}
          aria-label="Next page"
          className="p-1.5 rounded-xl bg-white/60 hover:bg-white/90 border border-white/80 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.8),0_1px_3px_rgba(0,0,0,0.02)] text-slate-600 disabled:opacity-40 disabled:hover:bg-white/60 backdrop-blur-sm cursor-pointer transition-all"
        >
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>
    </nav>
  );
};
