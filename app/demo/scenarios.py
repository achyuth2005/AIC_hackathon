"""
Phase 14.1's twenty synthetic demo patients, each built to teach one
specific thing. This is DATA GENERATION for the demo script, deliberately
distinct from app/ml/synthetic_data.py's bulk generator (CP6): that module
produces hundreds of unlabelled rows to train/evaluate the ML challenger;
this module produces twenty individually hand-designed, narratively
labelled cases meant to be looked at one at a time in a live demo.

Every vital-sign value below is chosen against this project's own already-
configured reference tables (app/config/hospital_profiles/default.yaml's
NEWS2/PEWS bands, hard triggers, and bypass triggers) rather than invented
independently -- Phase 14.1: "Vital sign values should be generated from
the reference tables of whichever published framework you adopt, not
invented." Every number in that config is itself [Assumption] or
[Requires clinical validation] as documented there; this module inherits
that status rather than adding new claims.

**[Assumption] applies to all twenty patients below: no real patient data
is used anywhere in this file.**

Fidelity note (stated once here, referenced per-scenario): two of the
twenty rows in Phase 14.1's table describe behaviour this backend could
not yet fully realise as of CP11 --
  - #13 (contradictory data) needed the Phase 9.3 Contradictory-
    Information engine, which did not exist at CP11 -- built at CP13, now
    marked FULL. See app/scoring/conflict_detection.py.
  - #19 (multilingual/voice intake) needs the LLM Intake Engine, which is
    explicitly deferred pending a user-supplied API key. This scenario
    seeds a real multilingual free-text symptom report alongside
    DIRECTLY-entered structured vitals, standing in for what the Intake
    Engine would otherwise extract automatically.
#19 is marked `fidelity="PARTIAL"` below rather than silently presented as
fully working; #16 (unconfirmed identity match) is also PARTIAL for the
reason given at its own definition (propose/confirm exist, candidate
search does not).
"""
from __future__ import annotations

from datetime import timedelta
from typing import List, Optional

from pydantic import BaseModel

from app.config.hospital_profile import HospitalProfile
from app.models.enums import (
    ArrivalMode,
    DeEscalationReasonCode,
    HumanDecisionAction,
    MeasurementStatus,
    ReliabilityTier,
    SourceType,
    ValueType,
)
from app.scoring import concepts
from app.scoring.risk_orchestrator import assess_case
from app.store.event_store import EventStore
from app.timeutil import utcnow


class DemoScenario(BaseModel):
    number: int
    key: str
    title: str
    demonstrates: str
    case_id: str
    fidelity: str  # "FULL" | "PARTIAL"
    note: Optional[str] = None


def _vital(
    store: EventStore,
    case_id: str,
    concept_code: str,
    value,
    value_type: ValueType,
    *,
    source_type: SourceType = SourceType.DEVICE,
    reliability_tier: ReliabilityTier = ReliabilityTier.MACHINE_MEASURED,
    observed_at=None,
    measurement_status: MeasurementStatus = MeasurementStatus.MEASURED,
):
    return store.add_observation(
        case_id=case_id,
        concept_code=concept_code,
        value=value,
        value_type=value_type,
        source_type=source_type,
        reliability_tier=reliability_tier,
        measurement_status=measurement_status,
        observed_at=observed_at or utcnow(),
    )


def _full_adult_vitals(store, case_id, *, rr, spo2, hr, sbp, temp, consciousness="ALERT", suppl_o2=False, observed_at=None):
    _vital(store, case_id, concepts.RESP_RATE, rr, ValueType.NUMERIC, observed_at=observed_at)
    _vital(store, case_id, concepts.SPO2, spo2, ValueType.NUMERIC, observed_at=observed_at)
    _vital(store, case_id, concepts.HEART_RATE, hr, ValueType.NUMERIC, observed_at=observed_at)
    _vital(store, case_id, concepts.SYSTOLIC_BP, sbp, ValueType.NUMERIC, observed_at=observed_at)
    _vital(store, case_id, concepts.TEMPERATURE, temp, ValueType.NUMERIC, observed_at=observed_at)
    _vital(store, case_id, concepts.CONSCIOUSNESS_LEVEL, consciousness, ValueType.CODED, observed_at=observed_at)
    _vital(store, case_id, concepts.SUPPLEMENTAL_OXYGEN, suppl_o2, ValueType.BOOLEAN, observed_at=observed_at)


