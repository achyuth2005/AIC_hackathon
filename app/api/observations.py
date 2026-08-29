"""
Observation-level endpoints not scoped under a case path -- specifically
supersede (Phase 4.2 "never mutate, always supersede"), addressed by
observation_id directly since the caller is correcting one specific fact.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, status as http_status

from app.api.deps import get_store
from app.schemas.observation import ObservationResponse, ObservationSupersedeRequest
from app.store.event_store import EventStore

router = APIRouter(prefix="/observations", tags=["observations"])


@router.post(
    "/{observation_id}/supersede",
    response_model=ObservationResponse,
    status_code=http_status.HTTP_201_CREATED,
)
def supersede_observation(
    observation_id: str, body: ObservationSupersedeRequest, store: EventStore = Depends(get_store)
) -> ObservationResponse:
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
