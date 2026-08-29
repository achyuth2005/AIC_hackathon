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
    <header className="h-16 bg-slate-900/90 backdrop-blur border-b border-slate-800 px-4 sm:px-6 flex items-center justify-between sticky top-0 z-30">
      <div className="flex items-center gap-4">
        <Link to="/" className="flex items-center gap-3 group">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-cyan-600 to-cyan-400 flex items-center justify-center shadow-md shadow-cyan-900/40 group-hover:scale-105 transition-transform">
            <Activity className="w-5 h-5 text-slate-950 font-bold" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold tracking-tight text-slate-100 text-base">
                PatientTriage<span className="text-cyan-400">.ai</span>
              </span>
              <span className="text-[10px] uppercase tracking-wider font-bold bg-cyan-950/80 text-cyan-400 border border-cyan-800/60 px-1.5 py-0.5 rounded">
                Guardian ED
              </span>
            </div>
            <div className="text-[11px] text-slate-400 hidden sm:block">
              Emergency Department Triage & Time Engine
            </div>
          </div>
        </Link>

        {/* Live status dot */}
        <div
          className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-800/80 border border-slate-700/60 text-[11px]"
          title={isError ? 'Backend Disconnected' : 'Connected to FastAPI Backend'}
        >
          <span
            className={`w-2 h-2 rounded-full ${
              isError ? 'bg-rose-500 animate-pulse' : 'bg-emerald-400'
            }`}
          />
          <span className="text-slate-300 font-mono">
            {isError ? 'OFFLINE' : 'LIVE :8000'}
          </span>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <Link
          to="/demo"
          className="hidden lg:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-950/60 hover:bg-indigo-900/80 text-indigo-300 hover:text-indigo-100 border border-indigo-800/50 text-xs font-semibold transition-colors"
        >
          <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
          Demo & Surge
        </Link>

        <Link
          to="/queue/printable"
          title="Printable degraded paper snapshot"
          className="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-slate-100 border border-slate-700 text-xs transition-colors"
        >
          <Printer className="w-3.5 h-3.5 text-slate-400" />
          <span className="hidden md:inline">Paper Snapshot</span>
        </Link>

        {isAuthenticated && user && (
          <>
            <div className="h-5 w-px bg-slate-800 hidden sm:block" />
            <RoleSwitcher />
            <button
              onClick={handleLogout}
              title="Log out (clear demo session)"
              className="p-2 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-slate-800/80 transition-colors cursor-pointer"
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