# ---------------------------------------------------------------------
# 1 -- Adult, obvious critical presentation: Emergency Bypass, sub-second, no LLM.
# ---------------------------------------------------------------------
def _scenario_01(store: EventStore, profile: HospitalProfile) -> DemoScenario:
    from app.bypass.engine import evaluate_and_activate

    case = store.create_case(age_years=45)
    _vital(store, case.case_id, concepts.SPO2, 70.0, ValueType.NUMERIC)  # <=75 -> PROFOUND_HYPOXIA
    evaluate_and_activate(case, store, profile)
    return DemoScenario(
        number=1, key="CRITICAL_BYPASS_ADULT", title="Adult, obvious critical presentation",
        demonstrates="Emergency Bypass fires sub-second on a deterministic physiological trigger; skips the queue entirely, no LLM involved.",
        case_id=case.case_id, fidelity="FULL",
    )


# ---------------------------------------------------------------------
# 2 -- Adult, clearly minor complaint: correct low acuity, no over-triage.
# ---------------------------------------------------------------------
def _scenario_02(store: EventStore, profile: HospitalProfile) -> DemoScenario:
    case = store.create_case(age_years=30)
    _full_adult_vitals(store, case.case_id, rr=16, spo2=98, hr=72, sbp=118, temp=36.8)
    assess_case(case, store, profile)
    return DemoScenario(
        number=2, key="MINOR_COMPLAINT_ADULT", title="Adult, clearly minor complaint",
        demonstrates="Fully normal vitals score correctly low (no over-triage) via the same deterministic pipeline as every other case.",
        case_id=case.case_id, fidelity="FULL",
    )


# ---------------------------------------------------------------------
# 3 -- Ambiguous: vague symptoms, borderline vitals, self-reported only.
# ---------------------------------------------------------------------
def _scenario_03(store: EventStore, profile: HospitalProfile) -> DemoScenario:
    case = store.create_case(age_years=35)
    # Only 2 of 7 required concepts given, both self-reported and borderline
    # -- most of the picture is simply missing, not merely uncertain.
    _vital(
        store, case.case_id, concepts.SPO2, 94.0, ValueType.NUMERIC,
        source_type=SourceType.PATIENT, reliability_tier=ReliabilityTier.PATIENT_REPORTED,
    )
    _vital(
        store, case.case_id, concepts.RESP_RATE, 21.0, ValueType.NUMERIC,
        source_type=SourceType.PATIENT, reliability_tier=ReliabilityTier.PATIENT_REPORTED,
    )
    assess_case(case, store, profile)
    return DemoScenario(
        number=3, key="AMBIGUOUS_BORDERLINE_SELF_REPORTED", title="Ambiguous presentation, self-reported only",
        demonstrates="Low confidence band and outright abstention: the system holds the case at its configured safer floor and asks for a specific observation instead of guessing.",
        case_id=case.case_id, fidelity="FULL",
    )


