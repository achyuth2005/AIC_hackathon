"""
Phase 8.4 control tower (CP15): "anticipate, not report. Five tiles
maximum, every tile actionable." Exactly the five named tiles, in the
order the architecture doc lists them -- "if a tile does not change what
someone does in the next fifteen minutes, cut it" is why this stops at
five rather than surfacing every engine this backend has.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Dict, List

from app.config.hospital_profile import HospitalProfile
from app.models.enums import CaseStatus, DeteriorationTrend, ResourceStatus, ResourceType
from app.ops.flow_engine import check_stuck_patients
from app.queue.time_engine import deterioration_trend
from app.schemas.control_tower import (
    AcuityBandTile,
    CapacityTile,
    ControlTowerResponse,
    DeterioratingPatientTile,
    IncomingAmbulanceTile,
)
from app.store.event_store import EventStore


def _patients_by_acuity_band(store: EventStore, active_cases) -> List[AcuityBandTile]:
    counts: Dict[int, int] = defaultdict(int)
    overdue: Dict[int, int] = defaultdict(int)
    for case in active_cases:
        latest = store.get_latest_risk_assessment(case.case_id)
        if latest is None:
            continue
        counts[latest.final_acuity] += 1
        if case.reassessment_overdue:
            overdue[latest.final_acuity] += 1
    return [
        AcuityBandTile(acuity=acuity, case_count=counts[acuity], overdue_count=overdue.get(acuity, 0))
        for acuity in sorted(counts)
    ]


def _deteriorating_patients(store: EventStore, active_cases) -> List[DeterioratingPatientTile]:
    tiles = []
    for case in active_cases:
        history = store.get_risk_assessment_history(case.case_id)
        if deterioration_trend(history) == DeteriorationTrend.WORSENING:
            tiles.append(
                DeterioratingPatientTile(
                    case_id=case.case_id,
                    display_name=case.display_name,
                    from_acuity=history[-2].final_acuity,
                    to_acuity=history[-1].final_acuity,
                )
            )
    return tiles


def _capacity(store: EventStore, profile: HospitalProfile, active_cases) -> List[CapacityTile]:
    tiles = []
    active_case_ids = {c.case_id for c in active_cases}
    for resource_type in ResourceType:
        resources = store.list_resources(profile.profile_id, resource_type=resource_type)
        available = sum(1 for r in resources if r.status == ResourceStatus.AVAILABLE)
        occupied = sum(1 for r in resources if r.status == ResourceStatus.OCCUPIED)
        out_of_service = sum(1 for r in resources if r.status == ResourceStatus.OUT_OF_SERVICE)
        occupied_case_ids = {r.assigned_case_id for r in resources if r.status == ResourceStatus.OCCUPIED}
        needed_estimate = len(active_case_ids - occupied_case_ids)
        tiles.append(
            CapacityTile(
                resource_type=resource_type.value,
                available=available,
                occupied=occupied,
                out_of_service=out_of_service,
                needed_estimate=needed_estimate,
            )
        )
    return tiles


def _incoming_ambulances(store: EventStore, profile: HospitalProfile) -> List[IncomingAmbulanceTile]:
    pre_arrival = store.list_cases(status=CaseStatus.PRE_ARRIVAL, hospital_profile_id=profile.profile_id)
    tiles = []
    for case in pre_arrival:
        latest = store.get_latest_risk_assessment(case.case_id)
        tiles.append(
            IncomingAmbulanceTile(
                case_id=case.case_id,
                display_name=case.display_name,
                predicted_acuity=latest.final_acuity if latest else None,
            )
        )
    return tiles


def build_control_tower(store: EventStore, profile: HospitalProfile) -> ControlTowerResponse:
    active_cases = store.list_cases(status=CaseStatus.ACTIVE, hospital_profile_id=profile.profile_id)
    return ControlTowerResponse(
        patients_by_acuity_band=_patients_by_acuity_band(store, active_cases),
        deteriorating_patients=_deteriorating_patients(store, active_cases),
        stuck_patients=check_stuck_patients(store, profile),
        capacity=_capacity(store, profile, active_cases),
        incoming_ambulances=_incoming_ambulances(store, profile),
    )
