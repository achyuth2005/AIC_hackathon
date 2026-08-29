"""
Groq (OpenAI-compatible chat completions) HTTP client (Phase 3.2, CP17).

This is the ONLY module in this codebase that makes an outbound network
call to an LLM provider. Every caller must go through
app/privacy/llm_gateway.py's LLMClientConfig first (zero_retention
enforced, redaction applied there) -- this module doesn't redact anything
itself; it just sends whatever it's given and returns the raw response
text, so an unredacted payload reaching here is a bug in the CALLER, not
something this module can catch after the fact. Its own contribution to
the "gate" is `"store": false` on every request (Phase 10.2's "zero-
retention API configuration" -- an OpenAI-compatible parameter Groq's
endpoint accepts without error; whether Groq's backend actually honours it
is a provider data-handling question this code cannot verify or prove,
[Requires legal validation] like every other compliance-adjacent claim in
this project).

Phase 9.5 failure mode: any network error, timeout, non-2xx response, or
an empty/missing message content raises LLMUnavailableError. Callers
(app/llm/intake.py, app/llm/explanation.py) must catch this and fall back
to their deterministic path -- never let a raised exception here become an
unhandled 500 in place of "LLM unavailable, rules-only".
"""
from __future__ import annotations

import os
from typing import Optional

import httpx

from app.privacy.llm_gateway import LLMClientConfig

_GROQ_BASE_URL = "https://api.groq.com/openai/v1/chat/completions"


class LLMUnavailableError(RuntimeError):
    """Raised for anything that means 'could not get a usable response
    from the LLM' -- missing API key, network failure, timeout, non-2xx,
    or an empty completion. Deliberately one exception type: every caller
    treats all of these identically (fall back to a deterministic path),
    so there is no value in distinguishing them further at the type
    level."""


class LLMClient:
    def __init__(self, config: LLMClientConfig, *, http_client: Optional[httpx.Client] = None, timeout: float = 20.0):
        self.config = config
        self._http_client = http_client  # injected in tests; a real one is opened per-call otherwise
        self._timeout = timeout

    def _api_key(self) -> str:
        key = os.environ.get(self.config.api_key_env_var)
        if not key:
            raise LLMUnavailableError(
                f"No value set for environment variable {self.config.api_key_env_var!r} "
                f"(HospitalProfile.llm.api_key_env_var)."
            )
        return key

    def _post(self, payload: dict) -> dict:
        headers = {"Authorization": f"Bearer {self._api_key()}", "Content-Type": "application/json"}
        try:
            if self._http_client is not None:
                response = self._http_client.post(_GROQ_BASE_URL, json=payload, headers=headers, timeout=self._timeout)
            else:
                with httpx.Client(timeout=self._timeout) as client:
                    response = client.post(_GROQ_BASE_URL, json=payload, headers=headers)
        except httpx.HTTPError as exc:
            raise LLMUnavailableError(f"Network error calling {self.config.provider}: {exc}") from exc

        if response.status_code >= 400:
            raise LLMUnavailableError(
                f"{self.config.provider} returned HTTP {response.status_code}: {response.text[:500]}"
            )
        try:
            return response.json()
        except ValueError as exc:
            raise LLMUnavailableError(f"{self.config.provider} returned a non-JSON response.") from exc

    def _complete(self, *, system_prompt: str, user_prompt: str, max_tokens: int, json_mode: bool) -> str:
        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": max_tokens,
            "store": False,  # Phase 10.2 "zero-retention API configuration" -- see module docstring
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        body = self._post(payload)
        try:
            content = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMUnavailableError(f"Unexpected response shape from {self.config.provider}: {body!r}") from exc

        if not content or not content.strip():
            raise LLMUnavailableError(f"{self.config.provider} returned an empty completion.")
        return content

    def complete_json(self, *, system_prompt: str, user_prompt: str, max_tokens: int = 900) -> str:
        """Returns the raw JSON text the model produced -- NOT parsed
        here. Callers validate against their own Pydantic schema (Phase
        3.2: 'force structured JSON output and validate it against a
        schema; reject and retry rather than accept malformed output') --
        parsing is the caller's job so each caller's retry/schema policy
        stays local to it."""
        return self._complete(system_prompt=system_prompt, user_prompt=user_prompt, max_tokens=max_tokens, json_mode=True)

    def complete_text(self, *, system_prompt: str, user_prompt: str, max_tokens: int = 700) -> str:
        return self._complete(system_prompt=system_prompt, user_prompt=user_prompt, max_tokens=max_tokens, json_mode=False)