# ---------------------------------------------------------------------
# 4 -- Paediatric: 3-year-old with fever.
# ---------------------------------------------------------------------
def _scenario_04(store: EventStore, profile: HospitalProfile) -> DemoScenario:
    case = store.create_case(age_years=3)
    _full_adult_vitals(store, case.case_id, rr=26, spo2=98, hr=110, sbp=100, temp=39.5)
    _vital(store, case.case_id, concepts.WORK_OF_BREATHING, "NORMAL", ValueType.CODED)
    assess_case(case, store, profile)
    return DemoScenario(
        number=4, key="PAEDIATRIC_FEVER_TODDLER", title="Paediatric: 3-year-old with fever",
        demonstrates="The Age Router selects PEWS, not NEWS2: every numeric vital sits inside this toddler's own normal range (PEWS TODDLER band) except temperature, which alone is enough to escalate under paediatric's tighter single-parameter threshold -- an adult-calibrated read of the same raw numbers would score very differently.",
        case_id=case.case_id, fidelity="FULL",
    )


# ---------------------------------------------------------------------
# 5 -- Paediatric: infant, subtle presentation.
# ---------------------------------------------------------------------
def _scenario_05(store: EventStore, profile: HospitalProfile) -> DemoScenario:
    case = store.create_case(age_years=0)
    _full_adult_vitals(store, case.case_id, rr=45, spo2=97, hr=130, sbp=85, temp=37.0)
    _vital(store, case.case_id, concepts.WORK_OF_BREATHING, "MODERATE", ValueType.CODED)
    assess_case(case, store, profile)
    return DemoScenario(
        number=5, key="PAEDIATRIC_INFANT_SUBTLE", title="Paediatric: infant, subtle presentation",
        demonstrates="Every numeric vital is unremarkable for this infant's own PEWS band -- the qualitative work-of-breathing sign alone drives the escalation, exactly as Phase 3.3 requires for paediatrics. (CP11 also fixed a real bug found while building this scenario: these same numeric vitals used to wrongly trip adult-calibrated hard triggers; see default.yaml's CP11 comment.)",
        case_id=case.case_id, fidelity="FULL",
    )


# ---------------------------------------------------------------------
# 6 -- Geriatric: 78-year-old, atypical presentation, blunted vitals.
# ---------------------------------------------------------------------
def _scenario_06(store: EventStore, profile: HospitalProfile) -> DemoScenario:
    case = store.create_case(age_years=78)
    _full_adult_vitals(store, case.case_id, rr=22, spo2=93, hr=95, sbp=105, temp=37.2)
    assess_case(case, store, profile)
    return DemoScenario(
        number=6, key="GERIATRIC_ATYPICAL", title="Geriatric: 78-year-old, atypical presentation",
        demonstrates="Identical raw vitals score more urgently under the geriatric adjustment's tightened aggregate-to-ESI bands than the same numbers would under the adult mapping -- why adult-calibrated thresholds under-triage the elderly.",
        case_id=case.case_id, fidelity="FULL",
    )


# ---------------------------------------------------------------------
# 7 -- Zero history: first-time patient, no record.
# ---------------------------------------------------------------------
def _scenario_07(store: EventStore, profile: HospitalProfile) -> DemoScenario:
    case = store.create_case(age_years=50)
    _full_adult_vitals(store, case.case_id, rr=17, spo2=97, hr=80, sbp=122, temp=37.0)
    assess_case(case, store, profile)
    return DemoScenario(
        number=7, key="ZERO_HISTORY_FIRST_TIME", title="Zero history, first-time patient",
        demonstrates="The system functions fully with no history block at all -- population defaults + missingness flags, never a fabricated history.",
        case_id=case.case_id, fidelity="FULL",
    )


