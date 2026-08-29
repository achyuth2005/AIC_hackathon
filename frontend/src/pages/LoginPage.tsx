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
    <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-4 sm:p-6 relative overflow-hidden">
      {/* Background glowing gradients */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-cyan-600/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-indigo-600/10 rounded-full blur-3xl pointer-events-none" />

      <div className="w-full max-w-lg relative z-10 space-y-6">
        {/* Brand header */}
        <div className="text-center space-y-2">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-tr from-cyan-600 to-cyan-400 shadow-xl shadow-cyan-900/50 mb-2">
            <Activity className="w-8 h-8 text-slate-950 stroke-[2.5]" />
          </div>
          <h1 className="text-3xl font-extrabold tracking-tight text-slate-100">
            PatientTriage<span className="text-cyan-400">.ai</span>
          </h1>
          <p className="text-sm text-slate-400 max-w-md mx-auto">
            Emergency Department Triage & Guardian Reassessment Queue
          </p>
        </div>

        {/* Demo login card */}
        <div className="bg-slate-900/80 backdrop-blur-xl border border-slate-800 rounded-2xl p-6 shadow-2xl shadow-black/60">
          <h2 className="text-base font-semibold text-slate-100 mb-1 flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-cyan-400" />
            Select Demo Identity
          </h2>
          <p className="text-xs text-slate-400 mb-5">
            Choose a role to access the corresponding clinician surface with signed HS256 tokens.
          </p>

          <RoleSelector />
        </div>

        {/* Clinical Invariant Note */}
        <div className="flex items-start gap-2.5 p-3 rounded-xl bg-slate-900/40 border border-slate-800/60 text-xs text-slate-400">
          <ShieldAlert className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
          <div>
            <span className="text-slate-300 font-medium">Core Clinical Invariant:</span>{' '}
            Waiting does not make a patient sicker, but waiting makes the system look again. ML can only escalate; human de-escalation is strictly reason-gated.
          </div>
        </div>
      </div>
    </div>
  );
};
