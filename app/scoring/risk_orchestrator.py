"""
The Phase 3.1 invariant, assembled and persisted:

    final_acuity = min(rule_based_acuity, ml_suggested_acuity, override_acuity_if_escalating)

This is the ONLY function in the codebase that ties together the Clinical
Scoring Engine (CP3/CP4, Layers 1/2/4), the ML Risk Challenger (CP6, Layer
3), and the Confidence & Abstention Engine (CP5), and persists the result
as an immutable RiskAssessment (Phase 4.3). The clinician-override term
(Phase 9.6) is not implemented yet -- CP9/10 -- so today's formula is
effectively final_acuity = min(rule_acuity, ml_suggested_acuity, abstention_floor).
"""
from __future__ import annotations

import hashlib
from datetime import datetime
from typing import List, Optional

from app.config.hospital_profile import HospitalProfile
from app.models.case import Case
from app.models.enums import DecidingLayer
from app.models.risk_assessment import RiskAssessment
from app.ml.challenger import MLChallenger
from app.ml.features import extract_features_from_case
from app.scoring import concepts
from app.scoring.confidence import compute_confidence
from app.scoring.engine import score_case
from app.store.event_store import EventStore

RULE_ENGINE_VERSION = "rules-v1"  # bump when NEWS2/PEWS/hard-trigger logic changes shape, not just config values

_ML_FEATURE_SOURCE_CONCEPTS = [
    concepts.RESP_RATE,
    concepts.SPO2,
    concepts.HEART_RATE,
    concepts.SYSTOLIC_BP,
    concepts.TEMPERATURE,
] + concepts.ML_FEATURE_CONCEPTS


def _snapshot_hash(observation_ids: List[str]) -> str:
    joined = "|".join(sorted(set(oid for oid in observation_ids if oid)))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def _collect_ml_observation_ids(store: EventStore, case_id: str) -> List[str]:
    ids = []
    for concept_code in _ML_FEATURE_SOURCE_CONCEPTS:
        obs = store.get_latest_current_observation(case_id, concept_code)
        if obs is not None:
            ids.append(obs.observation_id)
    return ids


def assess_case(
    case: Case,
    store: EventStore,
    profile: HospitalProfile,
    as_of: Optional[datetime] = None,
    commit: bool = True,
) -> RiskAssessment:
    """`commit=False`: threaded straight through to
    EventStore.save_risk_assessment so a caller composing this with other
    writes in the same request (POST /cases/{id}/observations composes
    this with the observation write and evaluate_and_activate()) can keep
    the whole thing in one transaction -- a scoring failure here then rolls
    back the observation too, rather than leaving it permanently persisted
    with no assessment ever computed against it."""
    result = score_case(case, store, profile, as_of)

    # ML does not run at all on an age-unknown case -- same scope boundary
    # CP4 drew for hard triggers: there is no reliable age-normalised
    # feature vector to build (Phase 3.3 Layer 1 gates everything after it).
    ml_prediction = None
    if not result.age_unknown and profile.ml_challenger.enabled:
        features = extract_features_from_case(case, store, profile, as_of)
        ml_prediction = MLChallenger(profile).predict(features)

    confidence = compute_confidence(
        result, profile, ml_suggested_acuity=ml_prediction.suggested_acuity if ml_prediction else None
    )

    if confidence.should_abstain:
        # Whenever abstention is active at all, "we didn't have enough
        # information" is the honest headline reason for the final value --
        # even if the abstention floor happens to numerically coincide with
        # what rules/ML would have produced anyway (e.g. the age-unknown
        # default and the abstention floor are both 3 in default.yaml).
        # Mislabeling that coincidence as an ordinary RULES decision would
        # bury exactly the fact Phase 9.2 wants surfaced.
        deciding_layer = DecidingLayer.ABSTENTION
    elif ml_prediction is not None and ml_prediction.suggested_acuity < result.rule_acuity:
        # Phase 3.3: "If it suggests a higher acuity than the rules, it
        # escalates". Equal to rule_acuity is agreement, not an escalation
        # -- credited to RULES, matching "if it suggests lower, the
        # suggestion is ... discarded operationally" (a tie is the same
        # non-event as a lower suggestion, just at the boundary).
        deciding_layer = DecidingLayer.ML
    else:
        deciding_layer = DecidingLayer.RULES

    component_observation_ids = [c.observation_id for c in result.components if c.observation_id]
    ml_observation_ids = _collect_ml_observation_ids(store, case.case_id) if ml_prediction is not None else []
    all_observation_ids = sorted(set(component_observation_ids) | set(ml_observation_ids))

    return store.save_risk_assessment(
        case_id=case.case_id,
        rule_engine_version=RULE_ENGINE_VERSION,
        rule_acuity=result.rule_acuity,
        rule_component_breakdown=[c.model_dump(mode="json") for c in result.components],
        ml_model_version=ml_prediction.model_version if ml_prediction else None,
        ml_probability=ml_prediction.probability if ml_prediction else None,
        ml_suggested_acuity=ml_prediction.suggested_acuity if ml_prediction else None,
        hard_triggers_fired=[t.model_dump(mode="json") for t in result.hard_triggers_fired],
        final_acuity=confidence.final_acuity,
        deciding_layer=deciding_layer,
        confidence_band=confidence.band,
        confidence_score=confidence.score,
        confidence_reasons=confidence.reasons,
        should_abstain=confidence.should_abstain,
        abstention_message=confidence.abstention_message,
        input_snapshot_hash=_snapshot_hash(all_observation_ids),
        input_observation_ids=all_observation_ids,
        computed_at=as_of,
        commit=commit,
    )
