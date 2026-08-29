import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { ProfileProvider } from './contexts/ProfileContext';
import { ToastProvider } from './components/ui/Toast';
import { AppShell } from './components/layout/AppShell';

// Pages
import { LoginPage } from './pages/LoginPage';
import { QueuePage } from './pages/QueuePage';
import { NotFoundPage } from './pages/NotFoundPage';
import { StyleGuidePage } from './pages/StyleGuidePage';
import { RegisterPage } from './pages/RegisterPage';
import { CaseDetailPage } from './pages/CaseDetailPage';
import { OpsPage } from './pages/OpsPage';
import { DoctorListPage } from './pages/DoctorListPage';
import { DoctorCasePage } from './pages/DoctorCasePage';
import { ControlTowerPage } from './pages/ControlTowerPage';
import { AlertsPage } from './pages/AlertsPage';
import { AmbulancePage } from './pages/AmbulancePage';
import { AmbulanceCasePage } from './pages/AmbulanceCasePage';
import { PatientPage } from './pages/PatientPage';
import { AdminPage } from './pages/AdminPage';
import { DemoPage } from './pages/DemoPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 0,
    },
  },
});

const ProtectedLayout: React.FC = () => {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="w-8 h-8 rounded-full border-2 border-cyan-500/30 border-t-cyan-500 animate-spin" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<Navigate to="/queue" replace />} />
        <Route path="/queue" element={<QueuePage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/cases/:caseId" element={<CaseDetailPage />} />
        <Route path="/doctor" element={<DoctorListPage />} />
        <Route path="/doctor/:caseId" element={<DoctorCasePage />} />
        <Route path="/control-tower" element={<ControlTowerPage />} />
        <Route path="/ops" element={<OpsPage />} />
        <Route path="/alerts" element={<AlertsPage />} />
        <Route path="/ambulance" element={<AmbulancePage />} />
        <Route path="/ambulance/:caseId" element={<AmbulanceCasePage />} />
        <Route path="/admin" element={<AdminPage />} />
        <Route path="/demo" element={<DemoPage />} />
        <Route path="/styleguide" element={<StyleGuidePage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </AppShell>
  );
};

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <ProfileProvider>
        <AuthProvider>
          <ToastProvider>
            <BrowserRouter>
              <Routes>
                {/* Public unauthenticated routes outside AppShell */}
                <Route path="/login" element={<LoginPage />} />
                <Route path="/patient/:caseId" element={<PatientPage />} />
                
                {/* Authenticated application routes */}
                <Route path="/*" element={<ProtectedLayout />} />
              </Routes>
            </BrowserRouter>
          </ToastProvider>
        </AuthProvider>
      </ProfileProvider>
    </QueryClientProvider>
  );
};
export default App;
