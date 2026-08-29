"""
Tests for the Phase 14.1 demo scenario seed (CP11): all twenty patients
are created without error, and each one's specific "demonstrates" claim
actually holds -- not just that seeding doesn't crash.
"""
from app.config.hospital_profile import load_hospital_profile
from app.demo.scenarios import seed_demo_patients
from app.models.enums import BypassSource, CaseStatus, DeteriorationTrend, IdentityLinkStatus
from app.store.event_store import EventStore

PROFILE = load_hospital_profile("default")


def test_seeds_exactly_twenty_scenarios_with_unique_numbers_and_cases(store: EventStore):
    scenarios = seed_demo_patients(store, PROFILE)
    assert len(scenarios) == 20
    assert sorted(s.number for s in scenarios) == list(range(1, 21))
    assert len({s.case_id for s in scenarios}) == 20  # every case is distinct


def test_only_the_known_gap_scenarios_are_marked_partial_and_say_why(store: EventStore):
    # 19 (LLM Intake Engine) is a pending checkpoint not yet built; 16
    # (identity match) is partial because only propose/confirm are built,
    # not a candidate *search* against a patient registry (no such
    # registry exists here). 13 (Contradictory Information) was PARTIAL as
    # of CP11 and is now FULL as of CP13 -- see test_scenario_13 below.
    scenarios = seed_demo_patients(store, PROFILE)
    partial = {s.number: s for s in scenarios if s.fidelity == "PARTIAL"}
    assert set(partial.keys()) == {16, 19}
    for s in partial.values():
        assert s.note  # each partial scenario explains the gap


def test_scenario_01_activates_emergency_bypass(store: EventStore):
    scenarios = seed_demo_patients(store, PROFILE)
    s1 = next(s for s in scenarios if s.number == 1)
    case = store.get_case(s1.case_id)
    assert case.emergency_bypass_active is True
    assert case.emergency_bypass_last_source == BypassSource.PHYSIOLOGICAL


def test_scenario_02_is_low_acuity(store: EventStore):
    scenarios = seed_demo_patients(store, PROFILE)
    s2 = next(s for s in scenarios if s.number == 2)
    ra = store.get_latest_risk_assessment(s2.case_id)
    assert ra.final_acuity >= 4


def test_scenario_03_abstains_at_low_confidence(store: EventStore):
    scenarios = seed_demo_patients(store, PROFILE)
    s3 = next(s for s in scenarios if s.number == 3)
    ra = store.get_latest_risk_assessment(s3.case_id)
    assert ra.should_abstain is True


def test_scenario_06_geriatric_scores_more_urgently_than_adult_would(store: EventStore):
    """The exact vitals in scenario 6, scored under the ADULT mapping
    instead, would land in a less urgent band -- proving the geriatric
    adjustment is doing real work, not just present in config."""
    scenarios = seed_demo_patients(store, PROFILE)
    s6 = next(s for s in scenarios if s.number == 6)
    ra = store.get_latest_risk_assessment(s6.case_id)

    case = store.get_case(s6.case_id)
    assert case.age_years == 78
    geriatric_band = PROFILE.age_band_for(78)
    assert geriatric_band == "GERIATRIC"

    # Aggregate score (6, per rule_component_breakdown) maps to ESI2 under
    # geriatric_adjustment.aggregate_to_esi but ESI3 under news2.aggregate_to_esi.
    aggregate = sum(c["points"] for c in ra.rule_component_breakdown if not c["is_missing"])
    adult_esi = next(
        band.esi_level for band in PROFILE.news2.aggregate_to_esi
        if band.min_score <= aggregate and (band.max_score is None or aggregate <= band.max_score)
    )
    assert ra.rule_acuity < adult_esi


def test_scenario_09_shows_a_worsening_trend_across_two_assessments(store: EventStore):
    scenarios = seed_demo_patients(store, PROFILE)
    s9 = next(s for s in scenarios if s.number == 9)
    history = store.get_risk_assessment_history(s9.case_id)
    assert len(history) == 2
    assert history[1].final_acuity < history[0].final_acuity  # more urgent second time

    from app.queue.time_engine import deterioration_trend
    assert deterioration_trend(history) == DeteriorationTrend.WORSENING


def test_scenario_10_forces_reassessment_overdue(store: EventStore):
    scenarios = seed_demo_patients(store, PROFILE)
    s10 = next(s for s in scenarios if s.number == 10)
    case = store.get_case(s10.case_id)
    assert case.reassessment_overdue is True


def test_scenario_11_is_overdue_without_acuity_changing(store: EventStore):
    scenarios = seed_demo_patients(store, PROFILE)
    s11 = next(s for s in scenarios if s.number == 11)
    case = store.get_case(s11.case_id)
    history = store.get_risk_assessment_history(s11.case_id)
    assert case.reassessment_overdue is True
    assert len(history) == 1  # forcing the flag did not itself create a new assessment


