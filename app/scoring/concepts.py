"""
Controlled vocabulary for the vital-sign/clinical-sign concepts the Scoring
Engine reads (Phase 3.2: "Mapping extracted terms to coded concepts ->
Deterministic lookup"). These are the concept_code values that belong in
Observation rows for NEWS2/PEWS scoring to find them.
"""

RESP_RATE = "RESP_RATE"
SPO2 = "SPO2"
SUPPLEMENTAL_OXYGEN = "SUPPLEMENTAL_OXYGEN"  # BOOLEAN
SYSTOLIC_BP = "SYSTOLIC_BP"
HEART_RATE = "HEART_RATE"
CONSCIOUSNESS_LEVEL = "CONSCIOUSNESS_LEVEL"  # CODED: see CONSCIOUSNESS_CODES
TEMPERATURE = "TEMPERATURE"
WORK_OF_BREATHING = "WORK_OF_BREATHING"  # CODED, paediatric only: see WORK_OF_BREATHING_CODES
SYMPTOM_TEXT = "SYMPTOM_TEXT"  # TEXT: free-text presenting complaint, scanned by the Emergency Bypass text detector (Phase 3.5 #3)

# Coded values for CONSCIOUSNESS_LEVEL. NEW_CONFUSION is NEWS2's own
# addition to plain AVPU ("new confusion" scores as non-alert even though a
# confused-but-talking patient is technically "Voice" on a literal AVPU
# reading).
CONSCIOUSNESS_CODES = {"ALERT", "NEW_CONFUSION", "VOICE", "PAIN", "UNRESPONSIVE"}

WORK_OF_BREATHING_CODES = {"NORMAL", "MILD", "MODERATE", "SEVERE"}

# The six NEWS2/PEWS-shared physiological parameters plus the two
# qualitative/boolean signs. Used by the engine to know what to fetch.
ADULT_REQUIRED_CONCEPTS = [
    RESP_RATE,
    SPO2,
    SUPPLEMENTAL_OXYGEN,
    SYSTOLIC_BP,
    HEART_RATE,
    CONSCIOUSNESS_LEVEL,
    TEMPERATURE,
]
PAEDIATRIC_REQUIRED_CONCEPTS = ADULT_REQUIRED_CONCEPTS + [WORK_OF_BREATHING]

# ---------------------------------------------------------------------
# CP6 additions: concepts the ML Risk Challenger reads that the
# deterministic frameworks above do not use at all (Phase 3.3 Layer 3:
# "features the fixed frameworks ignore" -- history, symptom flags, onset
# timing). Represented as ordinary Observations like everything else, just
# consumed by app/ml/features.py instead of news2.py/pews.py.
# ---------------------------------------------------------------------
SYMPTOM_ONSET_MINUTES = "SYMPTOM_ONSET_MINUTES"  # NUMERIC: minutes since symptom onset, patient/paramedic-reported

# Boolean history flags (SourceType.HISTORICAL_RECORD when sourced from a
# prior visit; SourceType.PATIENT/NURSE when reported fresh at intake).
HISTORY_CARDIAC = "HISTORY_CARDIAC"
HISTORY_RESPIRATORY = "HISTORY_RESPIRATORY"
HISTORY_DIABETES = "HISTORY_DIABETES"

# Boolean symptom flags -- structured, not the SYMPTOM_TEXT free-text field.
SYMPTOM_CHEST_PAIN = "SYMPTOM_CHEST_PAIN"
SYMPTOM_BREATHLESSNESS = "SYMPTOM_BREATHLESSNESS"
SYMPTOM_ALTERED_CONSCIOUSNESS = "SYMPTOM_ALTERED_CONSCIOUSNESS"

ML_FEATURE_CONCEPTS = [
    SYMPTOM_ONSET_MINUTES,
    HISTORY_CARDIAC,
    HISTORY_RESPIRATORY,
    HISTORY_DIABETES,
    SYMPTOM_CHEST_PAIN,
    SYMPTOM_BREATHLESSNESS,
    SYMPTOM_ALTERED_CONSCIOUSNESS,
]

# ---------------------------------------------------------------------
# Audit fix (dimension 3, Validation): the complete controlled vocabulary,
# as a set the API boundary can actually check a caller's concept_code
# against. Previously only app/llm/intake.py's Literal-typed extraction
# schema enforced "concept_code must be one of these" -- the direct
# POST /cases/{id}/observations path (ObservationCreateRequest) accepted
# any string, silently invisible to every downstream engine on a typo.
# Same discipline as KNOWN_EVENT_TYPES in app/models/event.py: add a new
# concept here deliberately, never by an unchecked string reaching a
# scorer that simply doesn't recognise it.
# ---------------------------------------------------------------------
KNOWN_CONCEPT_CODES = frozenset(
    ADULT_REQUIRED_CONCEPTS + PAEDIATRIC_REQUIRED_CONCEPTS + ML_FEATURE_CONCEPTS + [SYMPTOM_TEXT]
)

# Audit fix (dimension 3, Validation): plausible physiological bounds for
# the five numeric vitals, single-sourced here so the LLM Intake Engine
# (app/llm/intake.py) and the direct nurse-entry schema
# (app/schemas/observation.py) apply the identical check instead of the
# LLM path alone validating range while direct entry accepted anything.
# [Assumption], same convention as every clinical threshold in
# app/config/hospital_profile.py: generous outer bounds meant to catch
# data-entry errors (a stray digit, a unit mix-up), not to encode a
# clinical judgement about what's survivable. Values assumed to already be
# in the canonical unit noted below (Celsius for temperature) -- a caller
# entering Fahrenheit directly (bypassing the LLM intake path's own
# unit-aware normalisation) is a known, separate scope boundary, not
# silently mishandled by widening these bounds to cover both scales.
VITAL_PLAUSIBLE_RANGES = {
    RESP_RATE: (0.0, 100.0),
    SPO2: (0.0, 100.0),
    HEART_RATE: (0.0, 300.0),
    SYSTOLIC_BP: (0.0, 300.0),
    TEMPERATURE: (25.0, 45.0),  # Celsius
}
