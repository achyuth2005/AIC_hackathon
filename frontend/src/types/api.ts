import {
  Role,
  ArrivalMode,
  CaseStatus,
  IdentityLinkStatus,
  EmergencyBypassSource,
  DecidingLayer,
  ConfidenceBand,
  DeteriorationTrend,
  PrimaryAttentionFlag,
  ObservationValueType,
  ObservationSourceType,
  ReliabilityTier,
  MeasurementStatus,
  ClinicianAction,
  DeEscalationReasonCode,
  AlertType,
  AlertDismissalReasonCode,
  ResourceType,
  ResourceStatus,
  DiagnosticTestStatus,
  StuckPatternId,
  StuckRouteTo,
  PatientStage,
} from './enums';

// Auth
export interface LoginRequest {
  role: Role;
}

export interface DemoUser {
  user_id: string;
  display_name: string;
  role: Role;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: DemoUser;
}

// Cases
export interface CaseResponse {
  case_id: string;
  hospital_profile_id: string;
  mrn: string | null;
  display_name: string | null;
  date_of_birth: string | null; // YYYY-MM-DD
  age_years: number | null;
  sex: string | null;
  // Medical History feature: free-text past medical history (e.g. "COPD,
  // Type 2 Diabetes"). null/empty means none recorded -- render an
  // explicit "No known medical history" state rather than leaving blank.
  medical_history: string | null;
  arrival_mode: ArrivalMode;
  status: CaseStatus;
  identity_link_status: IdentityLinkStatus;
  created_at: string; // naive UTC
  arrived_at: string | null;
  emergency_bypass_active: boolean;
  emergency_bypass_first_activated_at: string | null;
  emergency_bypass_last_activated_at: string | null;
  emergency_bypass_last_reason: string | null;
  emergency_bypass_last_source: EmergencyBypassSource | null;
  emergency_bypass_last_trigger_id: string | null;
  last_reassessed_at: string | null;
  reassessment_overdue: boolean;
  reassessment_overdue_since: string | null;
  candidate_mrn?: string | null;
  candidate_display_name?: string | null;
  candidate_confidence?: number | null;
}

export interface CaseCreateRequest {
  hospital_profile_id?: string;
  mrn?: string | null;
  display_name?: string | null;
  date_of_birth?: string | null;
  age_years?: number | null;
  sex?: string | null;
  medical_history?: string | null;
  arrival_mode?: ArrivalMode;
  estimated_transport_minutes?: number | null;
}

export interface CaseDetailResponse extends CaseResponse {
  current_observations: ObservationResponse[];
  latest_risk_assessment: RiskAssessmentResponse | null;
  wait_time_estimate: WaitTimeEstimate | null;
}

// Observations
export interface ObservationResponse {
  observation_id: string;
  case_id: string;
  concept_code: string;
  value_type: ObservationValueType;
  value: number | boolean | string | null;
  unit: string | null;
  source_type: ObservationSourceType;
  source_id: string | null;
  reliability_tier: ReliabilityTier;
  measurement_status: MeasurementStatus;
  observed_at: string;
  recorded_at: string;
  extraction_confidence: number | null;
  superseded_by: string | null;
  is_current: boolean;
}

export interface ObservationCreateRequest {
  concept_code: string;
  value?: number | boolean | string | null;
  value_type: ObservationValueType;
  unit?: string | null;
  source_type: ObservationSourceType;
  source_id?: string | null;
  reliability_tier: ReliabilityTier;
  measurement_status: MeasurementStatus;
  observed_at: string;
  extraction_confidence?: number | null;
}

// Risk Assessments & Scoring
export interface ScoreComponent {
  concept_code: string;
  label: string;
  raw_value: number | boolean | string | null;
  unit: string | null;
  points: number | null;
  is_missing: boolean;
  missing_reason: string | null;
  observation_id: string | null;
  observed_at: string | null;
  reliability_tier: ReliabilityTier | null;
}

