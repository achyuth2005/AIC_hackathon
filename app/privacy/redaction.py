"""
Deterministic redaction shim (Phase 10.2): "A deterministic redaction
layer sits between the patient state store and every LLM call. Names,
contact details, identifiers and addresses are stripped and replaced with
tokens before the prompt is constructed, and re-hydrated in the response
on the way back. The LLM sees 'a 67-year-old patient', never a name."

This module is the "gatekeeper before the gates": it exists and is fully
tested BEFORE the LLM Intake/Explanation engines it will sit in front of
are built (those need a user-supplied API key and are the explicitly
deferred next checkpoint). Nothing in app/privacy/ makes an HTTP call or
imports an LLM SDK -- it only prepares/cleans text and data, and
app/privacy/llm_gateway.py is the one place a future LLM-calling module is
required to route through.

Two-tier redaction strategy, deterministic end to end (no NER model, no
LLM-based redaction -- using an LLM to redact before calling an LLM would
be circular and would defeat the "deterministic" requirement):

1. **Known-identifier substring matching**: this system already knows,
   structurally, exactly which strings identify THIS patient (their own
   `display_name`, `mrn`) -- those exact values are scrubbed from any
   free text wherever they appear, verbatim, before anything else runs.
2. **Pattern-based scrubbing**: phone numbers, email addresses, and
   national/health-ID-shaped numeric sequences (e.g. a 12-digit Aadhaar-
   shaped number, an alphanumeric MRN/ABHA-shaped token) are matched by
   regex and replaced, independent of whether they happen to belong to
   this patient (a caregiver's phone number mentioned in free text is
   exactly the kind of "contact detail" Phase 10.2 also names).

What this deliberately does NOT attempt: general-purpose named-entity
recognition to catch every possible way a name could appear in free text
(e.g. "it's Priya's dad calling" with no structural marker). That is a
harder, genuinely unsolved problem for a deterministic, offline shim, and
is stated here as a known limitation rather than silently claimed as
solved -- see `KNOWN_LIMITATIONS` below.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

KNOWN_LIMITATIONS = (
    "Known-identifier substring matching only catches THIS patient's own "
    "display_name/mrn verbatim, and pattern matching only catches PII in "
    "phone/email/ID-shaped forms. Free-text mentions of a name with no "
    "structural marker (e.g. a relative's name in a sentence) are not "
    "guaranteed to be caught -- this is a deterministic shim, not an NER "
    "model, and that boundary is stated here rather than silently claimed "
    "as solved."
)

# Order matters: more specific patterns first, so e.g. a phone number
# embedded next to digits doesn't get partially eaten by a looser pattern.
# Each entry is (label, compiled_pattern, extra_guard). extra_guard, if
# given, is an additional predicate the matched text must satisfy --
# used for the alphanumeric ID pattern below, where a plain regex
# character class can't cleanly express "at least one letter AND one
# digit" without fragile lookahead chains.
_PATTERNS: List[tuple] = [
    ("EMAIL", re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"), None),
    # Phone numbers: optional +country code, then 8-13 digits with optional
    # spaces/hyphens -- deliberately loose (better to over-redact a
    # number-shaped string than under-redact a real phone number). A bare
    # 12-digit run (Aadhaar-shaped, [Assumption] for the assumed India
    # jurisdiction, Phase 10.1) also falls inside this length range.
    ("PHONE", re.compile(r"(?:\+?\d{1,3}[\s-]?)?(?:\d[\s-]?){8,13}\d"), None),
    # National/health-ID-shaped tokens: the alphanumeric shape typical of
    # an MRN/ABHA-style identifier -- at least one letter AND one digit,
    # 6+ characters, enforced by the guard below rather than the regex
    # itself.
    (
        "ID",
        re.compile(r"\b[A-Za-z0-9-]{6,}\b"),
        lambda s: any(c.isalpha() for c in s) and any(c.isdigit() for c in s),
    ),
]


@dataclass
class RedactionResult:
    redacted_text: str
    token_map: Dict[str, str] = field(default_factory=dict)  # token -> original value, kept server-side only

    def rehydrate(self, text: str) -> str:
        """Reverses tokens back to their original values -- for displaying
        an LLM's response to a clinician, never for anything sent back to
        the LLM. See app/privacy/llm_gateway.py's module docstring."""
        for token, original in self.token_map.items():
            text = text.replace(token, original)
        return text


def redact_text(text: Optional[str], *, known_identifiers: Optional[Dict[str, str]] = None) -> RedactionResult:
    """`known_identifiers` is {label: value}, e.g. {"NAME": case.display_name,
    "MRN": case.mrn} -- values already known to identify this specific
    patient, scrubbed by exact substring match before the generic
    pattern-based pass runs. Values that are None/empty are skipped
    (nothing to match)."""
    if not text:
        return RedactionResult(redacted_text=text or "", token_map={})

    token_map: Dict[str, str] = {}
    counters: Dict[str, int] = {}
    working = text

    def _next_token(label: str) -> str:
        counters[label] = counters.get(label, 0) + 1
        return f"[{label}_{counters[label]}]"

    for label, value in (known_identifiers or {}).items():
        if not value:
            continue
        value_str = str(value)
        while value_str in working:
            token = _next_token(label)
            token_map[token] = value_str
            working = working.replace(value_str, token, 1)

    for label, pattern, guard in _PATTERNS:
        def _replace(match: re.Match, label=label, guard=guard) -> str:
            matched = match.group(0)
            if guard is not None and not guard(matched):
                return matched  # doesn't actually satisfy the guard -- leave it alone
            token = _next_token(label)
            token_map[token] = matched
            return token

        working = pattern.sub(_replace, working)

    return RedactionResult(redacted_text=working, token_map=token_map)