def test_scenario_12_appears_on_the_stuck_patients_list(store: EventStore):
    from app.ops.flow_engine import check_stuck_patients

    scenarios = seed_demo_patients(store, PROFILE)
    s12 = next(s for s in scenarios if s.number == 12)
    stuck = check_stuck_patients(store, PROFILE)
    assert any(s.case_id == s12.case_id and s.pattern_id == "RESULT_NOT_REVIEWED" for s in stuck)


def test_scenario_13_uses_the_conservative_value_and_flags_the_conflict(store: EventStore):
    """As of CP13: the conservative (abnormal, device-measured) reading is
    what scoring actually used, NOT the milder, later-timestamped
    self-report -- and the conflict is on record for display/resolution."""
    scenarios = seed_demo_patients(store, PROFILE)
    s13 = next(s for s in scenarios if s.number == 13)

    ra = store.get_latest_risk_assessment(s13.case_id)
    hr_component = next(c for c in ra.rule_component_breakdown if c["concept_code"] == "HEART_RATE")
    assert hr_component["raw_value"] == 125.0  # the abnormal device reading, not the milder self-report

    conflicts = store.list_data_conflicts(s13.case_id, include_resolved=True)
    assert len(conflicts) == 1
    assert conflicts[0].concept_code == "HEART_RATE"
    assert conflicts[0].resolved is False

    event_types = [e.event_type for e in store.get_timeline(s13.case_id)]
    assert "DATA_CONFLICT_DETECTED" in event_types


def test_scenario_14_abstains_on_zero_data(store: EventStore):
    scenarios = seed_demo_patients(store, PROFILE)
    s14 = next(s for s in scenarios if s.number == 14)
    ra = store.get_latest_risk_assessment(s14.case_id)
    assert ra.should_abstain is True


def test_scenario_15_is_pre_arrival_but_already_scored(store: EventStore):
    scenarios = seed_demo_patients(store, PROFILE)
    s15 = next(s for s in scenarios if s.number == 15)
    case = store.get_case(s15.case_id)
    assert case.status == CaseStatus.PRE_ARRIVAL
    ra = store.get_latest_risk_assessment(s15.case_id)
    assert ra is not None


def test_scenario_16_runs_unlinked_with_a_proposed_candidate(store: EventStore):
    scenarios = seed_demo_patients(store, PROFILE)
    s16 = next(s for s in scenarios if s.number == 16)
    case = store.get_case(s16.case_id)
    assert case.identity_link_status == IdentityLinkStatus.CANDIDATE_PROPOSED
    event_types = [e.event_type for e in store.get_timeline(s16.case_id)]
    assert "IDENTITY_MATCH_PROPOSED" in event_types
    assert "IDENTITY_MATCH_CONFIRMED" not in event_types


def test_scenario_17_escalated_with_override_deciding_layer(store: EventStore):
    from app.models.enums import DecidingLayer

    scenarios = seed_demo_patients(store, PROFILE)
    s17 = next(s for s in scenarios if s.number == 17)
    ra = store.get_latest_risk_assessment(s17.case_id)
    assert ra.deciding_layer == DecidingLayer.OVERRIDE
    decisions = store.get_decision_history(s17.case_id)
    assert decisions[0].flagged_for_review is False


def test_scenario_18_de_escalated_and_flagged(store: EventStore):
    scenarios = seed_demo_patients(store, PROFILE)
    s18 = next(s for s in scenarios if s.number == 18)
    decisions = store.get_decision_history(s18.case_id)
    assert decisions[0].flagged_for_review is True
    assert decisions[0].reason_code is not None
    flagged = store.list_flagged_for_review()
    assert any(d.case_id == s18.case_id for d in flagged)


def test_scenario_20_min_invariant_refuses_ml_downgrade(store: EventStore):
    from app.models.enums import DecidingLayer

    scenarios = seed_demo_patients(store, PROFILE)
    s20 = next(s for s in scenarios if s.number == 20)
    ra = store.get_latest_risk_assessment(s20.case_id)
    assert ra.ml_suggested_acuity is not None
    assert ra.ml_suggested_acuity > ra.rule_acuity  # ML wanted LESS urgent
    assert ra.final_acuity == ra.rule_acuity  # min() kept the more urgent rules number
    assert ra.deciding_layer == DecidingLayer.RULES


# ---------------------------------------------------------------------
# HTTP surface
# ---------------------------------------------------------------------
def test_seed_endpoint_returns_all_twenty(client):
    resp = client.post("/demo/seed")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 20
    assert all("case_id" in row for row in body)
