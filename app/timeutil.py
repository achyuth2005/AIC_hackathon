"""
Single time convention for the whole backend: all datetimes are stored and
compared as **naive UTC**. This sidesteps a real SQLite behaviour (it does
not reliably round-trip tz-aware datetimes -- offset info is silently
dropped on read), which would otherwise cause is_stale / reassessment-timer
comparisons (CP7 Time Engine) to raise or silently misbehave depending on
whether a value came from the DB or from Python. Postgres would keep the
offset, so relying on tz-awareness would make behaviour DB-dependent.

Every write path (EventStore) normalizes through `to_naive_utc` so callers
may pass either naive or tz-aware datetimes; every read/compare uses `utcnow`.
"""
from __future__ import annotations

from datetime import datetime, timezone


def utcnow() -> datetime:
    """Current time as naive UTC."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def to_naive_utc(dt: datetime) -> datetime:
    """Normalize any datetime to naive UTC.

    - tz-aware -> converted to UTC, then tzinfo stripped.
    - naive -> assumed to already be UTC (this backend never accepts naive
      local time; callers at the API boundary are responsible for that).
    """
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt
