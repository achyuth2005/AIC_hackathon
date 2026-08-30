import React from 'react';
import { RegisterCaseForm } from '../features/registration/RegisterCaseForm';
import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';

export const RegisterPage: React.FC = () => {
  return (
    <div className="space-y-6 pb-12">
      <div className="flex items-center justify-between max-w-2xl mx-auto">
        <Link
          to="/queue"
          className="inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-indigo-600 font-medium transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Guardian Queue
        </Link>
      </div>

      <RegisterCaseForm />
    </div>
  );
};
