"""
Guardian Queue endpoint (Phase 5.2, Phase 8.2 nurse dashboard's main view).
"""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse

from app.api.deps import get_store
from app.config.hospital_profile import load_hospital_profile
from app.queue.guardian_queue import build_queue
from app.queue.models import QueueEntry
from app.queue.printable import render_printable_snapshot
from app.store.event_store import EventStore

router = APIRouter(prefix="/queue", tags=["queue"])


@router.get("", response_model=List[QueueEntry])
def get_queue(
    hospital_profile_id: str = Query(default="default"),
    store: EventStore = Depends(get_store),
) -> List[QueueEntry]:
    """Returns every ACTIVE case under `hospital_profile_id`, in Guardian
    Queue order (Phase 5.2): final_acuity ascending first, above all else --
    see app/queue/guardian_queue.py for the full lexicographic key.

    Reading this endpoint has documented side effects: it opportunistically
    flags newly-overdue reassessments and backfills a missing initial
    assessment, in place of a real scheduler (see guardian_queue.py's
    module docstring)."""
    profile = load_hospital_profile(hospital_profile_id)
    return build_queue(store, profile)


@router.get("/printable", response_class=PlainTextResponse)
def get_printable_queue_snapshot(
    hospital_profile_id: str = Query(default="default"),
    store: EventStore = Depends(get_store),
) -> str:
    """Phase 9.5: 'Total system failure -> Printed queue snapshot with
    acuity, arrival time and reassessment-due time. Print this in the
    demo.' Plain text, no JS/CSS -- open this URL in any browser and
    press print, or curl it straight to a printer. Built from the exact
    same build_queue() the nurse dashboard uses; see
    app/queue/printable.py's module docstring."""
    profile = load_hospital_profile(hospital_profile_id)
    entries = build_queue(store, profile)
    return render_printable_snapshot(entries, hospital_profile_id=hospital_profile_id)