export interface HardTriggerResult {
  trigger_id: string;
  label: string;
  concept_code: string;
  raw_value: number | boolean | string | null;
  target_esi_level: number;
}

export interface RiskAssessmentResponse {
  assessment_id: string;
  case_id: string;
  computed_at: string;
  rule_engine_version: string;
  rule_acuity: number;
  rule_component_breakdown: ScoreComponent[];
  ml_model_version: string | null;
  ml_probability: number | null;
  ml_suggested_acuity: number | null;
  hard_triggers_fired: HardTriggerResult[];
  final_acuity: number;
  deciding_layer: DecidingLayer;
  confidence_band: ConfidenceBand;
  confidence_score: number;
  confidence_reasons: string[];
  should_abstain: boolean;
  abstention_message: string | null;
  input_snapshot_hash: string;
  input_observation_ids: string[];
}

// Wait Time
export interface WaitTimeEstimate {
  lower_minutes: number;
  upper_minutes: number;
  patients_ahead: number;
  available_capacity: number;
  basis: 'BAND_HISTORY' | 'GLOBAL_HISTORY' | 'CONFIGURED_DEFAULT';
  sample_size: number;
  caveat: string;
}

// Queue
export interface QueueEntry {
  case_id: string;
  display_name: string | null;
  mrn: string | null;
  final_acuity: number;
  confidence_band: ConfidenceBand | null;
  should_abstain: boolean;
  time_critical_pathway_flag: boolean;
  deterioration_trend: DeteriorationTrend;
  time_in_current_band_minutes: number | null;
  arrival_time: string;
  waiting_minutes: number;
  reassessment: {
    is_due: boolean;
    interval_minutes: number | null;
    minutes_since_last_reassessment: number;
    minutes_overdue: number | null;
  };
  emergency_bypass_active: boolean;
  wait_time_estimate: WaitTimeEstimate;
  one_line_presentation: string | null;
  primary_attention_flag: PrimaryAttentionFlag;
  stage?: PatientStage;
  arrival_mode?: ArrivalMode;
  identity_link_status?: IdentityLinkStatus;
}

// Decisions & Overrides
export interface OverrideRequest {
  action: ClinicianAction;
  target_acuity?: number | null;
  reason_code?: DeEscalationReasonCode | null;
  free_text_reason?: string | null;
}

export interface HumanDecisionResponse {
  decision_id: string;
  case_id: string;
  clinician_id: string;
  role: string;
  timestamp: string;
  system_recommendation: number;
  clinician_action: ClinicianAction;
  resulting_acuity: number;
  reason_code: DeEscalationReasonCode | null;
  free_text_reason: string | null;
  linked_assessment_id: string;
  flagged_for_review: boolean;
}

// Alerts
export interface CriticalBypassPayload {
  case_id: string;
  source: EmergencyBypassSource | null;
  reason: string | null;
}

export interface AcuityBandCrossedPayload {
  case_id: string;
  from_acuity: number;
  to_acuity: number;
  assessment_id: string;
}

export interface ReassessmentOverdueAggregatePayload {
  case_ids: string[];
  count: number;
}

export interface AlertResponse {
  alert_id: string;
  hospital_profile_id: string;
  alert_type: AlertType;
  created_at: string;
  payload: Record<string, unknown>;
  dismissed: boolean;
  dismissed_at: string | null;
  dismissed_by: string | null;
  dismissal_reason_code: AlertDismissalReasonCode | null;
  dismissal_free_text: string | null;
}

export interface AlertDismissRequest {
  reason_code: AlertDismissalReasonCode;
  free_text_reason?: string | null;
}

export interface AlertBudgetReport {
  window_minutes: number;
  nurses_on_shift: number;
  interruptive_alerts_in_window: number;
  alerts_per_nurse_per_hour: number;
  target_alerts_per_nurse_per_hour: number | null;
  within_budget: boolean | null;
  breakdown_by_type: Record<string, number>;
}

export interface AcuityBandTile {
  acuity: number;
  case_count: number;
  overdue_count: number;
}

