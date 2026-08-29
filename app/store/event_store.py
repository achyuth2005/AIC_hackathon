"""
EventStore: the single write/read path onto the Patient State Store.

This is the concrete implementation of Phase 11.D's central box: "PATIENT
STATE STORE (event-sourced, append-only) ... every engine below is a
consumer of this stream." Nothing outside this module should construct or
mutate Case/Observation/Event rows directly -- that is what keeps
"never mutate, always supersede" (Phase 4.2) an enforced invariant rather
than a convention someone can bypass later.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.case import Case
from app.models.observation import Observation
from app.models.event import Event, KNOWN_EVENT_TYPES
from app.models.risk_assessment import RiskAssessment
from app.models.resource import Resource
from app.models.diagnostic_test import DiagnosticTest
from app.models.human_decision import HumanDecision
from app.models.alert import Alert
from app.models.data_conflict import DataConflict
from app.models.case_review import CaseReview
from app.models.ambulance_transport import AmbulanceTransport
from app.models.enums import (
    AlertDismissalReasonCode,
    AlertType,
    ArrivalMode,
    BypassSource,
    CaseStatus,
    ConfidenceBand,
    DecidingLayer,
    DeEscalationReasonCode,
    DiagnosticTestStatus,
    HumanDecisionAction,
    IdentityLinkStatus,
    MeasurementStatus,
    ReliabilityTier,
    ResourceStatus,
    ResourceType,
    SourceType,
    ValueType,
)
from app.timeutil import utcnow as _utcnow, to_naive_utc


class UnknownEventTypeError(ValueError):
    pass


class ObservationAlreadySupersededError(ValueError):
    pass


class NotFoundError(KeyError):
    """Raised for any missing Case/Observation lookup -- the API layer maps
    this uniformly to HTTP 404 regardless of which entity was missing."""
    pass


class InvalidArrivalError(ValueError):
    """Raised when record_arrival is called on a case that isn't awaiting
    arrival (Phase 7.1: PATIENT_ARRIVED is specifically the ambulance-to-ED
    transition, not a generic re-check-in)."""
    pass


class CapacityConflictError(RuntimeError):
    """Phase 6.2: raised when no resource of the requested type is
    AVAILABLE. NOT a scoring exception -- acuity is untouched by this;
    the caller (API layer) maps it to a 409 carrying the candidate actions
    from HospitalProfile.ops.capacity_conflict_candidate_actions, exactly
    as Phase 6.2 describes: 'the system surfaces the conflict. A human
    resolves it.'"""
    def __init__(self, resource_type: ResourceType, candidate_actions: List[str]):
        self.resource_type = resource_type
        self.candidate_actions = candidate_actions
        super().__init__(f"No {resource_type.value} resource is available.")