# ---------------------------------------------------------------------
# 8 -- Returning patient, rich relevant history.
# ---------------------------------------------------------------------
def _scenario_08(store: EventStore, profile: HospitalProfile) -> DemoScenario:
    case = store.create_case(age_years=55, mrn="MRN-100958", display_name="Returning Patient")
    _full_adult_vitals(store, case.case_id, rr=18, spo2=96, hr=88, sbp=128, temp=37.1)
    _vital(
        store, case.case_id, concepts.HISTORY_CARDIAC, True, ValueType.BOOLEAN,
        source_type=SourceType.HISTORICAL_RECORD, reliability_tier=ReliabilityTier.CLINICIAN_OBSERVED,
    )
    _vital(
        store, case.case_id, concepts.HISTORY_RESPIRATORY, True, ValueType.BOOLEAN,
        source_type=SourceType.HISTORICAL_RECORD, reliability_tier=ReliabilityTier.CLINICIAN_OBSERVED,
    )
    _vital(
        store, case.case_id, concepts.SYMPTOM_CHEST_PAIN, True, ValueType.BOOLEAN,
        source_type=SourceType.PATIENT, reliability_tier=ReliabilityTier.PATIENT_REPORTED,
    )
    _vital(
        store, case.case_id, concepts.SYMPTOM_ONSET_MINUTES, 30.0, ValueType.NUMERIC,
        source_type=SourceType.PATIENT, reliability_tier=ReliabilityTier.PATIENT_REPORTED,
    )
    assess_case(case, store, profile)
    return DemoScenario(
        number=8, key="RETURNING_RICH_HISTORY", title="Returning patient, rich relevant history",
        demonstrates="History as an additive ML-challenger signal (cardiac/respiratory history + chest pain + recent onset), relevance-filtered rather than dumped onto the rules engine, which never reads history at all by design.",
        case_id=case.case_id, fidelity="FULL",
    )


# ---------------------------------------------------------------------
# 9 -- Patient whose repeat vitals worsen: Guardian Queue auto-escalation.
# ---------------------------------------------------------------------
def _scenario_09(store: EventStore, profile: HospitalProfile) -> DemoScenario:
    case = store.create_case(age_years=60)
    _full_adult_vitals(store, case.case_id, rr=20, spo2=95, hr=90, sbp=120, temp=37.0)
    assess_case(case, store, profile)

    later = utcnow() + timedelta(minutes=20)
    _full_adult_vitals(store, case.case_id, rr=26, spo2=92, hr=115, sbp=95, temp=38.5, observed_at=later)
    assess_case(case, store, profile, as_of=later)
    return DemoScenario(
        number=9, key="WORSENING_TREND_AUTO_ESCALATION", title="Patient whose repeat vitals worsen",
        demonstrates="Two consecutive RiskAssessments, each worse than the last -- the Time Engine's deterioration_trend reads WORSENING and the Guardian Queue re-sorts the case above newer, calmer arrivals without any human input.",
        case_id=case.case_id, fidelity="FULL",
    )


# ---------------------------------------------------------------------
# 10 -- Patient who taps "I feel worse".
# ---------------------------------------------------------------------
def _scenario_10(store: EventStore, profile: HospitalProfile) -> DemoScenario:
    case = store.create_case(age_years=40)
    _full_adult_vitals(store, case.case_id, rr=18, spo2=96, hr=84, sbp=124, temp=37.0)
    assess_case(case, store, profile)
    store.report_patient_worsening(case.case_id, note="Patient says the pain has gotten much worse.")
    return DemoScenario(
        number=10, key="SELF_REPORTED_WORSENING", title='Patient who taps "I feel worse"',
        demonstrates="One tap forces a reassessment prompt immediately, without waiting for the elapsed-time timer or touching acuity itself -- a waiting patient becomes an active sensor.",
        case_id=case.case_id, fidelity="FULL",
    )


