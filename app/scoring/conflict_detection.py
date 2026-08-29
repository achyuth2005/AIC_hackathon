"""
Contradictory Information (Phase 9.3, CP13): "Do not average, do not
silently pick one. Flag both values with their sources and times, surface
a DATA_CONFLICT_DETECTED event, and compute acuity from the more
conservative value until a human resolves it."

Conservativeness is scored via the SAME per-parameter tables the
framework scorers (news2.py/pews.py) use for real scoring
(evaluate_range_bands / evaluate_coded_points / deviation_points), passed
in by the caller as `scorers` -- never a separate, parallel "which
direction is worse" rule that could silently drift out of sync with the
tables that actually decide acuity.

Scope boundary, stated once here rather than re-litigated per call site:
this module is wired into app/scoring/engine.py's score_case() only --
the one place "acuity" is actually computed (Phase 9.3's own wording).
The Emergency Bypass detectors (app/bypass/engine.py) and the ML
challenger's feature extraction (app/ml/features.py) each call
fetch_readings independently and keep using plain "latest current
observation", not conflict-aware resolution:
  - Bypass is meant to be sub-millisecond, always-on arithmetic over
    whatever just arrived; recency matters more than reconciling two
    disagreeing readings for a peri-arrest check.
  - The ML challenger is escalation-only and sits behind Phase 3.1's
    min() -- the rules acuity (which DOES go through conflict
    resolution) still wins if ML is conflict-blind, so the safety
    invariant is unaffected.
Both are deliberate, not silently inconsistent.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Dict, List, Optional

from app.models.enums import MeasurementStatus
from app.models.observation import Observation
from app.store.event_store import EventStore

ConservativenessScorer = Callable[[object], int]


@dataclass
class ResolvedConcept:
    """What score_case should use for this concept: either the sole
    current reading (no conflict), the automatically-conservative one (an
    unresolved conflict), or a human's chosen one (a resolved conflict)."""
    observation: Observation
    is_conflict: bool = False
    conflict_id: Optional[str] = None
    newly_detected: bool = False
    conservative_observation_id: Optional[str] = None
    all_observation_ids: Optional[List[str]] = None


def resolve_conflicts_for_scoring(
    store: EventStore,
    case_id: str,
    concept_codes: List[str],
    scorers: Dict[str, ConservativenessScorer],
    staleness_window_for: Callable[[str], Optional[object]],
    as_of: Optional[datetime] = None,
) -> Dict[str, ResolvedConcept]:
    """One entry per concept in `concept_codes` that has at least one
    usable (current, MEASURED, non-stale) observation AND a configured
    scorer. A concept with zero such observations, or no scorer at all
    (e.g. SYMPTOM_TEXT -- there is nothing to numerically compare a
    free-text value against), is simply absent from the result; the
    caller's normal 'missing' handling applies unchanged.

    Does NOT persist anything itself -- returns which concepts have a
    newly-detected conflict (`newly_detected=True`) so the caller
    (score_case) can persist it via EventStore.create_data_conflict once
    it has decided the call is really happening (keeping this function a
    pure read + decide step, like every other function in app/scoring/
    that isn't app/scoring/engine.py itself)."""
    resolved: Dict[str, ResolvedConcept] = {}
    for concept_code in concept_codes:
        scorer = scorers.get(concept_code)
        if scorer is None:
            continue

        window = staleness_window_for(concept_code)
        candidates = [
            o
            for o in store.get_current_observations(case_id, concept_code)
            if o.measurement_status == MeasurementStatus.MEASURED and not o.is_stale(window, as_of=as_of)
        ]
        if not candidates:
            continue

        distinct_values = {o.value for o in candidates}
        if len(distinct_values) < 2:
            resolved[concept_code] = ResolvedConcept(observation=candidates[-1])
            continue

        observation_ids = sorted(o.observation_id for o in candidates)
        scored = sorted(candidates, key=lambda o: scorer(o.value), reverse=True)
        conservative = scored[0]

        existing = store.find_data_conflict_by_observation_set(case_id, concept_code, observation_ids)
        if existing is not None and existing.resolved:
            chosen = next(
                (o for o in candidates if o.observation_id == existing.kept_observation_id), conservative
            )
            resolved[concept_code] = ResolvedConcept(
                observation=chosen, is_conflict=True, conflict_id=existing.conflict_id,
            )
        else:
            resolved[concept_code] = ResolvedConcept(
                observation=conservative,
                is_conflict=True,
                conflict_id=existing.conflict_id if existing else None,
                newly_detected=existing is None,
                conservative_observation_id=conservative.observation_id,
                all_observation_ids=observation_ids,
            )
    return resolved
