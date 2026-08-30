"""
Integration tests for app/queue/guardian_queue.py (Phase 5.2, 5.3): the
lexicographic ordering property, reassessment-overdue flagging, and the
deterioration-trend/time-in-band tiebreakers -- all against real Case/
Observation/RiskAssessment rows.
"""
from datetime import timedelta

from app.config.hospital_profile import load_hospital_profile
from app.models.enums import MeasurementStatus, ReliabilityTier, SourceType, ValueType
from app.queue.guardian_queue import build_queue
from app.scoring import concepts
from app.scoring.risk_orchestrator import assess_case
from app.store.event_store import EventStore
from app.timeutil import utcnow

PROFILE = load_hospital_profile("default")


def _add(store: EventStore, case_id, concept_code, value, value_type, observed_at):
    return store.add_observation(
        case_id=case_id,
        concept_code=concept_code,
        value=value,
        value_type=value_type,
        source_type=SourceType.NURSE,
        reliability_tier=ReliabilityTier.CLINICIAN_OBSERVED,
        measurement_status=MeasurementStatus.MEASURED,
        observed_at=observed_at,
    )


def _make_case_at_acuity(store: EventStore, age_years: int, spo2_value: float, at):
    """Creates a case and drives it to a specific acuity via SpO2 alone,
    with everything else normal, at a given point in time."""
    case = store.create_case(age_years=age_years)
    for concept, value, vtype in [
        (concepts.RESP_RATE, 16.0, ValueType.NUMERIC),
        (concepts.SPO2, spo2_value, ValueType.NUMERIC),
        (concepts.SUPPLEMENTAL_OXYGEN, False, ValueType.BOOLEAN),
        (concepts.SYSTOLIC_BP, 120.0, ValueType.NUMERIC),
        (concepts.HEART_RATE, 75.0, ValueType.NUMERIC),
        (concepts.CONSCIOUSNESS_LEVEL, "ALERT", ValueType.CODED),
        (concepts.TEMPERATURE, 37.0, ValueType.NUMERIC),
    ]:
        _add(store, case.case_id, concept, value, vtype, at)
    assess_case(case, store, PROFILE, as_of=at)
    return store.get_case(case.case_id)


def test_lexicographic_ordering_cannot_be_overcome_by_waiting(store: EventStore):
    """THE core Phase 5.2 safety property: a level-4 patient who has waited
    for hours must never outrank a level-2 patient who just arrived."""
    now = utcnow()
    long_waiter = _make_case_at_acuity(store, 40, spo2_value=98.0, at=now - timedelta(hours=6))  # ESI5-ish, ancient
    just_arrived = _make_case_at_acuity(store, 40, spo2_value=93.0, at=now)  # SpO2 92-93 -> 2pts -> more urgent band

    queue = build_queue(store, PROFILE, as_of=now)
    case_ids_in_order = [e.case_id for e in queue]

    assert case_ids_in_order.index(just_arrived.case_id) < case_ids_in_order.index(long_waiter.case_id)


def test_within_band_longer_time_in_band_sorts_first(store: EventStore):
    now = utcnow()
    # Both land at the same acuity band (missing 2/7 vitals -> capped at
    # ESI3 by the missing-data cap, Phase 3.3), entered at different times.
    entered_long_ago = store.create_case(age_years=40)
    _add(store, entered_long_ago.case_id, concepts.RESP_RATE, 16.0, ValueType.NUMERIC, now - timedelta(minutes=40))
    assess_case(entered_long_ago, store, PROFILE, as_of=now - timedelta(minutes=40))

    entered_recently = store.create_case(age_years=40)
    _add(store, entered_recently.case_id, concepts.RESP_RATE, 16.0, ValueType.NUMERIC, now - timedelta(minutes=5))
    assess_case(entered_recently, store, PROFILE, as_of=now - timedelta(minutes=5))

    queue = build_queue(store, PROFILE, as_of=now)
    entries_by_id = {e.case_id: e for e in queue}
    assert entries_by_id[entered_long_ago.case_id].final_acuity == entries_by_id[entered_recently.case_id].final_acuity

    case_ids_in_order = [e.case_id for e in queue]
    assert case_ids_in_order.index(entered_long_ago.case_id) < case_ids_in_order.index(entered_recently.case_id)