# ---------------------------------------------------------------------
# 11 -- Patient whose reassessment interval lapses.
# ---------------------------------------------------------------------
def _scenario_11(store: EventStore, profile: HospitalProfile) -> DemoScenario:
    case = store.create_case(age_years=50)
    _full_adult_vitals(store, case.case_id, rr=19, spo2=95, hr=88, sbp=118, temp=37.2)
    assessment = assess_case(case, store, profile)  # ESI3 here -> 30 minute reassessment interval

    # A seed script cannot wait 30 real minutes for the elapsed-time timer
    # to trip on its own, so this reaches the exact same end state
    # (case.reassessment_overdue=True, REASSESSMENT_DUE logged) the timer
    # itself would produce, via the identical method the Guardian Queue
    # calls when it discovers a real lapse (CP7/CP9's flag_reassessment_
    # overdue) -- not a fabricated shortcut, just the same effect without
    # the wait. final_acuity is untouched either way.
    store.flag_reassessment_overdue(case.case_id)
    return DemoScenario(
        number=11, key="REASSESSMENT_INTERVAL_LAPSED", title="Reassessment interval lapses",
        demonstrates="REASSESSMENT_DUE fires and the Guardian Queue marks the case overdue -- and critically, final_acuity does not change just because time passed.",
        case_id=case.case_id, fidelity="FULL",
        note=f"Reassessment interval for this case's acuity ({assessment.final_acuity}) is "
             f"{profile.reassessment_minutes_for(assessment.final_acuity)} minutes; forced overdue directly rather than waiting it out.",
    )


# ---------------------------------------------------------------------
# 12 -- Operationally stuck: result available, unreviewed.
# ---------------------------------------------------------------------
def _scenario_12(store: EventStore, profile: HospitalProfile) -> DemoScenario:
    case = store.create_case(age_years=45)
    _full_adult_vitals(store, case.case_id, rr=18, spo2=96, hr=82, sbp=120, temp=37.0)
    assess_case(case, store, profile)

    now = utcnow()
    test = store.order_test(case.case_id, "XRAY", occurred_at=now - timedelta(hours=2))
    store.mark_sample_collected(test.test_id, occurred_at=now - timedelta(minutes=90))
    store.mark_result_available(test.test_id, occurred_at=now - timedelta(minutes=45))  # window is 30 min -- already stuck
    return DemoScenario(
        number=12, key="OPERATIONALLY_STUCK_RESULT_UNREVIEWED", title="Operationally stuck: result available, unreviewed",
        demonstrates="Stuck Patient Detection surfaces this on the ops list (GET /ops/stuck-patients), routed to the doctor queue, entirely separately from the acuity-ordered clinical queue -- and acuity is untouched.",
        case_id=case.case_id, fidelity="FULL",
    )


# ---------------------------------------------------------------------
# 13 -- Contradictory data: patient reports mild, device reports abnormal.
# ---------------------------------------------------------------------
def _scenario_13(store: EventStore, profile: HospitalProfile) -> DemoScenario:
    case = store.create_case(age_years=50)
    now = utcnow()
    _vital(store, case.case_id, concepts.SYMPTOM_TEXT, "Patient states they feel a little unwell, nothing severe.",
           ValueType.TEXT, source_type=SourceType.PATIENT, reliability_tier=ReliabilityTier.PATIENT_REPORTED, observed_at=now - timedelta(minutes=10))
    # Device reading comes first and is genuinely abnormal (tachycardic);
    # the patient's own later self-report of "feels normal" for the SAME
    # concept is deliberately timestamped AFTER it.
    _vital(store, case.case_id, concepts.HEART_RATE, 125.0, ValueType.NUMERIC,
           source_type=SourceType.DEVICE, reliability_tier=ReliabilityTier.MACHINE_MEASURED, observed_at=now - timedelta(minutes=10))
    _vital(store, case.case_id, concepts.HEART_RATE, 78.0, ValueType.NUMERIC,
           source_type=SourceType.PATIENT, reliability_tier=ReliabilityTier.PATIENT_REPORTED, observed_at=now)
    # The rest of the required concepts, unremarkable, so heart rate is the
    # one and only conflicting/interesting signal in this case.
    for code, val in ((concepts.RESP_RATE, 17.0), (concepts.SPO2, 97.0), (concepts.SYSTOLIC_BP, 118.0), (concepts.TEMPERATURE, 37.0)):
        _vital(store, case.case_id, code, val, ValueType.NUMERIC, observed_at=now)
    _vital(store, case.case_id, concepts.CONSCIOUSNESS_LEVEL, "ALERT", ValueType.CODED, observed_at=now)
    _vital(store, case.case_id, concepts.SUPPLEMENTAL_OXYGEN, False, ValueType.BOOLEAN, observed_at=now)
    assess_case(case, store, profile, as_of=now)
    return DemoScenario(
        number=13, key="CONTRADICTORY_DATA", title="Contradictory data: patient reports mild, device reports abnormal",
        demonstrates="Both HEART_RATE values remain visible with their sources and times; a DATA_CONFLICT_DETECTED event is raised (GET /cases/{id}/conflicts); and the more conservative (abnormal, 125 bpm) device reading is what scoring actually used -- not the patient's later, milder self-report -- until a human resolves it (POST /conflicts/{id}/resolve).",
        case_id=case.case_id, fidelity="FULL",
    )