export interface DeterioratingPatientTile {
  case_id: string;
  display_name: string | null;
  from_acuity: number;
  to_acuity: number;
}

export interface IncomingAmbulanceTile {
  case_id: string;
  display_name: string | null;
  predicted_acuity: number | null;
}

export interface ControlTowerResponse {
  patients_by_acuity_band: AcuityBandTile[];
  deteriorating_patients: DeterioratingPatientTile[];
  stuck_patients: StuckPatternResult[];
  capacity: {
    resource_type: string;
    available: number;
    occupied: number;
    out_of_service: number;
    needed_estimate: number;
  }[];
  incoming_ambulances: IncomingAmbulanceTile[];
}

export interface StuckPatternResult {
  pattern_id: StuckPatternId;
  label: string;
  case_id: string;
  minutes_overdue: number;
  route_to: StuckRouteTo;
}

export interface DoctorCaseTrend {
  concept_code: string;
  previous_value: unknown;
  previous_observed_at: string;
  current_value: unknown;
  current_observed_at: string;
  delta: number | null;
}

export interface DoctorPendingAction {
  kind: 'RESULT_AWAITING_REVIEW' | 'UNRESOLVED_DATA_CONFLICT';
  description: string;
  reference_id: string;
}

export interface DoctorCaseView {
  case_id: string;
  display_name: string | null;
  medical_history: string | null;
  current_observations: ObservationResponse[];
  latest_risk_assessment: RiskAssessmentResponse | null;
  trends: DoctorCaseTrend[];
  is_first_review: boolean;
  last_reviewed_at: string | null;
  changed_since_last_review: EventResponse[];
  pending_actions: DoctorPendingAction[];
}

export interface PatientCaseView {
  case_id: string;
  display_name: string | null;
  stage: PatientStage;
  next_step_message: string;
  wait_time_estimate: WaitTimeEstimate | null;
}

// Events & Timeline
export interface EventResponse {
  event_id: string;
  case_id: string | null;
  event_type: string;
  payload: Record<string, unknown>;
  occurred_at: string;
  recorded_at: string;
}

// Resources
export interface ResourceResponse {
  resource_id: string;
  hospital_profile_id: string;
  resource_type: ResourceType;
  label: string;
  status: ResourceStatus;
  assigned_case_id: string | null;
  assigned_at: string | null;
  occupancy_stuck_flagged: boolean;
}

export interface ResourceCreateRequest {
  resource_type: ResourceType;
  label: string;
  hospital_profile_id?: string;
}

export interface AssignResourceRequest {
  resource_type: ResourceType;
}

export interface CapacityConflictResponse {
  detail: string;
  resource_type: ResourceType;
  candidate_actions: string[];
}

export interface DoctorQueueItemResponse {
  case_id: string;
  display_name: string | null;
  mrn: string | null;
  age_years: number | null;
  sex: string | null;
  final_acuity: number;
  acuity_trend: DeteriorationTrend;
  arrival_time: string;
  waiting_minutes: number;
  time_in_current_band_minutes: number | null;
  assigned_resource_label?: string | null;
  unreviewed_results_count: number;
  stuck_flagged: boolean;
  stuck_reasons?: string[];
  recent_vital_summary?: Record<string, {
    latest_value: unknown;
    previous_value?: unknown;
    trend_direction?: DeteriorationTrend | string;
    unit?: string | null;
  }>;
}

export interface DoctorCaseDetailResponse {
  case_id: string;
  patient_summary: {
    display_name: string | null;
    mrn: string | null;
    age_years: number | null;
    sex: string | null;
    waiting_minutes: number;
    assigned_resource_label?: string | null;
    medical_history?: string | null;
  };
  acuity_summary: {
    final_acuity: number;
    confidence_band: ConfidenceBand;
    deciding_layer: DecidingLayer;
  };
  unreviewed_tests: DiagnosticTestResponse[];
  vital_trends: {
    concept_code: string;
    latest_value: unknown;
    previous_value?: unknown;
    trend_direction: DeteriorationTrend;
    unit?: string | null;
  }[];
  stuck_status?: {
    stuck_flagged: boolean;
    stuck_reasons: string[];
  };
}

