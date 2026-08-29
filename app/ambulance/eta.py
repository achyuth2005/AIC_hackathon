"""
ETA range simulation (Phase 7.2, CP18).

"Your assumption that outbound travel time predicts return travel time
does not hold" -- four independent reasons given in the architecture doc
(directional/time-varying traffic, variable on-scene time, a possibly
different return destination, non-emergency-conditions return driving).
This module does not attempt to derive an ETA from any outbound leg at
all, and never will -- there is no outbound-leg data anywhere in this
schema to derive one from.

Instead it follows the doc's own explicit "Hackathon" recommendation
verbatim: "simulate a GPS trace along a route and show the ETA range
narrowing as the vehicle approaches. This demos in fifteen seconds and
needs no real API key or network dependency." `AmbulanceTransport`
(app/models/ambulance_transport.py) holds one simulated total-duration
estimate per case; this module turns "how much time has elapsed since
that estimate was made" into a range that narrows as the simulated
arrival approaches -- never a point estimate, matching Phase 6.4's own
wait-time-prediction discipline ("never present a single number").

[Assumption]: the narrowing curve itself (NARROWING_FRACTION,
MINIMUM_WIDTH_MINUTES below) is illustrative, not derived from any real
GPS/routing uncertainty model -- there is no real GPS trace in this
prototype, only a single simulated total-duration figure per transport.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.ambulance_transport import AmbulanceTransport
from app.timeutil import to_naive_utc, utcnow

# The range's half-width is this fraction of the remaining time, floored
# at a minimum so a report never claims false precision moments before
# arrival, and capped so a very early call doesn't show an absurdly wide
# range either. [Assumption], illustrative only.
NARROWING_FRACTION = 0.3
MINIMUM_WIDTH_MINUTES = 2.0
MAXIMUM_WIDTH_MINUTES = 20.0


class ETARange(BaseModel):
    lower_minutes: float
    upper_minutes: float
    arrived: bool  # simulated transport time has fully elapsed
    delayed_additional_minutes: float
    caveat: str = (
        "Simulated estimate, not a live GPS feed -- a range that narrows as the "
        "vehicle approaches, never a commitment. A paramedic-flagged delay changes it."
    )


def compute_eta_range(transport: AmbulanceTransport, as_of: Optional[datetime] = None) -> ETARange:
    now = to_naive_utc(as_of) if as_of is not None else utcnow()
    elapsed_minutes = (now - transport.transport_started_at).total_seconds() / 60.0
    total_minutes = transport.estimated_total_minutes + transport.delayed_additional_minutes
    remaining = max(0.0, total_minutes - elapsed_minutes)

    if remaining <= 0.0:
        return ETARange(
            lower_minutes=0.0, upper_minutes=0.0, arrived=True,
            delayed_additional_minutes=transport.delayed_additional_minutes,
        )

    width = min(MAXIMUM_WIDTH_MINUTES, max(MINIMUM_WIDTH_MINUTES, remaining * NARROWING_FRACTION))
    lower = max(0.0, remaining - width / 2.0)
    upper = remaining + width / 2.0
    return ETARange(
        lower_minutes=round(lower, 1), upper_minutes=round(upper, 1), arrived=False,
        delayed_additional_minutes=transport.delayed_additional_minutes,
    )
