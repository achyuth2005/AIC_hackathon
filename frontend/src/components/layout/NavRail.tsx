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
    <aside className="w-64 bg-slate-900/60 border-r border-slate-800/80 p-3 hidden md:flex flex-col justify-between shrink-0">
      <div className="space-y-1">
        <div className="px-3 py-2 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
          Navigation
        </div>
        {visibleItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all ${
                isActive
                  ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 shadow-sm font-semibold'
                  : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/60'
              }`
            }
          >
            <span className="shrink-0">{item.icon}</span>
            <span className="truncate">{item.label}</span>
          </NavLink>
        ))}
      </div>

      <div className="p-3 bg-slate-950/60 rounded-xl border border-slate-800/60 text-xs text-slate-400">
        <div className="font-semibold text-slate-300">Phase 13 MVP Engine</div>
        <div className="text-[11px] mt-0.5 text-slate-500">
          Deterministic NEWS2/PEWS + ML Challenger + 3× Surge Sim
        </div>
      </div>
    </aside>
  );
};
