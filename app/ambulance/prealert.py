"""
Ambulance pre-alert (Phase 7.3, CP18): "Not the full case. A pre-alert
should be scannable in three seconds: predicted acuity band, one-line
presentation, key abnormal vitals with times, interventions already
performed, ETA range, and what the hospital should prepare. Everything
else stays one tap away."

`interventions_already_performed` is deliberately always an empty list,
not fabricated: this prototype has no intervention/treatment-tracking
data model anywhere (Phase 6.1 names medication/equipment tracking out of
scope), so there is nothing to populate it from. Returning an empty list
rather than omitting the field keeps the shape Phase 7.3 asks for while
being honest that the data behind it doesn't exist yet -- the field is
ready for a future paramedic-documentation feature to fill in.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from app.ambulance.eta import ETARange, compute_eta_range
from app.config.hospital_profile import HospitalProfile
from app.models.case import Case
from app.scoring.presentation import one_line_presentation
from app.store.event_store import EventStore

# [Requires clinical validation]: illustrative prepare-for text per acuity
# band, same convention as every other illustrative mapping in this
# project. Deliberately generic -- "what the hospital should prepare" in
# the real doc's own example is a scannable one-line cue, not a care plan.
_PREPARE_MESSAGES = {
    1: "Prepare a resuscitation-capable space and team; be ready for immediate life support.",
    2: "Prepare an urgent treatment space; clinician review needed on arrival.",
    3: "Prepare a standard treatment space.",
    4: "Standard intake; no special preparation anticipated.",
    5: "Standard intake; no special preparation anticipated.",
}


class KeyAbnormalVital(BaseModel):
    concept_code: str
    label: str
    raw_value: Any
    unit: Optional[str]
    observed_at: Any
    points: int


class PreAlertView(BaseModel):
    case_id: str
    predicted_acuity_band: Optional[int]
    one_line_presentation: Optional[str]
    key_abnormal_vitals: List[KeyAbnormalVital]
    interventions_already_performed: List[str]  # always [] -- see module docstring
    eta_range: Optional[ETARange]
    what_hospital_should_prepare: str


def build_pre_alert(case: Case, store: EventStore, profile: HospitalProfile) -> PreAlertView:
    latest = store.get_latest_risk_assessment(case.case_id)
    predicted_acuity = latest.final_acuity if latest else None

    key_abnormal_vitals = []
    if latest is not None:
        for component in latest.rule_component_breakdown:
            if not component.get("is_missing") and (component.get("points") or 0) > 0:
                key_abnormal_vitals.append(
                    KeyAbnormalVital(
                        concept_code=component["concept_code"], label=component["label"],
                        raw_value=component.get("raw_value"), unit=component.get("unit"),
                        observed_at=component.get("observed_at"), points=component["points"],
                    )
                )

    transport = store.get_ambulance_transport(case.case_id)
    eta_range = compute_eta_range(transport) if transport is not None else None

    prepare = _PREPARE_MESSAGES.get(predicted_acuity, "Awaiting vitals -- preparation cannot be predicted yet.")

    return PreAlertView(
        case_id=case.case_id,
        predicted_acuity_band=predicted_acuity,
        one_line_presentation=one_line_presentation(store, case.case_id),
        key_abnormal_vitals=key_abnormal_vitals,
        interventions_already_performed=[],
        eta_range=eta_range,
        what_hospital_should_prepare=prepare,
    )
