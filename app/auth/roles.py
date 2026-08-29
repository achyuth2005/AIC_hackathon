"""
Role vocabulary for the CP9.5 Auth/RBAC mock (Phase 10.2: "Authentication:
role-based login, three roles (nurse, doctor, admin). No SSO build.").
Exactly the three roles the architecture names -- no PATIENT role exists
here, because the endpoints patients themselves use (the "I feel worse"
button, Phase 8.1) are deliberately zero-friction and unauthenticated;
adding a fourth role would gate a feature the architecture explicitly
wants frictionless.
"""
from enum import Enum


class Role(str, Enum):
    NURSE = "NURSE"
    DOCTOR = "DOCTOR"
    ADMIN = "ADMIN"
