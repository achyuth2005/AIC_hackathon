"""
Resource registry and occupancy lifecycle (Phase 6.1, 6.2, 6.3).
"""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status as http_status

from app.api.deps import get_store
from app.models.enums import ResourceStatus, ResourceType
from app.schemas.resource import ResourceCreateRequest, ResourceResponse
from app.store.event_store import EventStore

router = APIRouter(prefix="/resources", tags=["resources"])


@router.post("", response_model=ResourceResponse, status_code=http_status.HTTP_201_CREATED)
def create_resource(body: ResourceCreateRequest, store: EventStore = Depends(get_store)) -> ResourceResponse:
    resource = store.create_resource(
        resource_type=body.resource_type, label=body.label, hospital_profile_id=body.hospital_profile_id
    )
    return ResourceResponse.model_validate(resource)


@router.get("", response_model=List[ResourceResponse])
def list_resources(
    hospital_profile_id: str = Query(default="default"),
    resource_type: Optional[ResourceType] = Query(default=None),
    status: Optional[ResourceStatus] = Query(default=None),
    store: EventStore = Depends(get_store),
) -> List[ResourceResponse]:
    resources = store.list_resources(hospital_profile_id, resource_type=resource_type, status=status)
    return [ResourceResponse.model_validate(r) for r in resources]


@router.post("/{resource_id}/confirm-occupancy", response_model=ResourceResponse)
def confirm_occupancy(resource_id: str, store: EventStore = Depends(get_store)) -> ResourceResponse:
    """Phase 6.3 'assigned space never occupied' pattern's resolving
    action: the nurse confirms the patient is physically in the assigned
    space, clearing that pattern's clock."""
    resource = store.confirm_occupancy(resource_id)
    return ResourceResponse.model_validate(resource)


@router.post("/{resource_id}/release", response_model=ResourceResponse)
def release_resource(resource_id: str, store: EventStore = Depends(get_store)) -> ResourceResponse:
    resource = store.release_resource(resource_id)
    return ResourceResponse.model_validate(resource)
