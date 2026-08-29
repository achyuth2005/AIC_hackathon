"""
Controlled vocabularies for the Patient State Store.

Every enum here is taken verbatim from the architecture document
(Phase 4.2 Observation record, Phase 7 arrival modes) rather than invented.
Do not add values silently; extending these is a schema/architecture decision.
"""
from enum import Enum


class SourceType(str, Enum):
    """Phase 4.2: `source_type`."""
    DEVICE = "DEVICE"
    NURSE = "NURSE"
    DOCTOR = "DOCTOR"
    PARAMEDIC = "PARAMEDIC"
    PATIENT = "PATIENT"
    HISTORICAL_RECORD = "HISTORICAL_RECORD"
    AI_INFERRED = "AI_INFERRED"


class ReliabilityTier(int, Enum):
    """Phase 4.2: `reliability_tier`. Lower number = more reliable."""
    MACHINE_MEASURED = 1
    CLINICIAN_OBSERVED = 2
    PATIENT_REPORTED = 3
    AI_INFERRED = 4


class MeasurementStatus(str, Enum):
    """Phase 4.2: `measurement_status`. MEASURED is the only status that
    represents an actual reading; every other value must NOT be treated as
    normal (Phase 3.3 "Handling missing data", Phase 9.4)."""
    MEASURED = "MEASURED"
    NOT_MEASURED = "NOT_MEASURED"
    UNOBTAINABLE = "UNOBTAINABLE"
    REFUSED = "REFUSED"
    UNKNOWN = "UNKNOWN"
    DEVICE_ERROR = "DEVICE_ERROR"


class ValueType(str, Enum):
    """Phase 4.2: `value // numeric | coded | boolean | text`.
    Not named as an explicit field in the doc, but required to know which of
    the typed value columns on Observation is populated."""
    NUMERIC = "NUMERIC"
    CODED = "CODED"
    BOOLEAN = "BOOLEAN"
    TEXT = "TEXT"


class ArrivalMode(str, Enum):
    """Phase 7: walk-in vs ambulance case continuity."""
    WALK_IN = "WALK_IN"
    AMBULANCE = "AMBULANCE"


class CaseStatus(str, Enum):
    """Lifecycle of a Case. PRE_ARRIVAL covers the ambulance case that exists
    before PATIENT_ARRIVED fires (Phase 7.1: "Arrival is an event, not a new
    case")."""
    PRE_ARRIVAL = "PRE_ARRIVAL"
    ACTIVE = "ACTIVE"
    DISPOSED = "DISPOSED"


class IdentityLinkStatus(str, Enum):
    """Phase 7.1: ambulance-to-ED identity matching must never silently
    auto-merge on a fuzzy match."""
    UNLINKED = "UNLINKED"
    CANDIDATE_PROPOSED = "CANDIDATE_PROPOSED"
    CONFIRMED = "CONFIRMED"


