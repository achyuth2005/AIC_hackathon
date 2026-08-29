import React from 'react';
import { Header } from './Header';
import { NavRail } from './NavRail';
import { ConnectionBanner } from '../feedback/ConnectionBanner';

interface AppShellProps {
  children: React.ReactNode;
}

export const AppShell: React.FC<AppShellProps> = ({ children }) => {
  return (
    <div className="min-h-screen flex flex-col bg-slate-950 text-slate-100 selection:bg-cyan-500/30 selection:text-cyan-200">
      <ConnectionBanner />
      <Header />
      <div className="flex-1 flex overflow-hidden">
        <NavRail />
        <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto">
          {children}
        </main>
      </div>
    </div>
  );
};
