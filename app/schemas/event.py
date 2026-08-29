from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict


class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_id: str
    case_id: Optional[str]
    event_type: str
    payload: Dict[str, Any]
    occurred_at: datetime
    recorded_at: datetime