class EventStore:
    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Case lifecycle (Phase 7.1: one record, ambulance to disposition)
    # ------------------------------------------------------------------
    def create_case(
        self,
        *,
        hospital_profile_id: str = "default",
        mrn: Optional[str] = None,
        display_name: Optional[str] = None,
        date_of_birth=None,
        age_years: Optional[int] = None,
        sex: Optional[str] = None,
        arrival_mode: ArrivalMode = ArrivalMode.WALK_IN,
        identity_link_status: Optional[IdentityLinkStatus] = None,
    ) -> Case:
        if identity_link_status is None:
            # Phase 7.1: ambulance cases start unlinked until a human
            # confirms identity; walk-ins are confirmed by construction
            # (the patient is standing in front of registration).
            identity_link_status = (
                IdentityLinkStatus.UNLINKED
                if arrival_mode == ArrivalMode.AMBULANCE
                else IdentityLinkStatus.CONFIRMED
            )
        status = CaseStatus.PRE_ARRIVAL if arrival_mode == ArrivalMode.AMBULANCE else CaseStatus.ACTIVE

        now = _utcnow()
        case = Case(
            hospital_profile_id=hospital_profile_id,
            mrn=mrn,
            display_name=display_name,
            date_of_birth=date_of_birth,
            age_years=age_years,
            sex=sex,
            arrival_mode=arrival_mode,
            status=status,
            identity_link_status=identity_link_status,
            last_reassessed_at=now,  # Phase 5.3 clock starts immediately, not on the first observation
        )
        self.db.add(case)
        self.db.flush()  # populate case.case_id before we reference it

        self.append_event(
            case_id=case.case_id,
            event_type="CASE_CREATED",
            payload={"arrival_mode": arrival_mode.value, "hospital_profile_id": hospital_profile_id},
        )
        self.db.commit()
        self.db.refresh(case)
        return case

    def get_case(self, case_id: str) -> Optional[Case]:
        return self.db.get(Case, case_id)

    def list_cases(self, status: Optional[CaseStatus] = None) -> List[Case]:
        """Raw listing, ordered by creation time. NOT the Guardian Queue --
        acuity-based lexicographic ordering (Phase 5.2) is CP7; this exists
        so CP2 has something the frontend can call while that's built."""
        q = self.db.query(Case)
        if status is not None:
            q = q.filter(Case.status == status)
        return q.order_by(Case.created_at.asc()).all()

    def record_arrival(self, case_id: str, *, occurred_at: Optional[datetime] = None) -> Case:
        """Phase 4.4 / 7.1: PATIENT_ARRIVED is the ambulance-to-ED
        transition. It is an event on the existing case, not a new case."""
        case = self.db.get(Case, case_id)
        if case is None:
            raise NotFoundError(f"No case {case_id}")
        if case.status != CaseStatus.PRE_ARRIVAL:
            raise InvalidArrivalError(
                f"Case {case_id} is not awaiting arrival (status={case.status.value}); "
                f"PATIENT_ARRIVED only applies to the ambulance PRE_ARRIVAL -> ACTIVE transition."
            )

        arrived_at = to_naive_utc(occurred_at) if occurred_at is not None else _utcnow()
        case.status = CaseStatus.ACTIVE
        case.arrived_at = arrived_at
        self.append_event(case_id=case_id, event_type="PATIENT_ARRIVED", occurred_at=arrived_at)
        self.db.commit()
        self.db.refresh(case)
        return case

    def propose_identity_match(
        self,
        case_id: str,
        *,
        candidate_mrn: str,
        candidate_display_name: Optional[str] = None,
        confidence: Optional[float] = None,
        occurred_at: Optional[datetime] = None,
    ) -> Case:
        """Phase 7.1 identity matching, minimal viable slice (CP11): 'system
        proposes candidate matches with confidence, a human confirms, ...
        until confirmed the case runs as unlinked.' This method IS the
        propose half -- it moves identity_link_status from UNLINKED to
        CANDIDATE_PROPOSED and logs the candidate, nothing more.

        Deliberately NOT built: the fuzzy-matching search itself (querying
        a patient registry/MPI for candidates by name/DOB/ABHA-ID). No such
        registry exists in this prototype -- there is nothing to search
        against -- so `candidate_mrn`/`candidate_display_name` are supplied
        by the caller as already-found candidates, exactly as a real
        upstream matching service would hand them to this step. That
        larger piece (Phase 7.1's 'candidate matches' search) remains
        explicitly out of scope, not silently faked here."""
        case = self.db.get(Case, case_id)
        if case is None:
            raise NotFoundError(f"No case {case_id}")

        now = to_naive_utc(occurred_at) if occurred_at is not None else _utcnow()
        case.identity_link_status = IdentityLinkStatus.CANDIDATE_PROPOSED
        self.append_event(
            case_id=case_id,
            event_type="IDENTITY_MATCH_PROPOSED",
            payload={
                "candidate_mrn": candidate_mrn,
                "candidate_display_name": candidate_display_name,
                "confidence": confidence,
            },
            occurred_at=now,
        )
        self.db.commit()
        self.db.refresh(case)
        return case

    def confirm_identity_match(
        self,
        case_id: str,
        *,
        mrn: str,
        confirmed_by: str,
        display_name: Optional[str] = None,
        occurred_at: Optional[datetime] = None,
    ) -> Case:
        """Phase 7.1's confirm half: 'a human confirms, the confirmation is
        logged.' Never auto-merges -- this is the only path that ever sets
        identity_link_status to CONFIRMED and writes case.mrn, and it
        requires an explicit human identity (`confirmed_by`) to do so,
        the same pattern as CP10's override audit trail."""
        case = self.db.get(Case, case_id)
        if case is None:
            raise NotFoundError(f"No case {case_id}")

        now = to_naive_utc(occurred_at) if occurred_at is not None else _utcnow()
        case.identity_link_status = IdentityLinkStatus.CONFIRMED
        case.mrn = mrn
        if display_name:
            case.display_name = display_name
        self.append_event(
            case_id=case_id,
            event_type="IDENTITY_MATCH_CONFIRMED",
            payload={"mrn": mrn, "confirmed_by": confirmed_by},
            occurred_at=now,
        )
        self.db.commit()
        self.db.refresh(case)
        return case

    def activate_emergency_bypass(
        self,
        case_id: str,
        *,
        source: BypassSource,
        reason: str,
        trigger_id: Optional[str] = None,
        occurred_at: Optional[datetime] = None,
    ) -> Case:
        """Phase 3.5: 'an alert plus a state flag'. Any of the three
        detectors may call this; none can cancel another, and re-firing an
        already-active case is not an error -- it is logged as a fresh
        event and updates the *last* activation summary on the case, while
        `first_activated_at` is preserved from whichever detector fired
        first. There is deliberately no deactivate/clear method here:
        resolving a bypass is a clinical decision outside this backend's
        scope at this checkpoint."""
        case = self.db.get(Case, case_id)
        if case is None:
            raise NotFoundError(f"No case {case_id}")

        now = to_naive_utc(occurred_at) if occurred_at is not None else _utcnow()
        if not case.emergency_bypass_active:
            case.emergency_bypass_first_activated_at = now
        case.emergency_bypass_active = True
        case.emergency_bypass_last_activated_at = now
        case.emergency_bypass_last_reason = reason
        case.emergency_bypass_last_source = source
        case.emergency_bypass_last_trigger_id = trigger_id

        self.append_event(
            case_id=case_id,
            event_type="EMERGENCY_BYPASS_ACTIVATED",
            payload={"source": source.value, "reason": reason, "trigger_id": trigger_id},
            occurred_at=now,
        )
        self.db.commit()
        self.db.refresh(case)
        return case

    # ------------------------------------------------------------------
    # Observations (Phase 4.2)
    # ------------------------------------------------------------------
    def add_observation(
        self,
        *,
        case_id: str,
        concept_code: str,
        value: Any,
        value_type: ValueType,
        source_type: SourceType,
        reliability_tier: ReliabilityTier,
        measurement_status: MeasurementStatus,
        observed_at: datetime,
        unit: Optional[str] = None,
        source_id: Optional[str] = None,
        extraction_confidence: Optional[float] = None,
    ) -> Observation:
        """Always creates a new row. To correct a value, call
        supersede_observation instead -- there is no update path here by
        design (Phase 4.2 "never mutate, always supersede")."""
        if self.db.get(Case, case_id) is None:
            raise NotFoundError(f"No case {case_id}")
        if source_type == SourceType.AI_INFERRED and extraction_confidence is None:
            raise ValueError(
                "extraction_confidence is required for AI_INFERRED observations (Phase 4.2)."
            )

        observed_at = to_naive_utc(observed_at)

        obs = Observation(
            case_id=case_id,
            concept_code=concept_code,
            value_type=value_type,
            unit=unit,
            source_type=source_type,
            source_id=source_id,
            reliability_tier=reliability_tier,
            measurement_status=measurement_status,
            observed_at=observed_at,
            recorded_at=_utcnow(),
            extraction_confidence=extraction_confidence,
        )
        self._assign_typed_value(obs, value_type, value)

        self.db.add(obs)
        self.db.flush()

        self.append_event(
            case_id=case_id,
            event_type="OBSERVATION_RECORDED",
            payload={
                "observation_id": obs.observation_id,
                "concept_code": concept_code,
                "measurement_status": measurement_status.value,
                "reliability_tier": int(reliability_tier),
                "source_type": source_type.value,
            },
            occurred_at=observed_at,
        )
        self.db.commit()
        self.db.refresh(obs)
        return obs

    def supersede_observation(
        self,
        *,
        observation_id: str,
        value: Any,
        value_type: ValueType,
        source_type: SourceType,
        reliability_tier: ReliabilityTier,
        measurement_status: MeasurementStatus,
        observed_at: datetime,
        unit: Optional[str] = None,
        source_id: Optional[str] = None,
        extraction_confidence: Optional[float] = None,
    ) -> Observation:
        """Corrects a prior observation. The prior row is retained and
        marked superseded_by the new row; it is never deleted or edited
        (Phase 4.2, Phase 9.3 audit-trail requirement)."""
        old = self.db.get(Observation, observation_id)
        if old is None:
            raise NotFoundError(f"No observation {observation_id}")
        if old.superseded_by is not None:
            raise ObservationAlreadySupersededError(
                f"Observation {observation_id} was already superseded by {old.superseded_by}; "
                f"supersede the current one instead."
            )

        new_obs = self.add_observation(
            case_id=old.case_id,
            concept_code=old.concept_code,
            value=value,
            value_type=value_type,
            source_type=source_type,
            reliability_tier=reliability_tier,
            measurement_status=measurement_status,
            observed_at=observed_at,
            unit=unit,
            source_id=source_id,
            extraction_confidence=extraction_confidence,
        )

        old.superseded_by = new_obs.observation_id
        self.append_event(
            case_id=old.case_id,
            event_type="OBSERVATION_SUPERSEDED",
            payload={"old_observation_id": old.observation_id, "new_observation_id": new_obs.observation_id},
        )
        self.db.commit()
        self.db.refresh(new_obs)
        return new_obs

    def get_latest_current_observation(self, case_id: str, concept_code: str) -> Optional[Observation]:
        """The single most recent non-superseded observation for one
        concept -- what the Clinical Scoring Engine (CP3) scores against.
        Not the same question as 'is this observation current' (not
        superseded): a patient can have several current readings of the
        same concept over time (that's how trend detection, Phase 5.4,
        sees deterioration) -- this picks the latest of those for scoring
        a snapshot right now."""
        return (
            self.db.query(Observation)
            .filter(
                Observation.case_id == case_id,
                Observation.concept_code == concept_code,
                Observation.superseded_by.is_(None),
            )
            .order_by(Observation.observed_at.desc())
            .first()
        )

    def get_recent_current_observations(self, case_id: str, concept_code: str, limit: int = 2) -> List[Observation]:
        """The `limit` most recent non-superseded observations for one
        concept, most recent first -- CP6's ML feature extraction uses this
        for trend deltas (Phase 16.2: 'vital trend deltas ... this is where
        ML beats a fixed score'). Not the same query as
        get_latest_current_observation, which only needs the single most
        recent one for deterministic scoring."""
        return (
            self.db.query(Observation)
            .filter(
                Observation.case_id == case_id,
                Observation.concept_code == concept_code,
                Observation.superseded_by.is_(None),
            )
            .order_by(Observation.observed_at.desc())
            .limit(limit)
            .all()
        )

    def get_current_observations(
        self, case_id: str, concept_code: Optional[str] = None
    ) -> List[Observation]:
        """Returns only current (non-superseded) observations -- what every
        downstream engine (Age Router, Scoring Engine, ...) should read."""
        q = self.db.query(Observation).filter(
            Observation.case_id == case_id, Observation.superseded_by.is_(None)
        )
        if concept_code is not None:
            q = q.filter(Observation.concept_code == concept_code)
        return q.order_by(Observation.observed_at.asc()).all()

    @staticmethod
    def _assign_typed_value(obs: Observation, value_type: ValueType, value: Any) -> None:
        if value_type == ValueType.NUMERIC:
            obs.value_numeric = float(value) if value is not None else None
        elif value_type == ValueType.TEXT:
            obs.value_text = value
        elif value_type == ValueType.CODED:
            obs.value_coded = value
        elif value_type == ValueType.BOOLEAN:
            obs.value_boolean = bool(value) if value is not None else None
        else:  # pragma: no cover - exhaustive by enum
            raise ValueError(f"Unknown value_type {value_type}")

    # ------------------------------------------------------------------
    # Event stream (Phase 4.4)
    # ------------------------------------------------------------------
    def append_event(
        self,
        *,
        case_id: Optional[str],
        event_type: str,
        payload: Optional[Dict[str, Any]] = None,
        occurred_at: Optional[datetime] = None,
    ) -> Event:
        if event_type not in KNOWN_EVENT_TYPES:
            raise UnknownEventTypeError(
                f"'{event_type}' is not in KNOWN_EVENT_TYPES (app/models/event.py). "
                f"Add it there deliberately rather than typo-ing a new event kind."
            )
        now = _utcnow()
        event = Event(
            case_id=case_id,
            event_type=event_type,
            payload=payload or {},
            occurred_at=to_naive_utc(occurred_at) if occurred_at is not None else now,
            recorded_at=now,
        )
        self.db.add(event)
        self.db.flush()
        return event

    def get_timeline(self, case_id: str) -> List[Event]:
        return (
            self.db.query(Event)
            .filter(Event.case_id == case_id)
            .order_by(Event.recorded_at.asc())
            .all()
        )

    # ------------------------------------------------------------------
    # RiskAssessment (Phase 4.3, CP6): the persisted output of the scoring
    # stack. Never mutated -- new information produces a new row, same
    # discipline as Observation's own supersession-not-mutation rule.
    # ------------------------------------------------------------------
    def save_risk_assessment(
        self,
        *,
        case_id: str,
        rule_engine_version: str,
        rule_acuity: int,
        rule_component_breakdown: List[dict],
        ml_model_version: Optional[str],
        ml_probability: Optional[float],
        ml_suggested_acuity: Optional[int],
        hard_triggers_fired: List[dict],
        final_acuity: int,
        deciding_layer: DecidingLayer,
        confidence_band: ConfidenceBand,
        confidence_score: float,
        confidence_reasons: List[str],
        should_abstain: bool,
        abstention_message: Optional[str],
        input_snapshot_hash: str,
        input_observation_ids: List[str],
        computed_at: Optional[datetime] = None,
    ) -> RiskAssessment:
        case = self.db.get(Case, case_id)
        if case is None:
            raise NotFoundError(f"No case {case_id}")

        now = to_naive_utc(computed_at) if computed_at is not None else _utcnow()
        assessment = RiskAssessment(
            case_id=case_id,
            computed_at=now,
            rule_engine_version=rule_engine_version,
            rule_acuity=rule_acuity,
            rule_component_breakdown=rule_component_breakdown,
            ml_model_version=ml_model_version,
            ml_probability=ml_probability,
            ml_suggested_acuity=ml_suggested_acuity,
            hard_triggers_fired=hard_triggers_fired,
            final_acuity=final_acuity,
            deciding_layer=deciding_layer,
            confidence_band=confidence_band,
            confidence_score=confidence_score,
            confidence_reasons=confidence_reasons,
            should_abstain=should_abstain,
            abstention_message=abstention_message,
            input_snapshot_hash=input_snapshot_hash,
            input_observation_ids=input_observation_ids,
        )
        self.db.add(assessment)
        self.db.flush()

        self.append_event(
            case_id=case_id,
            event_type="RISK_ASSESSMENT_COMPUTED",
            payload={
                "assessment_id": assessment.assessment_id,
                "final_acuity": final_acuity,
                "deciding_layer": deciding_layer.value,
                "confidence_band": confidence_band.value,
            },
            occurred_at=now,
        )
        for trigger in hard_triggers_fired:
            self.append_event(
                case_id=case_id,
                event_type="HARD_TRIGGER_FIRED",
                payload=trigger,
                occurred_at=now,
            )

        # Phase 5.3: "Reassessment collects new observations. New
        # observations re-run the scoring stack." -- this IS a
        # reassessment, so the clock the Guardian Queue watches (CP7)
        # resets here regardless of whether one was overdue. REASSESSMENT_
        # COMPLETED is only emitted when it actually clears a
        # previously-overdue state (or via the explicit mark_reassessed()
        # nurse action below) -- firing it on every routine re-score, most
        # of which are nowhere near overdue, would make the event stream
        # noise rather than signal.
        if case.reassessment_overdue:
            self.append_event(
                case_id=case_id,
                event_type="REASSESSMENT_COMPLETED",
                payload={"resolved_via": "new_observation", "was_overdue_since": str(case.reassessment_overdue_since)},
                occurred_at=now,
            )
        case.last_reassessed_at = now
        case.reassessment_overdue = False
        case.reassessment_overdue_since = None

        self.db.commit()
        self.db.refresh(assessment)
        return assessment

    # ------------------------------------------------------------------
    # Reassessment timer (Phase 5.3, CP7)
    # ------------------------------------------------------------------
    def mark_reassessed(self, case_id: str, *, occurred_at: Optional[datetime] = None) -> Case:
        """Phase 8.2's nurse one-tap 'mark reassessed' action: an explicit
        human acknowledgment that this patient has been looked at again,
        distinct from (and not requiring) a new numeric observation. Always
        logs REASSESSMENT_COMPLETED, whether or not the case was actually
        overdue -- unlike the automatic path in save_risk_assessment, a
        deliberate human action is always worth recording."""
        case = self.db.get(Case, case_id)
        if case is None:
            raise NotFoundError(f"No case {case_id}")

        now = to_naive_utc(occurred_at) if occurred_at is not None else _utcnow()
        was_overdue = case.reassessment_overdue
        self.append_event(
            case_id=case_id,
            event_type="REASSESSMENT_COMPLETED",
            payload={"resolved_via": "manual_nurse_action", "was_overdue": was_overdue},
            occurred_at=now,
        )
        case.last_reassessed_at = now
        case.reassessment_overdue = False
        case.reassessment_overdue_since = None
        self.db.commit()
        self.db.refresh(case)
        return case

    def flag_reassessment_overdue(
        self, case_id: str, *, occurred_at: Optional[datetime] = None, reason: str = "INTERVAL_EXCEEDED"
    ) -> Case:
        """Called by the Guardian Queue (CP7) when it notices a case has
        crossed its reassessment interval and isn't already flagged, and by
        report_patient_worsening (CP8) when a patient's self-report forces
        the same state immediately regardless of elapsed time. Idempotent
        by construction: the caller is expected to check
        `case.reassessment_overdue` first (this method doesn't re-check,
        so calling it twice would log REASSESSMENT_DUE twice -- the
        caller's responsibility, not this method's, exactly like
        activate_emergency_bypass leaves 'should I fire' to its callers)."""
        case = self.db.get(Case, case_id)
        if case is None:
            raise NotFoundError(f"No case {case_id}")

        now = to_naive_utc(occurred_at) if occurred_at is not None else _utcnow()
        case.reassessment_overdue = True
        case.reassessment_overdue_since = now
        self.append_event(case_id=case_id, event_type="REASSESSMENT_DUE", payload={"reason": reason}, occurred_at=now)
        self.db.commit()
        self.db.refresh(case)
        return case

    def report_patient_worsening(
        self, case_id: str, *, occurred_at: Optional[datetime] = None, note: Optional[str] = None
    ) -> Case:
        """Phase 8.1: 'the I feel worse button ... one tap, it creates a
        PATIENT_SELF_REPORTED_WORSENING event, it forces a reassessment
        prompt.' Deliberately does NOT touch final_acuity or run the
        scoring stack itself -- a self-report is not physiology (Phase 9.3:
        a monitor reading outweighs a self-report for scoring purposes).
        What it does is force the case onto the nurse's overdue list
        immediately, reusing the exact same reassessment_overdue flag the
        elapsed-time timer sets (CP7), rather than inventing a second,
        parallel 'urgent' flag the Guardian Queue would also have to
        understand. Every tap logs PATIENT_SELF_REPORTED_WORSENING, even a
        second tap on an already-overdue case -- unlike the flag itself,
        each self-report is a distinct, always-worth-recording signal
        (Phase 3.5's bypass logging follows the same rule)."""
        case = self.db.get(Case, case_id)
        if case is None:
            raise NotFoundError(f"No case {case_id}")

        now = to_naive_utc(occurred_at) if occurred_at is not None else _utcnow()
        self.append_event(
            case_id=case_id,
            event_type="PATIENT_SELF_REPORTED_WORSENING",
            payload={"note": note},
            occurred_at=now,
        )
        if not case.reassessment_overdue:
            # flag_reassessment_overdue commits (and logs REASSESSMENT_DUE)
            # -- that commit also persists the PATIENT_SELF_REPORTED_
            # WORSENING event flushed just above, in the same transaction.
            return self.flag_reassessment_overdue(case_id, occurred_at=now, reason="PATIENT_SELF_REPORTED_WORSENING")

        # Already overdue: nothing else to flag, but the event above still
        # needs to be committed -- flush() alone does not persist it.
        self.db.commit()
        self.db.refresh(case)
        return case

    def get_latest_risk_assessment(self, case_id: str) -> Optional[RiskAssessment]:
        return (
            self.db.query(RiskAssessment)
            .filter(RiskAssessment.case_id == case_id)
            .order_by(RiskAssessment.computed_at.desc())
            .first()
        )

    def get_risk_assessment_history(self, case_id: str) -> List[RiskAssessment]:
        return (
            self.db.query(RiskAssessment)
            .filter(RiskAssessment.case_id == case_id)
            .order_by(RiskAssessment.computed_at.asc())
            .all()
        )

    # ------------------------------------------------------------------
    # Human override / audit trail (Phase 4.3, 9.6, CP10)
    # ------------------------------------------------------------------
    def record_human_override(
        self,
        case_id: str,
        *,
        clinician_id: str,
        role: str,
        action: HumanDecisionAction,
        target_acuity: Optional[int] = None,
        reason_code: Optional[DeEscalationReasonCode] = None,
        free_text_reason: Optional[str] = None,
        occurred_at: Optional[datetime] = None,
    ) -> HumanDecision:
        """Phase 9.6's asymmetric override friction, enforced here rather
        than merely documented: ESCALATE (and ACCEPT) need nothing beyond
        an authenticated identity; DE_ESCALATE requires an explicit
        target_acuity AND a structured reason_code or this raises before
        anything is persisted. 'The system never blocks either' direction
        outright -- friction, not a hard stop -- but the friction is a
        server-enforced contract, not just a UI convention a caller could
        route around.

        Every accepted call does two things: persists the HumanDecision
        audit row (always), and -- unless the decision changes nothing
        (ACCEPT) -- creates a new RiskAssessment with
        deciding_layer=OVERRIDE so the decision is 'applied instantly'
        (Phase 9.6) rather than sitting unread in an audit log; the
        Guardian Queue and case-detail views read final_acuity off the
        latest RiskAssessment exactly like any other reassessment.

        Note this is deliberately NOT the same invariant as Phase 3.1's
        automated min(rule_based_acuity, ml_suggested_acuity,
        override_acuity_if_escalating) -- that formula governs the
        *automated* scoring pipeline (app/scoring/risk_orchestrator.py)
        and can never silently lower a patient's acuity on its own. This
        method is the separate, explicit, accountable path Phase 9.6
        describes for a human to do so deliberately, with friction and a
        permanent audit trail standing in for the algorithmic guardrail
        that deliberately does not apply to a human's own judgement.
        """
        case = self.db.get(Case, case_id)
        if case is None:
            raise NotFoundError(f"No case {case_id}")
        latest = self.get_latest_risk_assessment(case_id)
        if latest is None:
            raise ValueError(f"Case {case_id} has no RiskAssessment yet -- nothing to override.")

        system_recommendation = latest.final_acuity
        now = to_naive_utc(occurred_at) if occurred_at is not None else _utcnow()
        flagged_for_review = False

        if action == HumanDecisionAction.ACCEPT:
            resulting_acuity = system_recommendation
        elif action == HumanDecisionAction.ESCALATE:
            resulting_acuity = target_acuity if target_acuity is not None else max(1, system_recommendation - 1)
            if resulting_acuity >= system_recommendation:
                raise ValueError(
                    f"ESCALATE must make the case MORE urgent (a lower acuity number) than the current "
                    f"{system_recommendation}; got {resulting_acuity}. Use DE_ESCALATE for the opposite direction."
                )
        elif action == HumanDecisionAction.DE_ESCALATE:
            if target_acuity is None:
                raise ValueError("DE_ESCALATE requires an explicit target_acuity.")
            if target_acuity <= system_recommendation:
                raise ValueError(
                    f"DE_ESCALATE must make the case LESS urgent (a higher acuity number) than the current "
                    f"{system_recommendation}; got {target_acuity}. Use ESCALATE for the opposite direction."
                )
            if reason_code is None:
                raise ValueError("DE_ESCALATE requires a structured reason_code (Phase 9.6 asymmetric friction).")
            resulting_acuity = target_acuity
            flagged_for_review = True
        else:
            raise ValueError(
                f"Unsupported clinician_action for override: {action}. MODIFY is a reserved enum value with no "
                f"defined behaviour yet -- see HumanDecisionAction's docstring."
            )

        decision = HumanDecision(
            case_id=case_id,
            clinician_id=clinician_id,
            role=role,
            timestamp=now,
            system_recommendation=system_recommendation,
            clinician_action=action,
            resulting_acuity=resulting_acuity,
            reason_code=reason_code,
            free_text_reason=free_text_reason,
            linked_assessment_id=latest.assessment_id,
            flagged_for_review=flagged_for_review,
        )
        self.db.add(decision)
        self.db.flush()

        self.append_event(
            case_id=case_id,
            event_type="HUMAN_DECISION_RECORDED",
            payload={
                "decision_id": decision.decision_id,
                "clinician_id": clinician_id,
                "role": role,
                "clinician_action": action.value,
                "system_recommendation": system_recommendation,
                "resulting_acuity": resulting_acuity,
                "reason_code": reason_code.value if reason_code else None,
                "flagged_for_review": flagged_for_review,
            },
            occurred_at=now,
        )

        if resulting_acuity != system_recommendation:
            self.save_risk_assessment(
                case_id=case_id,
                rule_engine_version=latest.rule_engine_version,
                rule_acuity=latest.rule_acuity,
                rule_component_breakdown=latest.rule_component_breakdown,
                ml_model_version=latest.ml_model_version,
                ml_probability=latest.ml_probability,
                ml_suggested_acuity=latest.ml_suggested_acuity,
                hard_triggers_fired=latest.hard_triggers_fired,
                final_acuity=resulting_acuity,
                deciding_layer=DecidingLayer.OVERRIDE,
                confidence_band=latest.confidence_band,
                confidence_score=latest.confidence_score,
                confidence_reasons=latest.confidence_reasons,
                should_abstain=False,  # a human decision is definitionally not an abstention
                abstention_message=None,
                input_snapshot_hash=latest.input_snapshot_hash,
                input_observation_ids=latest.input_observation_ids,
                computed_at=now,
            )
        else:
            # ACCEPT: no acuity change to reflect, but a human did just
            # look at this patient -- count it as a reassessment via the
            # existing Phase 8.2 mechanics rather than inventing a second
            # "this counts as attention paid" pathway.
            self.mark_reassessed(case_id, occurred_at=now)

        self.db.commit()
        self.db.refresh(decision)
        return decision

    def get_decision_history(self, case_id: str) -> List[HumanDecision]:
        return (
            self.db.query(HumanDecision)
            .filter(HumanDecision.case_id == case_id)
            .order_by(HumanDecision.timestamp.asc())
            .all()
        )

    def list_flagged_for_review(self, hospital_profile_id: str = "default") -> List[HumanDecision]:
        """Phase 9.6: de-escalations are 'flagged for retrospective
        review' -- this is that review queue. Deliberately read-only here
        (no 'mark reviewed' mutation): Phase 9.6 asks that these be
        flagged and visible, not that this prototype also build a review-
        closure workflow, which is a distinct, unscoped piece of work."""
        return (
            self.db.query(HumanDecision)
            .join(Case, HumanDecision.case_id == Case.case_id)
            .filter(HumanDecision.flagged_for_review == True, Case.hospital_profile_id == hospital_profile_id)  # noqa: E712
            .order_by(HumanDecision.timestamp.desc())
            .all()
        )

    # ------------------------------------------------------------------
    # Contradictory Information (Phase 9.3, CP13). Detection/resolution
    # logic itself lives in app/scoring/conflict_detection.py; this class
    # only persists/queries one DataConflict row.
    # ------------------------------------------------------------------
    def find_data_conflict_by_observation_set(
        self, case_id: str, concept_code: str, observation_ids: List[str]
    ) -> Optional[DataConflict]:
        """Dedupe lookup: a conflict is 'the same one' iff it involves the
        exact same set of observations. A new observation joining or
        replacing the set is a genuinely new conflict instance."""
        target = sorted(observation_ids)
        candidates = (
            self.db.query(DataConflict)
            .filter(DataConflict.case_id == case_id, DataConflict.concept_code == concept_code)
            .all()
        )
        for candidate in candidates:
            if sorted(candidate.observation_ids) == target:
                return candidate
        return None

    def create_data_conflict(
        self,
        *,
        case_id: str,
        concept_code: str,
        observation_ids: List[str],
        conservative_observation_id: str,
        occurred_at: Optional[datetime] = None,
    ) -> DataConflict:
        now = to_naive_utc(occurred_at) if occurred_at is not None else _utcnow()
        conflict = DataConflict(
            case_id=case_id,
            concept_code=concept_code,
            observation_ids=sorted(observation_ids),
            conservative_observation_id=conservative_observation_id,
            detected_at=now,
        )
        self.db.add(conflict)
        self.db.flush()
        self.append_event(
            case_id=case_id,
            event_type="DATA_CONFLICT_DETECTED",
            payload={
                "conflict_id": conflict.conflict_id,
                "concept_code": concept_code,
                "observation_ids": conflict.observation_ids,
                "conservative_observation_id": conservative_observation_id,
            },
            occurred_at=now,
        )
        self.db.commit()
        self.db.refresh(conflict)
        return conflict

    def get_data_conflict(self, conflict_id: str) -> Optional[DataConflict]:
        return self.db.get(DataConflict, conflict_id)

    def list_data_conflicts(self, case_id: str, *, include_resolved: bool = False) -> List[DataConflict]:
        q = self.db.query(DataConflict).filter(DataConflict.case_id == case_id)
        if not include_resolved:
            q = q.filter(DataConflict.resolved == False)  # noqa: E712
        return q.order_by(DataConflict.detected_at.desc()).all()

    def resolve_data_conflict(
        self,
        conflict_id: str,
        *,
        resolved_by: str,
        kept_observation_id: str,
        resolution_note: Optional[str] = None,
        occurred_at: Optional[datetime] = None,
    ) -> DataConflict:
        """Phase 9.3: 'until a human resolves it.' The human's chosen
        observation becomes what subsequent scoring uses for this concept
        (app/scoring/conflict_detection.py checks `resolved`/
        `kept_observation_id` before falling back to the automatic
        conservative rule) -- resolving is a judgement call, not merely an
        acknowledgement."""
        conflict = self.db.get(DataConflict, conflict_id)
        if conflict is None:
            raise NotFoundError(f"No data conflict {conflict_id}")
        if conflict.resolved:
            raise ValueError(f"Data conflict {conflict_id} is already resolved.")
        if kept_observation_id not in conflict.observation_ids:
            raise ValueError(
                f"kept_observation_id {kept_observation_id} is not one of the observations in this conflict: "
                f"{conflict.observation_ids}"
            )

        now = to_naive_utc(occurred_at) if occurred_at is not None else _utcnow()
        conflict.resolved = True
        conflict.resolved_at = now
        conflict.resolved_by = resolved_by
        conflict.kept_observation_id = kept_observation_id
        conflict.resolution_note = resolution_note
        self.append_event(
            case_id=conflict.case_id,
            event_type="DATA_CONFLICT_RESOLVED",
            payload={
                "conflict_id": conflict_id,
                "concept_code": conflict.concept_code,
                "resolved_by": resolved_by,
                "kept_observation_id": kept_observation_id,
            },
            occurred_at=now,
        )
        self.db.commit()
        self.db.refresh(conflict)
        return conflict

    # ------------------------------------------------------------------
    # Case reviews (Phase 8.3, CP15): "what changed since you last looked
    # at this patient."
    # ------------------------------------------------------------------
    def get_case_review(self, case_id: str, reviewer_id: str) -> Optional[CaseReview]:
        return (
            self.db.query(CaseReview)
            .filter(CaseReview.case_id == case_id, CaseReview.reviewer_id == reviewer_id)
            .first()
        )

    def mark_case_reviewed(
        self, case_id: str, reviewer_id: str, *, occurred_at: Optional[datetime] = None
    ) -> CaseReview:
        """Upserted, not appended -- see CaseReview's module docstring for
        why this one table breaks the append-only convention."""
        if self.db.get(Case, case_id) is None:
            raise NotFoundError(f"No case {case_id}")
        now = to_naive_utc(occurred_at) if occurred_at is not None else _utcnow()
        review = self.get_case_review(case_id, reviewer_id)
        if review is None:
            review = CaseReview(case_id=case_id, reviewer_id=reviewer_id, reviewed_at=now)
            self.db.add(review)
        else:
            review.reviewed_at = now
        self.db.commit()
        self.db.refresh(review)
        return review

    # ------------------------------------------------------------------
    # Ambulance ETA simulation (Phase 7.2, CP18). Narrowing-range
    # computation itself lives in app/ambulance/eta.py; this class only
    # persists/queries the one evolving AmbulanceTransport row per case.
    # ------------------------------------------------------------------
    def start_ambulance_transport(
        self, case_id: str, *, estimated_total_minutes: float, occurred_at: Optional[datetime] = None
    ) -> AmbulanceTransport:
        if self.db.get(Case, case_id) is None:
            raise NotFoundError(f"No case {case_id}")
        now = to_naive_utc(occurred_at) if occurred_at is not None else _utcnow()
        transport = AmbulanceTransport(
            case_id=case_id, transport_started_at=now, estimated_total_minutes=estimated_total_minutes,
            last_updated_at=now,
        )
        self.db.add(transport)
        self.append_event(
            case_id=case_id, event_type="AMBULANCE_TRANSPORT_STARTED",
            payload={"estimated_total_minutes": estimated_total_minutes}, occurred_at=now,
        )
        self.db.commit()
        self.db.refresh(transport)
        return transport

    def get_ambulance_transport(self, case_id: str) -> Optional[AmbulanceTransport]:
        return self.db.get(AmbulanceTransport, case_id)

    def mark_transport_delayed(
        self, case_id: str, *, additional_minutes: float, reason: Optional[str] = None,
        occurred_at: Optional[datetime] = None,
    ) -> AmbulanceTransport:
        """Phase 7.2: 'Add a paramedic-controlled delayed flag.' Extends
        the estimate rather than replacing it, so 'how much longer than
        planned' stays visible on the record."""
        transport = self.db.get(AmbulanceTransport, case_id)
        if transport is None:
            raise NotFoundError(f"No ambulance transport recorded for case {case_id}")
        now = to_naive_utc(occurred_at) if occurred_at is not None else _utcnow()
        transport.delayed_additional_minutes += additional_minutes
        transport.last_updated_at = now
        self.append_event(
            case_id=case_id, event_type="AMBULANCE_TRANSPORT_DELAYED",
            payload={"additional_minutes": additional_minutes, "reason": reason}, occurred_at=now,
        )
        self.db.commit()
        self.db.refresh(transport)
        return transport

    # ------------------------------------------------------------------
    # Alerts (Phase 8.5, CP12). Creation/dedupe logic itself lives in
    # app/alerts/engine.py (same split as Stuck Patient Detection: this
    # class only knows how to persist/query one Alert row).
    # ------------------------------------------------------------------
    def create_alert(
        self,
        *,
        hospital_profile_id: str,
        alert_type: AlertType,
        payload: Dict[str, Any],
        dedupe_case_id: Optional[str] = None,
        dedupe_assessment_id: Optional[str] = None,
        occurred_at: Optional[datetime] = None,
    ) -> Alert:
        now = to_naive_utc(occurred_at) if occurred_at is not None else _utcnow()
        alert = Alert(
            hospital_profile_id=hospital_profile_id,
            alert_type=alert_type,
            payload=payload,
            dedupe_case_id=dedupe_case_id,
            dedupe_assessment_id=dedupe_assessment_id,
            created_at=now,
        )
        self.db.add(alert)
        self.db.flush()
        self.append_event(
            case_id=dedupe_case_id,
            event_type="ALERT_RAISED",
            payload={"alert_id": alert.alert_id, "alert_type": alert_type.value, **payload},
            occurred_at=now,
        )
        self.db.commit()
        self.db.refresh(alert)
        return alert

    def get_alert(self, alert_id: str) -> Optional[Alert]:
        return self.db.get(Alert, alert_id)

    def list_alerts(
        self, hospital_profile_id: str = "default", *, include_dismissed: bool = False
    ) -> List[Alert]:
        q = self.db.query(Alert).filter(Alert.hospital_profile_id == hospital_profile_id)
        if not include_dismissed:
            q = q.filter(Alert.dismissed == False)  # noqa: E712
        return q.order_by(Alert.created_at.desc()).all()

    def list_alerts_since(self, hospital_profile_id: str, since: datetime) -> List[Alert]:
        """All alerts (dismissed or not) raised at/after `since` -- what
        the alert-budget measurement counts, since a dismissed alert still
        interrupted someone at the moment it was raised."""
        return (
            self.db.query(Alert)
            .filter(Alert.hospital_profile_id == hospital_profile_id, Alert.created_at >= since)
            .order_by(Alert.created_at.asc())
            .all()
        )

    def existing_alert_for_case(self, alert_type: AlertType, case_id: str) -> Optional[Alert]:
        return (
            self.db.query(Alert)
            .filter(Alert.alert_type == alert_type, Alert.dedupe_case_id == case_id)
            .first()
        )

    def existing_alert_for_assessment(self, assessment_id: str) -> Optional[Alert]:
        return self.db.query(Alert).filter(Alert.dedupe_assessment_id == assessment_id).first()

    def get_open_aggregate_alert(self, hospital_profile_id: str) -> Optional[Alert]:
        return (
            self.db.query(Alert)
            .filter(
                Alert.hospital_profile_id == hospital_profile_id,
                Alert.alert_type == AlertType.REASSESSMENT_OVERDUE_AGGREGATE,
                Alert.dismissed == False,  # noqa: E712
            )
            .first()
        )

    def update_alert_payload(self, alert_id: str, payload: Dict[str, Any]) -> Alert:
        """Phase 8.5 'aggregate, never repeat': the one mutation this
        otherwise-immutable-by-default row gets -- refreshing the live
        member list/count of the single open aggregate alert in place,
        rather than raising a new alert every time the overdue set
        changes."""
        alert = self.db.get(Alert, alert_id)
        if alert is None:
            raise NotFoundError(f"No alert {alert_id}")
        alert.payload = payload
        self.db.commit()
        self.db.refresh(alert)
        return alert

    def dismiss_alert(
        self,
        alert_id: str,
        *,
        dismissed_by: str,
        reason_code: AlertDismissalReasonCode,
        free_text_reason: Optional[str] = None,
        occurred_at: Optional[datetime] = None,
    ) -> Alert:
        """Phase 8.5: 'every alert is dismissible with a reason, and
        dismissal reasons feed the tuning loop.'"""
        alert = self.db.get(Alert, alert_id)
        if alert is None:
            raise NotFoundError(f"No alert {alert_id}")
        if alert.dismissed:
            raise ValueError(f"Alert {alert_id} is already dismissed.")

        now = to_naive_utc(occurred_at) if occurred_at is not None else _utcnow()
        alert.dismissed = True
        alert.dismissed_at = now
        alert.dismissed_by = dismissed_by
        alert.dismissal_reason_code = reason_code
        alert.dismissal_free_text = free_text_reason
        self.append_event(
            case_id=alert.dedupe_case_id,
            event_type="ALERT_DISMISSED",
            payload={
                "alert_id": alert_id,
                "alert_type": alert.alert_type.value,
                "dismissed_by": dismissed_by,
                "reason_code": reason_code.value,
            },
            occurred_at=now,
        )
        self.db.commit()
        self.db.refresh(alert)
        return alert

    # ------------------------------------------------------------------
    # Resources (Phase 6.1, 6.2, CP9)
    # ------------------------------------------------------------------
    def create_resource(
        self, *, resource_type: ResourceType, label: str, hospital_profile_id: str = "default"
    ) -> Resource:
        resource = Resource(resource_type=resource_type, label=label, hospital_profile_id=hospital_profile_id)
        self.db.add(resource)
        self.db.commit()
        self.db.refresh(resource)
        return resource

    def list_resources(
        self,
        hospital_profile_id: str = "default",
        resource_type: Optional[ResourceType] = None,
        status: Optional[ResourceStatus] = None,
    ) -> List[Resource]:
        q = self.db.query(Resource).filter(Resource.hospital_profile_id == hospital_profile_id)
        if resource_type is not None:
            q = q.filter(Resource.resource_type == resource_type)
        if status is not None:
            q = q.filter(Resource.status == status)
        return q.order_by(Resource.label.asc()).all()

    def get_resource(self, resource_id: str) -> Optional[Resource]:
        return self.db.get(Resource, resource_id)

    def get_assigned_resources_for_case(self, case_id: str) -> List[Resource]:
        """Resources currently OCCUPIED and assigned to this case -- used by
        the Phase 6.4 wait-time model to tell 'still waiting for service'
        apart from 'already being seen', which must not count as one of the
        patients still ahead in the queue."""
        return (
            self.db.query(Resource)
            .filter(Resource.assigned_case_id == case_id, Resource.status == ResourceStatus.OCCUPIED)
            .all()
        )

    def get_resource_assignment_history(self, hospital_profile_id: str = "default", limit: int = 200) -> List[Event]:
        """RESOURCE_ASSIGNED events for cases under this profile, most
        recent first. Deliberately reads the append-only event log rather
        than the live Resource row (Resource.assigned_at is cleared on
        release/reassignment, so it cannot answer 'how long did previous
        patients wait historically'). Feeds the Phase 6.4 wait-time model's
        rolling median service time -- see app/ops/wait_time.py."""
        return (
            self.db.query(Event)
            .join(Case, Event.case_id == Case.case_id)
            .filter(Event.event_type == "RESOURCE_ASSIGNED", Case.hospital_profile_id == hospital_profile_id)
            .order_by(Event.occurred_at.desc())
            .limit(limit)
            .all()
        )

    def assign_resource(
        self, case_id: str, resource_type: ResourceType, profile, *, occurred_at: Optional[datetime] = None
    ) -> Resource:
        """Phase 6.2: finds an AVAILABLE resource of `resource_type` for
        this case. Raises CapacityConflictError (after logging
        CAPACITY_CONFLICT_RAISED) if none is free -- never silently
        downgrades a patient's acuity or reorders around the constraint;
        that decision is left entirely to the human the conflict is
        raised to."""
        if self.db.get(Case, case_id) is None:
            raise NotFoundError(f"No case {case_id}")
        now = to_naive_utc(occurred_at) if occurred_at is not None else _utcnow()

        candidate = (
            self.db.query(Resource)
            .filter(
                Resource.hospital_profile_id == profile.profile_id,
                Resource.resource_type == resource_type,
                Resource.status == ResourceStatus.AVAILABLE,
            )
            .order_by(Resource.label.asc())
            .first()
        )
        if candidate is None:
            self.append_event(
                case_id=case_id,
                event_type="CAPACITY_CONFLICT_RAISED",
                payload={
                    "resource_type": resource_type.value,
                    "candidate_actions": profile.ops.capacity_conflict_candidate_actions,
                },
                occurred_at=now,
            )
            self.db.commit()
            raise CapacityConflictError(resource_type, profile.ops.capacity_conflict_candidate_actions)

        candidate.status = ResourceStatus.OCCUPIED
        candidate.assigned_case_id = case_id
        candidate.assigned_at = now
        candidate.occupancy_stuck_flagged = False
        self.append_event(
            case_id=case_id,
            event_type="RESOURCE_ASSIGNED",
            payload={
                "resource_id": candidate.resource_id,
                "resource_type": resource_type.value,
                "label": candidate.label,
            },
            occurred_at=now,
        )
        self.db.commit()
        self.db.refresh(candidate)
        return candidate

    def confirm_occupancy(self, resource_id: str, *, occurred_at: Optional[datetime] = None) -> Resource:
        """Phase 6.3 'assigned space never occupied' pattern's resolving
        event: PATIENT_IN_SPACE."""
        resource = self.db.get(Resource, resource_id)
        if resource is None:
            raise NotFoundError(f"No resource {resource_id}")
        if resource.assigned_case_id is None:
            raise ValueError(f"Resource {resource_id} is not currently assigned to a case.")

        now = to_naive_utc(occurred_at) if occurred_at is not None else _utcnow()
        resource.occupancy_stuck_flagged = False
        self.append_event(
            case_id=resource.assigned_case_id,
            event_type="PATIENT_IN_SPACE",
            payload={"resource_id": resource_id},
            occurred_at=now,
        )
        self.db.commit()
        self.db.refresh(resource)
        return resource

    def release_resource(self, resource_id: str, *, occurred_at: Optional[datetime] = None) -> Resource:
        resource = self.db.get(Resource, resource_id)
        if resource is None:
            raise NotFoundError(f"No resource {resource_id}")

        now = to_naive_utc(occurred_at) if occurred_at is not None else _utcnow()
        case_id = resource.assigned_case_id
        resource.status = ResourceStatus.AVAILABLE
        resource.assigned_case_id = None
        resource.assigned_at = None
        resource.occupancy_stuck_flagged = False
        self.append_event(
            case_id=case_id, event_type="RESOURCE_RELEASED", payload={"resource_id": resource_id}, occurred_at=now
        )
        self.db.commit()
        self.db.refresh(resource)
        return resource

    def flag_resource_occupancy_stuck(self, resource_id: str, *, occurred_at: Optional[datetime] = None) -> Resource:
        """Called by the Flow Engine sweep (CP9) when an assigned resource
        has sat unoccupied past its configured window. Idempotent by
        construction -- same contract as flag_reassessment_overdue: the
        caller checks `occupancy_stuck_flagged` first."""
        resource = self.db.get(Resource, resource_id)
        if resource is None:
            raise NotFoundError(f"No resource {resource_id}")

        now = to_naive_utc(occurred_at) if occurred_at is not None else _utcnow()
        resource.occupancy_stuck_flagged = True
        self.append_event(
            case_id=resource.assigned_case_id,
            event_type="STUCK_PATIENT_DETECTED",
            payload={"pattern_id": "ASSIGNED_SPACE_NOT_OCCUPIED", "resource_id": resource_id, "route_to": "CHARGE_NURSE"},
            occurred_at=now,
        )
        self.db.commit()
        self.db.refresh(resource)
        return resource

    # ------------------------------------------------------------------
    # Diagnostic tests (Phase 6.3, CP9)
    # ------------------------------------------------------------------
    def order_test(self, case_id: str, test_type: str, *, occurred_at: Optional[datetime] = None) -> DiagnosticTest:
        if self.db.get(Case, case_id) is None:
            raise NotFoundError(f"No case {case_id}")

        now = to_naive_utc(occurred_at) if occurred_at is not None else _utcnow()
        test = DiagnosticTest(case_id=case_id, test_type=test_type, status=DiagnosticTestStatus.ORDERED, ordered_at=now)
        self.db.add(test)
        self.db.flush()

        self.append_event(
            case_id=case_id,
            event_type="TEST_ORDERED",
            payload={"test_id": test.test_id, "test_type": test_type},
            occurred_at=now,
        )
        self.db.commit()
        self.db.refresh(test)
        return test

    def mark_sample_collected(self, test_id: str, *, occurred_at: Optional[datetime] = None) -> DiagnosticTest:
        test = self.db.get(DiagnosticTest, test_id)
        if test is None:
            raise NotFoundError(f"No diagnostic test {test_id}")

        now = to_naive_utc(occurred_at) if occurred_at is not None else _utcnow()
        test.status = DiagnosticTestStatus.SAMPLE_COLLECTED
        test.sample_collected_at = now
        test.stuck_flagged = False  # resolves pattern 1; pattern 2's clock hasn't started yet
        self.append_event(
            case_id=test.case_id, event_type="SAMPLE_COLLECTED", payload={"test_id": test_id}, occurred_at=now
        )
        self.db.commit()
        self.db.refresh(test)
        return test

    def mark_result_available(self, test_id: str, *, occurred_at: Optional[datetime] = None) -> DiagnosticTest:
        test = self.db.get(DiagnosticTest, test_id)
        if test is None:
            raise NotFoundError(f"No diagnostic test {test_id}")

        now = to_naive_utc(occurred_at) if occurred_at is not None else _utcnow()
        test.status = DiagnosticTestStatus.RESULT_AVAILABLE
        test.result_available_at = now
        test.stuck_flagged = False  # pattern 2's clock starts fresh from here
        self.append_event(
            case_id=test.case_id, event_type="RESULT_AVAILABLE", payload={"test_id": test_id}, occurred_at=now
        )
        self.db.commit()
        self.db.refresh(test)
        return test

    def mark_result_reviewed(self, test_id: str, *, occurred_at: Optional[datetime] = None) -> DiagnosticTest:
        test = self.db.get(DiagnosticTest, test_id)
        if test is None:
            raise NotFoundError(f"No diagnostic test {test_id}")

        now = to_naive_utc(occurred_at) if occurred_at is not None else _utcnow()
        test.status = DiagnosticTestStatus.RESULT_REVIEWED
        test.result_reviewed_at = now
        test.stuck_flagged = False
        self.append_event(
            case_id=test.case_id, event_type="RESULT_REVIEWED", payload={"test_id": test_id}, occurred_at=now
        )
        self.db.commit()
        self.db.refresh(test)
        return test

    def flag_test_stuck(self, test_id: str, *, pattern_id: str, occurred_at: Optional[datetime] = None) -> DiagnosticTest:
        test = self.db.get(DiagnosticTest, test_id)
        if test is None:
            raise NotFoundError(f"No diagnostic test {test_id}")

        now = to_naive_utc(occurred_at) if occurred_at is not None else _utcnow()
        test.stuck_flagged = True
        route_to = "NURSE_OPS" if pattern_id == "TEST_ORDERED_NOT_COLLECTED" else "DOCTOR_QUEUE"
        self.append_event(
            case_id=test.case_id,
            event_type="STUCK_PATIENT_DETECTED",
            payload={"pattern_id": pattern_id, "test_id": test_id, "route_to": route_to},
            occurred_at=now,
        )
        self.db.commit()
        self.db.refresh(test)
        return test

    def get_diagnostic_tests_for_case(self, case_id: str) -> List[DiagnosticTest]:
        return (
            self.db.query(DiagnosticTest)
            .filter(DiagnosticTest.case_id == case_id)
            .order_by(DiagnosticTest.ordered_at.asc())
            .all()
        )

    def list_in_flight_diagnostic_tests(self, hospital_profile_id: str = "default") -> List[DiagnosticTest]:
        """Every not-yet-fully-reviewed test belonging to an ACTIVE case
        under this hospital profile -- what the Flow Engine sweep (CP9)
        checks for stuck patterns 1 and 2."""
        return (
            self.db.query(DiagnosticTest)
            .join(Case, DiagnosticTest.case_id == Case.case_id)
            .filter(
                Case.status == CaseStatus.ACTIVE,
                Case.hospital_profile_id == hospital_profile_id,
                DiagnosticTest.status != DiagnosticTestStatus.RESULT_REVIEWED,
            )
            .all()
        )
