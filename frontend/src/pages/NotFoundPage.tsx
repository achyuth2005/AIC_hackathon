import React from 'react';
import { Link } from 'react-router-dom';
import { AlertCircle, ArrowLeft } from 'lucide-react';
import { Button } from '../components/ui/Button';

export const NotFoundPage: React.FC = () => {
  return (
    <div className="min-h-[70vh] flex flex-col items-center justify-center text-center p-4">
      <div className="w-16 h-16 rounded-2xl bg-rose-950/60 border border-rose-800/80 flex items-center justify-center mb-4">
        <AlertCircle className="w-8 h-8 text-rose-400" />
      </div>
      <h1 className="text-3xl font-bold text-slate-100 mb-2">Page Not Found</h1>
      <p className="text-sm text-slate-400 max-w-md mb-6">
        The route you requested does not exist or has been moved.
      </p>
      <Link to="/queue">
        <Button leftIcon={<ArrowLeft className="w-4 h-4" />}>
          Return to Guardian Queue
        </Button>
      </Link>
    </div>
  );
};
