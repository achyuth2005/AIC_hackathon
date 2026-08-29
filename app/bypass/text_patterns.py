"""
Emergency Bypass detector #3 (Phase 3.5): "A curated critical-phrase list
plus, optionally, an LLM classifier restricted to a binary escalate/
do-not-escalate output." Only the curated-phrase half is implemented here --
the LLM classifier is explicitly optional in the source document and
depends on an external API key this checkpoint does not require (deferred
to CP14's Intake Engine). This detector runs standalone and is sufficient
on its own per Phase 3.5's own wording.
"""
from __future__ import annotations

from typing import List, Optional


def detect_critical_phrase(text: Optional[str], phrases: List[str]) -> Optional[str]:
    """Case-insensitive substring match. Returns the first configured
    phrase found in `text`, or None. Deliberately simple and fully
    deterministic -- inspectable and reproducible, per Phase 3.2's
    'deterministic lookup' principle applied to this detector too."""
    if not text:
        return None
    lowered = text.lower()
    for phrase in phrases:
        if phrase.lower() in lowered:
            return phrase
    return None