# ---------------------------------------------------------------------
# 14 -- Missing vitals entirely.
# ---------------------------------------------------------------------
def _scenario_14(store: EventStore, profile: HospitalProfile) -> DemoScenario:
    case = store.create_case(age_years=42)
    assess_case(case, store, profile)
    return DemoScenario(
        number=14, key="MISSING_VITALS_ENTIRELY", title="Missing vitals entirely",
        demonstrates="Zero observations recorded: missingness caps acuity at the configured safety floor and devastates confidence to the point of abstention -- never silently treated as normal.",
        case_id=case.case_id, fidelity="FULL",
    )


# ---------------------------------------------------------------------
# 15 -- Ambulance pre-arrival, high acuity.
# ---------------------------------------------------------------------
def _scenario_15(store: EventStore, profile: HospitalProfile) -> DemoScenario:
    case = store.create_case(age_years=58, arrival_mode=ArrivalMode.AMBULANCE)
    _vital(store, case.case_id, concepts.RESP_RATE, 24.0, ValueType.NUMERIC,
           source_type=SourceType.PARAMEDIC, reliability_tier=ReliabilityTier.CLINICIAN_OBSERVED)
    _vital(store, case.case_id, concepts.SPO2, 90.0, ValueType.NUMERIC,
           source_type=SourceType.PARAMEDIC, reliability_tier=ReliabilityTier.CLINICIAN_OBSERVED)
    _vital(store, case.case_id, concepts.SYSTOLIC_BP, 85.0, ValueType.NUMERIC,
           source_type=SourceType.PARAMEDIC, reliability_tier=ReliabilityTier.CLINICIAN_OBSERVED)
    _vital(store, case.case_id, concepts.HEART_RATE, 115.0, ValueType.NUMERIC,
           source_type=SourceType.PARAMEDIC, reliability_tier=ReliabilityTier.CLINICIAN_OBSERVED)
    _vital(store, case.case_id, concepts.TEMPERATURE, 37.4, ValueType.NUMERIC,
           source_type=SourceType.PARAMEDIC, reliability_tier=ReliabilityTier.CLINICIAN_OBSERVED)
    _vital(store, case.case_id, concepts.CONSCIOUSNESS_LEVEL, "ALERT", ValueType.CODED,
           source_type=SourceType.PARAMEDIC, reliability_tier=ReliabilityTier.CLINICIAN_OBSERVED)
    _vital(store, case.case_id, concepts.SUPPLEMENTAL_OXYGEN, True, ValueType.BOOLEAN,
           source_type=SourceType.PARAMEDIC, reliability_tier=ReliabilityTier.CLINICIAN_OBSERVED)
    assess_case(case, store, profile)  # a predicted acuity while still PRE_ARRIVAL -- Phase 7.3's pre-alert content
    return DemoScenario(
        number=15, key="AMBULANCE_PREARRIVAL_HIGH_ACUITY", title="Ambulance pre-arrival, high acuity",
        demonstrates="Case created and scored before the patient physically arrives (status=PRE_ARRIVAL); the hospital gets a predicted acuity band to prepare the team ahead of time -- PATIENT_ARRIVED later transitions the SAME case, never a new one.",
        case_id=case.case_id, fidelity="FULL",
    )


