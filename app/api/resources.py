"""
Resource registry and occupancy lifecycle (Phase 6.1, 6.2, 6.3).
"""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status as http_status

from app.api.deps import get_store
from app.auth.deps import get_current_user, require_hospital_scope, require_role
from app.auth.models import AuthenticatedUser
from app.auth.roles import Role
from app.models.enums import ResourceStatus, ResourceType
from app.schemas.resource import ResourceCreateRequest, ResourceResponse
from app.store.event_store import EventStore, NotFoundError

router = APIRouter(prefix="/resources", tags=["resources"])


@router.post("", response_model=ResourceResponse, status_code=http_status.HTTP_201_CREATED)
def create_resource(
    body: ResourceCreateRequest,
    store: EventStore = Depends(get_store),
    current_user: AuthenticatedUser = Depends(require_role(Role.ADMIN)),
) -> ResourceResponse:
    # Audit fix (Critical, dimension 1): previously unauthenticated --
    # anyone could provision (or, via mismatched hospital_profile_id,
    # pollute another hospital's) bed/resource inventory. Provisioning
    # physical capacity is an operational/administrative action, not a
    # point-of-care one, so this is ADMIN-only (least privilege, same
    # reasoning app/api/audit.py's monitoring endpoint already applies) --
    # and always created under the caller's own hospital, never a
    # client-supplied one.
    resource = store.create_resource(
        resource_type=body.resource_type, label=body.label, hospital_profile_id=current_user.hospital_profile_id
    )
    return ResourceResponse.model_validate(resource)


@router.get("", response_model=List[ResourceResponse])
def list_resources(
    resource_type: Optional[ResourceType] = Query(default=None),
    status: Optional[ResourceStatus] = Query(default=None),
    store: EventStore = Depends(get_store),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> List[ResourceResponse]:
    # Audit fix (Critical, dimension 1/IDOR): previously unauthenticated
    # and let the caller specify ANY hospital_profile_id to list. Now
    # requires a staff token and is always scoped to that token's own
    # hospital.
    resources = store.list_resources(current_user.hospital_profile_id, resource_type=resource_type, status=status)
    return [ResourceResponse.model_validate(r) for r in resources]


@router.post("/{resource_id}/confirm-occupancy", response_model=ResourceResponse)
def confirm_occupancy(
    resource_id: str,
    store: EventStore = Depends(get_store),
    current_user: AuthenticatedUser = Depends(require_role(Role.NURSE, Role.DOCTOR, Role.ADMIN)),
) -> ResourceResponse:
    """Phase 6.3 'assigned space never occupied' pattern's resolving
    action: the nurse confirms the patient is physically in the assigned
    space, clearing that pattern's clock."""
    _require_resource_in_scope(resource_id, store, current_user)
    resource = store.confirm_occupancy(resource_id)
    return ResourceResponse.model_validate(resource)


@router.post("/{resource_id}/release", response_model=ResourceResponse)
def release_resource(
    resource_id: str,
    store: EventStore = Depends(get_store),
    current_user: AuthenticatedUser = Depends(require_role(Role.NURSE, Role.DOCTOR, Role.ADMIN)),
) -> ResourceResponse:
    _require_resource_in_scope(resource_id, store, current_user)
    resource = store.release_resource(resource_id)
    return ResourceResponse.model_validate(resource)


def _require_resource_in_scope(resource_id: str, store: EventStore, current_user: AuthenticatedUser) -> None:
    """Audit fix (Critical, dimension 1/IDOR): confirm-occupancy/release
    were previously unauthenticated and unscoped -- any caller could
    occupy or free any hospital's bed by ID. Resource rows carry
    hospital_profile_id directly (no case lookup needed, unlike
    observations/tests)."""
    resource = store.get_resource(resource_id)
    if resource is None:
        raise NotFoundError(f"No resource {resource_id}")
    require_hospital_scope(current_user, resource.hospital_profile_id)
