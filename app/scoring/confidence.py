"""
Confidence & Abstention Engine (Phase 9.1, 9.2).

"Deterministic, composed of four inputs, surfaced as three bands with
reasons ... Low confidence never means low acuity. It means the system
says less and asks for more, while holding the patient at the safer
level." (Phase 9.1)

"The system must be able to say: 'insufficient information for a
recommendation. Nurse assessment required.' When it abstains it does not
fall back to a default low level. It holds a configured minimum band until
a human assesses." (Phase 9.2)

This module is a pure function over a ClinicalScoreResult (Phase 3.3
Layers 1-4) plus an optional ML suggestion -- no DB access, directly
unit-testable, and independent of whether CP6's ML challenger exists yet.
`ml_suggested_acuity=None` is not a placeholder for "not implemented"; it is
itself a legitimate confidence input (Phase 9.5: "ML model unavailable ->
confidence band drops") that will simply start reflecting a real value once
CP6 wires the challenger in, no changes needed here.
"""
from __future__ import annotations

from typing import List, Optional

from app.config.hospital_profile import AcuityBand, ConfidenceConfig, HospitalProfile
from app.models.enums import ConfidenceBand
from app.scoring.banding import evaluate_acuity_bands
from app.scoring.models import ClinicalScoreResult, ConfidenceResult


def _acuity_bands_for(result: ClinicalScoreResult, profile: HospitalProfile) -> Optional[List[AcuityBand]]:
    """Which AcuityBand list produced this result's framework_acuity --
    needed to compute 'distance from a band boundary' (input 3). Returns
    None for the age-unknown/no-framework path, where no aggregate-based
    banding applies at all."""
    if result.framework == "NEWS2":
        if result.age_band == "GERIATRIC":
            return profile.geriatric_adjustment.aggregate_to_esi
        return profile.news2.aggregate_to_esi
    if result.framework == "PEWS":
        return profile.pews.aggregate_to_esi
    return None


def _completeness_penalty(result: ClinicalScoreResult, cfg: ConfidenceConfig) -> tuple[float, List[str]]:
    if not result.components:
        return cfg.max_completeness_penalty, ["No vital signs recorded for this case."]

    missing = [c for c in result.components if c.is_missing]
    fraction_missing = len(missing) / len(result.components)
    penalty = cfg.max_completeness_penalty * fraction_missing

    reasons: List[str] = []
    if missing:
        labels = ", ".join(c.label for c in missing)
        reasons.append(f"{len(missing)} of {len(result.components)} vital signs not available ({labels}).")
    return penalty, reasons


def _ml_agreement_penalty(
    result: ClinicalScoreResult, ml_suggested_acuity: Optional[int], cfg: ConfidenceConfig
) -> tuple[float, List[str], bool]:
    if ml_suggested_acuity is None:
        return cfg.ml_unavailable_penalty, ["ML risk model was not available for this assessment."], False

    diff = abs(result.framework_acuity - ml_suggested_acuity)
    if diff == 0:
        return 0.0, [], True
    penalty = cfg.ml_disagreement_penalty_per_level * diff
    return (
        penalty,
        [f"ML challenger suggested ESI {ml_suggested_acuity} versus the rules' ESI {result.framework_acuity}."],
        True,
    )


def _boundary_penalty(
    result: ClinicalScoreResult, bands: Optional[List[AcuityBand]], cfg: ConfidenceConfig
) -> tuple[float, List[str]]:
    if bands is None or result.aggregate_score is None:
        return 0.0, []

    band = next(
        (
            b
            for b in bands
            if result.aggregate_score >= b.min_score and (b.max_score is None or result.aggregate_score <= b.max_score)
        ),
        None,
    )
    if band is None:
        return 0.0, []  # defensive: aggregate_score already validated by evaluate_acuity_bands upstream

    if band.max_score is not None and band.min_score == band.max_score:
        # A zero-width band (e.g. NEWS2's [0,0] "perfectly normal" band) has
        # no interior -- every value in it IS the edge, so "distance from
        # the boundary" isn't a meaningful concept here. Without this guard
        # every perfectly healthy patient would register as "borderline",
        # which would make the signal fire on the majority case instead of
        # discriminating anything.
        return 0.0, []

    # The lower edge only represents genuine ambiguity if a less-urgent band
    # actually exists below it (min_score > 0); the aggregate score has a
    # hard floor of 0, so sitting at a band's min_score of 0 is not "one
    # unlucky reading away from looking healthier" -- there is no healthier
    # reading than 0.
    lower_distance = (result.aggregate_score - band.min_score) if band.min_score > 0 else float("inf")
    upper_distance = (band.max_score - result.aggregate_score) if band.max_score is not None else float("inf")
    distance = min(lower_distance, upper_distance)

    if distance <= cfg.boundary_margin:
        return cfg.boundary_penalty, [f"Score is borderline for its acuity band (within {cfg.boundary_margin:g} point(s) of the next band)."]
    return 0.0, []


