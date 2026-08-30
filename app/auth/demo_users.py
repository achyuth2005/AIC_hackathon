"""
CP9.5's "lightweight ... mock": exactly one hard-coded demo identity per
role (Phase 18.6/895: "JWT with three hard-coded roles ... demonstrates
RBAC without consuming a day"). This is NOT a user directory or a
credential store -- there is no password, no per-hospital staff list, and
no session management. A real deployment replaces this whole module with
a real identity provider (SSO / hospital directory); nothing downstream of
`AuthenticatedUser` (app/auth/models.py) needs to change when that
happens, because every consumer -- this module's own dependencies, and
CP10's audit trail -- only ever sees that same shape, never these
hard-coded records directly.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from app.auth.roles import Role


@dataclass(frozen=True)
class DemoUser:
    user_id: str
    display_name: str
    role: Role
    # Audit finding (RBAC/IDOR, dimension 1): the auth model previously had
    # no tenancy dimension at all -- any of the three roles could act on any
    # hospital_profile_id's data. Every demo identity is now scoped to a
    # hospital profile the same way a real SSO/directory claim would be, and
    # app/auth/deps.py's require_hospital_scope enforces it on every
    # ID-addressed lookup.
    hospital_profile_id: str = "default"


DEMO_USERS: Dict[Role, DemoUser] = {
    Role.NURSE: DemoUser(user_id="demo-nurse-01", display_name="Nurse Priya Nair", role=Role.NURSE),
    Role.DOCTOR: DemoUser(user_id="demo-doctor-01", display_name="Dr. Arjun Rao", role=Role.DOCTOR),
    Role.ADMIN: DemoUser(user_id="demo-admin-01", display_name="Admin Sana Sheikh", role=Role.ADMIN),
}
