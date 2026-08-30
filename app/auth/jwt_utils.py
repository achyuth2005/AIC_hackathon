"""
JWT issuance/verification for the CP9.5 Auth/RBAC mock. HS256, a single
shared secret, short-lived tokens. This is a demo-appropriate session
policy, not a security-reviewed production one -- consistent with every
other [Assumption] in this codebase, stated rather than hidden.

`AUTH_SECRET_KEY` follows the same override-via-env-var pattern as
app/db.py's `DATABASE_URL`: unset in dev (falls back to an obviously-fake
default, loud about it), set for real by whoever deploys this.
"""
from __future__ import annotations

import os
from datetime import timedelta
from typing import Any, Dict

import jwt

from app.auth.demo_users import DemoUser
from app.timeutil import utcnow

_DEV_DEFAULT_SECRET = "dev-only-insecure-secret-DO-NOT-USE-IN-PRODUCTION"


def _load_secret_key() -> str:
    """Audit finding (Critical, dimension 1): the previous fallback let the
    app boot silently on the well-known, publicly-readable dev secret if an
    operator forgot to set AUTH_SECRET_KEY -- anyone who has seen this
    source (it's public) could forge a valid token for any role. Failing
    startup outright in a non-dev environment turns that into a deploy-time
    error instead of a silent, forgeable production secret."""
    key = os.environ.get("AUTH_SECRET_KEY")
    if key:
        return key
    app_env = os.environ.get("APP_ENV", "dev").lower()
    if app_env not in ("dev", "development", "test", "testing"):
        raise RuntimeError(
            "AUTH_SECRET_KEY is not set. Refusing to start with the public, "
            "well-known dev default outside dev/test (APP_ENV="
            f"{app_env!r}). Set AUTH_SECRET_KEY to a real secret."
        )
    return _DEV_DEFAULT_SECRET


SECRET_KEY = _load_secret_key()
ALGORITHM = "HS256"
TOKEN_TTL_MINUTES = 12 * 60  # a demo "shift", not a tuned security figure


class InvalidTokenError(ValueError):
    """Raised for a missing/expired/tampered/malformed token. The API
    layer maps this uniformly to HTTP 401."""
    pass


def create_access_token(user: DemoUser) -> str:
    now = utcnow()
    payload = {
        "sub": user.user_id,
        "role": user.role.value,
        "display_name": user.display_name,
        "hospital_profile_id": user.hospital_profile_id,
        "iat": now,
        "exp": now + timedelta(minutes=TOKEN_TTL_MINUTES),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError as exc:
        raise InvalidTokenError(str(exc)) from exc
