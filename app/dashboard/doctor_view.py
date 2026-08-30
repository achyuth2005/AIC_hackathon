"""
Phase 8.3 doctor view (CP15): "decision support, not information dumping."

The high-value element -- "what changed since you last looked at this
patient" -- is why this module exists (Phase 8.3's own words: "worth
building before anything else on this screen"). It's answerable because
this is an event-sourced store: every fact that ever entered the system
is a timestamped, append-only row, so "what changed since T" is simply
"every event after T", not a bolt-on diffing mechanism.

Deliberately absent from this view, by construction rather than by
frontend discretion: differential diagnoses, treatment suggestions, or
anything that would position the system as a clinical decision *maker*.
This project's scoring engines only ever output an acuity level and a
confidence band -- there is no differential/treatment-suggestion
generator anywhere in the codebase to accidentally surface here.
"""
from __future__ import annotations

from typing import List, Optional

from app.config.hospital_profile import HospitalProfile
from app.models.case import Case
from app.models.enums import DiagnosticTestStatus
from app.schemas.doctor_view import DoctorCaseView, PendingAction, VitalTrend
from app.schemas.event import EventResponse
from app.schemas.observation import ObservationResponse
from app.schemas.risk_assessment import RiskAssessmentResponse
from app.scoring import concepts
from app.store.event_store import EventStore

_TREND_CONCEPTS = [concepts.RESP_RATE, concepts.SPO2, concepts.HEART_RATE, concepts.SYSTOLIC_BP, concepts.TEMPERATURE]


def _compute_trends(store: EventStore, case_id: str) -> List[VitalTrend]:
    trends = []
    for concept_code in _TREND_CONCEPTS:
        recent = store.get_recent_current_observations(case_id, concept_code, limit=2)
        if len(recent) < 2:
            continue  # no trend yet with only one reading -- not shown at all, not shown as flat
        current, previous = recent[0], recent[1]  # most-recent first
        delta = None
        if isinstance(current.value, (int, float)) and isinstance(previous.value, (int, float)):
            delta = float(current.value) - float(previous.value)
        trends.append(
            VitalTrend(
                concept_code=concept_code,
                previous_value=previous.value,
                previous_observed_at=previous.observed_at,
                current_value=current.value,
                current_observed_at=current.observed_at,
                delta=delta,
            )
        )
    return trends


def _pending_actions(store: EventStore, case_id: str) -> List[PendingAction]:
    actions: List[PendingAction] = []
    for test in store.get_diagnostic_tests_for_case(case_id):
        if test.status == DiagnosticTestStatus.RESULT_AVAILABLE:
            actions.append(
                PendingAction(
                    kind="RESULT_AWAITING_REVIEW",
                    description=f"{test.test_type} result available, not yet reviewed.",
                    reference_id=test.test_id,
                )
            )
    for conflict in store.list_data_conflicts(case_id):  # open (unresolved) by default
        actions.append(
            PendingAction(
                kind="UNRESOLVED_DATA_CONFLICT",
                description=f"Conflicting {conflict.concept_code} readings awaiting resolution.",
                reference_id=conflict.conflict_id,
            )
        )
    return actions


def build_doctor_view(case: Case, store: EventStore, profile: HospitalProfile, reviewer_id: str) -> DoctorCaseView:
    current_observations = store.get_current_observations(case.case_id)
    latest_assessment = store.get_latest_risk_assessment(case.case_id)

    review = store.get_case_review(case.case_id, reviewer_id)
    is_first_review = review is None
    since = review.reviewed_at if review is not None else None
    timeline = store.get_timeline(case.case_id)
    changed_since = [e for e in timeline if since is None or e.occurred_at > since]

    return DoctorCaseView(
        case_id=case.case_id,
        display_name=case.display_name,
        medical_history=case.medical_history,
        current_observations=[ObservationResponse.model_validate(o) for o in current_observations],
        latest_risk_assessment=(
            RiskAssessmentResponse.model_validate(latest_assessment) if latest_assessment else None
        ),
        trends=_compute_trends(store, case.case_id),
        is_first_review=is_first_review,
        last_reviewed_at=review.reviewed_at if review else None,
        changed_since_last_review=[EventResponse.model_validate(e) for e in changed_since],
        pending_actions=_pending_actions(store, case.case_id),
    )
