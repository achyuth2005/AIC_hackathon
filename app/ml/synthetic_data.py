"""
Synthetic training data generator for the ML Risk Challenger (Phase 16.3).

"State the circularity plainly: a model trained on data you generated has
learned your generator, not clinical reality." This module IS that
generator, documented in full below so that circularity is visible rather
than hidden inside a black box. Every relationship encoded here is a
deliberate, simplified, illustrative choice -- none of it is sourced from a
clinical dataset -- and every one is [Assumption]. Do not treat any
resulting model as clinically validated (Phase 16.4's shadow-mode path
exists precisely because of this).

Phase 16.1's target, stated explicitly (repeated in TARGET_LABEL_DEFINITION
below and in app/ml/train.py's saved metadata, so it travels with the
artifact rather than living only in this docstring): **the probability of
a critical outcome within this ED visit**, where "critical outcome" is a
composite label meaning any of -- required immediate life-saving
intervention, required resuscitation-bay-level care, or required
critical-care admission. This synthetic generator does not simulate any
of those three outcomes individually; it operationalises "critical" as
membership in the most severe tail (~8%, LABEL_POSITIVE_PERCENTILE below)
of its own latent severity variable z, which is itself synthetic and
carries no clinical meaning outside this generator (see step 2). The
composite label's REAL-WORLD definition above is what a production
version of this model would need retrospective, clinician-adjudicated
labels for (Phase 16.4) -- this generator only demonstrates the mechanism
of producing and calibrating a probability against a stand-in for it.

Generative process, in order:
  1. Sample age_years uniformly over [0, 95].
  2. Sample a latent "true severity" z from a weighted combination of:
     age extremity (U-shaped: very young and very old skew sicker),
     three Bernoulli history flags, three Bernoulli symptom flags, and
     Gaussian noise. z has no clinical meaning outside this generator.
  3. Derive five vitals from z with a simple, monotonic, DIRECTIONAL
     relationship (higher z -> more deranged) plus independent Gaussian
     noise: respiratory rate and heart rate rise with z; SpO2 and
     (usually) systolic BP fall with z; temperature deviates from 37.0C in
     a randomly chosen direction (fever or hypothermia) scaled by z. Real
     physiology is far more nuanced (e.g. early sepsis can present with a
     normal-to-high blood pressure) -- this is intentionally simplified.
  4. Derive a second "follow-up" reading per trend-tracked vital
     (respiratory rate, heart rate, SpO2) by applying a further
     z-scaled shift, so vital_delta = follow_up - first is directionally
     informative of severity, the way Phase 16.2 asks trend features to be.
  5. Sample arrival mode and onset time with a mild z-dependent skew
     (sicker synthetic patients are modestly more likely to arrive by
     ambulance and more likely to have a short onset-to-arrival window).
  6. Apply missingness to every field independently at a fixed rate,
     UNCORRELATED with z or the label. This is a known, named
     simplification: real missingness patterns likely correlate with
     acuity, triage speed, or documentation burden, which a synthetic
     generator like this one cannot faithfully reproduce.
  7. Assign the binary label via a logistic function of z centred on a
     configurable percentile of the z distribution, so the base rate is a
     realistic minority class (not the ~50/50 a naive generator would
     produce) -- Phase 16.3: "Deliberately generate a realistic class
     imbalance rather than a balanced set."

Every sample round-trips through app/ml/features.py's own MLFeatures model
so the generated rows are in EXACTLY the schema and imputation convention
extract_features_from_case() produces at inference time -- training and
serving can never silently drift apart in field order or meaning.
"""
from __future__ import annotations

from typing import Tuple

import numpy as np

from app.ml.features import POPULATION_DEFAULTS, MLFeatures
from app.scoring import concepts

MISSINGNESS_RATE = 0.12  # [Assumption] applied independently to every field
LABEL_POSITIVE_PERCENTILE = 92  # z-distribution percentile centring the label logistic
LABEL_TEMPERATURE = 0.2  # sharper transition -> realistic ~10% base rate rather than a wide grey zone

