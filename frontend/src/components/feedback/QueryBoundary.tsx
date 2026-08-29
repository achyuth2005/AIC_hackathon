import React from 'react';
import { Skeleton } from '../ui/Skeleton';
import { ErrorState } from '../ui/ErrorState';
import { EmptyState } from '../ui/EmptyState';

export interface QueryBoundaryProps<T> {
  isLoading: boolean;
  isError: boolean;
  error?: unknown;
  data?: T | null;
  onRetry?: () => void;
  isEmpty?: (data: T) => boolean;
  emptyTitle?: string;
  emptyDescription?: React.ReactNode;
  emptyActionText?: string;
  onEmptyAction?: () => void;
  loadingSkeleton?: React.ReactNode;
  children: React.ReactNode | ((data: T) => React.ReactNode);
}

export function QueryBoundary<T>({
  isLoading,
  isError,
  error,
  data,
  onRetry,
  isEmpty,
  emptyTitle = 'No data available',
  emptyDescription,
  emptyActionText,
  onEmptyAction,
  loadingSkeleton,
  children,
}: QueryBoundaryProps<T>): React.ReactElement {
  if (isLoading) {
    return (
      <>
        {loadingSkeleton || (
          <div className="space-y-3 p-4">
            <Skeleton className="h-8 w-1/3" />
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-24 w-full" />
          </div>
        )}
      </>
    );
  }

  if (isError) {
    return <ErrorState error={error} onRetry={onRetry} />;
  }

  if (data !== undefined && data !== null && isEmpty && isEmpty(data)) {
    return (
      <EmptyState
        title={emptyTitle}
        description={emptyDescription}
        actionText={emptyActionText}
        onAction={onEmptyAction}
      />
    );
  }

  if (typeof children === 'function' && data !== undefined && data !== null) {
    return <>{children(data)}</>;
  }

  return <>{children}</>;
}
