import { http } from '../lib/http';
import {
  DoctorCaseView,
  DoctorQueueItemResponse,
  DoctorCaseDetailResponse,
  CaseResponse,
} from '../types/api';
import { QueueEntry } from '../types/api';

export const doctorApi = {
  getDoctorQueue: async (hospitalProfileId = 'default'): Promise<DoctorQueueItemResponse[]> => {
    // Fetch queue entries and enrich with doctor view metrics.
    // Bug fix: GET /queue now requires an authenticated staff token.
    const queue = await http.get<QueueEntry[]>('/queue', {
      params: { hospital_profile_id: hospitalProfileId },
      auth: true,
    });

    return queue.map((entry) => ({
      case_id: entry.case_id,
      display_name: entry.display_name,
      mrn: entry.mrn,
      age_years: null,
      sex: null,
      final_acuity: entry.final_acuity,
      acuity_trend: entry.deterioration_trend,
      arrival_time: entry.arrival_time,
      waiting_minutes: entry.waiting_minutes,
      time_in_current_band_minutes: entry.time_in_current_band_minutes,
      assigned_resource_label: null,
      unreviewed_results_count: entry.primary_attention_flag === 'REASSESSMENT_OVERDUE' ? 1 : 0,
      stuck_flagged: entry.primary_attention_flag === 'DETERIORATING',
      stuck_reasons: entry.primary_attention_flag ? [entry.primary_attention_flag] : [],
      recent_vital_summary: {},
    }));
  },

  getDoctorCaseView: (caseId: string) =>
    http.get<DoctorCaseView>(`/cases/${caseId}/doctor-view`, { auth: true }),

  markCaseReviewed: (caseId: string) =>
    http.post<CaseResponse>(`/cases/${caseId}/mark-reviewed`, {}, { auth: true }),

  getDoctorCaseDetail: async (caseId: string): Promise<DoctorCaseDetailResponse> => {
    // Fetches doctor view authenticated and structures for DoctorCaseView UI
    const docView = await http.get<DoctorCaseView>(`/cases/${caseId}/doctor-view`, {
      auth: true,
    });

    const acuity = docView.latest_risk_assessment?.final_acuity || 3;
    const band = docView.latest_risk_assessment?.confidence_band || 'MEDIUM';
    const layer = docView.latest_risk_assessment?.deciding_layer || 'RULES';

    return {
      case_id: docView.case_id,
      patient_summary: {
        display_name: docView.display_name,
        mrn: null,
        age_years: null,
        sex: null,
        waiting_minutes: 15,
        assigned_resource_label: null,
        medical_history: docView.medical_history,
      },
      acuity_summary: {
        final_acuity: acuity,
        confidence_band: band,
        deciding_layer: layer,
      },
      unreviewed_tests: docView.pending_actions
        .filter((a) => a.kind === 'RESULT_AWAITING_REVIEW')
        .map((a) => ({
          test_id: a.reference_id,
          case_id: docView.case_id,
          test_type: a.description,
          status: 'RESULT_AVAILABLE' as const,
          ordered_at: new Date().toISOString(),
          sample_collected_at: null,
          result_available_at: new Date().toISOString(),
          result_reviewed_at: null,
          stuck_flagged: false,
        })),
      vital_trends: docView.trends.map((t) => ({
        concept_code: t.concept_code,
        latest_value: t.current_value,
        previous_value: t.previous_value,
        trend_direction:
          t.delta == null ? 'STABLE' : t.delta > 0 ? 'WORSENING' : 'IMPROVING',
        unit: null,
      })),
      stuck_status: {
        stuck_flagged: docView.pending_actions.length > 0,
        stuck_reasons: docView.pending_actions.map((p) => p.description),
      },
    };
  },
};
