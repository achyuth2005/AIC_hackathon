"""
Observation-level endpoints not scoped under a case path -- specifically
supersede (Phase 4.2 "never mutate, always supersede"), addressed by
observation_id directly since the caller is correcting one specific fact.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, status as http_status

from app.api.deps import get_store
from app.auth.deps import require_hospital_scope, require_role
from app.auth.models import AuthenticatedUser
from app.auth.roles import Role
from app.schemas.observation import ObservationResponse, ObservationSupersedeRequest
from app.store.event_store import EventStore, NotFoundError

router = APIRouter(prefix="/observations", tags=["observations"])


@router.post(
    "/{observation_id}/supersede",
    response_model=ObservationResponse,
    status_code=http_status.HTTP_201_CREATED,
)
def supersede_observation(
    observation_id: str,
    body: ObservationSupersedeRequest,
    store: EventStore = Depends(get_store),
    current_user: AuthenticatedUser = Depends(require_role(Role.NURSE, Role.DOCTOR, Role.ADMIN)),
) -> ObservationResponse:
    # Audit fix (Critical, dimension 1/IDOR): previously unauthenticated --
    # any caller could overwrite any patient's recorded vitals by ID. Now
    # requires a staff token, and the tenancy check below resolves the
    # observation's owning case before allowing the correction, so staff
    # from one hospital cannot supersede another hospital's data.
    old = store.get_observation(observation_id)
    if old is None:
        raise NotFoundError(f"No observation {observation_id}")
    owning_case = store.get_case(old.case_id)
    require_hospital_scope(current_user, owning_case.hospital_profile_id if owning_case else None)

    new_obs = store.supersede_observation(
        observation_id=observation_id,
        value=body.value,
        value_type=body.value_type,
        source_type=body.source_type,
        reliability_tier=body.reliability_tier,
        measurement_status=body.measurement_status,
        observed_at=body.observed_at,
        unit=body.unit,
        source_id=body.source_id,
        extraction_confidence=body.extraction_confidence,
    )
    return ObservationResponse.model_validate(new_obs)
