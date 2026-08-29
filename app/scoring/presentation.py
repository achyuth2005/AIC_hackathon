"""
Shared "one-line presentation" helper: the latest current free-text
symptom report, truncated for a dense list view. Used by the Guardian
Queue's nurse-facing column (Phase 8.2, CP15) and the ambulance pre-alert
(Phase 7.3, CP18) -- factored out once rather than duplicated between them.
"""
from __future__ import annotations

from typing import Optional

from app.scoring import concepts
from app.store.event_store import EventStore

_MAX_CHARS = 80


def one_line_presentation(store: EventStore, case_id: str, *, max_chars: int = _MAX_CHARS) -> Optional[str]:
    obs = store.get_latest_current_observation(case_id, concepts.SYMPTOM_TEXT)
    if obs is None or not obs.value_text:
        return None
    text = obs.value_text.strip()
    return text if len(text) <= max_chars else text[: max_chars - 1].rstrip() + "…"
