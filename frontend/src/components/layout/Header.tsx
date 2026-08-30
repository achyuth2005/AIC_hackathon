import React from 'react';
import { useAuth } from '../../hooks/useAuth';
import { useHealth } from '../../hooks/useHealth';
import { RoleSwitcher } from './RoleSwitcher';
import { LogOut, Activity, Printer, Sparkles } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';

export const Header: React.FC = () => {
  const { user, logout, isAuthenticated } = useAuth();
  const { isError } = useHealth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <header className="h-16 bg-white/65 backdrop-blur-xl border-b border-white/80 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.6),0_8px_32px_rgba(31,38,135,0.03)] px-4 sm:px-6 flex items-center justify-between sticky top-0 z-30 print:hidden">
      <div className="flex items-center gap-4">
        <Link to="/" className="flex items-center gap-3 group">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 to-indigo-500 flex items-center justify-center shadow-md shadow-indigo-900/10 group-hover:scale-105 transition-transform">
            <Activity className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold tracking-tight text-slate-900 text-base">
                PatientTriage<span className="text-indigo-600">.ai</span>
              </span>
              <span className="text-[10px] uppercase tracking-wider font-bold bg-indigo-500/10 text-indigo-700 border border-indigo-200/40 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.7)] px-1.5 py-0.5 rounded-full">
                Guardian ED
              </span>
            </div>
            <div className="text-[11px] text-slate-500 hidden sm:block">
              Emergency Department Triage & Time Engine
            </div>
          </div>
        </Link>

        {/* Live status dot */}
        <div
          className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white/60 backdrop-blur-md border border-white/80 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.8),0_2px_8px_rgba(31,38,135,0.03)] text-[11px]"
          title={isError ? 'Backend Disconnected' : 'Connected to FastAPI Backend'}
        >
          <span
            className={`w-2 h-2 rounded-full ${
              isError ? 'bg-rose-500 animate-pulse' : 'bg-emerald-500'
            }`}
          />
          <span className="text-slate-500 font-mono">
            {isError ? 'Offline' : 'Live 3s sweep'}
          </span>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <Link
          to="/demo"
          className="hidden lg:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-500/10 hover:bg-indigo-500/15 text-indigo-700 border border-indigo-200/40 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.8)] text-xs font-semibold backdrop-blur-sm transition-all"
        >
          <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
          Demo & Surge
        </Link>

        <Link
          to="/queue/printable"
          title="Printable degraded paper snapshot"
          className="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-white/60 hover:bg-white/90 text-slate-700 border border-white/80 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.8),0_2px_6px_rgba(0,0,0,0.03)] text-xs font-medium backdrop-blur-sm transition-all"
        >
          <Printer className="w-3.5 h-3.5 text-slate-500" />
          <span className="hidden md:inline">Print Paper Snapshot</span>
        </Link>

        {isAuthenticated && user && (
          <>
            <div className="h-5 w-px bg-slate-200/60 hidden sm:block" />
            <RoleSwitcher />
            <button
              onClick={handleLogout}
              title="Log out (clear demo session)"
              className="p-2 rounded-lg text-slate-500 hover:text-rose-600 hover:bg-white/60 transition-colors cursor-pointer"
              aria-label="Log out"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </>
        )}
      </div>
    </header>
  );
};
