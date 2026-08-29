"""
The LLM gateway (Phase 10.2): "a deterministic redaction layer sits
between the patient state store and every LLM call ... use a zero-
retention API configuration. State this explicitly."

This module is that sentence, enforced in code rather than left as a
deployment note: `LLMClientConfig` cannot be constructed with
`zero_retention=False` at all, and `prepare_llm_request()` is the single
sanctioned way to turn a Case into something that would ever leave this
process bound for an LLM API. Every future LLM-calling module (the Intake
and Explanation engines, both explicitly deferred pending a user-supplied
API key) MUST build its request through this function -- there is no
other exported way in app/privacy/ to get a prompt-shaped payload out of a
Case, by design.

No network call happens anywhere in this module. It prepares a request;
it does not send one. The actual HTTP client is the next checkpoint's
concern once an API key exists -- this is "the gatekeeper before the
gates" the user asked for, fully testable without one.
"""
from __future__ import annotations

from typing import Dict, Optional

from pydantic import BaseModel, field_validator

from app.config.hospital_profile import HospitalProfile
from app.models.case import Case
from app.privacy.snapshot import RedactedCaseSnapshot, build_redacted_snapshot
from app.store.event_store import EventStore


class LLMClientConfig(BaseModel):
    """Phase 10.2: 'Use a zero-retention API configuration. State this
    explicitly.' `zero_retention` cannot be set to False -- there is no
    escape hatch, because this project has no path for handling a
    provider's retained-prompt data if one were ever configured."""
    provider: str
    model: str
    api_key_env_var: str
    zero_retention: bool = True

    @field_validator("zero_retention")
    @classmethod
    def _must_be_zero_retention(cls, value: bool) -> bool:
        if value is not True:
            raise ValueError(
                "LLMClientConfig.zero_retention must be True -- Phase 10.2 requires an explicit "
                "zero-retention API configuration for every outbound LLM call in this project. "
                "There is no supported way to configure a retaining provider here."
            )
        return value


class LLMRequest(BaseModel):
    """The fully-prepared, safe-to-send payload. Nothing outside this
    shape (plus `config`) should ever be serialised into an actual API
    call -- in particular, never the token_map returned alongside this by
    `prepare_llm_request`, which must stay server-side."""
    config: LLMClientConfig
    snapshot: RedactedCaseSnapshot


def prepare_llm_request(
    case: Case, store: EventStore, profile: HospitalProfile, config: LLMClientConfig
) -> tuple[LLMRequest, Dict[str, str]]:
    """The mandatory gate: redact, then attach the (enforced zero-
    retention) client config. Returns (request, token_map) -- `token_map`
    is for rehydrating the LLM's eventual response for display and must
    never be transmitted; see app/privacy/redaction.py's RedactionResult.
    """
    snapshot, token_map = build_redacted_snapshot(case, store, profile)
    return LLMRequest(config=config, snapshot=snapshot), token_map
