"""
AmbulanceTransport (Phase 7.2, CP18): "the ETA assumption" -- your
outbound travel time does not predict return travel time (four
independent reasons, see the architecture doc), so this project does not
attempt to derive an ETA from an outbound leg at all. Instead it follows
the doc's own explicit "Hackathon" recommendation: "simulate a GPS trace
along a route and show the ETA range narrowing as the vehicle
approaches. This demos in fifteen seconds and needs no real API key or
network dependency."

One row per PRE_ARRIVAL case (1:1 with Case) -- deliberately NOT
append-only, unlike almost everything else in this codebase, for the
same reason CaseReview (CP15) isn't: this represents a single evolving
fact ("this transport's current estimated total duration"), not a history
of facts. `delayed_additional_minutes` accumulates rather than replacing
the original estimate, so "how much longer than planned" stays visible.
"""
from __future__ import annotations

from sqlalchemy import Column, DateTime, Float, ForeignKey, String

from app.db import Base
from app.timeutil import utcnow as _utcnow


class AmbulanceTransport(Base):
    __tablename__ = "ambulance_transports"

    case_id = Column(String, ForeignKey("cases.case_id"), primary_key=True)
    transport_started_at = Column(DateTime(), nullable=False, default=_utcnow)
    estimated_total_minutes = Column(Float, nullable=False)
    delayed_additional_minutes = Column(Float, nullable=False, default=0.0)
    last_updated_at = Column(DateTime(), nullable=False, default=_utcnow)

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<AmbulanceTransport case={self.case_id} estimated_total_minutes="
            f"{self.estimated_total_minutes} delayed_additional_minutes={self.delayed_additional_minutes}>"
        )
