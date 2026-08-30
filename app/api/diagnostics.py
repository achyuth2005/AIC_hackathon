"""
Diagnostic test lifecycle actions (Phase 6.3). Ordering a test happens
case-scoped (POST /cases/{id}/tests, app/api/cases.py); everything after
that is addressed by test_id directly, since a case can have several tests
in flight independently.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_store
from app.auth.deps import require_hospital_scope, require_role
from app.auth.models import AuthenticatedUser
from app.auth.roles import Role
from app.schemas.diagnostic_test import DiagnosticTestResponse
from app.store.event_store import EventStore, NotFoundError

router = APIRouter(prefix="/tests", tags=["diagnostics"])

_STAFF_ROLES = (Role.NURSE, Role.DOCTOR, Role.ADMIN)


def _require_test_in_scope(test_id: str, store: EventStore, current_user: AuthenticatedUser) -> None:
    """Audit fix (Critical, dimension 1/IDOR): these three endpoints were
    previously unauthenticated and unscoped -- any caller could falsify a
    lab-result-reviewed milestone for any hospital's test by ID.
    DiagnosticTest doesn't carry hospital_profile_id directly, so its
    owning case is resolved to check tenancy."""
    test = store.get_diagnostic_test(test_id)
    if test is None:
        raise NotFoundError(f"No diagnostic test {test_id}")
    owning_case = store.get_case(test.case_id)
    require_hospital_scope(current_user, owning_case.hospital_profile_id if owning_case else None)


@router.post("/{test_id}/sample-collected", response_model=DiagnosticTestResponse)
def mark_sample_collected(
    test_id: str,
    store: EventStore = Depends(get_store),
    current_user: AuthenticatedUser = Depends(require_role(*_STAFF_ROLES)),
) -> DiagnosticTestResponse:
    """Resolves Phase 6.3's 'test ordered, no sample collected' pattern."""
    _require_test_in_scope(test_id, store, current_user)
    test = store.mark_sample_collected(test_id)
    return DiagnosticTestResponse.model_validate(test)


@router.post("/{test_id}/result-available", response_model=DiagnosticTestResponse)
def mark_result_available(
    test_id: str,
    store: EventStore = Depends(get_store),
    current_user: AuthenticatedUser = Depends(require_role(*_STAFF_ROLES)),
) -> DiagnosticTestResponse:
    """Starts the clock for Phase 6.3's 'result available, not reviewed' pattern."""
    _require_test_in_scope(test_id, store, current_user)
    test = store.mark_result_available(test_id)
    return DiagnosticTestResponse.model_validate(test)


@router.post("/{test_id}/result-reviewed", response_model=DiagnosticTestResponse)
def mark_result_reviewed(
    test_id: str,
    store: EventStore = Depends(get_store),
    current_user: AuthenticatedUser = Depends(require_role(*_STAFF_ROLES)),
) -> DiagnosticTestResponse:
    """Resolves Phase 6.3's 'result available, not reviewed' pattern."""
    _require_test_in_scope(test_id, store, current_user)
    test = store.mark_result_reviewed(test_id)
    return DiagnosticTestResponse.model_validate(test)
