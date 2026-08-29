"""
Schemas for the Phase 8.5 Alert Aggregation Engine (CP12).
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict

from app.models.enums import AlertDismissalReasonCode, AlertType


class AlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    alert_id: str
    hospital_profile_id: str
    alert_type: AlertType
    created_at: datetime
    payload: Dict[str, Any]
    dismissed: bool
    dismissed_at: Optional[datetime]
    dismissed_by: Optional[str]
    dismissal_reason_code: Optional[AlertDismissalReasonCode]
    dismissal_free_text: Optional[str]


class AlertDismissRequest(BaseModel):
    reason_code: AlertDismissalReasonCode
    free_text_reason: Optional[str] = None
