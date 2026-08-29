export type Role = 'NURSE' | 'DOCTOR' | 'ADMIN';

export type ArrivalMode = 'WALK_IN' | 'AMBULANCE';

export type CaseStatus = 'PRE_ARRIVAL' | 'ACTIVE' | 'DISPOSED';

export type IdentityLinkStatus = 'UNLINKED' | 'CANDIDATE_PROPOSED' | 'CONFIRMED';

export type EmergencyBypassSource = 'HUMAN' | 'PHYSIOLOGICAL' | 'TEXT_PATTERN';

export type DecidingLayer = 'RULES' | 'ML' | 'OVERRIDE' | 'ABSTENTION';

export type ConfidenceBand = 'HIGH' | 'MEDIUM' | 'LOW';

export type DeteriorationTrend = 'WORSENING' | 'STABLE' | 'IMPROVING' | 'UNKNOWN';

export type PrimaryAttentionFlag =
  | 'DETERIORATING'
  | 'REASSESSMENT_OVERDUE'
  | 'UNKNOWN_VITALS'
  | 'DATA_CONFLICT'
  | 'NONE';

export type ObservationValueType = 'NUMERIC' | 'CODED' | 'BOOLEAN' | 'TEXT';

export type ObservationSourceType =
  | 'DEVICE'
  | 'NURSE'
  | 'DOCTOR'
  | 'PARAMEDIC'
  | 'PATIENT'
  | 'HISTORICAL_RECORD'
  | 'AI_INFERRED';

export type ReliabilityTier = 1 | 2 | 3 | 4;

export type MeasurementStatus =
  | 'MEASURED'
  | 'NOT_MEASURED'
  | 'UNOBTAINABLE'
  | 'REFUSED'
  | 'UNKNOWN'
  | 'DEVICE_ERROR';

export type ClinicianAction = 'ACCEPT' | 'ESCALATE' | 'DE_ESCALATE' | 'MODIFY';

export type DeEscalationReasonCode =
  | 'PATIENT_STABLE_ON_CLINICAL_REVIEW'
  | 'TRANSIENT_SPIKE_RESOLVED'
  | 'ARTIFACT_OR_MEASUREMENT_ERROR'
  | 'PAIN_OR_DISTRESS_INDEPENDENT_OF_ACUITY'
  | 'KNOWN_BASELINE_ABNORMALITY';

export type AlertType =
  | 'CRITICAL_BYPASS_PATIENT'
  | 'ACUITY_BAND_CROSSED_UPWARD'
  | 'REASSESSMENT_OVERDUE_AGGREGATE';

export type AlertDismissalReasonCode =
  | 'ALREADY_ACTIONED'
  | 'NOT_ACTIONABLE_RIGHT_NOW'
  | 'FALSE_POSITIVE'
  | 'DUPLICATE'
  | 'RESOLVED_AUTOMATICALLY'
  | 'OTHER';

export type ResourceType = 'CLINICIAN' | 'TREATMENT_SPACE' | 'RESUSCITATION_BAY';

export type ResourceStatus = 'AVAILABLE' | 'OCCUPIED' | 'OUT_OF_SERVICE';

export type DiagnosticTestStatus =
  | 'ORDERED'
  | 'SAMPLE_COLLECTED'
  | 'RESULT_AVAILABLE'
  | 'RESULT_REVIEWED';

export type StuckPatternId =
  | 'TEST_ORDERED_NOT_COLLECTED'
  | 'RESULT_NOT_REVIEWED'
  | 'ASSIGNED_SPACE_NOT_OCCUPIED';

export type StuckRouteTo = 'NURSE_OPS' | 'DOCTOR_QUEUE' | 'CHARGE_NURSE';

export type PatientStage = 'PRE_ARRIVAL' | 'WAITING' | 'IN_TREATMENT' | 'DISPOSED';