# ---------------------------------------------------------------------
# 16 -- Ambulance patient with unconfirmed identity match.
# ---------------------------------------------------------------------
def _scenario_16(store: EventStore, profile: HospitalProfile) -> DemoScenario:
    case = store.create_case(age_years=68, arrival_mode=ArrivalMode.AMBULANCE)
    _full_adult_vitals(store, case.case_id, rr=20, spo2=95, hr=90, sbp=110, temp=37.3)
    assess_case(case, store, profile)
    # A candidate match is proposed (as an upstream matching search would
    # supply it -- see propose_identity_match's docstring) but deliberately
    # left UNCONFIRMED: "runs unlinked until confirmed."
    store.propose_identity_match(
        case.case_id, candidate_mrn="MRN-004821", candidate_display_name="Priya Sharma", confidence=0.82
    )
    return DemoScenario(
        number=16, key="AMBULANCE_UNCONFIRMED_IDENTITY", title="Ambulance patient with unconfirmed identity match",
        demonstrates="A candidate match is proposed with a confidence score but the case runs fully unlinked (history block empty) until a human explicitly confirms via POST /cases/{id}/identity/confirm -- never an automatic merge.",
        case_id=case.case_id, fidelity="PARTIAL",
        note="Confirm/propose steps are built; the fuzzy candidate-search itself (against a patient registry) is out of scope -- no such registry exists in this prototype.",
    )


# ---------------------------------------------------------------------
# 17 -- Clinician escalating override: one tap, no friction, instant.
# ---------------------------------------------------------------------
def _scenario_17(store: EventStore, profile: HospitalProfile) -> DemoScenario:
    case = store.create_case(age_years=44)
    _full_adult_vitals(store, case.case_id, rr=19, spo2=95, hr=92, sbp=116, temp=37.4)
    assess_case(case, store, profile)
    store.record_human_override(
        case.case_id, clinician_id="demo-nurse-01", role="NURSE", action=HumanDecisionAction.ESCALATE
    )
    return DemoScenario(
        number=17, key="CLINICIAN_ESCALATING_OVERRIDE", title="Clinician escalating override",
        demonstrates="One call, no reason code, applied instantly -- DecidingLayer.OVERRIDE now backs a fresh RiskAssessment and the case moves up the Guardian Queue immediately.",
        case_id=case.case_id, fidelity="FULL",
    )


# ---------------------------------------------------------------------
# 18 -- Clinician de-escalating override: reason code required, full audit.
# ---------------------------------------------------------------------
def _scenario_18(store: EventStore, profile: HospitalProfile) -> DemoScenario:
    case = store.create_case(age_years=50)
    _full_adult_vitals(store, case.case_id, rr=23, spo2=93, hr=100, sbp=108, temp=37.0)
    assessment = assess_case(case, store, profile)
    store.record_human_override(
        case.case_id,
        clinician_id="demo-doctor-01",
        role="DOCTOR",
        action=HumanDecisionAction.DE_ESCALATE,
        target_acuity=assessment.final_acuity + 1,
        reason_code=DeEscalationReasonCode.PATIENT_STABLE_ON_CLINICAL_REVIEW,
        free_text_reason="Repeat vitals normalised on direct review; patient ambulatory and comfortable.",
    )
    return DemoScenario(
        number=18, key="CLINICIAN_DEESCALATING_OVERRIDE", title="Clinician de-escalating override",
        demonstrates="Required a structured reason code and clinician identity; flagged for retrospective review (GET /overrides/flagged-for-review); the full HumanDecision audit record is retrievable via GET /cases/{id}/decisions for on-screen display.",
        case_id=case.case_id, fidelity="FULL",
    )


