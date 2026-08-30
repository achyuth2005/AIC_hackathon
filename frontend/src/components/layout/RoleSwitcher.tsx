import React, { useState } from 'react';
import { useAuth } from '../../hooks/useAuth';
import { Role } from '../../types/enums';
import { ChevronDown, UserCheck, Stethoscope, Shield } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export const RoleSwitcher: React.FC = () => {
  const { user, login, isLoading } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const navigate = useNavigate();

  if (!user) return null;

  const roles: { role: Role; label: string; name: string; icon: React.ReactNode }[] = [
    { role: 'NURSE', label: 'Nurse', name: 'Nurse Priya Nair', icon: <UserCheck className="w-4 h-4 text-indigo-600" /> },
    { role: 'DOCTOR', label: 'Doctor', name: 'Dr. Arjun Rao', icon: <Stethoscope className="w-4 h-4 text-emerald-600" /> },
    { role: 'ADMIN', label: 'Admin', name: 'Admin Sana Sheikh', icon: <Shield className="w-4 h-4 text-purple-600" /> },
  ];

  const handleSwitch = async (role: Role) => {
    if (role === user.role) {
      setIsOpen(false);
      return;
    }
    setIsOpen(false);
    await login(role);
    if (role === 'NURSE') navigate('/queue');
    else if (role === 'DOCTOR') navigate('/doctor');
    else if (role === 'ADMIN') navigate('/admin');
  };

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={isLoading}
        className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/60 hover:bg-white/90 border border-white/80 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.8),0_2px_8px_rgba(0,0,0,0.03)] text-xs text-slate-700 backdrop-blur-md transition-all cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-indigo-400"
      >
        <span className="w-2 h-2 rounded-full bg-emerald-500 shrink-0" />
        <span className="font-medium text-slate-900">{user.display_name}</span>
        <span className="px-1.5 py-0.5 rounded-full bg-slate-500/10 text-slate-700 font-mono text-[10px] uppercase font-bold tracking-wider">
          {user.role}
        </span>
        <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
      </button>

      {isOpen && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setIsOpen(false)} />
          <div className="absolute right-0 mt-2 w-64 rounded-2xl bg-white/80 backdrop-blur-2xl border border-white/90 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.9),0_16px_40px_rgba(31,38,135,0.08)] p-2 z-50 animate-fade-in">
            <div className="px-3 py-2 text-[11px] font-semibold text-slate-400 uppercase tracking-wider border-b border-slate-100/60">
              Quick Role Switch (Demo)
            </div>
            <div className="py-1 space-y-1">
              {roles.map((r) => {
                const isActive = user.role === r.role;
                return (
                  <button
                    key={r.role}
                    onClick={() => handleSwitch(r.role)}
                    className={`w-full text-left px-3 py-2 rounded-xl flex items-center justify-between text-xs transition-all cursor-pointer ${
                      isActive
                        ? 'bg-indigo-500/15 text-indigo-900 font-semibold shadow-[inset_0_0_0_1px_rgba(99,102,241,0.2)]'
                        : 'text-slate-600 hover:bg-white/60 hover:text-slate-900'
                    }`}
                  >
                    <div className="flex items-center gap-2.5">
                      {r.icon}
                      <div>
                        <div>{r.label}</div>
                        <div className="text-[10px] text-slate-400">{r.name}</div>
                      </div>
                    </div>
                    {isActive && <span className="w-1.5 h-1.5 rounded-full bg-indigo-600" />}
                  </button>
                );
              })}
            </div>
          </div>
        </>
      )}
    </div>
  );
};
