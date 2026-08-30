import React, { useEffect } from 'react';
import { RoleSelector } from '../features/auth/RoleSelector';
import { useAuth } from '../hooks/useAuth';
import { useNavigate } from 'react-router-dom';
import { Activity, ShieldAlert, Sparkles } from 'lucide-react';

export const LoginPage: React.FC = () => {
  const { isAuthenticated, user } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (isAuthenticated && user) {
      if (user.role === 'NURSE') navigate('/queue');
      else if (user.role === 'DOCTOR') navigate('/doctor');
      else if (user.role === 'ADMIN') navigate('/admin');
    }
  }, [isAuthenticated, user, navigate]);

  return (
    <div className="min-h-screen bg-transparent flex flex-col items-center justify-center p-4 sm:p-6 relative overflow-hidden">
      {/* Background subtle decorative blobs */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-indigo-100/40 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-indigo-100/40 rounded-full blur-3xl pointer-events-none" />

      <div className="w-full max-w-lg relative z-10 space-y-6">
        {/* Brand header */}
        <div className="text-center space-y-2">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-tr from-indigo-600 to-indigo-500 shadow-xl shadow-indigo-900/10 mb-2">
            <Activity className="w-8 h-8 text-white stroke-[2.5]" />
          </div>
          <h1 className="text-3xl font-extrabold tracking-tight text-slate-900">
            PatientTriage<span className="text-indigo-600">.ai</span>
          </h1>
          <p className="text-sm text-slate-500 max-w-md mx-auto">
            Emergency Department Triage & Guardian Reassessment Queue
          </p>
        </div>

        {/* Demo login card */}
        <div className="bg-white/65 backdrop-blur-xl border border-white/80 rounded-3xl p-6 sm:p-8 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.9),0_16px_48px_rgba(31,38,135,0.06)]">
          <h2 className="text-base font-semibold text-slate-900 mb-1 flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-indigo-600" />
            Select Demo Identity
          </h2>
          <p className="text-xs text-slate-500 mb-5">
            Choose a role to access the corresponding clinician surface with signed HS256 tokens.
          </p>

          <RoleSelector />
        </div>

        {/* Clinical Invariant Note */}
        <div className="flex items-start gap-2.5 p-3.5 rounded-2xl bg-white/50 backdrop-blur-md border border-white/80 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.8),0_2px_8px_rgba(31,38,135,0.02)] text-xs text-slate-500">
          <ShieldAlert className="w-4 h-4 text-indigo-600 shrink-0 mt-0.5" />
          <div>
            <span className="text-slate-700 font-semibold">Core Clinical Invariant:</span>{' '}
            Waiting does not make a patient sicker, but waiting makes the system look again. ML can only escalate; human de-escalation is strictly reason-gated.
          </div>
        </div>
      </div>
    </div>
  );
};
