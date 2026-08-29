"""
Override & equity monitoring (Phase 9.6's closing line: "Override rate and
override direction become your primary model-monitoring signals in
production"; Phase 9.7: "measure acuity distribution and override rate by
demographic subgroup as a standing evaluation output, not as a one-off
fairness audit ... State that you measure it. Do not claim you have
solved it.")

This module only MEASURES. It draws no conclusions, flags no case as
biased, and applies no correction -- a skewed distribution here is a
prompt for clinical/statistical review, not evidence of anything on its
own. Stated once here (and in the report's own `caveat` field) rather than
re-argued at every call site.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from app.config.hospital_profile import HospitalProfile
from app.models.case import Case
from app.models.enums import HumanDecisionAction
from app.models.human_decision import HumanDecision
from app.store.event_store import EventStore

_CAVEAT = (
    "A standing measurement, not a fairness audit: a skewed distribution here is a "
    "prompt for clinical/statistical review, not evidence of bias by itself (Phase 9.7)."
)


class SubgroupStats(BaseModel):
    subgroup: str
    case_count: int
    acuity_distribution: Dict[int, int]  # final_acuity -> count of cases currently at that level
    decision_count: int
    escalate_count: int
    de_escalate_count: int
    override_rate: Optional[float]  # (escalate + de_escalate) / decision_count; None if no decisions yet


class OverrideMonitoringReport(BaseModel):
    total_cases: int
    total_decisions: int
    action_counts: Dict[str, int]
    overall_override_rate: Optional[float]
    overall_de_escalation_rate: Optional[float]
    flagged_for_review_count: int
    by_age_band: List[SubgroupStats]
    by_sex: List[SubgroupStats]
    caveat: str = Field(default=_CAVEAT)


def _subgroup_stats(
    subgroup: str,
    entries: List[Tuple[Case, Optional[int]]],
    decisions_by_case: Dict[str, List[HumanDecision]],
) -> SubgroupStats:
    acuity_distribution: Dict[int, int] = defaultdict(int)
    for _, latest_acuity in entries:
        if latest_acuity is not None:
            acuity_distribution[latest_acuity] += 1

    decision_count = 0
    escalate_count = 0
    de_escalate_count = 0
    for case, _ in entries:
        for decision in decisions_by_case.get(case.case_id, []):
            decision_count += 1
            if decision.clinician_action == HumanDecisionAction.ESCALATE:
                escalate_count += 1
            elif decision.clinician_action == HumanDecisionAction.DE_ESCALATE:
                de_escalate_count += 1

    override_rate = (escalate_count + de_escalate_count) / decision_count if decision_count else None
    return SubgroupStats(
        subgroup=subgroup,
        case_count=len(entries),
        acuity_distribution=dict(acuity_distribution),
        decision_count=decision_count,
        escalate_count=escalate_count,
        de_escalate_count=de_escalate_count,
        override_rate=override_rate,
    )


def compute_override_monitoring(store: EventStore, profile: HospitalProfile) -> OverrideMonitoringReport:
    cases = [c for c in store.list_cases() if c.hospital_profile_id == profile.profile_id]

    decisions_by_case: Dict[str, List[HumanDecision]] = {}
    all_decisions: List[HumanDecision] = []
    for case in cases:
        history = store.get_decision_history(case.case_id)
        decisions_by_case[case.case_id] = history
        all_decisions.extend(history)

    action_counts: Dict[str, int] = defaultdict(int)
    for decision in all_decisions:
        action_counts[decision.clinician_action.value] += 1
    total_decisions = len(all_decisions)
    escalate_total = action_counts.get(HumanDecisionAction.ESCALATE.value, 0)
    de_escalate_total = action_counts.get(HumanDecisionAction.DE_ESCALATE.value, 0)
    overall_override_rate = (escalate_total + de_escalate_total) / total_decisions if total_decisions else None
    overall_de_escalation_rate = de_escalate_total / total_decisions if total_decisions else None
    flagged_for_review_count = sum(1 for d in all_decisions if d.flagged_for_review)

    by_age_band: Dict[str, List[Tuple[Case, Optional[int]]]] = defaultdict(list)
    by_sex: Dict[str, List[Tuple[Case, Optional[int]]]] = defaultdict(list)
    for case in cases:
        latest = store.get_latest_risk_assessment(case.case_id)
        latest_acuity = latest.final_acuity if latest else None
        band = (profile.age_band_for(case.age_years) if case.age_years is not None else None) or "UNKNOWN"
        by_age_band[band].append((case, latest_acuity))
        by_sex[case.sex or "UNKNOWN"].append((case, latest_acuity))

    return OverrideMonitoringReport(
        total_cases=len(cases),
        total_decisions=total_decisions,
        action_counts=dict(action_counts),
        overall_override_rate=overall_override_rate,
        overall_de_escalation_rate=overall_de_escalation_rate,
        flagged_for_review_count=flagged_for_review_count,
        by_age_band=[_subgroup_stats(band, entries, decisions_by_case) for band, entries in by_age_band.items()],
        by_sex=[_subgroup_stats(sex, entries, decisions_by_case) for sex, entries in by_sex.items()],
    )
