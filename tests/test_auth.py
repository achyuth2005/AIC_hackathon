"""
Tests for the CP9.5 Auth/RBAC mock: login issuing a role-scoped token,
get_current_user/require_role's authentication and authorization behavior.
"""
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.auth.deps import get_current_user, require_role
from app.auth.jwt_utils import InvalidTokenError, create_access_token, decode_access_token
from app.auth.demo_users import DEMO_USERS
from app.auth.roles import Role


def test_login_issues_a_token_for_the_requested_role(client):
    resp = client.post("/auth/login", json={"role": "DOCTOR"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["role"] == "DOCTOR"
    assert body["access_token"]


def test_login_rejects_an_unknown_role(client):
    resp = client.post("/auth/login", json={"role": "SUPERUSER"})
    assert resp.status_code == 422  # not one of the three enum values


def test_token_round_trips_through_decode(client):
    user = DEMO_USERS[Role.ADMIN]
    token = create_access_token(user)
    payload = decode_access_token(token)
    assert payload["sub"] == user.user_id
    assert payload["role"] == "ADMIN"


def test_decode_rejects_a_tampered_token(client):
    user = DEMO_USERS[Role.NURSE]
    token = create_access_token(user)
    # Flip every character in the signature segment (not just the last
    # one): base64url's last character only encodes 2 of its 6 bits when
    # the preceding padding lines up a certain way, so flipping just the
    # final character can -- rarely, depending on the byte values that
    # happen to fall there -- decode back to the SAME underlying byte and
    # produce a still-valid signature by coincidence. Flipping the whole
    # segment removes that flakiness deterministically.
    header_payload, signature = token.rsplit(".", 1)
    flipped_signature = "".join("A" if c != "A" else "B" for c in signature)
    tampered = f"{header_payload}.{flipped_signature}"
    with pytest.raises(InvalidTokenError):
        decode_access_token(tampered)


# ---------------------------------------------------------------------
# require_role, exercised against a throwaway FastAPI app so this test
# doesn't depend on which real endpoint happens to use it.
# ---------------------------------------------------------------------
def _build_probe_app():
    app = FastAPI()

    @app.get("/whoami")
    def whoami(user=Depends(get_current_user)):
        return {"user_id": user.user_id, "role": user.role.value}

    @app.get("/admin-only")
    def admin_only(user=Depends(require_role(Role.ADMIN))):
        return {"ok": True}

    return TestClient(app)


def test_missing_token_is_401():
    probe = _build_probe_app()
    resp = probe.get("/whoami")
    assert resp.status_code == 401


def test_valid_token_resolves_to_the_right_identity():
    probe = _build_probe_app()
    token = create_access_token(DEMO_USERS[Role.DOCTOR])
    resp = probe.get("/whoami", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["role"] == "DOCTOR"


def test_require_role_blocks_a_disallowed_role():
    probe = _build_probe_app()
    nurse_token = create_access_token(DEMO_USERS[Role.NURSE])
    resp = probe.get("/admin-only", headers={"Authorization": f"Bearer {nurse_token}"})
    assert resp.status_code == 403


def test_require_role_allows_the_permitted_role():
    probe = _build_probe_app()
    admin_token = create_access_token(DEMO_USERS[Role.ADMIN])
    resp = probe.get("/admin-only", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
