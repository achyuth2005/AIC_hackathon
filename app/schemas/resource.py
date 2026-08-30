from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ResourceStatus, ResourceType


class ResourceCreateRequest(BaseModel):
    resource_type: ResourceType
    label: str = Field(min_length=1, max_length=100)
    hospital_profile_id: str = Field(default="default", max_length=100)


class AssignResourceRequest(BaseModel):
    resource_type: ResourceType


class ResourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    resource_id: str
    hospital_profile_id: str
    resource_type: ResourceType
    label: str
    status: ResourceStatus
    assigned_case_id: Optional[str]
    assigned_at: Optional[datetime]
    occupancy_stuck_flagged: bool


class CapacityConflictResponse(BaseModel):
    """Phase 6.2: the shape of a 409 raised by POST /cases/{id}/assign-resource."""
    detail: str
    resource_type: ResourceType
    candidate_actions: List[str]
