import { http } from '../lib/http';
import { PatientCaseView, CaseResponse } from '../types/api';

export const patientApi = {
  getPatientView: (caseId: string) =>
    http.get<PatientCaseView>(`/cases/${caseId}/patient-view`),

  reportWorsening: (caseId: string, note?: string) =>
    http.post<CaseResponse>(`/cases/${caseId}/self-reported-worsening`, {
      note: note || 'Patient self-reported feeling worse via kiosk / waiting room app.',
    }),
};
