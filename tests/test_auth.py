"""
Tests for the CP9.5 Auth/RBAC mock: login issuing a role-scoped token,
get_current_user/require_role's authentication and authorization behavior.
"""
import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.auth.deps import get_current_user, require_hospital_scope, require_role
from app.auth.jwt_utils import InvalidTokenError, create_access_token, decode_access_token
from app.auth.demo_users import DEMO_USERS
from app.auth.models import AuthenticatedUser
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


# ---------------------------------------------------------------------
# Audit remediation: hospital-scope tenancy (dimension 1/IDOR).
# ---------------------------------------------------------------------
def test_token_carries_the_issuing_user_s_hospital_scope():
    user = DEMO_USERS[Role.NURSE]
    assert user.hospital_profile_id == "default"
    token = create_access_token(user)
    payload = decode_access_token(token)
    assert payload["hospital_profile_id"] == "default"


def test_a_token_predating_the_hospital_profile_id_claim_defaults_safely():
    """Audit fix robustness: decode_access_token's payload is trusted
    as-is by get_current_user, but a token issued before this claim
    existed (or a hand-built payload missing it) must not crash the
    request -- it defaults to "default" rather than raising a KeyError."""
    import jwt as pyjwt

    from app.auth.jwt_utils import ALGORITHM, SECRET_KEY, TOKEN_TTL_MINUTES
    from app.timeutil import utcnow
    from datetime import timedelta

    now = utcnow()
    legacy_payload = {
        "sub": "demo-nurse-01",
        "role": "NURSE",
        "display_name": "Nurse Priya Nair",
        "iat": now,
        "exp": now + timedelta(minutes=TOKEN_TTL_MINUTES),
        # no "hospital_profile_id" key at all
    }
    legacy_token = pyjwt.encode(legacy_payload, SECRET_KEY, algorithm=ALGORITHM)

    probe = _build_probe_app()
    resp = probe.get("/whoami", headers={"Authorization": f"Bearer {legacy_token}"})
    assert resp.status_code == 200


def test_require_hospital_scope_allows_matching_hospital():
    user = AuthenticatedUser(user_id="u1", display_name="Nurse", role=Role.NURSE, hospital_profile_id="hosp-a")
    require_hospital_scope(user, "hosp-a")  # must not raise


def test_require_hospital_scope_blocks_a_different_hospital_as_not_found():
    """A nurse authenticated for one hospital must not be able to
    distinguish "this record exists under another hospital" from "this
    record doesn't exist" -- both are a 404, never a 403 (see
    require_hospital_scope's own docstring on why that distinction itself
    would leak information in this domain)."""
    user = AuthenticatedUser(user_id="u1", display_name="Nurse", role=Role.NURSE, hospital_profile_id="hosp-a")
    with pytest.raises(HTTPException) as exc_info:
        require_hospital_scope(user, "hosp-b")
    assert exc_info.value.status_code == 404


def test_require_hospital_scope_blocks_an_unresolvable_hospital():
    user = AuthenticatedUser(user_id="u1", display_name="Nurse", role=Role.NURSE, hospital_profile_id="hosp-a")
    with pytest.raises(HTTPException) as exc_info:
        require_hospital_scope(user, None)
    assert exc_info.value.status_code == 404


def test_cross_hospital_case_access_is_404_not_leaked(client, store, nurse_headers):
    """End-to-end regression for the Critical IDOR finding: a staff token
    scoped to "default" must not be able to read a case created under a
    different hospital_profile_id, even by exact case_id. The case is
    seeded directly via the store (not the API) purely because there is no
    second hospital_profile YAML in this test fixture set to route
    load_hospital_profile() through -- the tenancy check under test runs
    entirely off the case's stored hospital_profile_id regardless of how
    it was created."""
    other_hospital_case = store.create_case(hospital_profile_id="other-hospital", age_years=40)

    # The "default"-scoped nurse cannot see it at all.
    resp = client.get(f"/cases/{other_hospital_case.case_id}", headers=nurse_headers)
    assert resp.status_code == 404
