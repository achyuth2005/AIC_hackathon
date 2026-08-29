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
