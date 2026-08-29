"""
Schemas for the Phase 3.2 LLM Intake/Explanation engines (CP17).
"""
from __future__ import annotations

from pydantic import BaseModel


class IntakeRequest(BaseModel):
    """Free text from a patient/caregiver/nurse-entered statement. This
    is the ONE input the Intake Engine accepts -- it is never given
    numbers to validate, only prose to extract candidate facts from."""
    text: str
