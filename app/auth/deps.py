"""
FastAPI dependencies for the CP9.5 Auth/RBAC mock: extract and verify the
bearer token, expose the caller's identity+role to any endpoint that
declares a dependency on it.

This is the secure channel CP10's audit trail needs. Before CP9.5, an
endpoint like emergency-bypass took `triggered_by_role`/`triggered_by_id`
directly out of the request body -- a known, explicitly-flagged gap
(nothing stopped a client from claiming to be any role/identity it liked).
`get_current_user`/`require_role` replace that with identity read out of a
server-verified token, so "who did this" in the audit trail is trustworthy
rather than merely self-reported.
"""
from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.jwt_utils import InvalidTokenError, decode_access_token
from app.auth.models import AuthenticatedUser
from app.auth.roles import Role

# auto_error=False: a missing header should raise our own 401 with our own
# message, not FastAPI/Starlette's generic one.
_bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> AuthenticatedUser:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token.")
    try:
        payload = decode_access_token(credentials.credentials)
    except InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid or expired token: {exc}")
    return AuthenticatedUser(
        user_id=payload["sub"], display_name=payload["display_name"], role=Role(payload["role"])
    )


def require_role(*allowed_roles: Role):
    """Dependency factory: `Depends(require_role(Role.NURSE, Role.ADMIN))`.
    Phase 10.2 "least privilege by role", applied per-endpoint. Returns a
    dependency that both authenticates AND authorizes in one step."""

    def _check(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role {user.role.value} is not permitted to perform this action.",
            )
        return user

    return _check
