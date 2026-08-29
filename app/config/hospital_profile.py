"""
HospitalProfile: per-site clinical configuration (Phase 18.1).

"No code forks per hospital. Every clinical parameter is data, reviewed and
owned by that hospital's clinical governance." -> this loads a YAML file per
profile_id rather than branching code.

CP3 added the typed configuration for the Clinical Scoring Engine (Phase 3.3
Layer 2): NEWS2 (adult), a geriatric sensitivity adjustment layered on the
same NEWS2 tables, and a PEWS-style paediatric config. CP4 adds Layer 4 hard
escalation triggers and the Emergency Bypass detector configuration (Phase
3.5). Exactly which numbers are cited from the RCP NEWS2 report versus
engineering assumptions pending clinical validation is documented inline in
default.yaml's comments -- the [Sourced]/[Assumption]/[Requires clinical
validation] convention from the source document, kept next to each value
rather than in a separate file that could drift out of sync with it.
"""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Dict, List, Literal, Optional, Tuple

import yaml
from pydantic import BaseModel, Field

_PROFILES_DIR = os.path.join(os.path.dirname(__file__), "hospital_profiles")


class AgeBandDefinition(BaseModel):
    name: str  # e.g. "PAEDIATRIC", "ADULT", "GERIATRIC"
    min_age_years: float
    max_age_years: Optional[float] = None  # None = no upper bound


class ReassessmentInterval(BaseModel):
    acuity_level: int
    max_wait_minutes: int  # Phase 5.3: interval that triggers REASSESSMENT_DUE


# ---------------------------------------------------------------------
# Shared scoring primitives (Phase 3.2 "Vital sign abnormality flagging ->
# Deterministic, age-banded tables"). One generic table-evaluator shape is
# reused by NEWS2 and PEWS rather than bespoke if/elif chains per parameter,
# so a clinician correcting a threshold only ever edits YAML.
# ---------------------------------------------------------------------
class RangeBand(BaseModel):
    """One row of a banded scoring table. `min`/`max` are inclusive; None
    means unbounded on that side. Bands are evaluated in list order and the
    first match wins -- the config author is responsible for non-overlapping,
    fully-covering bands (the scoring engine raises rather than guessing if
    a value matches none of them)."""
    min: Optional[float] = None
    max: Optional[float] = None
    points: int


class AcuityBand(BaseModel):
    """Maps an aggregate-score range to an ESI level. This score-to-ESI
    mapping is NOT defined by NEWS2/PEWS/ESI themselves -- it is this
    project's own [Requires clinical validation] bridge between an
    early-warning score and a 5-level triage scale (Phase 3.3)."""
    min_score: float
    max_score: Optional[float] = None
    esi_level: int


# ---------------------------------------------------------------------
# Trigger conditions (Phase 3.3 Layer 4 hard triggers, Phase 3.5 Emergency
# Bypass detector #2). One condition shape shared by both -- evaluation
# logic lives in app/scoring/trigger_conditions.py (not here: config models
# stay data-only, no engine code imports config-adjacent modules that would
# risk a circular import back into config).
# ---------------------------------------------------------------------
class TriggerCondition(BaseModel):
    concept_code: str
    comparison: Literal["lte", "gte", "eq"]
    numeric_threshold: Optional[float] = None  # for lte/gte
    coded_value: Optional[str] = None          # for eq against a CODED concept
    boolean_value: Optional[bool] = None       # for eq against a BOOLEAN concept


class HardTriggerDefinition(BaseModel):
    """Phase 3.3 Layer 4: 'a small set of hospital-configured
    single-parameter triggers that force top acuity regardless of aggregate
    score.' Fires *within* the normal scoring pipeline -- the case is still
    queued, just forced to the top of it (contrast with
    EmergencyBypassPhysiologicalTrigger below, which skips the queue
    entirely). [Requires clinical validation] end to end."""
    trigger_id: str
    label: str
    condition: TriggerCondition
    applies_to_age_bands: List[str] = Field(default_factory=list)  # empty = all bands
    target_esi_level: int = 1


class EmergencyBypassPhysiologicalTrigger(BaseModel):
    """Phase 3.5 detector #2: 'Configured single-parameter red flags
    evaluated the instant any vital arrives ... Pure arithmetic,
    sub-millisecond, no network dependency.' Deliberately a SEPARATE,
    independently-configured list from hard_trigger_definitions above, even
    though it reuses the same TriggerCondition shape: this one's
    consequence is 'skip all queues', not 'top of the queue', so a hospital
    may reasonably want a stricter (or different) threshold set for it.
    [Requires clinical validation]."""
    trigger_id: str
    label: str
    condition: TriggerCondition
    applies_to_age_bands: List[str] = Field(default_factory=list)