def _reliability_penalty(result: ClinicalScoreResult, cfg: ConfidenceConfig) -> tuple[float, List[str]]:
    used = [c for c in result.components if not c.is_missing and c.reliability_tier is not None]
    if not used:
        return 0.0, []

    per_component_penalties = [cfg.reliability_tier_penalties.get(int(c.reliability_tier), 0.0) for c in used]
    avg_penalty = sum(per_component_penalties) / len(per_component_penalties)

    reasons: List[str] = []
    low_reliability = [c for c in used if cfg.reliability_tier_penalties.get(int(c.reliability_tier), 0.0) > 0]
    if low_reliability:
        labels = ", ".join(c.label for c in low_reliability)
        reasons.append(f"Some inputs are lower-reliability (patient-reported or AI-inferred): {labels}.")
    return avg_penalty, reasons


def compute_confidence(
    result: ClinicalScoreResult,
    profile: HospitalProfile,
    ml_suggested_acuity: Optional[int] = None,
) -> ConfidenceResult:
    cfg = profile.confidence

    # Phase 3.1's own min(): folded in here so `final_acuity` below is
    # always the complete rules+ML combination (still missing only the
    # CP9/10 clinician-override term), not rules alone. ml_suggested_acuity
    # can only ever tighten this (lower the ESI number) -- if it's less
    # urgent than the rules, min() already discards it, which is exactly
    # Phase 3.3's "if it suggests lower, the suggestion is ... discarded
    # operationally."
    base_acuity = min(result.rule_acuity, ml_suggested_acuity) if ml_suggested_acuity is not None else result.rule_acuity

    # Total data void (no components at all -- covers both the age-unknown
    # path, whose components list is always empty, and a same-age-band case
    # with zero vitals recorded) abstains immediately regardless of score
    # arithmetic below (Phase 9.2).
    if not result.components:
        message = (
            "Age not recorded for this case; insufficient information for a recommendation. "
            "Nurse assessment required."
            if result.age_unknown
            else "No vital signs recorded; insufficient information for a recommendation. Nurse assessment required."
        )
        return ConfidenceResult(
            band=ConfidenceBand.LOW,
            score=0.0,
            reasons=[message],
            should_abstain=True,
            abstention_message=message,
            final_acuity=min(base_acuity, cfg.abstention_minimum_acuity),
            ml_considered=ml_suggested_acuity is not None,
        )

    reasons: List[str] = []
    score = 100.0

    completeness_penalty, completeness_reasons = _completeness_penalty(result, cfg)
    score -= completeness_penalty
    reasons += completeness_reasons

    ml_penalty, ml_reasons, ml_considered = _ml_agreement_penalty(result, ml_suggested_acuity, cfg)
    score -= ml_penalty
    reasons += ml_reasons

    bands = _acuity_bands_for(result, profile)
    boundary_penalty, boundary_reasons = _boundary_penalty(result, bands, cfg)
    score -= boundary_penalty
    reasons += boundary_reasons

    reliability_penalty, reliability_reasons = _reliability_penalty(result, cfg)
    score -= reliability_penalty
    reasons += reliability_reasons

    score = max(0.0, min(100.0, score))

    should_abstain = score < cfg.abstention_score_threshold
    abstention_message = None
    final_acuity = base_acuity
    if should_abstain:
        abstention_message = "Insufficient information for a confident recommendation. Nurse assessment required."
        final_acuity = min(base_acuity, cfg.abstention_minimum_acuity)
        reasons.append(abstention_message)

    if score >= cfg.high_confidence_min_score:
        band = ConfidenceBand.HIGH
    elif score >= cfg.medium_confidence_min_score:
        band = ConfidenceBand.MEDIUM
    else:
        band = ConfidenceBand.LOW

    if not reasons:
        reasons.append("All expected vitals present, machine-measured, and comfortably within their acuity band.")

    return ConfidenceResult(
        band=band,
        score=score,
        reasons=reasons,
        should_abstain=should_abstain,
        abstention_message=abstention_message,
        final_acuity=final_acuity,
        ml_considered=ml_considered,
    )
