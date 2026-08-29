"""
Diagnostic test lifecycle actions (Phase 6.3). Ordering a test happens
case-scoped (POST /cases/{id}/tests, app/api/cases.py); everything after
that is addressed by test_id directly, since a case can have several tests
in flight independently.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_store
from app.schemas.diagnostic_test import DiagnosticTestResponse
from app.store.event_store import EventStore

router = APIRouter(prefix="/tests", tags=["diagnostics"])


@router.post("/{test_id}/sample-collected", response_model=DiagnosticTestResponse)
def mark_sample_collected(test_id: str, store: EventStore = Depends(get_store)) -> DiagnosticTestResponse:
    """Resolves Phase 6.3's 'test ordered, no sample collected' pattern."""
    test = store.mark_sample_collected(test_id)
    return DiagnosticTestResponse.model_validate(test)


@router.post("/{test_id}/result-available", response_model=DiagnosticTestResponse)
def mark_result_available(test_id: str, store: EventStore = Depends(get_store)) -> DiagnosticTestResponse:
    """Starts the clock for Phase 6.3's 'result available, not reviewed' pattern."""
    test = store.mark_result_available(test_id)
    return DiagnosticTestResponse.model_validate(test)


@router.post("/{test_id}/result-reviewed", response_model=DiagnosticTestResponse)
def mark_result_reviewed(test_id: str, store: EventStore = Depends(get_store)) -> DiagnosticTestResponse:
    """Resolves Phase 6.3's 'result available, not reviewed' pattern."""
    test = store.mark_result_reviewed(test_id)
    return DiagnosticTestResponse.model_validate(test)
