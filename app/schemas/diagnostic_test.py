from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import DiagnosticTestStatus


class OrderTestRequest(BaseModel):
    # No controlled vocabulary exists anywhere in this codebase for test
    # types (unlike concept_code -- see app/scoring/concepts.py), so this
    # stays free text rather than inventing an enum with no source of
    # truth; bounded so it can't be used to store arbitrarily large blobs.
    test_type: str = Field(min_length=1, max_length=100)


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