def test_worsening_trend_sorts_before_stable_within_same_band(store: EventStore):
    """Both cases end up at the SAME final_acuity (ESI2, via NEWS2's own
    single-parameter red-score rule on respiratory rate) -- one arrived
    there via a worsening trend (previously ESI5), the other was already
    at ESI2 last time too (stable). Trend outranks time-in-band in Phase
    5.2's priority order, so this also proves trend isn't merely
    coinciding with -- but actually overriding -- the time-in-band key:
    the stable case has spent LONGER in this band (which would otherwise
    favour it under key 4), yet the worsening case must still sort first."""
    now = utcnow()

    worsening = store.create_case(age_years=40)
    _add(store, worsening.case_id, concepts.RESP_RATE, 16.0, ValueType.NUMERIC, now - timedelta(minutes=10))
    assess_case(worsening, store, PROFILE, as_of=now - timedelta(minutes=10))  # normal -> ESI5
    _add(store, worsening.case_id, concepts.RESP_RATE, 6.0, ValueType.NUMERIC, now)  # <=8 -> single-param ESI2
    assess_case(worsening, store, PROFILE, as_of=now)

    stable = store.create_case(age_years=40)
    _add(store, stable.case_id, concepts.RESP_RATE, 6.0, ValueType.NUMERIC, now - timedelta(minutes=10))
    assess_case(stable, store, PROFILE, as_of=now - timedelta(minutes=10))  # already ESI2
    _add(store, stable.case_id, concepts.RESP_RATE, 6.0, ValueType.NUMERIC, now)  # still ESI2
    assess_case(stable, store, PROFILE, as_of=now)

    queue = build_queue(store, PROFILE, as_of=now)
    entries_by_id = {e.case_id: e for e in queue}
    assert entries_by_id[worsening.case_id].final_acuity == entries_by_id[stable.case_id].final_acuity == 2
    assert entries_by_id[stable.case_id].time_in_current_band_minutes > entries_by_id[worsening.case_id].time_in_current_band_minutes

    case_ids_in_order = [e.case_id for e in queue]
    assert case_ids_in_order.index(worsening.case_id) < case_ids_in_order.index(stable.case_id)


def test_reassessment_overdue_is_flagged_once_and_clears_after_mark_reassessed(store: EventStore):
    now = utcnow()
    case = _make_case_at_acuity(store, 40, spo2_value=98.0, at=now)  # ESI5 -> 120 min interval

    # Force the clock back as if this case hasn't been looked at in a while.
    stale_case = store.get_case(case.case_id)
    stale_case.last_reassessed_at = now - timedelta(minutes=200)
    store.db.commit()

    build_queue(store, PROFILE, as_of=now)  # first read: should flag it

    refreshed = store.get_case(case.case_id)
    assert refreshed.reassessment_overdue is True
    event_types = [e.event_type for e in store.get_timeline(case.case_id)]
    assert event_types.count("REASSESSMENT_DUE") == 1

    build_queue(store, PROFILE, as_of=now)  # second read: must NOT re-flag
    event_types_after = [e.event_type for e in store.get_timeline(case.case_id)]
    assert event_types_after.count("REASSESSMENT_DUE") == 1

    store.mark_reassessed(case.case_id, occurred_at=now)
    cleared = store.get_case(case.case_id)
    assert cleared.reassessment_overdue is False
    event_types_final = [e.event_type for e in store.get_timeline(case.case_id)]
    assert "REASSESSMENT_COMPLETED" in event_types_final


def test_one_malformed_case_does_not_take_down_the_whole_queue(store: EventStore):
    """Audit fix (Critical, fault isolation): build_queue used to be a
    plain list comprehension over every active case -- one case with a
    data/config problem (the real-world trigger: CONSCIOUSNESS_LEVEL=
    NEW_CONFUSION on a paediatric case, unbanded because PEWS's
    consciousness_points table had no entry for it) raised straight out of
    _build_entry and took down GET /queue -- and therefore
    GET /queue/printable, the documented total-system-failure paper
    fallback -- for every *other* patient in the hospital too. A single
    malformed case must now be logged and excluded from the read instead
    of failing it for everyone else."""
    now = utcnow()
    good_case = _make_case_at_acuity(store, 40, spo2_value=98.0, at=now)

    bad_case = store.create_case(age_years=40)
    for concept, value, vtype in [
        (concepts.RESP_RATE, 16.0, ValueType.NUMERIC),
        (concepts.SPO2, 98.0, ValueType.NUMERIC),
        (concepts.SUPPLEMENTAL_OXYGEN, False, ValueType.BOOLEAN),
        (concepts.SYSTOLIC_BP, 120.0, ValueType.NUMERIC),
        (concepts.HEART_RATE, 75.0, ValueType.NUMERIC),
        # Not a real AVPU/ACVPU code -- CONSCIOUSNESS_CODES membership is
        # documented (app/scoring/concepts.py) but not enforced at write
        # time, so this reaches scoring with no configured band anywhere,
        # standing in for any future config/data gap of this same shape.
        (concepts.CONSCIOUSNESS_LEVEL, "SOMNOLENT", ValueType.CODED),
        (concepts.TEMPERATURE, 37.0, ValueType.NUMERIC),
    ]:
        _add(store, bad_case.case_id, concept, value, vtype, now)
    # Deliberately no assess_case() call here: build_queue's self-healing
    # backfill (_build_entry, for a case with zero RiskAssessment history)
    # is what performs the first scoring attempt, which is where the
    # crash must be caught.

    entries = build_queue(store, PROFILE, as_of=now)  # must not raise

    entry_case_ids = {e.case_id for e in entries}
    assert good_case.case_id in entry_case_ids
    assert bad_case.case_id not in entry_case_ids
