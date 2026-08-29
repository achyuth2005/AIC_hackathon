"""
Schemas for Phase 7.2/7.3 ambulance ETA + pre-alert (CP18).
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class TransportDelayRequest(BaseModel):
    """Phase 7.2: 'a paramedic-controlled delayed flag.' No paramedic
    role/identity is modeled in this system's Auth/RBAC mock (CP9.5's
    three roles are nurse/doctor/admin) -- this endpoint is therefore
    unauthenticated, the same known-gap pattern already used for the
    'I feel worse' button and the human bypass affordance."""
    additional_minutes: float
    reason: Optional[str] = None