class NEWS2Config(BaseModel):
    """Phase 3.3 Layer 2, adult backbone. Parameter tables below are
    [Sourced]: Royal College of Physicians, NEWS2 (2017) -- see
    references.md. The aggregate_to_esi bridge and single-parameter
    escalation level are this project's own [Requires clinical validation]
    addition (NEWS2 itself only defines low/medium/high risk bands, not ESI
    levels)."""
    respiratory_rate: List[RangeBand]
    spo2_scale1: List[RangeBand]  # Scale 1 only; Scale 2 (hypercapnic risk) is out of scope, see note in yaml
    supplemental_oxygen_points: int
    systolic_bp: List[RangeBand]
    pulse: List[RangeBand]
    consciousness_points: Dict[str, int]  # AVPU / new-confusion -> points
    temperature: List[RangeBand]

    single_parameter_red_threshold: int  # any one component >= this -> escalate regardless of aggregate
    single_parameter_escalation_esi_level: int
    aggregate_to_esi: List[AcuityBand]
    missing_data_cap_esi_level: int  # Phase 3.3 "unknown is treated as potentially dangerous"


class GeriatricAdjustment(BaseModel):
    """Phase 3.3 Layer 1: geriatric must have 'its own reference ranges and
    its own escalation triggers'. NEWS2's parameter tables are reused as-is
    (NEWS2's own stated scope is adults 16+, no upper bound), but banding is
    tightened: elderly patients compensate physiologically and can look
    deceptively stable on aggregate score while showing smaller
    multi-parameter deviations, so both the single-parameter threshold and
    the aggregate->ESI thresholds are set to escalate earlier than the
    adult mapping. Entirely [Requires clinical validation] -- see
    Architecture Concern logged at CP3 for why this exists at all."""
    single_parameter_red_threshold: int
    single_parameter_escalation_esi_level: int
    aggregate_to_esi: List[AcuityBand]
    missing_data_cap_esi_level: int


class PEWSAgeBand(BaseModel):
    name: str
    min_age_years: float
    max_age_years: Optional[float] = None
    respiratory_rate_normal: Tuple[float, float]  # (low, high)
    heart_rate_normal: Tuple[float, float]
    systolic_bp_normal: Tuple[float, float]


class PEWSConfig(BaseModel):
    """Phase 3.3 Layer 2, paediatric backbone.

    Deliberate design simplification, stated up front rather than silently:
    RR/HR/SBP are NOT hand-authored per-age-band point tables (unlike NEWS2
    above). Instead each age band declares its own (low, high) normal range,
    and points are derived at score time from relative deviation outside
    that range via `deviation_band_thresholds`. This keeps the config
    honestly small and auditable instead of presenting ~70 hand-picked
    numbers as if they were a citable chart -- the source document
    explicitly says not to reproduce copyrighted scoring charts, and no
    single canonical PEWS point table is cited in the architecture doc to
    reproduce faithfully in the first place. [Requires clinical validation]
    end to end: the normal ranges, the deviation thresholds, and the
    resulting points are all illustrative pending a named PEWS variant and
    clinical sign-off (Phase 3.3 references ED-PEWS as LMIC-validated
    without reproducing its table).
    """
    age_bands: List[PEWSAgeBand]
    deviation_band_thresholds: List[float]  # e.g. [0.15, 0.30] -> points 1, 2, else 3 beyond that
    spo2_scale1: List[RangeBand]
    supplemental_oxygen_points: int
    work_of_breathing_points: Dict[str, int]  # qualitative sign Phase 3.3 flags as mattering more than numbers
    consciousness_points: Dict[str, int]
    temperature: List[RangeBand]

    single_parameter_red_threshold: int
    single_parameter_escalation_esi_level: int
    aggregate_to_esi: List[AcuityBand]
    missing_data_cap_esi_level: int

    def band_for_age(self, age_years: float) -> Optional[PEWSAgeBand]:
        for band in self.age_bands:
            lower_ok = age_years >= band.min_age_years
            upper_ok = band.max_age_years is None or age_years < band.max_age_years
            if lower_ok and upper_ok:
                return band
        return None


