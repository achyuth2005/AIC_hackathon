#!/usr/bin/env python3
"""
Medical History feature: synthetic ED patient seed generator.

Generates a batch of varied emergency-room patients using Faker, writes
them to a JSON seed file, and (optionally, via --seed-db) injects them
into the local development database as real Case + Observation rows
through the same EventStore / Clinical Scoring Engine every other patient
in this system goes through -- so seeded patients show up in the Guardian
Queue with a real RiskAssessment, not a hand-faked one.

This is deliberately separate from the two synthetic generators that
already exist in this codebase, neither of which fits this purpose:
  - app/ml/synthetic_data.py produces unlabelled FEATURE VECTORS to
    train/evaluate the ML Risk Challenger -- no Case rows, no
    medical_history, no chief complaints.
  - app/demo/scenarios.py produces twenty individually hand-designed,
    narratively-labelled cases for a live demo walkthrough -- not a bulk,
    randomised dataset.

Medical History requirement (the reason this script exists): EXACTLY 50%
of generated patients have a non-empty `medical_history`; the other 50%
have it strictly null/empty. This is an exact split (a shuffled list of
N//2 True / N//2 False flags), not a per-patient coin flip, so a run's
actual proportion never drifts from 50% the way independent sampling
could. Within the "has history" half, roughly half draw from a
HIGH_RISK_HISTORIES pool (COPD, CAD, Heart Failure, Immunosuppressed --
see app/scoring/medical_history.py's HIGH_RISK_HISTORY_KEYWORDS, which
this pool is written to match) so a meaningful fraction of the seeded
population actually exercises the Risk Engine's medical-history escalation
end to end, and the rest draw from a LOW_RISK_HISTORIES pool of common but
non-escalating chronic conditions -- so "has a history" and "has a
HIGH-RISK history" are deliberately not the same 50%.

Usage:
    python scripts/generate_patients.py                      # 750 patients -> JSON only
    python scripts/generate_patients.py --count 1000 --csv    # also write CSV
    python scripts/generate_patients.py --seed-db              # also inject into the dev DB
    python scripts/generate_patients.py --count 500 --seed 7 --seed-db
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import random
import sys
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from faker import Faker  # noqa: E402

# ---------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------

WALK_IN_FRACTION = 0.82  # "Majority ... Direct Walk-in, minority ... Ambulance"

SEVERITY_WEIGHTS = {  # loosely mirrors app/ml/synthetic_data.py's realistic minority-critical-class framing
    "CRITICAL": 0.08,
    "MODERATE": 0.32,
    "MINOR": 0.60,
}

# Chief complaints, grouped by rough severity so the free-text presenting
# complaint and the generated vitals point the same direction (a "minor
# laceration" complaint should not usually carry critical vitals, and vice
# versa) -- [Assumption], same status as every other illustrative
# relationship in this codebase's synthetic generators.
COMPLAINTS = {
    "CRITICAL": [
        "Crushing chest pain radiating to left arm, diaphoretic",
        "Sudden severe shortness of breath, unable to speak in full sentences",
        "Major trauma, high-speed motor vehicle collision",
        "Fall from height with suspected spinal injury",
        "Sudden facial droop and slurred speech, stroke alert",
        "Anaphylaxis after bee sting, facial swelling and stridor",
        "Witnessed generalised seizure, post-ictal and confused",
        "Severe abdominal pain with rigidity and hypotension",
        "Penetrating stab wound to the abdomen",
        "Unresponsive, found down, unknown downtime",
    ],
    "MODERATE": [
        "Moderate abdominal pain, worsening over 6 hours",
        "Deep laceration to forearm from kitchen knife, needs sutures",
        "Suspected fracture of the wrist after a fall",
        "Persistent fever with vomiting for two days",
        "Migraine with photophobia, not resolving with home medication",
        "Asthma exacerbation, increased wheeze and rescue inhaler use",
        "Moderate burn to hand from cooking oil",
        "Dog bite to lower leg, puncture wounds, needs cleaning",
        "Palpitations and lightheadedness, no chest pain",
        "Back pain after lifting, unable to bear weight comfortably",
    ],
    "MINOR": [
        "Minor laceration to finger while chopping vegetables",
        "Sprained ankle after stepping off a curb",
        "Sore throat and mild fever, cold-like symptoms",
        "Mild allergic rash after new laundry detergent",
        "Requesting refill of routine blood pressure medication",
        "Minor bump to the head, no loss of consciousness, feeling fine",
        "Ear pain for two days, no fever",
        "Mild lower back stiffness, chronic, no new injury",
        "Small splinter in palm, unable to remove at home",
        "Mild dehydration after a long hike, feeling better with water",
    ],
}

# High-risk histories are written to contain at least one of
# app/scoring/medical_history.py's HIGH_RISK_HISTORY_KEYWORDS verbatim, so
# a meaningful share of the "has history" half actually triggers the Risk
# Engine's escalation when paired with abnormal vitals.
HIGH_RISK_HISTORIES = [
    "COPD",
    "COPD, Hypertension",
    "Coronary Artery Disease (CAD)",
    "CAD, Type 2 Diabetes",
    "Congestive Heart Failure",
    "Heart Failure, Chronic Kidney Disease",
    "Immunosuppressed (post-transplant, on tacrolimus)",
    "Immunocompromised, on long-term chemotherapy",
    "COPD, Coronary Artery Disease",
]

# Common chronic conditions that do NOT match the Risk Engine's high-risk
# keyword list -- present in the record, but not an escalator by design.
LOW_RISK_HISTORIES = [
    "Hypertension",
    "Type 2 Diabetes",
    "Hypertension, Type 2 Diabetes",
    "Hypothyroidism",
    "Seasonal Allergies",
    "Osteoarthritis",
    "GERD",
    "Migraine",
    "Hyperlipidemia",
    "Anxiety",
]

# Bug fix (realistic hospital-state distribution): every previous run of
# this script left ALL generated patients ACTIVE forever. GET /queue and
# every wait-time estimate scale with however many ACTIVE cases exist
# (app/queue/guardian_queue.py, app/ops/wait_time.py) -- so a dev DB built
# from repeated runs of this script had 500-1000+ patients permanently
# "waiting", producing exactly the nonsense a live run of this system
# turned up: 511 patients ahead, a 32-day estimated wait. A real ED's
# *active* headcount is bounded by its physical capacity (beds, bays,
# staff), not by how many patients have ever passed through its doors --
# these two counts are therefore fixed absolute numbers, not a percentage
# of `count`. Everything else becomes DISPOSED: fully present and
# searchable (GET /cases, medical-history lookup, case review) but out of
# the live queue/wait-time picture, exactly like a real hospital's already
# -discharged patients are.
ACTIVE_WAITING_COUNT = 30
ACTIVE_IN_TREATMENT_COUNT = 15

# How a DISPOSED patient's ED journey actually ended -- carried on the
# PATIENT_DISPOSED event payload (see EventStore.dispose_case), not a new
# CaseStatus value, so this stays searchable without touching the schema
# every ACTIVE-population query in this codebase keys off. Realistic
# skew: most ED visits end in discharge; a minority are admitted; transfer
# and death are both rarer still. [Assumption], same status as every other
# illustrative distribution in this generator.
DISPOSITION_WEIGHTS = {
    "DISCHARGED": 0.75,
    "ADMITTED": 0.18,
    "TRANSFERRED": 0.05,
    "DECEASED": 0.02,
}


@dataclass
class GeneratedPatient:
    mrn: str
    display_name: str
    date_of_birth: str
    age_years: int
    sex: str
    arrival_mode: str
    medical_history: Optional[str]
    chief_complaint: str
    severity_tier: str
    estimated_transport_minutes: Optional[float]
    # "ACTIVE_WAITING" | "ACTIVE_IN_TREATMENT" | "DISPOSED" -- what
    # seed_database() drives this case to after registration+scoring; see
    # ACTIVE_WAITING_COUNT/ACTIVE_IN_TREATMENT_COUNT above.
    case_status_plan: str = "DISPOSED"
    disposition: Optional[str] = None  # only set when case_status_plan == "DISPOSED"
    vitals: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------

def _weighted_choice(rng: random.Random, weights: Dict[str, float]) -> str:
    keys = list(weights.keys())
    return rng.choices(keys, weights=[weights[k] for k in keys], k=1)[0]


def _vitals_for_tier(rng: random.Random, tier: str) -> Dict[str, Any]:
    """[Assumption]: simple per-tier uniform ranges, not a physiological
    model -- deliberately simple, matching this project's own convention
    (see app/ml/synthetic_data.py's module docstring on generator
    circularity) that every synthetic-data relationship here is
    illustrative, not clinically sourced."""
    if tier == "CRITICAL":
        rr = round(rng.uniform(28, 40), 0)
        spo2 = round(rng.uniform(78, 89), 0)
        hr = round(rng.uniform(125, 160), 0)
        sbp = round(rng.uniform(70, 88), 0)
        temp = round(rng.uniform(35.0, 39.8), 1)
        # NEW_CONFUSION is a NEWS2(adult)-only code -- PEWS's consciousness
        # mapping (paediatric patients) does not accept it (see
        # app/scoring/pews.py / app/scoring/concepts.py's CONSCIOUSNESS_CODES
        # docstring). Restricted to codes valid under BOTH frameworks so
        # this generator produces patients across the full age range
        # without needing to know which age band each row will route to.
        consciousness = rng.choice(["VOICE", "PAIN", "ALERT"])
        suppl_o2 = True
    elif tier == "MODERATE":
        rr = round(rng.uniform(20, 27), 0)
        spo2 = round(rng.uniform(92, 95), 0)
        hr = round(rng.uniform(100, 124), 0)
        sbp = round(rng.uniform(95, 110), 0)
        temp = round(rng.uniform(37.6, 38.9), 1)
        consciousness = "ALERT"
        suppl_o2 = rng.random() < 0.15
    else:  # MINOR
        rr = round(rng.uniform(12, 19), 0)
        spo2 = round(rng.uniform(96, 100), 0)
        hr = round(rng.uniform(60, 98), 0)
        sbp = round(rng.uniform(105, 129), 0)
        temp = round(rng.uniform(36.3, 37.3), 1)
        consciousness = "ALERT"
        suppl_o2 = False

    return {
        "RESP_RATE": rr,
        "SPO2": spo2,
        "HEART_RATE": hr,
        "SYSTOLIC_BP": sbp,
        "TEMPERATURE": temp,
        "CONSCIOUSNESS_LEVEL": consciousness,
        "SUPPLEMENTAL_OXYGEN": suppl_o2,
    }


def generate_patients(count: int, seed: int = 42) -> List[GeneratedPatient]:
    if not (500 <= count <= 1000):
        raise ValueError(f"count must be between 500 and 1000 (got {count})")
    if count < ACTIVE_WAITING_COUNT + ACTIVE_IN_TREATMENT_COUNT:
        raise ValueError(
            f"count must be at least {ACTIVE_WAITING_COUNT + ACTIVE_IN_TREATMENT_COUNT} to fit the "
            f"active cohort alone (got {count})"
        )

    rng = random.Random(seed)
    fake = Faker()
    Faker.seed(seed)

    # Medical History requirement: an EXACT 50/50 split, not a per-patient
    # coin flip -- shuffle a list with exactly count//2 True flags rather
    # than sampling independently, so the realised proportion can never
    # drift off 50% regardless of count or seed. Deliberately independent
    # of case_status_plan below: history is exactly 50/50 across the WHOLE
    # dataset, active and historical alike, so search/case-review still
    # exercises history-driven escalation against a real spread of already
    # -disposed patients too, not only the small active cohort.
    has_history_flags = [True] * (count // 2) + [False] * (count - count // 2)
    rng.shuffle(has_history_flags)

    # Realistic hospital-state distribution (see ACTIVE_WAITING_COUNT's own
    # comment): an exact split, same shuffled-list mechanism as
    # has_history_flags above, so the active headcount never drifts either.
    status_plans = (
        ["ACTIVE_WAITING"] * ACTIVE_WAITING_COUNT
        + ["ACTIVE_IN_TREATMENT"] * ACTIVE_IN_TREATMENT_COUNT
        + ["DISPOSED"] * (count - ACTIVE_WAITING_COUNT - ACTIVE_IN_TREATMENT_COUNT)
    )
    rng.shuffle(status_plans)

    patients: List[GeneratedPatient] = []
    today = date.today()

    for i in range(count):
        age_years = rng.randint(1, 94)
        sex = rng.choice(["MALE", "FEMALE", "OTHER"])
        dob = today - timedelta(days=age_years * 365 + rng.randint(0, 364))

        case_status_plan = status_plans[i]
        tier = _weighted_choice(rng, SEVERITY_WEIGHTS)
        complaint = rng.choice(COMPLAINTS[tier])
        vitals = _vitals_for_tier(rng, tier)

        if has_history_flags[i]:
            # Within the "has history" half, split roughly evenly between
            # a high-risk (Risk Engine escalator) and a low-risk history --
            # deliberately NOT the same 50% as "has any history at all".
            pool = HIGH_RISK_HISTORIES if rng.random() < 0.5 else LOW_RISK_HISTORIES
            medical_history: Optional[str] = rng.choice(pool)
        else:
            medical_history = None  # strictly empty/null, never an empty string

        if case_status_plan == "DISPOSED":
            # Historical patients are generated WALK_IN only: their
            # arrival_mode has no bearing on the search/case-review use
            # case this bulk historical dataset exists for, and forcing
            # AMBULANCE on hundreds of already-departed patients would
            # flood the *live* Ambulance Inbound Board (GET /cases?
            # arrival_mode=AMBULANCE lists every ambulance-origin case
            # regardless of status -- it has no status filter of its own)
            # with stale entries. AMBULANCE stays available for the small
            # active cohort below, at the original 82/18 split.
            arrival_mode = "WALK_IN"
            estimated_transport_minutes = None
            disposition: Optional[str] = _weighted_choice(rng, DISPOSITION_WEIGHTS)
        else:
            arrival_mode = "WALK_IN" if rng.random() < WALK_IN_FRACTION else "AMBULANCE"
            estimated_transport_minutes = round(rng.uniform(5, 35), 1) if arrival_mode == "AMBULANCE" else None
            disposition = None

        patients.append(
            GeneratedPatient(
                mrn=f"MRN-{100000 + i}",
                display_name=fake.name(),
                date_of_birth=dob.isoformat(),
                age_years=age_years,
                sex=sex,
                arrival_mode=arrival_mode,
                medical_history=medical_history,
                chief_complaint=complaint,
                severity_tier=tier,
                estimated_transport_minutes=estimated_transport_minutes,
                case_status_plan=case_status_plan,
                disposition=disposition,
                vitals=vitals,
            )
        )

    return patients


# ---------------------------------------------------------------------
# Output: JSON / CSV seed files
# ---------------------------------------------------------------------

def write_json(patients: List[GeneratedPatient], out_path: str) -> None:
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump([asdict(p) for p in patients], f, indent=2)


def write_csv(patients: List[GeneratedPatient], out_path: str) -> None:
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    fieldnames = [
        "mrn", "display_name", "date_of_birth", "age_years", "sex", "arrival_mode",
        "medical_history", "chief_complaint", "severity_tier", "estimated_transport_minutes",
        "case_status_plan", "disposition",
        "RESP_RATE", "SPO2", "HEART_RATE", "SYSTOLIC_BP", "TEMPERATURE",
        "CONSCIOUSNESS_LEVEL", "SUPPLEMENTAL_OXYGEN",
    ]
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for p in patients:
            row = asdict(p)
            row.update(row.pop("vitals"))
            writer.writerow(row)


# ---------------------------------------------------------------------
# Optional: inject into the real local dev database
# ---------------------------------------------------------------------

def _seed_baseline_department(store, profile) -> None:
    """Bug fix: provisions a resource department sized for this script's
    active cohort (ACTIVE_IN_TREATMENT_COUNT=15 concurrent treatment-space
    assignments below) so seed_database() never hits a CapacityConflictError
    just from its own seeding, and so the Ops & Resources page has real
    content immediately after a bulk seed -- previously GET /resources
    returned nothing at all until an admin provisioned beds by hand."""
    from app.models.enums import ResourceType

    for label in ["Resus 1", "Resus 2", "Resus 3"]:
        store.create_resource(resource_type=ResourceType.RESUSCITATION_BAY, label=label, hospital_profile_id=profile.profile_id)
    for i in range(1, 21):
        store.create_resource(resource_type=ResourceType.TREATMENT_SPACE, label=f"Bay {i}", hospital_profile_id=profile.profile_id)
    for i in range(1, 9):
        store.create_resource(resource_type=ResourceType.CLINICIAN, label=f"Dr. On-Call {i}", hospital_profile_id=profile.profile_id)


def seed_database(patients: List[GeneratedPatient]) -> None:
    """Creates a real Case (+ vitals + chief-complaint Observations) for
    every generated patient through EventStore, exactly like a real
    registration would, then runs the real assess_case() pipeline so each
    seeded patient has a genuine RiskAssessment (medical-history escalation
    included) -- not a pre-computed acuity written straight into the DB.

    Bug fix: every patient used to be left ACTIVE forever. Each one is now
    driven to its planned end state (p.case_status_plan, assigned by
    generate_patients() -- see ACTIVE_WAITING_COUNT's own comment) via the
    same store methods a real nurse/admin action would call: assign_resource
    for the small "currently in treatment" cohort, dispose_case for
    historical patients."""
    from app.config.hospital_profile import load_hospital_profile
    from app.db import SessionLocal, init_db
    from app.models.enums import ArrivalMode, MeasurementStatus, ReliabilityTier, ResourceType, SourceType, ValueType
    from app.scoring import concepts
    from app.scoring.risk_orchestrator import assess_case
    from app.store.event_store import CapacityConflictError, EventStore
    from app.timeutil import utcnow

    init_db()  # also runs the medical_history column patch (app/db.py) if needed
    profile = load_hospital_profile("default")
    db = SessionLocal()
    store = EventStore(db)
    _seed_baseline_department(store, profile)

    _VITAL_CONCEPTS = [
        (concepts.RESP_RATE, ValueType.NUMERIC),
        (concepts.SPO2, ValueType.NUMERIC),
        (concepts.HEART_RATE, ValueType.NUMERIC),
        (concepts.SYSTOLIC_BP, ValueType.NUMERIC),
        (concepts.TEMPERATURE, ValueType.NUMERIC),
        (concepts.CONSCIOUSNESS_LEVEL, ValueType.CODED),
        (concepts.SUPPLEMENTAL_OXYGEN, ValueType.BOOLEAN),
    ]

    try:
        created = 0
        for p in patients:
            case = store.create_case(
                mrn=p.mrn,
                display_name=p.display_name,
                date_of_birth=date.fromisoformat(p.date_of_birth),
                age_years=p.age_years,
                sex=p.sex,
                medical_history=p.medical_history,
                arrival_mode=ArrivalMode(p.arrival_mode),
            )

            if p.arrival_mode == "AMBULANCE":
                # Mirrors app/api/cases.py's real create_case flow: an
                # ambulance case starts PRE_ARRIVAL; bring it to ACTIVE
                # before scoring, exactly like the real PATIENT_ARRIVED
                # transition (app/store/event_store.py's record_arrival).
                store.record_arrival(case.case_id)

            observed_at = utcnow()
            for concept_code, value_type in _VITAL_CONCEPTS:
                store.add_observation(
                    case_id=case.case_id,
                    concept_code=concept_code,
                    value=p.vitals[concept_code],
                    value_type=value_type,
                    source_type=SourceType.DEVICE if value_type == ValueType.NUMERIC else SourceType.NURSE,
                    reliability_tier=ReliabilityTier.MACHINE_MEASURED
                    if value_type == ValueType.NUMERIC
                    else ReliabilityTier.CLINICIAN_OBSERVED,
                    measurement_status=MeasurementStatus.MEASURED,
                    observed_at=observed_at,
                )
            store.add_observation(
                case_id=case.case_id,
                concept_code=concepts.SYMPTOM_TEXT,
                value=p.chief_complaint,
                value_type=ValueType.TEXT,
                source_type=SourceType.PATIENT,
                reliability_tier=ReliabilityTier.PATIENT_REPORTED,
                measurement_status=MeasurementStatus.MEASURED,
                observed_at=observed_at,
            )

            assess_case(case, store, profile)

            # Drive the case to its planned end state (bug fix: this used
            # to be a no-op, leaving every patient ACTIVE forever).
            if p.case_status_plan == "ACTIVE_IN_TREATMENT":
                try:
                    store.assign_resource(case.case_id, ResourceType.TREATMENT_SPACE, profile)
                except CapacityConflictError:
                    # The baseline department above is sized to cover
                    # ACTIVE_IN_TREATMENT_COUNT concurrently; a genuine
                    # conflict here just leaves this one case WAITING
                    # instead of failing the whole seed run.
                    pass
            elif p.case_status_plan == "DISPOSED":
                store.dispose_case(case.case_id, disposition=p.disposition)
            # ACTIVE_WAITING: nothing further -- stays ACTIVE, unassigned.

            created += 1

        active_waiting = sum(1 for p in patients if p.case_status_plan == "ACTIVE_WAITING")
        active_in_treatment = sum(1 for p in patients if p.case_status_plan == "ACTIVE_IN_TREATMENT")
        disposed = sum(1 for p in patients if p.case_status_plan == "DISPOSED")
        print(
            f"Seeded {created} patients into the local dev database "
            f"({active_waiting} active/waiting, {active_in_treatment} active/in-treatment, "
            f"{disposed} disposed/historical)."
        )
    finally:
        db.close()


# ---------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--count", type=int, default=750, help="Number of patients to generate (500-1000). Default 750.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility. Default 42.")
    parser.add_argument(
        "--out", type=str, default=os.path.join("scripts", "seed_data", "generated_patients.json"),
        help="Output JSON path.",
    )
    parser.add_argument("--csv", action="store_true", help="Also write a CSV alongside the JSON output.")
    parser.add_argument(
        "--seed-db", action="store_true",
        help="Also inject the generated patients into the local dev database (DATABASE_URL / patienttriage.db) as real Cases.",
    )
    args = parser.parse_args()

    patients = generate_patients(args.count, seed=args.seed)

    write_json(patients, args.out)
    print(f"Wrote {len(patients)} patients to {args.out}")

    if args.csv:
        csv_path = os.path.splitext(args.out)[0] + ".csv"
        write_csv(patients, csv_path)
        print(f"Wrote {len(patients)} patients to {csv_path}")

    with_history = sum(1 for p in patients if p.medical_history)
    walk_in = sum(1 for p in patients if p.arrival_mode == "WALK_IN")
    active_waiting = sum(1 for p in patients if p.case_status_plan == "ACTIVE_WAITING")
    active_in_treatment = sum(1 for p in patients if p.case_status_plan == "ACTIVE_IN_TREATMENT")
    disposed = sum(1 for p in patients if p.case_status_plan == "DISPOSED")
    print(
        f"Summary: {with_history}/{len(patients)} ({with_history / len(patients):.0%}) have a recorded "
        f"medical_history; {walk_in}/{len(patients)} ({walk_in / len(patients):.0%}) arrived WALK_IN."
    )
    print(
        f"Planned hospital state: {active_waiting} active/waiting, {active_in_treatment} active/in-treatment, "
        f"{disposed} disposed/historical (applied to the DB only with --seed-db)."
    )

    if args.seed_db:
        seed_database(patients)


if __name__ == "__main__":
    main()
