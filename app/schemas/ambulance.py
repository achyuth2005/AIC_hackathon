"""
Schemas for Phase 7.2/7.3 ambulance ETA + pre-alert (CP18).
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class TransportDelayRequest(BaseModel):
    """Phase 7.2: 'a paramedic-controlled delayed flag.' No paramedic
    role/identity is modeled in this system's Auth/RBAC mock (CP9.5's
    three roles are nurse/doctor/admin) -- this endpoint is therefore
    unauthenticated, the same known-gap pattern already used for the
    'I feel worse' button and the human bypass affordance.

    Audit fix (Medium, dimension 3): `additional_minutes` previously had no
    lower bound. A negative value would silently *shorten* the ETA
    (EventStore.mark_transport_delayed does `+=`) on an unauthenticated
    endpoint -- "delayed" only ever means a positive addition."""
    additional_minutes: float = Field(gt=0)
    reason: Optional[str] = Field(default=None, max_length=500)