# ---------------------------------------------------------------------
# 19 -- Multilingual / voice intake.
# ---------------------------------------------------------------------
def _scenario_19(store: EventStore, profile: HospitalProfile) -> DemoScenario:
    case = store.create_case(age_years=29)
    _vital(
        store, case.case_id, concepts.SYMPTOM_TEXT,
        "मुझे सांस लेने में तकलीफ़ हो रही है और सीने में दर्द है",  # "I'm having difficulty breathing and chest pain"
        ValueType.TEXT, source_type=SourceType.PATIENT, reliability_tier=ReliabilityTier.PATIENT_REPORTED,
    )
    _full_adult_vitals(store, case.case_id, rr=22, spo2=94, hr=105, sbp=112, temp=37.1)
    assess_case(case, store, profile)
    return DemoScenario(
        number=19, key="MULTILINGUAL_VOICE_INTAKE", title="Multilingual / voice intake",
        demonstrates="Intended: LLM Intake Engine extracts structured vitals + symptoms from spoken/typed Hindi. NOT YET BUILT: the Intake Engine is explicitly deferred (needs a user-supplied LLM API key). This case seeds a real Hindi free-text symptom report (safe against the English-only bypass phrase list) alongside directly-entered structured vitals as a stand-in.",
        case_id=case.case_id, fidelity="PARTIAL",
        note="Structured vitals entered directly rather than extracted from the free text -- pending the Intake Engine checkpoint.",
    )


# ---------------------------------------------------------------------
# 20 -- ML challenger disagrees downward: the min() invariant refuses.
# Build the demo around this one.
# ---------------------------------------------------------------------
def _scenario_20(store: EventStore, profile: HospitalProfile) -> DemoScenario:
    case = store.create_case(age_years=40)
    # Deterministic aggregate = 7 (RR 3 + SpO2 3 + HR 1) -> adult ESI2 via
    # rules alone, with no chest-pain/history/onset signal for the ML
    # challenger to escalate on -- empirically verified (see CP11 checkpoint
    # report) to make the calibrated model suggest a materially LESS urgent
    # level than the rules engine.
    _full_adult_vitals(store, case.case_id, rr=25, spo2=91, hr=95, sbp=115, temp=37.0)
    assessment = assess_case(case, store, profile)
    return DemoScenario(
        number=20, key="ML_DISAGREES_DOWNWARD_MIN_INVARIANT", title="ML challenger disagrees downward",
        demonstrates="rule_acuity and ml_suggested_acuity visibly diverge (ML wants to go less urgent); final_acuity = min(...) always keeps the more urgent of the two, deciding_layer=RULES -- the min() invariant refusing to lower the level, on camera.",
        case_id=case.case_id, fidelity="FULL",
        note=f"Seeded result: rule_acuity={assessment.rule_acuity}, ml_suggested_acuity={assessment.ml_suggested_acuity}, "
             f"final_acuity={assessment.final_acuity}, deciding_layer={assessment.deciding_layer.value}.",
    )


_SCENARIO_BUILDERS = [
    _scenario_01, _scenario_02, _scenario_03, _scenario_04, _scenario_05,
    _scenario_06, _scenario_07, _scenario_08, _scenario_09, _scenario_10,
    _scenario_11, _scenario_12, _scenario_13, _scenario_14, _scenario_15,
    _scenario_16, _scenario_17, _scenario_18, _scenario_19, _scenario_20,
]


def seed_demo_patients(store: EventStore, profile: HospitalProfile) -> List[DemoScenario]:
    """Phase 14.1: creates all twenty scripted demo patients against
    `profile`. Intended for a fresh database; calling this twice creates a
    second batch of twenty rather than detecting/skipping duplicates --
    there is no tagging scheme here beyond the scenario `key`, which is
    deliberately not enforced unique (a demo re-seed is expected to be run
    against a clean DB, not de-duplicated against a dirty one)."""
    return [builder(store, profile) for builder in _SCENARIO_BUILDERS]
