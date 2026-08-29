"""
Feature schema for the ML Risk Challenger (Phase 3.3 Layer 3, Phase 16.2).

Phase 16.2 feature categories, and where each lives below:
  - age-normalised vital signs         -> age_years + the five vitals
  - vital trend deltas                 -> *_delta (Phase 16.2: "this is
                                           where ML beats a fixed score")
  - time since symptom onset, banded   -> onset_band
  - arrival mode                       -> arrival_mode_ambulance
  - relevant history flags             -> history_*
  - structured symptom flags           -> symptom_*
  - explicit missingness indicators
    for every field                    -> every feature above has a
                                           paired `*_missing` flag

[Assumption]: missing numeric vitals/onset are imputed to a fixed
population-typical default (see POPULATION_DEFAULTS) rather than left as
NaN, purely because scikit-learn's LogisticRegression cannot consume NaN.
This is safe ONLY because every imputed feature is paired with its own
missingness flag (Phase 16.2's own requirement) -- the model is trained to
read "value=default AND missing=1" as "we do not know this", not as
"this is normal". This is a different, and deliberately looser, rule than
the Clinical Scoring Engine's (Phase 3.3) "never impute as normal", which
applies to the deterministic score a clinician sees directly; this
imputation is purely an internal numerical-input requirement of the
escalation-only ML layer, invisible outside app/ml/.

Missing boolean history/symptom flags default to False (0), not
imputed-and-flagged the same way as vitals -- most real EHR problem lists
and intake forms only record a history/symptom flag when it is POSITIVE, so
"not recorded" and "recorded absent" are usually the same thing in
practice. Still paired with a missingness flag for audit symmetry and in
case a hospital's data does distinguish the two.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from app.config.hospital_profile import HospitalProfile
from app.models.case import Case
from app.models.enums import ArrivalMode, MeasurementStatus
from app.scoring import concepts
from app.scoring.readings import fetch_readings
from app.store.event_store import EventStore

# [Assumption]: rough adult-normal midpoints. Age is itself a feature, so
# the model has the information needed to partially compensate for an
# adult-shaped default being used on a paediatric/geriatric case when the
# corresponding missingness flag is 1.
POPULATION_DEFAULTS = {
    concepts.RESP_RATE: 16.0,
    concepts.SPO2: 97.0,
    concepts.HEART_RATE: 80.0,
    concepts.SYSTOLIC_BP: 120.0,
    concepts.TEMPERATURE: 37.0,
}

_TREND_CONCEPTS = [concepts.RESP_RATE, concepts.HEART_RATE, concepts.SPO2]

FEATURE_NAMES: List[str] = [
    "age_years",
    "resp_rate", "resp_rate_missing",
    "spo2", "spo2_missing",
    "heart_rate", "heart_rate_missing",
    "systolic_bp", "systolic_bp_missing",
    "temperature", "temperature_missing",
    "resp_rate_delta", "resp_rate_delta_missing",
    "heart_rate_delta", "heart_rate_delta_missing",
    "spo2_delta", "spo2_delta_missing",
    "onset_band", "onset_missing",
    "arrival_mode_ambulance",
    "history_cardiac", "history_cardiac_missing",
    "history_respiratory", "history_respiratory_missing",
    "history_diabetes", "history_diabetes_missing",
    "symptom_chest_pain", "symptom_chest_pain_missing",
    "symptom_breathlessness", "symptom_breathlessness_missing",
    "symptom_altered_consciousness", "symptom_altered_consciousness_missing",
]


class MLFeatures(BaseModel):
    age_years: float
    resp_rate: float
    resp_rate_missing: float
    spo2: float
    spo2_missing: float
    heart_rate: float
    heart_rate_missing: float
    systolic_bp: float
    systolic_bp_missing: float
    temperature: float
    temperature_missing: float
    resp_rate_delta: float
    resp_rate_delta_missing: float
    heart_rate_delta: float
    heart_rate_delta_missing: float
    spo2_delta: float
    spo2_delta_missing: float
    onset_band: float  # 0=<1h, 1=1-6h, 2=6-24h, 3=>24h
    onset_missing: float
    arrival_mode_ambulance: float
    history_cardiac: float
    history_cardiac_missing: float
    history_respiratory: float
    history_respiratory_missing: float
    history_diabetes: float
    history_diabetes_missing: float
    symptom_chest_pain: float
    symptom_chest_pain_missing: float
    symptom_breathlessness: float
    symptom_breathlessness_missing: float
    symptom_altered_consciousness: float
    symptom_altered_consciousness_missing: float

    def to_vector(self) -> List[float]:
        return [getattr(self, name) for name in FEATURE_NAMES]


def _onset_band(minutes: Optional[float]) -> float:
    if minutes is None:
        return 1.0  # mid-range placeholder; onset_missing flag carries the real signal
    if minutes < 60:
        return 0.0
    if minutes < 360:
        return 1.0
    if minutes < 1440:
        return 2.0
    return 3.0


def extract_features_from_case(
    case: Case, store: EventStore, profile: HospitalProfile, as_of: Optional[datetime] = None
) -> MLFeatures:
    """DB-backed extraction for a real case. Requires case.age_years to be
    known -- the caller (app/scoring/risk_orchestrator.py) is responsible
    for not invoking the ML challenger at all on an age-unknown case, the
    same scope boundary CP4's hard triggers already draw."""
    if case.age_years is None:
        raise ValueError("extract_features_from_case requires a known case.age_years")

    vital_concepts = [concepts.RESP_RATE, concepts.SPO2, concepts.HEART_RATE, concepts.SYSTOLIC_BP, concepts.TEMPERATURE]
    readings = fetch_readings(store, case.case_id, vital_concepts + concepts.ML_FEATURE_CONCEPTS, profile, as_of)

    def numeric_or_default(concept_code: str) -> tuple:
        reading = readings.get(concept_code)
        if reading is None or reading.measurement_status != MeasurementStatus.MEASURED or reading.is_stale:
            return POPULATION_DEFAULTS[concept_code], 1.0
        return float(reading.value), 0.0

    def boolean_or_default(concept_code: str) -> tuple:
        reading = readings.get(concept_code)
        if reading is None or reading.measurement_status != MeasurementStatus.MEASURED or reading.is_stale:
            return 0.0, 1.0
        return (1.0 if bool(reading.value) else 0.0), 0.0

    def trend_delta(concept_code: str) -> tuple:
        recent = store.get_recent_current_observations(case.case_id, concept_code, limit=2)
        measured = [
            o for o in recent
            if o.measurement_status == MeasurementStatus.MEASURED
        ]
        if len(measured) < 2:
            return 0.0, 1.0
        latest, previous = measured[0], measured[1]  # ordered desc by observed_at
        return float(latest.value - previous.value), 0.0

    resp_rate, resp_rate_missing = numeric_or_default(concepts.RESP_RATE)
    spo2, spo2_missing = numeric_or_default(concepts.SPO2)
    heart_rate, heart_rate_missing = numeric_or_default(concepts.HEART_RATE)
    systolic_bp, systolic_bp_missing = numeric_or_default(concepts.SYSTOLIC_BP)
    temperature, temperature_missing = numeric_or_default(concepts.TEMPERATURE)

    resp_rate_delta, resp_rate_delta_missing = trend_delta(concepts.RESP_RATE)
    heart_rate_delta, heart_rate_delta_missing = trend_delta(concepts.HEART_RATE)
    spo2_delta, spo2_delta_missing = trend_delta(concepts.SPO2)

    onset_reading = readings.get(concepts.SYMPTOM_ONSET_MINUTES)
    if onset_reading is None or onset_reading.measurement_status != MeasurementStatus.MEASURED:
        onset_band, onset_missing = _onset_band(None), 1.0
    else:
        onset_band, onset_missing = _onset_band(float(onset_reading.value)), 0.0

    history_cardiac, history_cardiac_missing = boolean_or_default(concepts.HISTORY_CARDIAC)
    history_respiratory, history_respiratory_missing = boolean_or_default(concepts.HISTORY_RESPIRATORY)
    history_diabetes, history_diabetes_missing = boolean_or_default(concepts.HISTORY_DIABETES)
    symptom_chest_pain, symptom_chest_pain_missing = boolean_or_default(concepts.SYMPTOM_CHEST_PAIN)
    symptom_breathlessness, symptom_breathlessness_missing = boolean_or_default(concepts.SYMPTOM_BREATHLESSNESS)
    symptom_altered_consciousness, symptom_altered_consciousness_missing = boolean_or_default(
        concepts.SYMPTOM_ALTERED_CONSCIOUSNESS
    )

    return MLFeatures(
        age_years=float(case.age_years),
        resp_rate=resp_rate, resp_rate_missing=resp_rate_missing,
        spo2=spo2, spo2_missing=spo2_missing,
        heart_rate=heart_rate, heart_rate_missing=heart_rate_missing,
        systolic_bp=systolic_bp, systolic_bp_missing=systolic_bp_missing,
        temperature=temperature, temperature_missing=temperature_missing,
        resp_rate_delta=resp_rate_delta, resp_rate_delta_missing=resp_rate_delta_missing,
        heart_rate_delta=heart_rate_delta, heart_rate_delta_missing=heart_rate_delta_missing,
        spo2_delta=spo2_delta, spo2_delta_missing=spo2_delta_missing,
        onset_band=onset_band, onset_missing=onset_missing,
        arrival_mode_ambulance=1.0 if case.arrival_mode == ArrivalMode.AMBULANCE else 0.0,
        history_cardiac=history_cardiac, history_cardiac_missing=history_cardiac_missing,
        history_respiratory=history_respiratory, history_respiratory_missing=history_respiratory_missing,
        history_diabetes=history_diabetes, history_diabetes_missing=history_diabetes_missing,
        symptom_chest_pain=symptom_chest_pain, symptom_chest_pain_missing=symptom_chest_pain_missing,
        symptom_breathlessness=symptom_breathlessness, symptom_breathlessness_missing=symptom_breathlessness_missing,
        symptom_altered_consciousness=symptom_altered_consciousness,
        symptom_altered_consciousness_missing=symptom_altered_consciousness_missing,
    )
