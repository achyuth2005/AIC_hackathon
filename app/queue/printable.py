"""
Printable queue snapshot (Phase 9.5): "Total system failure -> Printed
queue snapshot with acuity, arrival time and reassessment-due time. Print
this in the demo. It is a five-second moment that wins trust." And the
phase's own invariant: "removing every AI component leaves a working
digital triage form, a working timer, and a working queue. That is the
honest floor of the product."

This is that floor, rendered as plain monospace text: no JS, no CSS, no
JSON a browser would need help displaying -- curl it, or open it in any
browser and press print, and it is immediately legible. Deliberately
built from the SAME `build_queue()` the nurse dashboard already uses (no
parallel "degraded mode" query path to drift out of sync with the real
one) -- if the AI layers are down, the queue itself is unaffected either
way (Phase 9.5's whole point), so there is nothing special this renderer
needs to work around.
"""
from __future__ import annotations

from datetime import datetime
from typing import List

from app.queue.models import QueueEntry
from app.timeutil import utcnow

_HEADER = f"{'ESI':<4}{'ARRIVED':<20}{'WAITING':<10}{'PATIENT':<20}{'REASSESSMENT':<24}{'FLAG'}"


def _format_row(entry: QueueEntry) -> str:
    arrived = entry.arrival_time.strftime("%Y-%m-%d %H:%M")
    waiting = f"{entry.waiting_minutes:.0f}m"
    patient = (entry.display_name or entry.case_id[:8])[:19]
    if entry.reassessment.is_due:
        overdue = entry.reassessment.minutes_overdue
        reassessment = f"OVERDUE ({overdue:.0f}m)" if overdue is not None else "OVERDUE"
    else:
        reassessment = f"due in {entry.reassessment.interval_minutes}m" if entry.reassessment.interval_minutes else "n/a"
    flag = "BYPASS-ACTIVE" if entry.emergency_bypass_active else entry.primary_attention_flag.value

    return f"{entry.final_acuity:<4}{arrived:<20}{waiting:<10}{patient:<20}{reassessment:<24}{flag}"


def render_printable_snapshot(entries: List[QueueEntry], *, generated_at: datetime = None, hospital_profile_id: str = "default") -> str:
    generated_at = generated_at or utcnow()
    lines = [
        "PATIENTTRIAGE.AI -- PRINTED QUEUE SNAPSHOT (DEGRADED-MODE FALLBACK)",
        f"Hospital profile: {hospital_profile_id}    Generated: {generated_at.strftime('%Y-%m-%d %H:%M:%S')} UTC",
        f"{len(entries)} active patient(s), sorted by acuity (most urgent first), then by wait within band.",
        "-" * len(_HEADER),
        _HEADER,
        "-" * len(_HEADER),
    ]
    if not entries:
        lines.append("(queue is empty)")
    else:
        lines.extend(_format_row(e) for e in entries)
    lines.append("-" * len(_HEADER))
    lines.append(
        "This snapshot reflects the deterministic queue only -- acuity ordering, wait timers, and reassessment "
        "status hold regardless of any AI component's availability (Phase 9.5)."
    )
    return "\n".join(lines)