class ConfidenceConfig(BaseModel):
    """Phase 9.1: the four deterministic confidence inputs, weighted as
    point deductions from a 100-point starting score. Phase 9.1: 'A model
    self-reporting its own confidence in prose is not calibration' -- this
    is a formula over structured facts, not a language-model judgement.
    [Requires clinical validation] for every weight; the shape (four
    inputs, three bands, never lowers acuity) is what Phase 9.1 specifies,
    the numbers are this project's own illustrative starting point.
    """
    # Input 1: data completeness (Phase 9.1 "fewer known high-value fields
    # lowers confidence"). Deducted proportionally to the fraction of
    # required components that are missing/stale/not-measured.
    max_completeness_penalty: float = 90.0

    # Input 2: agreement between rules and ML (Phase 9.1). Until CP6 wires
    # in a real ML challenger, ml_suggested_acuity is always None, so this
    # deducts ml_unavailable_penalty on every case -- correct per Phase 9.5
    # ("ML model unavailable -> confidence band drops"), not a placeholder
    # bug. ml_disagreement_penalty_per_level applies once CP6 supplies a
    # real suggestion that differs from the framework's own acuity.
    ml_unavailable_penalty: float = 15.0
    ml_disagreement_penalty_per_level: float = 10.0

    # Input 3: distance from a band boundary (Phase 9.1 "borderline scores
    # lower confidence"). `boundary_margin` is in raw aggregate-score
    # points; a score within that margin of either edge of its own band is
    # borderline.
    boundary_margin: float = 1.0
    boundary_penalty: float = 15.0

    # Input 4: reliability tier of the inputs used (Phase 9.1 "self-reported
    # -only lowers confidence"). Penalty per component, averaged across the
    # components actually used in the aggregate score. Keyed by
    # ReliabilityTier's integer value (1=machine .. 4=AI-inferred).
    reliability_tier_penalties: Dict[int, float] = Field(
        default_factory=lambda: {1: 0.0, 2: 5.0, 3: 15.0, 4: 20.0}
    )

    # Final 0-100 score -> three bands (Phase 9.1).
    high_confidence_min_score: float = 75.0
    medium_confidence_min_score: float = 50.0  # below this -> LOW

    # Phase 9.2 abstention: below this score OR a total data void (no
    # components at all / age unknown), the system abstains outright rather
    # than merely showing LOW confidence.
    abstention_score_threshold: float = 25.0
    abstention_minimum_acuity: int = 3  # "holds a configured minimum band until a human assesses"


class MLChallengerConfig(BaseModel):
    """Phase 3.3 Layer 3: 'Output is a probability plus a suggested level.'
    `probability_to_esi` is this project's own [Requires clinical
    validation] bridge from a calibrated probability to an ESI level --
    analogous to NEWS2Config.aggregate_to_esi, but over a 0-1 probability
    instead of a raw aggregate score. `enabled=False` is the Phase 9.5
    failure-mode switch ('ML model unavailable -> rules-only acuity')."""
    enabled: bool = True
    probability_to_esi: List[AcuityBand] = Field(default_factory=list)  # min_score/max_score interpreted as probability


class LLMConfig(BaseModel):
    """Phase 3.2 (CP17): the LLM Intake/Explanation engines' switch and
    provider settings. `enabled=False` is the Phase 9.5 failure-mode
    switch ('LLM API unavailable -> structured entry forms replace
    conversational capture; explanations replaced by the rule component
    breakdown; rules engine unaffected either way') -- both engines fall
    back to a fully deterministic path when this is False, exactly like
    MLChallengerConfig.enabled does for Layer 3. `api_key_env_var` names
    an environment variable read at call time (app/llm/client.py) -- the
    key itself is never stored in config/YAML."""
    enabled: bool = True
    provider: str = "groq"
    model: str = "openai/gpt-oss-20b"
    api_key_env_var: str = "GROQ_API_KEY"
    request_timeout_seconds: float = 20.0


