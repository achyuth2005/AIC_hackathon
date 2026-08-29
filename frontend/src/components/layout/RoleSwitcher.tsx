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
    { role: 'NURSE', label: 'Nurse', name: 'Nurse Priya Nair', icon: <UserCheck className="w-4 h-4 text-cyan-400" /> },
    { role: 'DOCTOR', label: 'Doctor', name: 'Dr. Arjun Rao', icon: <Stethoscope className="w-4 h-4 text-emerald-400" /> },
    { role: 'ADMIN', label: 'Admin', name: 'Admin Sana Sheikh', icon: <Shield className="w-4 h-4 text-purple-400" /> },
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
        className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800/90 hover:bg-slate-700/90 border border-slate-700 text-xs text-slate-200 transition-colors cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
      >
        <span className="w-2 h-2 rounded-full bg-emerald-400 shrink-0" />
        <span className="font-medium text-slate-100">{user.display_name}</span>
        <span className="px-1.5 py-0.5 rounded bg-slate-900 text-slate-300 font-mono text-[10px] uppercase font-bold tracking-wider">
          {user.role}
        </span>
        <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
      </button>

      {isOpen && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setIsOpen(false)} />
          <div className="absolute right-0 mt-2 w-64 rounded-xl bg-slate-900 border border-slate-700/80 shadow-2xl p-2 z-50 animate-fade-in">
            <div className="px-3 py-2 text-[11px] font-semibold text-slate-400 uppercase tracking-wider border-b border-slate-800">
              Quick Role Switch (Demo)
            </div>
            <div className="py-1 space-y-1">
              {roles.map((r) => {
                const isActive = user.role === r.role;
                return (
                  <button
                    key={r.role}
                    onClick={() => handleSwitch(r.role)}
                    className={`w-full text-left px-3 py-2 rounded-lg flex items-center justify-between text-xs transition-colors cursor-pointer ${
                      isActive
                        ? 'bg-slate-800 text-cyan-300 font-medium'
                        : 'text-slate-300 hover:bg-slate-800/60 hover:text-slate-100'
                    }`}
                  >
                    <div className="flex items-center gap-2.5">
                      {r.icon}
                      <div>
                        <div>{r.label}</div>
                        <div className="text-[10px] text-slate-400">{r.name}</div>
                      </div>
                    </div>
                    {isActive && <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />}
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
