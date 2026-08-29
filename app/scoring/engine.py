"""
Clinical Scoring Engine orchestration (Phase 3.3 Layers 1-2 and, as of CP4,
Layer 4): Age Router -> concept fetch -> framework dispatch -> hard-trigger
override. This is the only module in app/scoring/ that touches the database
(via EventStore); news2.py/pews.py/hard_triggers.py remain pure functions
over VitalReading dicts so their arithmetic is directly unit-testable.

Explicitly NOT yet in scope here (later checkpoints):
  - The ML challenger and the final min(rules, ml, override) invariant
    (Phase 3.1) -- CP6. This engine only produces the "rules" term of that
    min(); hard_triggers_fired is carried on the result for CP6 to fold in.
  - Persisting the result as a RiskAssessment record / emitting
    RISK_ASSESSMENT_COMPUTED or HARD_TRIGGER_FIRED events (Phase 4.3) -- also
    CP6. score_case() does not persist its OWN result (still the caller's
    job, exactly as before) and can still be called freely (e.g. by the
    Guardian Queue re-scoring loop, CP7/8) without duplicating a
    RiskAssessment.
  - A full confidence/abstention *band* with reasons (Phase 9.1/9.2) -- CP5.
    What this engine does today (age-unknown handling, missing-data
    capping) is the minimum needed for its own correctness, not a
    substitute for CP5.

CP13 update: score_case() is no longer perfectly side-effect-free -- it
now also runs Phase 9.3 Contradictory-Information detection and persists
any NEWLY-found conflict (a DataConflict row + DATA_CONFLICT_DETECTED
event) via app/scoring/conflict_detection.py. This is safe to call
repeatedly for the same reason RiskAssessment-persistence duplication was
never a concern here: detection is deduplicated by the exact set of
observation_ids involved, so re-scoring an already-flagged conflict is a
no-op write, not a growing pile of duplicate rows.

Emergency Bypass (Phase 3.5) is a DIFFERENT, separate mechanism
(app/bypass/engine.py) that skips this scoring pipeline entirely -- it is
not called from here and does not feed into ClinicalScoreResult.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from app.config.hospital_profile import HospitalProfile, PEWSAgeBand
from app.models.case import Case
from app.scoring import age_router, concepts
from app.scoring.banding import deviation_points, evaluate_coded_points, evaluate_range_bands
from app.scoring.conflict_detection import resolve_conflicts_for_scoring
from app.scoring.hard_triggers import evaluate_hard_triggers
from app.scoring.models import ClinicalScoreResult
from app.scoring.news2 import score_news2
from app.scoring.pews import score_pews
from app.scoring.readings import fetch_readings
from app.store.event_store import EventStore


def _age_unknown_result(reason: str, profile: HospitalProfile) -> ClinicalScoreResult:
    return ClinicalScoreResult(
        framework="NONE",
        age_band=None,
        aggregate_score=None,
        framework_acuity=profile.unknown_age_default_esi_level,
        rule_acuity=profile.unknown_age_default_esi_level,
        components=[],
        age_unknown=True,
        reason=reason,
    )


def _apply_hard_triggers(
    result: ClinicalScoreResult, readings, profile: HospitalProfile, macro_age_band: str
) -> ClinicalScoreResult:
    fired = evaluate_hard_triggers(readings, profile.hard_trigger_definitions, macro_age_band)
    if not fired:
        return result

    override_level = min(t.target_esi_level for t in fired)
    new_acuity = min(result.rule_acuity, override_level)  # Layer 4 can only force MORE urgent, never less
    fired_labels = ", ".join(t.label for t in fired)
    return result.model_copy(
        update={
            "rule_acuity": new_acuity,
            "hard_triggers_fired": fired,
            "reason": result.reason + f"; HARD TRIGGER(S): {fired_labels} -> forced ESI {new_acuity}",
        }
    )


def _adult_conservativeness_scorers(profile: HospitalProfile) -> dict:
    """Phase 9.3 (CP13): the same NEWS2 parameter tables real scoring uses,
    reused directly so 'more conservative' can never silently drift out of
    sync with what actually decides acuity. Reused as-is for GERIATRIC too
    (Phase 3.3: geriatric reuses NEWS2's own parameter tables verbatim)."""
    return {
        concepts.RESP_RATE: lambda v: evaluate_range_bands(v, profile.news2.respiratory_rate),
        concepts.SPO2: lambda v: evaluate_range_bands(v, profile.news2.spo2_scale1),
        concepts.SYSTOLIC_BP: lambda v: evaluate_range_bands(v, profile.news2.systolic_bp),
        concepts.HEART_RATE: lambda v: evaluate_range_bands(v, profile.news2.pulse),
        concepts.TEMPERATURE: lambda v: evaluate_range_bands(v, profile.news2.temperature),
        concepts.CONSCIOUSNESS_LEVEL: lambda v: evaluate_coded_points(v, profile.news2.consciousness_points),
        concepts.SUPPLEMENTAL_OXYGEN: lambda v: 1 if v else 0,
    }


def _paediatric_conservativeness_scorers(profile: HospitalProfile, sub_band: PEWSAgeBand) -> dict:
    thresholds = profile.pews.deviation_band_thresholds
    return {
        concepts.RESP_RATE: lambda v: deviation_points(v, *sub_band.respiratory_rate_normal, thresholds),
        concepts.HEART_RATE: lambda v: deviation_points(v, *sub_band.heart_rate_normal, thresholds),
        concepts.SYSTOLIC_BP: lambda v: deviation_points(v, *sub_band.systolic_bp_normal, thresholds),
        concepts.SPO2: lambda v: evaluate_range_bands(v, profile.pews.spo2_scale1),
        concepts.TEMPERATURE: lambda v: evaluate_range_bands(v, profile.pews.temperature),
        concepts.CONSCIOUSNESS_LEVEL: lambda v: evaluate_coded_points(v, profile.pews.consciousness_points),
        concepts.WORK_OF_BREATHING: lambda v: evaluate_coded_points(v, profile.pews.work_of_breathing_points),
        concepts.SUPPLEMENTAL_OXYGEN: lambda v: 1 if v else 0,
    }


def _resolve_conflicts_and_persist(
    store: EventStore,
    case: Case,
    required_concepts,
    scorers: dict,
    profile: HospitalProfile,
    as_of: Optional[datetime],
) -> dict:
    """Phase 9.3 (CP13): detects and resolves any contradictory current
    readings among the concepts this scoring pass needs, persists any
    newly-found conflict as a DataConflict + DATA_CONFLICT_DETECTED event,
    and returns {concept_code: Observation} for fetch_readings'
    `preferred_observations` -- so a conflicted concept scores off the
    conservative (or, once a human has resolved it, their chosen) value
    rather than whichever observation merely has the latest timestamp."""
    resolved = resolve_conflicts_for_scoring(
        store, case.case_id, list(required_concepts), scorers, profile.staleness_window_for, as_of=as_of
    )
    preferred = {}
    for concept_code, r in resolved.items():
        preferred[concept_code] = r.observation
        if r.newly_detected:
            store.create_data_conflict(
                case_id=case.case_id,
                concept_code=concept_code,
                observation_ids=r.all_observation_ids,
                conservative_observation_id=r.conservative_observation_id,
                occurred_at=as_of,
            )
    return preferred


def score_case(
    case: Case, store: EventStore, profile: HospitalProfile, as_of: Optional[datetime] = None
) -> ClinicalScoreResult:
    """Phase 3.3 Layers 1, 2 and 4 end to end for one case: route by age,
    fetch the relevant concepts' latest current observations, dispatch to
    the correct published-framework scorer, then apply hard escalation
    triggers on top. Always returns a result -- age-unknown or an
    unconfigured age band degrades to `profile.unknown_age_default_esi_level`
    rather than raising, per Phase 9.2's "abstain, don't guess-low". Hard
    triggers are only evaluated once an age band is known (Layer 4 is
    scoped per Layer 1's bands, per Phase 3.3), not on the age-unknown path,
    which already holds at a conservative default."""
    routing = age_router.route(case.age_years, profile)

    if routing.age_band is None:
        return _age_unknown_result(routing.reason or "Age routing failed.", profile)

    if routing.age_band == "PAEDIATRIC":
        sub_band = profile.pews.band_for_age(routing.age_years)
        if sub_band is None:
            return _age_unknown_result(
                f"Age {routing.age_years} routed to PAEDIATRIC but matches no configured PEWS age sub-band.",
                profile,
            )
        required = set(concepts.PAEDIATRIC_REQUIRED_CONCEPTS) | _hard_trigger_concepts(profile)
        preferred = _resolve_conflicts_and_persist(
            store, case, required, _paediatric_conservativeness_scorers(profile, sub_band), profile, as_of
        )
        readings = fetch_readings(store, case.case_id, list(required), profile, as_of, preferred)
        result = score_pews(readings, profile.pews, sub_band)
        return _apply_hard_triggers(result, readings, profile, routing.age_band)

    if routing.age_band == "ADULT":
        required = set(concepts.ADULT_REQUIRED_CONCEPTS) | _hard_trigger_concepts(profile)
        preferred = _resolve_conflicts_and_persist(
            store, case, required, _adult_conservativeness_scorers(profile), profile, as_of
        )
        readings = fetch_readings(store, case.case_id, list(required), profile, as_of, preferred)
        result = score_news2(readings, profile.news2, profile.news2, "ADULT")
        return _apply_hard_triggers(result, readings, profile, routing.age_band)

    if routing.age_band == "GERIATRIC":
        required = set(concepts.ADULT_REQUIRED_CONCEPTS) | _hard_trigger_concepts(profile)
        preferred = _resolve_conflicts_and_persist(
            store, case, required, _adult_conservativeness_scorers(profile), profile, as_of
        )
        readings = fetch_readings(store, case.case_id, list(required), profile, as_of, preferred)
        result = score_news2(readings, profile.news2, profile.geriatric_adjustment, "GERIATRIC")
        return _apply_hard_triggers(result, readings, profile, routing.age_band)

    # Defensive only: reachable if a hospital profile defines an age band
    # name the engine doesn't know how to score -- a configuration bug.
    return _age_unknown_result(
        f"Age band '{routing.age_band}' has no configured scoring framework in the engine.",
        profile,
    )


def _hard_trigger_concepts(profile: HospitalProfile) -> set:
    """Ensures every concept a hard trigger references is actually fetched,
    even if it isn't one of the framework's own required parameters --
    otherwise a trigger on an unfetched concept would silently never fire."""
    return {d.condition.concept_code for d in profile.hard_trigger_definitions}
