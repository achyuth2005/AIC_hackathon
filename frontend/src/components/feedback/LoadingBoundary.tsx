import React from 'react';
import { Spinner } from '../ui/Spinner';

export interface LoadingBoundaryProps {
  isLoading: boolean;
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

export const LoadingBoundary: React.FC<LoadingBoundaryProps> = ({
  isLoading,
  children,
  fallback,
}) => {
  if (isLoading) {
    return (
      fallback || (
        <div className="flex items-center justify-center p-12">
          <Spinner size="lg" />
        </div>
      )
    );
  }

  return <>{children}</>;
};