# Phase 16.1: "Define the label explicitly and put the definition on a
# slide." This exact string is copied into app/ml/train.py's saved
# metadata.json so the definition ships with the trained artifact, not
# just this source file.
TARGET_LABEL_DEFINITION = (
    "Composite 'critical outcome within this ED visit': required immediate "
    "life-saving intervention, required resuscitation-bay-level care, or "
    "required critical-care admission. In this SYNTHETIC generator, "
    "operationalised as membership in the top ~8% of a latent severity "
    "variable (z) that has no clinical meaning outside the generator -- "
    "not a simulation of any of the three real outcomes individually. "
    "A production model requires retrospective, clinician-adjudicated "
    "labels for the real composite outcome (Phase 16.4)."
)


def _maybe_missing(rng: np.random.RandomState, value: float, default: float) -> Tuple[float, float]:
    if rng.random_sample() < MISSINGNESS_RATE:
        return default, 1.0
    return value, 0.0


def generate_dataset(n_samples: int = 3000, seed: int = 42):
    """Returns (X: np.ndarray [n, len(FEATURE_NAMES)], y: np.ndarray [n],
    age_years: np.ndarray [n]) -- age_years returned separately (even though
    it's also column 0 of X) so callers can slice per-age-band metrics
    (Phase 16.5) without re-deriving it from the imputed/vectorised form."""
    rng = np.random.RandomState(seed)

    age_years = rng.uniform(0, 95, size=n_samples)

    age_extremity = np.where(
        age_years < 2, (2 - age_years) / 2, np.where(age_years > 75, (age_years - 75) / 20, 0.0)
    )
    history_cardiac_raw = rng.binomial(1, 0.15, size=n_samples).astype(float)
    history_respiratory_raw = rng.binomial(1, 0.12, size=n_samples).astype(float)
    history_diabetes_raw = rng.binomial(1, 0.18, size=n_samples).astype(float)
    symptom_chest_pain_raw = rng.binomial(1, 0.12, size=n_samples).astype(float)
    symptom_breathlessness_raw = rng.binomial(1, 0.15, size=n_samples).astype(float)
    symptom_altered_consciousness_raw = rng.binomial(1, 0.05, size=n_samples).astype(float)

    z = (
        0.5 * age_extremity
        + 0.5 * history_cardiac_raw
        + 0.4 * history_respiratory_raw
        + 0.2 * history_diabetes_raw
        + 0.6 * symptom_chest_pain_raw
        + 0.6 * symptom_breathlessness_raw
        + 1.0 * symptom_altered_consciousness_raw
        + rng.normal(0, 0.3, size=n_samples)
    )

    resp_rate_raw = 16 + z * 6 + rng.normal(0, 2, size=n_samples)
    heart_rate_raw = 80 + z * 15 + rng.normal(0, 8, size=n_samples)
    spo2_raw = np.clip(97 - z * 4 + rng.normal(0, 1.5, size=n_samples), 70, 100)
    systolic_bp_raw = 120 - z * 10 + rng.normal(0, 10, size=n_samples)
    temp_direction = rng.choice([-1.0, 1.0], size=n_samples)
    temperature_raw = 37.0 + temp_direction * z * 0.5 + rng.normal(0, 0.4, size=n_samples)

    # Follow-up readings for trend deltas (step 4).
    resp_rate_followup = resp_rate_raw + z * 2 + rng.normal(0, 1.5, size=n_samples)
    heart_rate_followup = heart_rate_raw + z * 3 + rng.normal(0, 5, size=n_samples)
    spo2_followup = np.clip(spo2_raw - z * 1.5 + rng.normal(0, 1.0, size=n_samples), 70, 100)

    arrival_ambulance_p = np.clip(0.1 + 0.25 * z, 0.05, 0.9)
    arrival_mode_ambulance_raw = rng.binomial(1, arrival_ambulance_p).astype(float)

    onset_minutes_raw = np.clip(np.exp(rng.normal(5.5 - 0.3 * z, 0.8, size=n_samples)), 5, 4000)

    z_threshold = np.percentile(z, LABEL_POSITIVE_PERCENTILE)
    p_critical = 1.0 / (1.0 + np.exp(-(z - z_threshold) / LABEL_TEMPERATURE))
    y = rng.binomial(1, p_critical)

    rows = []
    for i in range(n_samples):
        resp_rate, resp_rate_missing = _maybe_missing(rng, resp_rate_raw[i], POPULATION_DEFAULTS[concepts.RESP_RATE])
        spo2, spo2_missing = _maybe_missing(rng, spo2_raw[i], POPULATION_DEFAULTS[concepts.SPO2])
        heart_rate, heart_rate_missing = _maybe_missing(rng, heart_rate_raw[i], POPULATION_DEFAULTS[concepts.HEART_RATE])
        systolic_bp, systolic_bp_missing = _maybe_missing(rng, systolic_bp_raw[i], POPULATION_DEFAULTS[concepts.SYSTOLIC_BP])
        temperature, temperature_missing = _maybe_missing(rng, temperature_raw[i], POPULATION_DEFAULTS[concepts.TEMPERATURE])

        # Trend deltas: missing if EITHER contributing reading is missing
        # (mirrors extract_features_from_case's "need 2 real readings").
        if rng.random_sample() < MISSINGNESS_RATE:
            resp_rate_delta, resp_rate_delta_missing = 0.0, 1.0
        else:
            resp_rate_delta, resp_rate_delta_missing = float(resp_rate_followup[i] - resp_rate_raw[i]), 0.0
        if rng.random_sample() < MISSINGNESS_RATE:
            heart_rate_delta, heart_rate_delta_missing = 0.0, 1.0
        else:
            heart_rate_delta, heart_rate_delta_missing = float(heart_rate_followup[i] - heart_rate_raw[i]), 0.0
        if rng.random_sample() < MISSINGNESS_RATE:
            spo2_delta, spo2_delta_missing = 0.0, 1.0
        else:
            spo2_delta, spo2_delta_missing = float(spo2_followup[i] - spo2_raw[i]), 0.0

        onset_minutes, onset_missing_flag = _maybe_missing(rng, onset_minutes_raw[i], 360.0)
        onset_band = 1.0 if onset_missing_flag else _band_onset(onset_minutes)

        history_cardiac, history_cardiac_missing = _maybe_missing(rng, history_cardiac_raw[i], 0.0)
        history_respiratory, history_respiratory_missing = _maybe_missing(rng, history_respiratory_raw[i], 0.0)
        history_diabetes, history_diabetes_missing = _maybe_missing(rng, history_diabetes_raw[i], 0.0)
        symptom_chest_pain, symptom_chest_pain_missing = _maybe_missing(rng, symptom_chest_pain_raw[i], 0.0)
        symptom_breathlessness, symptom_breathlessness_missing = _maybe_missing(rng, symptom_breathlessness_raw[i], 0.0)
        symptom_altered_consciousness, symptom_altered_consciousness_missing = _maybe_missing(
            rng, symptom_altered_consciousness_raw[i], 0.0
        )

        features = MLFeatures(
            age_years=float(age_years[i]),
            resp_rate=resp_rate, resp_rate_missing=resp_rate_missing,
            spo2=spo2, spo2_missing=spo2_missing,
            heart_rate=heart_rate, heart_rate_missing=heart_rate_missing,
            systolic_bp=systolic_bp, systolic_bp_missing=systolic_bp_missing,
            temperature=temperature, temperature_missing=temperature_missing,
            resp_rate_delta=resp_rate_delta, resp_rate_delta_missing=resp_rate_delta_missing,
            heart_rate_delta=heart_rate_delta, heart_rate_delta_missing=heart_rate_delta_missing,
            spo2_delta=spo2_delta, spo2_delta_missing=spo2_delta_missing,
            onset_band=onset_band, onset_missing=onset_missing_flag,
            arrival_mode_ambulance=float(arrival_mode_ambulance_raw[i]),
            history_cardiac=history_cardiac, history_cardiac_missing=history_cardiac_missing,
            history_respiratory=history_respiratory, history_respiratory_missing=history_respiratory_missing,
            history_diabetes=history_diabetes, history_diabetes_missing=history_diabetes_missing,
            symptom_chest_pain=symptom_chest_pain, symptom_chest_pain_missing=symptom_chest_pain_missing,
            symptom_breathlessness=symptom_breathlessness, symptom_breathlessness_missing=symptom_breathlessness_missing,
            symptom_altered_consciousness=symptom_altered_consciousness,
            symptom_altered_consciousness_missing=symptom_altered_consciousness_missing,
        )
        rows.append(features.to_vector())

    X = np.array(rows, dtype=float)
    return X, y, age_years


def _band_onset(minutes: float) -> float:
    if minutes < 60:
        return 0.0
    if minutes < 360:
        return 1.0
    if minutes < 1440:
        return 2.0
    return 3.0
