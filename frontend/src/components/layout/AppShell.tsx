import React from 'react';
import { Header } from './Header';
import { NavRail } from './NavRail';
import { ConnectionBanner } from '../feedback/ConnectionBanner';

interface AppShellProps {
  children: React.ReactNode;
}

export const AppShell: React.FC<AppShellProps> = ({ children }) => {
  return (
    <div className="min-h-screen flex flex-col bg-transparent text-slate-900 selection:bg-indigo-100 selection:text-indigo-900">
      <ConnectionBanner />
      <Header />
      <div className="flex-1 flex overflow-hidden print:overflow-visible print:block">
        <NavRail />
        <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto print:overflow-visible print:p-0 print:max-w-none">
          {children}
        </main>
      </div>
    </div>
  );
};
