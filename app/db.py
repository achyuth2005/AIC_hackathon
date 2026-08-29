"""
Database engine/session setup.

Architecture note (Phase 15 / Phase 18.1): the recommended production stack is
PostgreSQL with an append-only events table using JSONB payloads. This
environment has no local Postgres server, so we run on SQLite (the
architecture's explicitly sanctioned "simpler alternative", Phase 15) via
SQLAlchemy. No SQLite-only types/features are used in the models, so pointing
DATABASE_URL at a Postgres DSN later is a config change, not a rewrite.
"""
from __future__ import annotations

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "sqlite:///" + os.path.join(os.path.dirname(os.path.dirname(__file__)), "patienttriage.db"),
)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

Base = declarative_base()


def get_db():
    """FastAPI dependency: yields a session, closes it after the request.
    Rolls back on any exception so a flush() that ran before a mid-request
    error (e.g. EventStore raising after `db.flush()` but before `db.commit()`)
    never leaves an uncommitted, half-written transaction hanging around."""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> None:
    """Create all tables. Called at app startup and by test fixtures."""
    # Import models so they register on Base.metadata before create_all.
    from app.models import case, observation, event, risk_assessment, resource, diagnostic_test, human_decision, alert, data_conflict, case_review, ambulance_transport  # noqa: F401

    Base.metadata.create_all(bind=engine)
