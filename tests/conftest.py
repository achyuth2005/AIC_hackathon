"""
Isolated in-memory SQLite DB per test, so tests never touch the dev
patienttriage.db file and never leak state between tests.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.store.event_store import EventStore


@pytest.fixture()
def db_session():
    # StaticPool: FastAPI executes sync routes in a worker thread pool, so
    # the `client` fixture's requests run on a different thread than this
    # fixture. SQLAlchemy's default pooling for sqlite ":memory:" hands out
    # a separate connection (and therefore a separate, tableless database)
    # per thread; StaticPool forces every checkout to share the one
    # connection that actually has the schema on it.
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    # Import models so they're registered on Base.metadata before create_all.
    from app.models import case, observation, event, risk_assessment, resource, diagnostic_test, human_decision, alert, data_conflict, case_review, ambulance_transport  # noqa: F401

    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def store(db_session):
    return EventStore(db_session)


@pytest.fixture()
def client(db_session, monkeypatch):
    """TestClient wired to the SAME in-memory session as db_session.
    app.main's startup hook calls init_db() against the real dev sqlite
    file by default -- that's a harmless no-op for correctness (schema is
    already created against db_session's engine, which is what requests
    actually use via the dependency override) but pollutes the real
    patienttriage.db file with empty tables on every test run, so it's
    monkeypatched out here rather than left as test-suite side effects."""
    import app.main as main_module

    monkeypatch.setattr(main_module, "init_db", lambda: None)

    def _override_get_db():
        yield db_session

    main_module.app.dependency_overrides[get_db] = _override_get_db
    with TestClient(main_module.app) as test_client:
        yield test_client
    main_module.app.dependency_overrides.clear()


def auth_headers(client, role: str = "NURSE") -> dict:
    """Audit remediation support: nearly every mutating/PHI-reading
    endpoint now requires an authenticated staff token (see
    app/auth/deps.py's require_role/get_current_user). Logs in via the
    real POST /auth/login flow (not a shortcut around it) and returns a
    ready-to-use Authorization header for the given role ("NURSE",
    "DOCTOR", or "ADMIN")."""
    resp = client.post("/auth/login", json={"role": role})
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def nurse_headers(client):
    return auth_headers(client, "NURSE")


@pytest.fixture()
def doctor_headers(client):
    return auth_headers(client, "DOCTOR")


@pytest.fixture()
def admin_headers(client):
    return auth_headers(client, "ADMIN")