class OpsConfig(BaseModel):
    """Phase 6.3: 'an expected next event has not occurred within its
    configured window.' Three of the five named patterns are implemented
    (Phase 13's own MVP guidance: 'two or three patterns'); the other two
    ('disposition decided, not executed' and the reassessment-overdue
    pattern) are, respectively, out of scope for this checkpoint and
    already implemented as their own mechanism (CP7's reassessment timer --
    Phase 6.3's table itself notes that one is clinical, not operational,
    and routes it differently). [Requires clinical validation] for every
    window below; illustrative only.

    Phase 6.2: candidate_actions are shown to the charge nurse alongside a
    capacity conflict ('here are the candidate actions') -- a fixed,
    hospital-configured list, not computed. [Assumption]."""
    test_ordered_to_sample_window_minutes: int = 45
    result_available_to_reviewed_window_minutes: int = 30
    resource_assigned_to_occupied_window_minutes: int = 15
    capacity_conflict_candidate_actions: List[str] = Field(
        default_factory=lambda: [
            "Expedite a discharge to free a space",
            "Use an alternative space or resource type",
            "Escalate to the on-call team",
        ]
    )

    # ------------------------------------------------------------------
    # Waiting-time prediction (Phase 6.4): "Do not use machine learning
    # here. A simple queue model is more defensible and easier to
    # explain." See app/ops/wait_time.py for the formula itself; these are
    # just its tunable knobs. [Requires clinical validation] / [Assumption]
    # for every number below, same convention as the rest of this file.
    # ------------------------------------------------------------------
    # Used only as a cold-start fallback, when this hospital_profile_id has
    # too little (or no) history yet to compute a real rolling median from
    # observed arrival -> first-service-resource-assignment durations.
    default_service_minutes_by_acuity: Dict[int, float] = Field(
        default_factory=lambda: {1: 15.0, 2: 25.0, 3: 45.0, 4: 60.0, 5: 90.0}
    )
    wait_time_lookback_samples: int = 50
    wait_time_min_samples_for_band_specific_median: int = 3
    # How far the presented range widens around the point estimate --
    # Phase 6.4: "present it as a range that widens with uncertainty."
    # Wider when we fall back to a global (not band-specific) median or to
    # the configured default above, since that's a weaker basis.
    wait_time_range_widen_factor_normal: float = 0.4
    wait_time_range_widen_factor_low_confidence: float = 0.75


class HospitalProfile(BaseModel):
    profile_id: str
    acuity_framework: str  # e.g. "ESI-5" (Phase 3.3 Layer 2)
    age_band_definitions: List[AgeBandDefinition]

    news2: NEWS2Config
    geriatric_adjustment: GeriatricAdjustment
    pews: PEWSConfig

    # Phase 9.2 abstention, applied at the narrowest possible point: age is
    # the one input the Age Router itself cannot proceed without (Phase
    # 3.3 Layer 1 runs "before anything else happens"). This is distinct
    # from each framework's own missing_data_cap_esi_level, which handles
    # missing *vitals* once a framework has already been selected.
    unknown_age_default_esi_level: int = 3

    confidence: ConfidenceConfig = Field(default_factory=ConfidenceConfig)
    ml_challenger: MLChallengerConfig = Field(default_factory=MLChallengerConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    ops: OpsConfig = Field(default_factory=OpsConfig)

    hard_trigger_definitions: List[HardTriggerDefinition] = Field(default_factory=list)  # Phase 3.3 Layer 4
    emergency_bypass_physiological_triggers: List[EmergencyBypassPhysiologicalTrigger] = Field(default_factory=list)
    emergency_bypass_critical_phrases: List[str] = Field(default_factory=list)  # Phase 3.5 detector #3
    reassessment_intervals: List[ReassessmentInterval]
    staleness_windows_minutes: Dict[str, int] = Field(default_factory=dict)  # concept_code -> minutes
    available_integrations: List[str] = Field(default_factory=list)
    resource_types_enabled: List[str] = Field(default_factory=list)
    alert_budget_targets: Dict[str, float] = Field(default_factory=dict)
    language_set: List[str] = Field(default_factory=list)
    clinical_governance_contact: Optional[str] = None

    def age_band_for(self, age_years: float) -> Optional[str]:
        """CP3 (Age Router) entry point: resolve which band an age falls
        into. Returns None if no band matches (caller must treat this as an
        abstention-worthy gap, not default to adult -- Phase 9.2)."""
        for band in self.age_band_definitions:
            lower_ok = age_years >= band.min_age_years
            upper_ok = band.max_age_years is None or age_years < band.max_age_years
            if lower_ok and upper_ok:
                return band.name
        return None

    def reassessment_minutes_for(self, acuity_level: int) -> Optional[int]:
        for interval in self.reassessment_intervals:
            if interval.acuity_level == acuity_level:
                return interval.max_wait_minutes
        return None

    def staleness_window_for(self, concept_code: str):
        """Returns a timedelta, or None if the concept never goes stale
        (not configured). Consumed by app/scoring/engine.py and, later, the
        Time Engine (CP7)."""
        from datetime import timedelta

        minutes = self.staleness_windows_minutes.get(concept_code)
        return timedelta(minutes=minutes) if minutes is not None else None


@lru_cache(maxsize=32)
def load_hospital_profile(profile_id: str = "default") -> HospitalProfile:
    path = os.path.join(_PROFILES_DIR, f"{profile_id}.yaml")
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"No hospital profile config at {path}. Hospital profiles are "
            f"data files under app/config/hospital_profiles/, not code -- "
            f"add one rather than hard-coding thresholds (Phase 18.1)."
        )
    with open(path, "r") as f:
        raw = yaml.safe_load(f)
    return HospitalProfile(profile_id=profile_id, **raw)
