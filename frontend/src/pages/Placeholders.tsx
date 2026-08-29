import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card';

export const AmbulancePage: React.FC = () => (
  <div className="space-y-4">
    <h1 className="text-2xl font-bold text-slate-100">Ambulance Inbound Board</h1>
    <Card><CardHeader><CardTitle>Pre-Arrival Transports</CardTitle></CardHeader><CardContent><p className="text-sm text-slate-400">Implemented in Checkpoint 9.</p></CardContent></Card>
  </div>
);

export const AmbulanceCasePage: React.FC = () => (
  <div className="space-y-4">
    <h1 className="text-2xl font-bold text-slate-100">Ambulance Pre-Alert</h1>
    <Card><CardHeader><CardTitle>Inbound Paramedic Vitals & ETA</CardTitle></CardHeader><CardContent><p className="text-sm text-slate-400">Implemented in Checkpoint 9.</p></CardContent></Card>
  </div>
);

export const PatientPage: React.FC = () => (
  <div className="min-h-screen bg-slate-950 text-slate-100 p-6 flex flex-col items-center justify-center">
    <div className="max-w-md w-full bg-slate-900 border border-slate-800 p-6 rounded-2xl">
      <h1 className="text-xl font-bold">Public Patient View</h1>
      <p className="text-sm text-slate-400 mt-2">Implemented in Checkpoint 8.</p>
    </div>
  </div>
);

export const AdminPage: React.FC = () => (
  <div className="space-y-4">
    <h1 className="text-2xl font-bold text-slate-100">Admin Governance & Equity</h1>
    <Card><CardHeader><CardTitle>Override Review & Subgroup Monitoring</CardTitle></CardHeader><CardContent><p className="text-sm text-slate-400">Implemented in Checkpoint 10.</p></CardContent></Card>
  </div>
);

export const DemoPage: React.FC = () => (
  <div className="space-y-4">
    <h1 className="text-2xl font-bold text-slate-100">Demo Console & Surge Sim</h1>
    <Card><CardHeader><CardTitle>20 Scenarios & Surge Controls</CardTitle></CardHeader><CardContent><p className="text-sm text-slate-400">Implemented in Checkpoint 10.</p></CardContent></Card>
  </div>
);