class ConfidenceBand(str, Enum):
    """Phase 9.1: 'surfaced as three bands with reasons'. Low confidence
    never means low acuity -- see app/scoring/confidence.py."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class DecidingLayer(str, Enum):
    """Phase 4.3 RiskAssessment.deciding_layer: which term of
    final_acuity = min(rule_based_acuity, ml_suggested_acuity,
    override_acuity_if_escalating) (Phase 3.1) actually produced the final
    value. ABSTENTION is a CP5/CP6 addition beyond the three terms Phase
    4.3 names explicitly -- when the Confidence & Abstention Engine's floor
    (Phase 9.2) is what bound the result, tighter than either RULES or ML,
    the audit trail should say so plainly rather than mislabel it as an
    ordinary rules-based decision."""
    RULES = "RULES"
    ML = "ML"
    OVERRIDE = "OVERRIDE"       # CP9/10: clinician override, not used until then
    ABSTENTION = "ABSTENTION"   # CP5/CP6 addition, see above


class DeteriorationTrend(str, Enum):
    """Phase 5.4 / Phase 5.2 sort key `deterioration_trend_direction`:
    computed from consecutive RiskAssessment.final_acuity values for a
    case (CP7 Time Engine), not a separate ML signal. WORSENING = the most
    recent assessment is MORE urgent (lower ESI number) than the one
    before it."""
    WORSENING = "WORSENING"
    STABLE = "STABLE"
    IMPROVING = "IMPROVING"
    UNKNOWN = "UNKNOWN"  # fewer than 2 assessments to compare


class BypassSource(str, Enum):
    """Phase 3.5: which of the three redundant Emergency Bypass detectors
    fired. Multiple sources can fire independently for the same case --
    "any of which can fire, none of which can cancel another"."""
    HUMAN = "HUMAN"                # detector #1: one-tap staff control
    PHYSIOLOGICAL = "PHYSIOLOGICAL"  # detector #2: deterministic vital-sign trigger
    TEXT_PATTERN = "TEXT_PATTERN"    # detector #3: curated critical-phrase match


class ResourceType(str, Enum):
    """Phase 6.1 MVP scope decision: exactly the three 'Essential (MVP)'
    resource rows. Diagnostics/beds are 'useful, optional'; everything
    else (medication inventory, staff rostering, equipment) is out of
    scope or future -- not modelled as a ResourceType at all."""
    CLINICIAN = "CLINICIAN"
    TREATMENT_SPACE = "TREATMENT_SPACE"
    RESUSCITATION_BAY = "RESUSCITATION_BAY"


class ResourceStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    OCCUPIED = "OCCUPIED"
    OUT_OF_SERVICE = "OUT_OF_SERVICE"


class DiagnosticTestStatus(str, Enum):
    """Phase 6.3's first two stuck-patient patterns are two stages of the
    same lifecycle: ORDERED -> SAMPLE_COLLECTED -> RESULT_AVAILABLE ->
    RESULT_REVIEWED. A test stuck at ORDERED too long is pattern 1; stuck
    at RESULT_AVAILABLE too long is pattern 2."""
    ORDERED = "ORDERED"
    SAMPLE_COLLECTED = "SAMPLE_COLLECTED"
    RESULT_AVAILABLE = "RESULT_AVAILABLE"
    RESULT_REVIEWED = "RESULT_REVIEWED"


class HumanDecisionAction(str, Enum):
    """Phase 4.3's HumanDecision.clinician_action, verbatim. Phase 9.6's
    own prose only describes two friction-differentiated directions
    (escalate / de-escalate) plus implicitly agreeing with the system as
    it stands -- this project's override endpoint (CP10) produces ACCEPT,
    ESCALATE, and DE_ESCALATE. MODIFY is kept as a valid, schema-complete
    enum value but is not yet produced by any endpoint: the architecture
    doesn't specify a distinct behaviour for it beyond what a directional
    ESCALATE/DE_ESCALATE against an explicit target_acuity already covers,
    so inventing one would be guessing rather than following the doc."""
    ACCEPT = "ACCEPT"
    ESCALATE = "ESCALATE"
    DE_ESCALATE = "DE_ESCALATE"
    MODIFY = "MODIFY"


class DeEscalationReasonCode(str, Enum):
    """Phase 9.6: de-escalation "requires a structured reason code" but
    the architecture doc does not enumerate one. [Assumption]: this is an
    illustrative starting vocabulary, [Requires clinical validation] like
    every other illustrative code list in this project."""
    PATIENT_STABLE_ON_CLINICAL_REVIEW = "PATIENT_STABLE_ON_CLINICAL_REVIEW"
    VITALS_IMPROVED_SINCE_ASSESSMENT = "VITALS_IMPROVED_SINCE_ASSESSMENT"
    SYMPTOM_RESOLVED = "SYMPTOM_RESOLVED"
    INITIAL_ESCALATION_WAS_ERRONEOUS = "INITIAL_ESCALATION_WAS_ERRONEOUS"
    OTHER_CLINICAL_JUDGEMENT = "OTHER_CLINICAL_JUDGEMENT"


class PatientStage(str, Enum):
    """Phase 8.1's patient-facing hierarchy: 'where you are in the
    process.' Deliberately NOT the same vocabulary as CaseStatus/
    ResourceStatus -- this is the one-word stage a patient sees, and it
    must never be extendable to leak acuity/clinical detail."""
    PRE_ARRIVAL = "PRE_ARRIVAL"
    WAITING = "WAITING"
    IN_TREATMENT = "IN_TREATMENT"
    DISPOSED = "DISPOSED"


class NurseAttentionFlag(str, Enum):
    """Phase 8.2: 'the flag that most needs attention (deteriorating,
    overdue, unknown vitals, conflict).' Exactly one flag per case --
    the doc's own listed order is treated as the priority order when more
    than one condition applies at once (see app/queue/guardian_queue.py)."""
    DETERIORATING = "DETERIORATING"
    REASSESSMENT_OVERDUE = "REASSESSMENT_OVERDUE"
    UNKNOWN_VITALS = "UNKNOWN_VITALS"
    DATA_CONFLICT = "DATA_CONFLICT"
    NONE = "NONE"


class AlertType(str, Enum):
    """Phase 8.5: 'Only three things interrupt.' Exactly these three --
    anything else worth surfacing (deterioration trend shown in queue
    ordering, stuck patients on the ops list, capacity conflicts) is
    ambient, not an interruptive Alert (see app/alerts/engine.py)."""
    CRITICAL_BYPASS_PATIENT = "CRITICAL_BYPASS_PATIENT"          # a NEW critical-bypass patient
    ACUITY_BAND_CROSSED_UPWARD = "ACUITY_BAND_CROSSED_UPWARD"    # a patient crossing into a higher (more urgent) band
    REASSESSMENT_OVERDUE_AGGREGATE = "REASSESSMENT_OVERDUE_AGGREGATE"  # Phase 8.5: "three overdue reassessments is one notification, not three"


class AlertDismissalReasonCode(str, Enum):
    """Phase 8.5: 'Every alert is dismissible with a reason, and dismissal
    reasons feed the tuning loop.' [Assumption]: the architecture doc does
    not enumerate specific codes, so this is an illustrative starting
    vocabulary, [Requires clinical validation] like every other
    illustrative code list in this project. RESOLVED_AUTOMATICALLY is this
    project's own addition for the one case a human never touches: an
    aggregate reassessment alert whose underlying overdue set emptied out
    before anyone dismissed it (see Alert.dismissed_by = 'SYSTEM')."""
    ALREADY_ACTIONED = "ALREADY_ACTIONED"
    NOT_ACTIONABLE_RIGHT_NOW = "NOT_ACTIONABLE_RIGHT_NOW"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    DUPLICATE = "DUPLICATE"
    RESOLVED_AUTOMATICALLY = "RESOLVED_AUTOMATICALLY"
    OTHER = "OTHER"
