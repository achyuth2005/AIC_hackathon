"""
CP9.5 Auth/RBAC mock's HTTP surface: a demo-shortcut login (Phase 10.2 /
895) that hands back a token for one of the three hard-coded roles. No
password, no session store, no SSO -- deliberately a mock, not a
production auth system. See app/auth/demo_users.py and app/auth/deps.py
for what this token actually gates.
"""
from __future__ import annotations

from fastapi import APIRouter

from app.auth.demo_users import DEMO_USERS
from app.auth.jwt_utils import create_access_token
from app.auth.models import AuthenticatedUser, LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest) -> TokenResponse:
    """Pick a role, get a token for that role's hard-coded demo identity.
    A frontend implements this as the "role selector dropdown, clearly
    labelled as a demo shortcut" the architecture doc names -- not a real
    login form."""
    user = DEMO_USERS[body.role]
    token = create_access_token(user)
    return TokenResponse(
        access_token=token,
        user=AuthenticatedUser(user_id=user.user_id, display_name=user.display_name, role=user.role),
    )
