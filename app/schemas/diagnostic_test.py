from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.enums import DiagnosticTestStatus


class OrderTestRequest(BaseModel):
    test_type: str


class DiagnosticTestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    test_id: str
    case_id: str
    test_type: str
    status: DiagnosticTestStatus
    ordered_at: datetime
    sample_collected_at: Optional[datetime]
    result_available_at: Optional[datetime]
    result_reviewed_at: Optional[datetime]
    stuck_flagged: bool