// Diagnostic Tests
export interface DiagnosticTestResponse {
  test_id: string;
  case_id: string;
  test_type: string;
  status: DiagnosticTestStatus;
  ordered_at: string;
  sample_collected_at: string | null;
  result_available_at: string | null;
  result_reviewed_at: string | null;
  stuck_flagged: boolean;
}

export interface DiagnosticTestCreateRequest {
  test_type: string;
}

// Conflicts
export interface DataConflictResponse {
  conflict_id: string;
  case_id: string;
  concept_code: string;
  observation_ids: string[];
  conservative_observation_id: string;
  detected_at: string;
  resolved: boolean;
  resolved_at: string | null;
  resolved_by: string | null;
  kept_observation_id: string | null;
  resolution_note: string | null;
}

export interface ResolveConflictRequest {
  kept_observation_id: string;
  note?: string | null;
}

// Ambulance & Pre-Alert
export interface ETARange {
  lower_minutes: number;
  upper_minutes: number;
  arrived: boolean;
  delayed_additional_minutes: number;
  caveat: string;
}

export interface PreAlertKeyVital {
  concept_code: string;
  label: string;
  raw_value: unknown;
  unit: string | null;
  observed_at: unknown;
  points: number;
}

export interface PreAlertView {
  case_id: string;
  predicted_acuity_band: number | null;
  one_line_presentation: string | null;
  key_abnormal_vitals: PreAlertKeyVital[];
  interventions_already_performed: string[];
  eta_range: ETARange | null;
  what_hospital_should_prepare: string;
}

export interface TransportDelayRequest {
  additional_minutes: number;
  reason?: string | null;
}

export interface ProposeIdentityRequest {
  candidate_mrn: string;
  candidate_display_name?: string | null;
  confidence?: number | null;
}

export interface ConfirmIdentityRequest {
  mrn: string;
  display_name?: string | null;
}

export interface RecordArrivalRequest {
  occurred_at?: string | null;
}

// LLM Intake & Explanation
export interface ExplanationResult {
  text: string;
  grounded: boolean;
  fallback_used: boolean;
  fallback_reason: string | null;
  model_version: string | null;
  generated_at: string;
}

export interface IntakeOutcome {
  llm_available: boolean;
  parse_succeeded: boolean;
  reason: string | null;
  observations_created: string[];
  rejected: { concept_code: string; reason: string }[];
  model_version: string | null;
}

export interface IntakeRequest {
  text: string;
}

// Admin & Audit
export interface SubgroupStats {
  subgroup: string;
  case_count: number;
  acuity_distribution: Record<number, number>;
  decision_count: number;
  escalate_count: number;
  de_escalate_count: number;
  override_rate: number | null;
}

export interface OverrideMonitoringReport {
  total_cases: number;
  total_decisions: number;
  action_counts: Record<string, number>;
  overall_override_rate: number | null;
  overall_de_escalation_rate: number | null;
  flagged_for_review_count: number;
  by_age_band: SubgroupStats[];
  by_sex: SubgroupStats[];
  caveat: string;
}

// Demo
export interface DemoScenario {
  number: number;
  key: string;
  title: string;
  demonstrates: string;
  case_id: string;
  fidelity: 'FULL' | 'PARTIAL';
  note: string;
}

export interface SurgeSimulationResult {
  multiplier: number;
  baseline_count: number;
  surge_count: number;
  queue_length_before: number;
  queue_length_after: number;
  reassessment_overdue_count: number;
  acuity_ordering_holds: boolean;
  alerts_per_nurse_per_hour_baseline: number;
  alerts_per_nurse_per_hour_surge: number;
  alert_growth_below_volume_growth: boolean;
  capacity_conflict_demonstrated: boolean;
  stuck_patient_count: number;
  total_escalations_during_surge: number;
  ml_downgrade_refusals_count: number;
  narrative: string[];
}
