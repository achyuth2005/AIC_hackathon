"""
Shared Observation -> VitalReading conversion. The Clinical Scoring Engine
(Phase 3.3 Layer 2, app/scoring/engine.py), the Emergency Bypass
physiological detector (Phase 3.5 #2, app/bypass/engine.py), and the ML
challenger's feature extraction (app/ml/features.py) all need "the current
reading for this concept, with staleness resolved against this hospital's
configured window" -- factored out once rather than duplicated.
"""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from app.config.hospital_profile import HospitalProfile
from app.models.observation import Observation
from app.scoring.models import VitalReading
from app.store.event_store import EventStore


def fetch_readings(
    store: EventStore,
    case_id: str,
    concept_codes: List[str],
    profile: HospitalProfile,
    as_of: Optional[datetime] = None,
    preferred_observations: Optional[Dict[str, Observation]] = None,
) -> Dict[str, Optional[VitalReading]]:
    """`preferred_observations` (Phase 9.3, CP13): when the caller has
    already resolved which observation should count for a given concept
    -- e.g. app/scoring/engine.py's Contradictory-Information resolution,
    which picks the more conservative of several disagreeing current
    readings rather than whichever is merely most recent -- that
    observation is used verbatim instead of re-querying "latest current".
    Callers that don't pass this (bypass detectors, ML feature
    extraction) keep the original latest-current-observation behaviour
    unchanged; see app/scoring/conflict_detection.py's module docstring
    for why that's a deliberate scope boundary, not an oversight."""
    preferred_observations = preferred_observations or {}
    readings: Dict[str, Optional[VitalReading]] = {}
    for concept_code in concept_codes:
        obs = preferred_observations.get(concept_code) or store.get_latest_current_observation(case_id, concept_code)
        if obs is None:
            readings[concept_code] = None
            continue
        staleness_window = profile.staleness_window_for(concept_code)
        readings[concept_code] = VitalReading(
            value=obs.value,
            unit=obs.unit,
            measurement_status=obs.measurement_status,
            observed_at=obs.observed_at,
            observation_id=obs.observation_id,
            is_stale=obs.is_stale(staleness_window, as_of=as_of),
            reliability_tier=obs.reliability_tier,
        )
    return readings
