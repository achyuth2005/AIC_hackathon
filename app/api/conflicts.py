"""
Phase 9.3 Contradictory-Information resolution endpoint. Listing conflicts
is case-scoped (GET /cases/{id}/conflicts, app/api/cases.py, alongside the
case's other read surfaces); resolving one is addressed by conflict_id
directly, the same split CP9 used for resources/diagnostic tests.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_store
from app.auth.deps import require_role
from app.auth.models import AuthenticatedUser
from app.auth.roles import Role
from app.schemas.data_conflict import DataConflictResolveRequest, DataConflictResponse
from app.store.event_store import EventStore, NotFoundError

router = APIRouter(prefix="/conflicts", tags=["conflicts"])


@router.post("/{conflict_id}/resolve", response_model=DataConflictResponse)
def resolve_conflict(
    conflict_id: str,
    body: DataConflictResolveRequest,
    store: EventStore = Depends(get_store),
    current_user: AuthenticatedUser = Depends(require_role(Role.NURSE, Role.DOCTOR, Role.ADMIN)),
) -> DataConflictResponse:
    """Phase 9.3: 'until a human resolves it.' The chosen observation
    becomes what subsequent scoring uses for this concept (see
    app/scoring/conflict_detection.py) -- a clinical judgement call, not
    merely dismissing the flag."""
    conflict = store.get_data_conflict(conflict_id)
    if conflict is None:
        raise NotFoundError(f"No data conflict {conflict_id}")
    resolved = store.resolve_data_conflict(
        conflict_id,
        resolved_by=current_user.user_id,
        kept_observation_id=body.kept_observation_id,
        resolution_note=body.resolution_note,
    )
    return DataConflictResponse.model_validate(resolved)
