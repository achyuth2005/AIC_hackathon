import React from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import {
  ListOrdered,
  UserPlus,
  Stethoscope,
  LayoutDashboard,
  Bell,
  Truck,
  Layers,
  ShieldAlert,
  Sparkles,
  Palette,
} from 'lucide-react';
import { Role } from '../../types/enums';

interface NavItem {
  to: string;
  label: string;
  icon: React.ReactNode;
  roles?: Role[];
  badge?: string;
}

export const NavRail: React.FC = () => {
  const { hasRole } = useAuth();

  const navItems: NavItem[] = [
    {
      to: '/queue',
      label: 'Guardian Queue',
      icon: <ListOrdered className="w-5 h-5" />,
      roles: ['NURSE', 'DOCTOR', 'ADMIN'],
    },
    {
      to: '/register',
      label: 'New Walk-In',
      icon: <UserPlus className="w-5 h-5" />,
      roles: ['NURSE', 'ADMIN'],
    },
    {
      to: '/doctor',
      label: 'Doctor Worklist',
      icon: <Stethoscope className="w-5 h-5" />,
      roles: ['DOCTOR', 'ADMIN', 'NURSE'],
    },
    {
      to: '/control-tower',
      label: 'Control Tower',
      icon: <LayoutDashboard className="w-5 h-5" />,
      roles: ['NURSE', 'DOCTOR', 'ADMIN'],
    },
    {
      to: '/alerts',
      label: 'Alerts & Budget',
      icon: <Bell className="w-5 h-5" />,
      roles: ['NURSE', 'DOCTOR', 'ADMIN'],
    },
    {
      to: '/ambulance',
      label: 'Ambulance Pre-Alert',
      icon: <Truck className="w-5 h-5" />,
      roles: ['NURSE', 'ADMIN', 'DOCTOR'],
    },
    {
      to: '/ops',
      label: 'Ops & Resources',
      icon: <Layers className="w-5 h-5" />,
      roles: ['NURSE', 'DOCTOR', 'ADMIN'],
    },
    {
      to: '/admin',
      label: 'Audit & Equity',
      icon: <ShieldAlert className="w-5 h-5" />,
      roles: ['ADMIN'],
    },
    {
      to: '/demo',
      label: 'Demo & Surge',
      icon: <Sparkles className="w-5 h-5" />,
      roles: ['ADMIN', 'NURSE', 'DOCTOR'],
    },
    {
      to: '/styleguide',
      label: 'Styleguide',
      icon: <Palette className="w-5 h-5" />,
      roles: ['ADMIN', 'NURSE', 'DOCTOR'],
    },
  ];

  const visibleItems = navItems.filter((item) => {
    if (!item.roles) return true;
    return hasRole(...item.roles);
  });

  return (
    <aside className="w-64 bg-white/60 backdrop-blur-xl border-r border-white/80 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.7),0_8px_32px_rgba(31,38,135,0.03)] p-3 hidden md:flex flex-col justify-between shrink-0 print:hidden">
      <div className="space-y-1">
        <div className="px-3 py-2 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
          Navigation
        </div>
        {visibleItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 text-sm font-medium transition-all ${
                isActive
                  ? 'bg-white/75 text-indigo-700 font-semibold shadow-[inset_0_0_0_1px_rgba(255,255,255,0.9),0_4px_16px_rgba(79,70,229,0.06)] border-l-[3.5px] border-indigo-600 rounded-r-xl rounded-l-sm backdrop-blur-md'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-white/40 border-l-[3.5px] border-transparent rounded-r-xl rounded-l-sm'
              }`
            }
          >
            <span className="shrink-0">{item.icon}</span>
            <span className="truncate">{item.label}</span>
          </NavLink>
        ))}
      </div>

      <div className="p-3 bg-white/40 backdrop-blur-md rounded-xl border border-white/60 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.8),0_2px_8px_rgba(31,38,135,0.02)] text-xs text-slate-500">
        <div className="font-semibold text-slate-600">Phase 13 MVP Engine</div>
        <div className="text-[11px] mt-0.5 text-slate-400">
          Deterministic NEWS2/PEWS + ML Challenger + 3× Surge Sim
        </div>
      </div>
    </aside>
  );
};
