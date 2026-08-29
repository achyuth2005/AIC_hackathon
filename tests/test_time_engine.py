"""
Pure unit tests for app/queue/time_engine.py (Phase 5.1/5.3/5.4). Uses
plain (unpersisted) RiskAssessment instances -- no DB needed for these.
"""
from datetime import datetime, timedelta, timezone

from app.config.hospital_profile import load_hospital_profile
from app.models.enums import DeteriorationTrend
from app.models.risk_assessment import RiskAssessment
from app.queue import time_engine

PROFILE = load_hospital_profile("default")


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _assessment(final_acuity, computed_at):
    return RiskAssessment(final_acuity=final_acuity, computed_at=computed_at)


# ---------------------------------------------------------------------
# reassessment_status
# ---------------------------------------------------------------------
def test_not_due_when_within_interval():
    now = _now()
    last = now - timedelta(minutes=10)  # level 3's interval is 30 min
    status = time_engine.reassessment_status(3, last, PROFILE, as_of=now)
    assert status.is_due is False
    assert status.interval_minutes == 30
    assert status.minutes_overdue is None


def test_due_when_interval_exceeded():
    now = _now()
    last = now - timedelta(minutes=45)  # level 3's interval is 30 min
    status = time_engine.reassessment_status(3, last, PROFILE, as_of=now)
    assert status.is_due is True
    assert status.minutes_overdue == 15.0


def test_no_last_reassessed_at_is_not_due():
    status = time_engine.reassessment_status(3, None, PROFILE, as_of=_now())
    assert status.is_due is False


def test_no_final_acuity_is_not_due():
    status = time_engine.reassessment_status(None, _now() - timedelta(hours=5), PROFILE, as_of=_now())
    assert status.is_due is False
    assert status.interval_minutes is None


def test_more_urgent_bands_have_shorter_intervals():
    assert PROFILE.reassessment_minutes_for(2) < PROFILE.reassessment_minutes_for(4)


# ---------------------------------------------------------------------
# deterioration_trend
# ---------------------------------------------------------------------
def test_fewer_than_two_assessments_is_unknown():
    assert time_engine.deterioration_trend([]) == DeteriorationTrend.UNKNOWN
    assert time_engine.deterioration_trend([_assessment(4, _now())]) == DeteriorationTrend.UNKNOWN


def test_lower_acuity_number_is_worsening():
    now = _now()
    history = [_assessment(4, now - timedelta(minutes=30)), _assessment(2, now)]
    assert time_engine.deterioration_trend(history) == DeteriorationTrend.WORSENING


def test_higher_acuity_number_is_improving():
    now = _now()
    history = [_assessment(2, now - timedelta(minutes=30)), _assessment(4, now)]
    assert time_engine.deterioration_trend(history) == DeteriorationTrend.IMPROVING


def test_same_acuity_is_stable():
    now = _now()
    history = [_assessment(3, now - timedelta(minutes=30)), _assessment(3, now)]
    assert time_engine.deterioration_trend(history) == DeteriorationTrend.STABLE


def test_only_the_two_most_recent_assessments_matter():
    now = _now()
    history = [
        _assessment(2, now - timedelta(hours=2)),  # ancient worsening -- irrelevant now
        _assessment(4, now - timedelta(minutes=30)),
        _assessment(3, now),
    ]
    assert time_engine.deterioration_trend(history) == DeteriorationTrend.WORSENING


# ---------------------------------------------------------------------
# time_in_current_band_minutes
# ---------------------------------------------------------------------
def test_no_history_is_none():
    assert time_engine.time_in_current_band_minutes([], as_of=_now()) is None


def test_time_in_band_measured_from_earliest_matching_assessment():
    now = _now()
    history = [
        _assessment(4, now - timedelta(minutes=90)),  # different band -- band start is AFTER this
        _assessment(3, now - timedelta(minutes=60)),  # band entered here
        _assessment(3, now - timedelta(minutes=20)),  # same band, doesn't reset the clock
        _assessment(3, now),
    ]
    minutes = time_engine.time_in_current_band_minutes(history, as_of=now)
    assert minutes == 60.0


def test_single_assessment_band_time_is_time_since_it(store=None):
    now = _now()
    history = [_assessment(5, now - timedelta(minutes=12))]
    assert time_engine.time_in_current_band_minutes(history, as_of=now) == 12.0
