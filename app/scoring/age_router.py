"""
Age Router (Phase 3.3 Layer 1): "Patient is routed by age into paediatric,
adult or geriatric logic before anything else happens. Each band has its own
reference ranges and its own escalation triggers. This is not an
optimisation, it is a safety requirement."

This module does nothing except resolve the band -- it never guesses or
defaults to ADULT on a gap. An unroutable age is the caller's (the
Clinical Scoring Engine's) problem to treat conservatively, not this
module's to paper over.
"""
from __future__ import annotations

from app.config.hospital_profile import HospitalProfile
from app.scoring.models import AgeRoutingResult


def route(age_years, profile: HospitalProfile) -> AgeRoutingResult:
    if age_years is None:
        return AgeRoutingResult(
            age_years=None,
            age_band=None,
            reason="Age not recorded for this case; cannot select an age-appropriate scoring framework.",
        )

    band = profile.age_band_for(age_years)
    if band is None:
        # Reachable only if a hospital profile's age_band_definitions has a
        # gap -- a configuration bug, not a normal runtime state, but still
        # handled the safe way rather than raising.
        return AgeRoutingResult(
            age_years=age_years,
            age_band=None,
            reason=f"No configured age band in profile '{profile.profile_id}' covers age {age_years}.",
        )

    return AgeRoutingResult(age_years=age_years, age_band=band)
