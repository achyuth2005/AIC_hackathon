"""
Pydantic shapes for the CP9.5 Auth/RBAC mock's HTTP surface.
"""
from __future__ import annotations

from pydantic import BaseModel

from app.auth.roles import Role


class AuthenticatedUser(BaseModel):
    """The identity a verified token resolves to. Every endpoint that
    needs to know "who is doing this" (CP10's audit trail, above all)
    depends on this shape, never on raw request-body fields -- that is
    precisely the gap CP9.5 closes (see app/auth/deps.py).

    `hospital_profile_id` closes a separate, previously-open gap (audit
    finding, dimension 1): a role alone ("NURSE") is not a tenancy claim.
    Without this field, any authenticated staff member of any hospital
    could act on any other hospital's cases/resources/alerts by ID -- an
    IDOR that authentication alone does not close. This field is the unit
    app/auth/deps.py's require_hospital_scope checks against."""
    user_id: str
    display_name: str
    role: Role
    hospital_profile_id: str = "default"


class LoginRequest(BaseModel):
    """CP9.5's demo shortcut: pick a role, get a token for that role's one
    hard-coded demo identity. No password -- the architecture doc
    explicitly names this exact simplification ('role selector dropdown,
    clearly labelled as a demo shortcut') as an acceptable substitute for
    real SSO in a hackathon build."""
    role: Role


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthenticatedUser
