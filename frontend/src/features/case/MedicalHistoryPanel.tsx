import React from 'react';
import { Card } from '../../components/ui/Card';
import { Stethoscope } from 'lucide-react';

interface MedicalHistoryPanelProps {
  medicalHistory: string | null;
}

export const MedicalHistoryPanel: React.FC<MedicalHistoryPanelProps> = ({ medicalHistory }) => {
  const hasHistory = Boolean(medicalHistory && medicalHistory.trim().length > 0);

  // Parse comma-separated string into a list for tabular display, if present
  const historyItems = hasHistory
    ? medicalHistory!
        .split(',')
        .map((item) => item.trim())
        .filter((item) => item.length > 0)
    : [];

  return (
    <Card className="flex flex-col border-slate-200 shadow-sm">
      <div className="flex items-center gap-2 border-b border-slate-100 bg-slate-50/50 p-4">
        <Stethoscope className="w-5 h-5 text-indigo-600" />
        <h2 className="text-sm font-bold text-slate-800 tracking-tight uppercase">
          Patient Medical History
        </h2>
      </div>

      <div className="p-4">
        {hasHistory ? (
          <div className="overflow-hidden rounded-lg border border-slate-200">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50">
                <tr>
                  <th scope="col" className="px-4 py-3 text-left font-semibold text-slate-700">
                    Condition / Comorbidity
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 bg-white">
                {historyItems.map((condition, index) => (
                  <tr key={index} className="hover:bg-slate-50/50 transition-colors">
                    <td className="px-4 py-3 whitespace-normal text-slate-700 font-medium flex items-center gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-amber-400 shrink-0" />
                      {condition}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="flex items-center justify-center p-8 bg-slate-50 rounded-lg border border-dashed border-slate-200">
            <span className="text-sm font-medium italic text-slate-500">
              No known medical history recorded for this patient.
            </span>
          </div>
        )}
      </div>
    </Card>
  );
};
