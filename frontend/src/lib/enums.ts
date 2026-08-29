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
} from '../types/enums';

export const ROLE_LABELS: Record<Role, string> = {
  NURSE: 'Triage Nurse',
  DOCTOR: 'Physician',
  ADMIN: 'ED Administrator',
};

export const ARRIVAL_MODE_LABELS: Record<ArrivalMode, string> = {
  WALK_IN: 'Walk-in',
  AMBULANCE: 'Ambulance',
};

export const CASE_STATUS_LABELS: Record<CaseStatus, string> = {
  PRE_ARRIVAL: 'Pre-arrival',
  ACTIVE: 'Active in ED',
  DISPOSED: 'Disposed',
};

export const IDENTITY_STATUS_LABELS: Record<IdentityLinkStatus, string> = {
  UNLINKED: 'Unlinked',
  CANDIDATE_PROPOSED: 'Candidate Proposed',
  CONFIRMED: 'Identity Confirmed',
};

export const BYPASS_SOURCE_LABELS: Record<EmergencyBypassSource, string> = {
  HUMAN: 'Staff 1-Tap Trigger',
  PHYSIOLOGICAL: 'Critical Vitals Threshold',
  TEXT_PATTERN: 'Critical Phrase Match',
};

export const DECIDING_LAYER_LABELS: Record<DecidingLayer, string> = {
  RULES: 'Clinical Scoring (NEWS2/PEWS)',
  ML: 'ML Challenger Escalation',
  OVERRIDE: 'Clinician Override',
  ABSTENTION: 'Confidence Abstention',
};

export const CONFIDENCE_BAND_LABELS: Record<ConfidenceBand, string> = {
  HIGH: 'High Confidence',
  MEDIUM: 'Medium Confidence',
  LOW: 'Low Confidence',
};

export const DETERIORATION_TREND_LABELS: Record<DeteriorationTrend, string> = {
  WORSENING: 'Deteriorating',
  STABLE: 'Stable',
  IMPROVING: 'Improving',
  UNKNOWN: 'Trend Unknown',
};

export const ATTENTION_FLAG_LABELS: Record<PrimaryAttentionFlag, string> = {
  DETERIORATING: 'Deteriorating',
  REASSESSMENT_OVERDUE: 'Reassessment Overdue',
  UNKNOWN_VITALS: 'Vitals Incomplete',
  DATA_CONFLICT: 'Data Conflict',
  NONE: 'None',
};

export const SOURCE_TYPE_LABELS: Record<ObservationSourceType, string> = {
  DEVICE: 'Medical Device',
  NURSE: 'Triage Nurse',
  DOCTOR: 'Physician',
  PARAMEDIC: 'Paramedic / EMS',
  PATIENT: 'Patient Reported',
  HISTORICAL_RECORD: 'Historical EHR',
  AI_INFERRED: 'AI Inferred (Intake)',
};

export const RELIABILITY_TIER_LABELS: Record<ReliabilityTier, string> = {
  1: 'Tier 1: Device / Monitor',
  2: 'Tier 2: Clinician Assessed',
  3: 'Tier 3: Patient Reported',
  4: 'Tier 4: AI Inferred',
};

export const MEASUREMENT_STATUS_LABELS: Record<MeasurementStatus, string> = {
  MEASURED: 'Measured',
  NOT_MEASURED: 'Not Measured',
  UNOBTAINABLE: 'Unobtainable',
  REFUSED: 'Patient Refused',
  UNKNOWN: 'Unknown',
  DEVICE_ERROR: 'Device Error',
};

export const CLINICIAN_ACTION_LABELS: Record<ClinicianAction, string> = {
  ACCEPT: 'Accept Acuity',
  ESCALATE: 'Escalate Urgency',
  DE_ESCALATE: 'De-escalate Level',
  MODIFY: 'Modify (Unsupported)',
};

export const DE_ESCALATION_REASONS: Record<DeEscalationReasonCode, string> = {
  PATIENT_STABLE_ON_CLINICAL_REVIEW: 'Patient stable on clinical review',
  TRANSIENT_SPIKE_RESOLVED: 'Transient spike resolved',
  ARTIFACT_OR_MEASUREMENT_ERROR: 'Artifact or measurement error',
  PAIN_OR_DISTRESS_INDEPENDENT_OF_ACUITY: 'Pain or distress independent of acuity',
  KNOWN_BASELINE_ABNORMALITY: 'Known baseline abnormality',
};

export const ALERT_TYPE_LABELS: Record<AlertType, string> = {
  CRITICAL_BYPASS_PATIENT: 'Immediate Emergency Bypass Triggered',
  ACUITY_BAND_CROSSED_UPWARD: 'Acuity Deterioration Warning',
  REASSESSMENT_OVERDUE_AGGREGATE: 'Multiple Patients Overdue for Reassessment',
};

export const ALERT_DISMISSAL_REASONS: Record<AlertDismissalReasonCode, string> = {
  ALREADY_ACTIONED: 'Already actioned by clinician',
  NOT_ACTIONABLE_RIGHT_NOW: 'Not actionable right now (monitoring)',
  FALSE_POSITIVE: 'False positive / measurement artifact',
  DUPLICATE: 'Duplicate alert for same condition',
  RESOLVED_AUTOMATICALLY: 'Resolved automatically by system',
  OTHER: 'Other operational reason',
};

export const RESOURCE_TYPE_LABELS: Record<ResourceType, string> = {
  CLINICIAN: 'Clinician',
  TREATMENT_SPACE: 'Treatment Space',
  RESUSCITATION_BAY: 'Resuscitation Bay',
};

export const RESOURCE_STATUS_LABELS: Record<ResourceStatus, string> = {
  AVAILABLE: 'Available',
  OCCUPIED: 'Occupied',
  OUT_OF_SERVICE: 'Out of Service',
};

export const DIAGNOSTIC_STATUS_LABELS: Record<DiagnosticTestStatus, string> = {
  ORDERED: 'Ordered',
  SAMPLE_COLLECTED: 'Sample Collected',
  RESULT_AVAILABLE: 'Result Available',
  RESULT_REVIEWED: 'Result Reviewed',
};

export const STUCK_PATTERN_LABELS: Record<StuckPatternId, string> = {
  TEST_ORDERED_NOT_COLLECTED: 'Test ordered but sample not collected',
  RESULT_NOT_REVIEWED: 'Diagnostic result available but unreviewed',
  ASSIGNED_SPACE_NOT_OCCUPIED: 'Assigned space not occupied by patient',
};

export const STUCK_ROUTE_LABELS: Record<StuckRouteTo, string> = {
  NURSE_OPS: 'Nurse Operations',
  DOCTOR_QUEUE: 'Physician Queue',
  CHARGE_NURSE: 'Charge Nurse Tower',
};

export const PATIENT_STAGE_LABELS: Record<PatientStage, string> = {
  PRE_ARRIVAL: 'In Transit / Pre-arrival',
  WAITING: 'Waiting for Triage & Assessment',
  IN_TREATMENT: 'In Treatment Area',
  DISPOSED: 'Care Completed / Discharged',
};
