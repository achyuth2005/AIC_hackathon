"""
Guardian Queue endpoint (Phase 5.2, Phase 8.2 nurse dashboard's main view).
"""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse

from app.api.deps import get_store
from app.auth.deps import get_current_user
from app.auth.models import AuthenticatedUser
from app.config.hospital_profile import load_hospital_profile
from app.queue.guardian_queue import build_queue
from app.queue.models import QueueEntry
from app.queue.printable import render_printable_snapshot
from app.store.event_store import EventStore

router = APIRouter(prefix="/queue", tags=["queue"])


@router.get("", response_model=List[QueueEntry])
def get_queue(
    store: EventStore = Depends(get_store),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> List[QueueEntry]:
    """Returns every ACTIVE case under the caller's own hospital, in
    Guardian Queue order (Phase 5.2): final_acuity ascending first, above
    all else -- see app/queue/guardian_queue.py for the full
    lexicographic key.

    Reading this endpoint has documented side effects: it opportunistically
    flags newly-overdue reassessments and backfills a missing initial
    assessment, in place of a real scheduler (see guardian_queue.py's
    module docstring).

    Audit fix (Critical, dimension 1/IDOR): previously unauthenticated
    with a caller-suppliable hospital_profile_id -- this is the primary
    nurse-facing PHI view (names, MRNs, acuity) and was readable, and
    (via the write side effects above) mutable, by anyone. Now requires a
    staff token and is always scoped to that token's own hospital."""
    profile = load_hospital_profile(current_user.hospital_profile_id)
    return build_queue(store, profile)


@router.get("/printable", response_class=PlainTextResponse)
def get_printable_queue_snapshot(
    store: EventStore = Depends(get_store),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> str:
    """Phase 9.5: 'Total system failure -> Printed queue snapshot with
    acuity, arrival time and reassessment-due time. Print this in the
    demo.' Plain text, no JS/CSS -- open this URL in any browser and
    press print, or curl it straight to a printer. Built from the exact
    same build_queue() the nurse dashboard uses; see
    app/queue/printable.py's module docstring.

    Audit fix (Critical, dimension 1/IDOR): previously unauthenticated
    with a caller-suppliable hospital_profile_id, returning full PHI in
    plaintext to anyone. Now requires a staff token, same as every other
    PHI-reading view. Noted honestly: this narrows Phase 9.5's "total
    system failure" fallback to failures that leave the auth service and
    an already-issued token usable (a 12-hour token cached on a nurse's
    device still works through most outages of the clinical systems this
    is meant to survive) -- it does not cover a failure of authentication
    itself, which is a real, accepted residual tradeoff of closing the
    much larger, certain exposure of PHI to unauthenticated callers."""
    profile = load_hospital_profile(current_user.hospital_profile_id)
    entries = build_queue(store, profile)
    return render_printable_snapshot(entries, hospital_profile_id=current_user.hospital_profile_id)
