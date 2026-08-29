# Frontend Implementation Plan

**Project:** PatientTriage.ai — Emergency Department Triage & Guardian Queue
**Document status:** Authoritative frontend blueprint, handed to **Antigravity** for implementation.
**Backend commit inspected:** working tree at `/Users/achyu/Sem_5/AIC_hackathon/AIC_backend` as of 2026-08-29.
**Verification method:** every endpoint, request field, response field and status code below was read from the actual source **and** exercised against a live `TestClient` run of `app.main:app`. The full endpoint list was dumped from the app's own generated `/openapi.json` (49 operations). Anything not verifiable this way is explicitly marked `UNVERIFIED`.

---

## 1. Project Overview

PatientTriage.ai is an emergency-department triage system built around one governing invariant: **waiting does not make a patient sicker, but waiting makes the system look again.** A patient's acuity (ESI 1–5, where **1 is most urgent**) is computed by a deterministic clinical scoring stack. An ML model may only ever *escalate*, never de-escalate. A human clinician may de-escalate, but only with structured friction and a permanent audit record.

The backend is a **FastAPI + SQLAlchemy + SQLite** event-sourced application. It is feature-complete for the hackathon MVP scope (Phase 13 of the architecture document): 49 HTTP operations, 312 passing tests, an ML challenger artifact, an optional LLM intake/explanation layer with a fully deterministic fallback, and a 20-patient demo seeder plus a 3× surge simulator.

**There is currently no frontend of any kind in this repository.** This document specifies one, built entirely against the API surface that already exists.

The frontend serves **four distinct human surfaces** the architecture names (Phase 8), plus two operational surfaces:

| Surface | Primary user | Objective (verbatim from architecture) |
|---|---|---|
| Nurse Guardian Queue | Triage nurse | "Scan the department in five seconds, act in one tap." |
| Doctor View | Physician | "Decision support, not information dumping." |
| Control Tower | Charge nurse / ED lead | "Anticipate, not report. Five tiles maximum, every tile actionable." |
| Patient View | Patient / caregiver | "Reduce anxiety and reduce reception load. Not to triage." |
| Ambulance / Pre-alert | Paramedic + receiving ED | "Scannable in three seconds." |
| Admin & Demo Console | Admin / presenter | Override + equity monitoring; demo seeding and surge. |

---

## 2. Source of Truth

**The existing backend is the source of truth. This plan does not propose backend changes.**

Rules Antigravity must follow:

1. **Never invent an endpoint.** Section 6 lists every operation that exists. If a feature seems to need an endpoint not in Section 6, that feature is out of scope — raise it, do not build a workaround that fabricates data.
2. **Never invent a response field.** Section 13 lists the exact fields of every response type, copied from the Pydantic schemas and confirmed against live JSON.
3. **Never re-derive clinical logic in the frontend.** Acuity, confidence bands, deterioration trend, wait-time ranges, attention flags, queue ordering, and the one-line presentation are all *already computed by the backend* and returned pre-computed. The frontend renders them; it never recomputes them. In particular:
   - **Do not sort the queue.** `GET /queue` returns rows already in Guardian Queue order. Preserve array order exactly.
   - **Do not compute a wait time.** `wait_time_estimate` arrives as a range with a mandatory `caveat` string.
   - **Do not derive an acuity from vitals.** Only `final_acuity` from a `RiskAssessment` is authoritative.
4. **Two hard clinical display rules, enforced by the API and to be re-enforced in the UI:**
   - The patient-facing surface **must never render acuity, confidence, probability, or any clinical interpretation.** `GET /cases/{id}/patient-view` returns a schema with no field capable of carrying one. The frontend must not fetch acuity from another endpoint and render it on a patient screen.
   - The nurse/doctor surfaces **must never render raw ML probabilities, feature contributions, or technical confidence percentages** as primary information. Show `confidence_band` (`HIGH`/`MEDIUM`/`LOW`) plus the plain-language `confidence_reasons[]`. `confidence_score` and `ml_probability` may appear only inside an explicitly-labelled "technical detail" disclosure, never on the queue row.
5. **Where this plan and the backend disagree, the backend wins.** Re-read the route file and correct the plan.

Reference documents in the repo:
- `patienttriage-round2-architecture-review.md` — the original architecture (1095 lines). Phase 8 (interfaces), Phase 11.C (patient journey), Phase 13 (MVP scope), Phase 14 (demo scenarios + surge + 7-minute narrative), Phase 15 (technology stack) are the frontend-relevant sections.
- `PS.pdf` — original problem statement (not machine-read for this plan; `UNVERIFIED` as a source of frontend requirements).

---

## 3. Current Backend Architecture

### 3.1 Runtime

- **Framework:** FastAPI (`app/main.py`), ASGI, run with `uvicorn app.main:app --reload`.
- **Default dev port:** `8000` (uvicorn default — no port is hardcoded in the app).
- **Database:** SQLite by default at `<repo>/patienttriage.db`, overridable with the `DATABASE_URL` env var (`app/db.py`). Tables auto-create on startup via the lifespan hook.
- **Interactive docs:** FastAPI's defaults are active — `GET /docs` (Swagger UI) and `GET /openapi.json`. **Antigravity should generate TypeScript types from `/openapi.json` rather than hand-writing them where practical.**
- **Health check:** `GET /health` → `{"status":"ok"}`.

### 3.2 Module map

```
app/
├── main.py                 FastAPI app, router registration, exception→HTTP mapping
├── db.py                   SQLAlchemy engine/session; DATABASE_URL env override
├── api/                    HTTP routers ONLY — thin wrappers, no business logic
│   ├── auth.py             POST /auth/login
│   ├── cases.py            /cases/* — the largest surface (28 operations)
│   ├── queue.py            /queue, /queue/printable
│   ├── control_tower.py    /control-tower
│   ├── alerts.py           /alerts, /alerts/budget, dismiss
│   ├── audit.py            /overrides/flagged-for-review, /overrides/monitoring
│   ├── conflicts.py        /conflicts/{id}/resolve
│   ├── ops.py              /ops/stuck-patients
│   ├── resources.py        /resources/*
│   ├── diagnostics.py      /tests/{id}/*
│   ├── observations.py     /observations/{id}/supersede
│   └── demo.py             /demo/seed, /demo/surge
├── store/event_store.py    Append-only event store + all persistence (1471 lines)
├── scoring/                Age router → NEWS2/PEWS → hard triggers → confidence/abstention
├── ml/                     Challenger model (scikit-learn, artifact committed)
├── queue/                  Guardian Queue ordering + reassessment Time Engine
├── ops/                    Stuck-patient flow engine + wait-time prediction
├── alerts/                 Alert aggregation engine + alert-budget measurement
├── dashboard/              patient_view / doctor_view / control_tower builders
├── llm/                    Intake extraction + explanation (Groq); deterministic fallback
├── ambulance/              Simulated ETA range + pre-alert builder
├── auth/                   JWT mock, 3 hard-coded roles
├── audit/                  Override + equity monitoring report
├── privacy/                Redaction shim applied before any LLM call
├── config/                 HospitalProfile loader + hospital_profiles/default.yaml
└── demo/                   20 scripted patients + surge simulator
```

### 3.3 The scoring pipeline (what produces `final_acuity`)

Read-only context for the frontend — **do not reimplement**:

```
observation written
  → Age Router (PAEDIATRIC <16 / ADULT 16–65 / GERIATRIC 65+)
  → deterministic framework (NEWS2 for adult/geriatric, PEWS-style for paediatric)
  → single-parameter escalation rule
  → Layer 4 hard triggers (force ESI 1, still queued)
  → ML challenger (escalation-only: final = min(rules, ml))
  → Confidence & Abstention Engine (may floor acuity at a safer level)
  → RiskAssessment persisted with deciding_layer ∈ {RULES, ML, OVERRIDE, ABSTENTION}
```

Separately and in parallel, the **Emergency Bypass** engine has three redundant detectors (human one-tap, physiological thresholds, critical text phrases). Bypass sets `emergency_bypass_active: true` on the case; it is escalation-only and no detector can cancel another.

### 3.4 Behaviours the frontend must know about

**a) There is no scheduler. Several GET endpoints have documented write side effects.** This is intentional and documented in the backend's own module docstrings.

| Endpoint | Side effect on read |
|---|---|
| `GET /queue` | Flags newly-overdue reassessments; backfills a missing initial RiskAssessment |
| `GET /alerts` | Raises any newly-true alert condition; refreshes/auto-resolves the aggregate overdue alert |
| `GET /ops/stuck-patients` | Flags newly-stuck tests and resources |
| `GET /control-tower` | Runs the same stuck-patient sweep |

**Frontend consequence:** polling these endpoints is what makes the system's clocks advance. This is a *feature* for the demo (the surge scenario depends on it), but it means these GETs are **not** safe to call speculatively, must **not** be issued from a React `useEffect` that can double-fire in StrictMode without dedupe, and must **not** be retried aggressively on error. Use TanStack Query with a single shared query key per endpoint so React's StrictMode double-render does not produce two independent sweeps.

**b) There is no real-time transport.** No SSE, no WebSocket. The architecture explicitly sanctions the fallback: *"Poll every 3 seconds. Nobody in the audience can tell, and it will not break on stage."* **Polling is the design, not a compromise.**

**c) All timestamps are naive UTC with no timezone suffix.** Verified live: `"created_at": "2026-08-28T18:48:46.312764"`. `new Date(...)` in JS will parse this as **local time**, silently shifting every clock in the UI. See §19 issue 🟠-1 and §12.4 for the mandatory parsing helper.

**d) No pagination anywhere.** Every list endpoint returns the full set. Acceptable at demo scale (20–60 cases); the frontend should still virtualise or cap rendering above ~200 rows.

**e) Lower ESI number = more urgent.** ESI 1 is critical; ESI 5 is minor. All sorting, colour ramps and "escalate" semantics invert relative to intuition. Escalating means *decreasing* the number.

---

## 4. Frontend Goals

1. **Render, never recompute.** The frontend is a presentation and action layer over a backend that already owns every clinical decision.
2. **Five-second scan, one-tap action** on the nurse queue (Phase 8.2).
3. **Make the safety invariants visible.** The demo's most important moments are the ML challenger being refused a downgrade (`deciding_layer: RULES` while `ml_suggested_acuity > final_acuity`), abstention holding a case at a safer level, and a de-escalation producing a full audit record. The UI must make these legible, not bury them.
4. **Never leak clinical interpretation to the patient surface.**
5. **Degrade honestly.** When the LLM is unavailable the explanation endpoint still returns a deterministic explanation with `fallback_used: true` — show that state rather than hiding it. When the whole system fails, `GET /queue/printable` is the paper fallback and must be reachable in one click.
6. **Support the 7-minute demo narrative** (architecture Phase 14.3) end to end without the presenter touching a terminal.

**Explicit non-goals:** offline mode, i18n runtime switching (the profile declares `language_set: [en, hi]` but no translated strings exist in the backend — `UNVERIFIED` as a buildable feature), voice input (no ASR endpoint exists), and patient chat (no such endpoint exists).

---

## 5. User Workflow

Each flow below is written as **User action → Frontend state → API request → Backend processing → API response → Frontend state update → UI result.**

### 5.1 Role selection (demo login)

1. **User action:** presenter picks "Nurse", "Doctor" or "Admin" from a dropdown labelled *Demo shortcut — not a real login*.
2. **Frontend state:** `auth.status = 'authenticating'`.
3. **API:** `POST /auth/login` `{"role":"NURSE"}`.
4. **Backend:** looks up the one hard-coded `DemoUser` for that role, signs an HS256 JWT (12-hour TTL).
5. **Response 200:** `{access_token, token_type:"bearer", user:{user_id, display_name, role}}`.
6. **Frontend state:** token + user stored in an auth context and mirrored to `localStorage`; `auth.status='authenticated'`.
7. **UI:** redirect to the role's home route (`/queue` for NURSE, `/doctor` for DOCTOR, `/admin` for ADMIN); header shows `display_name` and role chip.

### 5.2 Walk-in registration → first acuity

1. **User action:** nurse fills the registration form (name, age, sex, MRN optional) and submits.
2. **Frontend state:** `form.submitting = true`.
3. **API:** `POST /cases` `{hospital_profile_id:"default", display_name, age_years, sex, arrival_mode:"WALK_IN"}`.
4. **Backend:** creates the case as `status: ACTIVE`, `identity_link_status: CONFIRMED`, starts the reassessment clock, **and immediately runs `assess_case`** — so a walk-in has a RiskAssessment before any vitals exist (it will be an abstention/missing-data result).
5. **Response 201:** `CaseResponse`.
6. **Frontend state:** navigate to `/cases/{case_id}`; invalidate the `queue` query.
7. **UI:** case detail opens showing an acuity with `should_abstain: true` and an `abstention_message` — the correct, honest initial state.

### 5.3 Recording vitals → rescore

1. **User action:** nurse enters a vitals set in the Record Vitals panel and taps Save.
2. **Frontend state:** optimistic "saving" per field; no optimistic acuity (never guess an acuity).
3. **API:** one `POST /cases/{case_id}/observations` **per concept** (there is no batch endpoint — see §19 🟡-3). Issue them sequentially, not in parallel, so the final rescore reflects the complete set.
4. **Backend, per observation:** persists the observation → runs the Emergency Bypass detectors (physiological + text) → runs the full scoring stack → persists a fresh RiskAssessment.
5. **Response 201:** `ObservationResponse` each time.
6. **Frontend state:** after the last write, invalidate `case`, `queue`, `alerts`, `control-tower`, `risk-assessments`.
7. **UI:** acuity badge, confidence band and rule component breakdown update; if a bypass fired, a persistent critical banner appears on the case and a `CRITICAL_BYPASS_PATIENT` alert appears in the alert feed on the next poll.

### 5.4 Guardian Queue monitoring (the always-on view)

1. **User action:** none — the queue is open on a wall screen.
2. **Frontend state:** TanStack Query polling `['queue', profileId]` every 3000 ms.
3. **API:** `GET /queue?hospital_profile_id=default`.
4. **Backend:** rebuilds the queue for all ACTIVE cases of that profile, *flagging newly-overdue reassessments as it goes*, sorted lexicographically by `(final_acuity ↑, time_critical_pathway ↓, deterioration_trend ↓, time_in_current_band ↓, arrival_time ↑)`.
5. **Response 200:** `QueueEntry[]`, already ordered.
6. **Frontend state:** replace the list; diff by `case_id` to animate rows that moved.
7. **UI:** four persistent columns per row (Phase 8.2): acuity+confidence, one-line presentation, time in band vs target, primary attention flag. Row actions: Escalate, Mark reassessed, Record vitals, Open case.

### 5.5 One-tap escalate

1. **User action:** nurse taps Escalate on a queue row.
2. **Frontend state:** row enters `mutating`.
3. **API:** `POST /cases/{case_id}/override` `{"action":"ESCALATE"}` with `Authorization: Bearer <token>`. **No reason, no target acuity, no confirmation dialog** — Phase 9.6 requires zero friction in this direction.
4. **Backend:** defaults `target_acuity` to `max(1, current − 1)`, writes a `HumanDecision`, and writes a new RiskAssessment with `deciding_layer: OVERRIDE` so it applies instantly.
5. **Response 200:** `HumanDecisionResponse` with `flagged_for_review: false`.
6. **Frontend state:** invalidate `queue`, `case`, `decisions`.
7. **UI:** row jumps to its new position; a transient toast confirms.
8. **Edge case (verified):** escalating a case already at ESI 1 returns **400** with `detail: "ESCALATE must make the case MORE urgent…"`. The frontend must **disable the Escalate control when `final_acuity === 1`** rather than surface that error.

### 5.6 Reason-gated de-escalate

1. **User action:** nurse taps De-escalate → a modal opens.
2. **Frontend state:** modal form requires `target_acuity` (must be strictly greater than current) and `reason_code` from the fixed 5-value vocabulary; `free_text_reason` optional.
3. **API:** `POST /cases/{case_id}/override` `{"action":"DE_ESCALATE","target_acuity":4,"reason_code":"PATIENT_STABLE_ON_CLINICAL_REVIEW","free_text_reason":"..."}` + bearer token.
4. **Backend:** enforces both requirements server-side (a client skipping the UI cannot bypass them), writes the decision with `flagged_for_review: true`, writes an OVERRIDE RiskAssessment.
5. **Response 200:** `HumanDecisionResponse` with `flagged_for_review: true`.
6. **Frontend state:** close modal, invalidate `queue`, `case`, `decisions`, `flagged-for-review`.
7. **UI:** the full audit record is displayed immediately on the case (Phase 14.1 patient #18 demands the audit record be shown on screen), and the case appears in the admin Retrospective Review queue.

### 5.7 Emergency bypass (the panic button)

1. **User action:** staff taps the persistent Immediate Escalation control.
2. **API:** `POST /cases/{case_id}/emergency-bypass` `{"reason": "optional"}` + bearer token (NURSE/DOCTOR/ADMIN).
3. **Backend:** activates bypass attributed to the *authenticated* identity (not a body field).
4. **Response 200:** `CaseResponse` with `emergency_bypass_active: true`.
5. **UI:** immediate, un-dismissible critical banner on the case; on the next `/alerts` poll a `CRITICAL_BYPASS_PATIENT` alert appears. **No confirmation dialog** — "zero latency" is the stated requirement.

### 5.8 Patient self-report ("I feel worse")

1. **User action:** patient taps the single large button on the public patient view.
2. **API:** `POST /cases/{case_id}/self-reported-worsening` `{"note": "optional"}` — **unauthenticated by design** (kiosk/caregiver mode must work without a login).
3. **Backend:** forces the case onto the overdue-reassessment list regardless of the elapsed-time clock. **Does not change `final_acuity`** — a self-report is not physiology.
4. **Response 200:** `CaseResponse` with `reassessment_overdue: true`.
5. **UI (patient):** a calm acknowledgement — "A nurse has been notified." **No acuity, no ranking, no promise of a time.**
6. **UI (nurse):** on the next poll the row's `primary_attention_flag` becomes `REASSESSMENT_OVERDUE`.

### 5.9 Doctor review

1. **User action:** doctor opens a case from the doctor list.
2. **API:** `GET /cases/{case_id}/doctor-view` **with bearer token** — the response is identity-relative ("what changed since *you* last looked").
3. **Backend:** builds trends (only for concepts with ≥2 current readings), the events since this reviewer's last review, and pending actions.
4. **Response 200:** `DoctorCaseView` including `is_first_review`, `last_reviewed_at`, `changed_since_last_review[]`, `pending_actions[]`.
5. **User action:** doctor taps "Mark reviewed" → `POST /cases/{case_id}/mark-reviewed` (bearer token) → advances *that doctor's own* review cursor.
6. **UI:** the "What changed since you last looked" panel is the hero of this screen (Phase 8.3: "worth building before anything else").

### 5.10 Ambulance pre-arrival

1. **User action:** dispatch creates an ambulance case with an estimated transport duration.
2. **API:** `POST /cases` `{arrival_mode:"AMBULANCE", estimated_transport_minutes: 12, ...}`.
3. **Backend:** case is `PRE_ARRIVAL`, `identity_link_status: UNLINKED`, **no** initial RiskAssessment, and the simulated ETA clock starts immediately.
4. Paramedic adds vitals via `POST /cases/{id}/observations` — this **does** produce a RiskAssessment even while `PRE_ARRIVAL`, which is what gives the pre-alert its predicted acuity.
5. **API (ED side):** `GET /cases/{id}/pre-alert` and `GET /cases/{id}/eta`, polled.
6. **User action (ED):** on arrival, `POST /cases/{case_id}/arrival` → case becomes `ACTIVE`, is reassessed, and enters the Guardian Queue. **Same `case_id` throughout — no second record.**
7. **Identity:** `POST /cases/{id}/identity/propose` (unauthenticated) then `POST /cases/{id}/identity/confirm` (bearer token). Never auto-merge in the UI.

### 5.11 Capacity assignment and conflict

1. **User action:** charge nurse taps "Assign treatment space".
2. **API:** `POST /cases/{case_id}/assign-resource` `{"resource_type":"TREATMENT_SPACE"}`.
3. **Backend:** assigns an AVAILABLE resource, or raises a capacity conflict.
4. **Response 200:** `ResourceResponse` — **or 409** `{detail, resource_type, candidate_actions[]}`.
5. **UI on 409:** this is **not an error toast.** Render a dedicated conflict panel showing what was needed and the hospital's configured `candidate_actions` as a checklist. Phase 6.2: the conflict is surfaced to the human; acuity is never silently downgraded to fit capacity.

### 5.12 Surge demo

1. **User action:** presenter taps "Trigger 3× surge" on the Demo Console.
2. **API:** `POST /demo/surge?baseline_count=10&multiplier=3` (slow — seconds; show a determinate-looking progress state).
3. **Response 200:** `SurgeSimulationResult` with checkable evidence for all six Phase 14.2 properties plus a `narrative[]` of strings.
4. **UI:** render the narrative as an ordered checklist with the numeric evidence beside each claim, and put the live alerts-per-nurse-per-hour counter (`GET /alerts/budget`) prominently on screen — Phase 14.2 calls this "the single most sophisticated thing you can show."

---

## 6. Backend API Contract

**Base URL:** `${VITE_API_BASE_URL}`, default `http://localhost:8000`.
**Content type:** `application/json` for every operation except `GET /queue/printable`, which is `text/plain`.
**Auth header:** `Authorization: Bearer <access_token>` where required.

### 6.0 Auth requirements at a glance (verified against the route decorators)

| Requirement | Endpoints |
|---|---|
| **No auth** | Everything not listed below — including `POST /cases`, `POST /cases/{id}/observations`, `GET /queue`, `GET /control-tower`, `GET /alerts`, all patient/pre-alert/ETA reads, `/demo/*`, `/resources/*`, `/tests/*`, `/ops/*`, `/observations/{id}/supersede`, `POST /cases/{id}/self-reported-worsening`, `POST /cases/{id}/ambulance/delay`, `POST /cases/{id}/identity/propose` |
| **Any authenticated user** | `GET /cases/{id}/doctor-view`, `POST /cases/{id}/mark-reviewed` |
| **NURSE, DOCTOR or ADMIN** | `POST /cases/{id}/override`, `POST /cases/{id}/emergency-bypass`, `POST /cases/{id}/identity/confirm`, `POST /alerts/{id}/dismiss`, `POST /conflicts/{id}/resolve`, `GET /overrides/flagged-for-review` |
| **ADMIN only** | `GET /overrides/monitoring` |

Missing token → **401** `{"detail":"Missing bearer token."}`. Wrong role → **403** `{"detail":"Role NURSE is not permitted to perform this action."}`.

### 6.1 Global error contract

Registered in `app/main.py`. Every response body is `{"detail": "<string>"}` except the 409 capacity conflict and 422 validation errors.

| Status | Cause | Body | Frontend handling |
|---|---|---|---|
| **400** | Any `ValueError` from the store (bad override direction, missing `target_acuity`, unknown event type) | `{"detail": "<human-readable sentence>"}` | Show `detail` verbatim — these strings are written for humans. Keep the form open with values intact. |
| **401** | Missing/expired/invalid token | `{"detail":"Missing bearer token."}` or `"Invalid or expired token: …"` | Clear auth state, redirect to role selector, preserve the intended route for post-login return. |
| **403** | Role not permitted | `{"detail":"Role X is not permitted…"}` | Do not redirect. Show an inline "not permitted for your role" state. Prefer *hiding* the control for that role in the first place. |
| **404** | `NotFoundError` — no such case/alert/conflict/test/resource/transport | `{"detail":"'No case abc'"}` | **Note the embedded single quotes** (see §19 🟡-1). Strip `^'|'$` before display, or use a generic "Not found" message. Render an empty state, not a crash. |
| **409** | Re-superseding an observation; invalid arrival transition | `{"detail":"<sentence>"}` | Explain and refetch — the client's view of state was stale. |
| **409** | **Capacity conflict** (only from `POST /cases/{id}/assign-resource`) | `{"detail", "resource_type", "candidate_actions": string[]}` | **Special-cased.** Render the conflict panel described in §5.11. |
| **422** | Pydantic request validation (wrong type, missing field, bad enum, `value` not matching `value_type`, `AI_INFERRED` without `extraction_confidence`) | FastAPI standard `{"detail":[{"loc":[...],"msg":"...","type":"..."}]}` | `detail` is an **array here, a string elsewhere.** Map `loc` to form fields for inline errors. Never `String(detail)` blindly. |
| **500** | Unexpected | may be HTML | Generic failure toast + a Retry action. |

**Retry policy:** `GET` requests may retry **once** after 1 s on a network error or 5xx. **Never auto-retry the four side-effecting GETs** (`/queue`, `/alerts`, `/ops/stuck-patients`, `/control-tower`) more than once — let the next poll tick recover instead. **Never auto-retry any POST** — every POST here is a clinical action.

---

### 6.2 Auth

#### `POST /auth/login`
Purpose: demo role shortcut. No password exists.

| | |
|---|---|
| Auth | none |
| Body | `{"role": "NURSE" \| "DOCTOR" \| "ADMIN"}` — `role` **required** |
| 200 | `{"access_token": string, "token_type": "bearer", "user": {"user_id": string, "display_name": string, "role": Role}}` |
| 422 | role not one of the three enum values |

Verified example response:
```json
{"access_token":"eyJhbGciOiJIUzI1NiIs...","token_type":"bearer",
 "user":{"user_id":"demo-nurse-01","display_name":"Nurse Priya Nair","role":"NURSE"}}
```
Demo identities (hard-coded): `demo-nurse-01` "Nurse Priya Nair", `demo-doctor-01` "Dr. Arjun Rao", `demo-admin-01` "Admin Sana Sheikh". Token TTL is 12 hours.

**Loading:** the dropdown is disabled while in flight. **Errors:** a failed login means the backend is down — show the connection-failure screen from §15.4.

---

### 6.3 Cases

#### `POST /cases` → **201** `CaseResponse`
Auth: none.

| Field | Type | Required | Default | Notes |
|---|---|---|---|---|
| `hospital_profile_id` | string | no | `"default"` | Only `"default"` exists as a profile file |
| `mrn` | string \| null | no | null | |
| `display_name` | string \| null | no | null | |
| `date_of_birth` | date (`YYYY-MM-DD`) \| null | no | null | |
| `age_years` | int \| null | no | null | **Without this the age router cannot pick a framework** → abstention floor at ESI 3 |
| `sex` | string \| null | no | null | Free string — no enum. Used for equity subgroup reporting |
| `arrival_mode` | `"WALK_IN"` \| `"AMBULANCE"` | no | `"WALK_IN"` | |
| `estimated_transport_minutes` | float \| null | no | null | **Only meaningful with `AMBULANCE`; silently ignored for `WALK_IN`.** Starts the simulated ETA clock |

Behaviour: `WALK_IN` → `status: ACTIVE`, `identity_link_status: CONFIRMED`, immediate initial RiskAssessment. `AMBULANCE` → `status: PRE_ARRIVAL`, `identity_link_status: UNLINKED`, **no** initial assessment.

Verified 201 body: see §13.1.

#### `GET /cases?status=` → **200** `CaseResponse[]`
Auth: none. `status` optional, one of `PRE_ARRIVAL|ACTIVE|DISPOSED`; an invalid value → 422. Ordered by `created_at` ascending. **This is not the Guardian Queue** and is not acuity-ordered. **There is no `hospital_profile_id` filter on this endpoint** (see §19 🟡-2).

#### `GET /cases/{case_id}` → **200** `CaseDetailResponse` / **404**
Auth: none. `CaseResponse` + `current_observations[]` + `latest_risk_assessment` (nullable) + `wait_time_estimate` (nullable — populated only for an ACTIVE case that has at least one assessment).

#### `GET /cases/{case_id}/patient-view` → **200** `PatientCaseView` / **404**
Auth: none, by design. Fields: `case_id`, `display_name`, `stage`, `next_step_message`, `wait_time_estimate?`. **No acuity field exists on this schema.** `wait_time_estimate` is present only when `stage === "WAITING"`.

#### `GET /cases/{case_id}/doctor-view` → **200** `DoctorCaseView` / **401** / **404**
Auth: **any authenticated user.** Identity-relative response.

#### `POST /cases/{case_id}/mark-reviewed` → **200** `CaseResponse` / **401** / **404**
Auth: any authenticated user. No body. Advances only the calling user's review cursor.

#### `POST /cases/{case_id}/observations` → **201** `ObservationResponse` / **404** / **422**
Auth: none. **The single most important write in the system** — triggers bypass evaluation and a full rescore.

| Field | Type | Required | Notes |
|---|---|---|---|
| `concept_code` | string | **yes** | Must be a code the scoring engine reads (§13.9) or it is stored but never scored |
| `value` | number \| boolean \| string \| null | no | Must match `value_type` or → 422 |
| `value_type` | `NUMERIC`\|`CODED`\|`BOOLEAN`\|`TEXT` | **yes** | |
| `unit` | string \| null | no | |
| `source_type` | `DEVICE`\|`NURSE`\|`DOCTOR`\|`PARAMEDIC`\|`PATIENT`\|`HISTORICAL_RECORD`\|`AI_INFERRED` | **yes** | |
| `source_id` | string \| null | no | |
| `reliability_tier` | **integer** 1\|2\|3\|4 | **yes** | 1=machine, 2=clinician, 3=patient-reported, 4=AI. **Send the number, not the name** |
| `measurement_status` | `MEASURED`\|`NOT_MEASURED`\|`UNOBTAINABLE`\|`REFUSED`\|`UNKNOWN`\|`DEVICE_ERROR` | **yes** | Only `MEASURED` is a real reading |
| `observed_at` | ISO-8601 datetime | **yes** | Send naive UTC (`2026-08-29T10:00:00`) — see §12.4 |
| `extraction_confidence` | float 0–1 \| null | conditional | **Required when `source_type === "AI_INFERRED"`**, else 422 |

Type-matching rules enforced by the schema: `NUMERIC` needs a number and **rejects booleans**; `BOOLEAN` needs a true boolean; `TEXT` and `CODED` both need a string.

#### `GET /cases/{case_id}/observations?concept_code=` → **200** `ObservationResponse[]` / **404**
Auth: none. Returns **current (non-superseded)** observations only.

#### `GET /cases/{case_id}/risk-assessments` → **200** `RiskAssessmentResponse[]` / **404**
Auth: none. Full history, chronological — this is the data source for the acuity-over-time chart.

#### `POST /cases/{case_id}/override` → **200** `HumanDecisionResponse` / **400** / **401** / **403** / **404**
Auth: NURSE, DOCTOR or ADMIN.

| Field | Type | Required | Notes |
|---|---|---|---|
| `action` | `ACCEPT`\|`ESCALATE`\|`DE_ESCALATE`\|`MODIFY` | **yes** | **`MODIFY` always → 400.** Do not offer it in the UI |
| `target_acuity` | int \| null | conditional | Optional for ESCALATE (defaults to `current−1`); ignored for ACCEPT; **required for DE_ESCALATE** |
| `reason_code` | `DeEscalationReasonCode` \| null | conditional | **Required for DE_ESCALATE** |
| `free_text_reason` | string \| null | no | |

Verified 400s: `"DE_ESCALATE requires an explicit target_acuity."`, `"DE_ESCALATE requires a structured reason_code (Phase 9.6 asymmetric friction)."`, `"ESCALATE must make the case MORE urgent (a lower acuity number) than the current 1; got 1. …"`, and `"Case {id} has no RiskAssessment yet -- nothing to override."`

#### `GET /cases/{case_id}/decisions` → **200** `HumanDecisionResponse[]` / **404**
Auth: none. The per-case audit trail.

#### `POST /cases/{case_id}/emergency-bypass` → **200** `CaseResponse` / **401** / **403** / **404**
Auth: NURSE/DOCTOR/ADMIN. Body `{"reason": string | null}` — `reason` is **optional** and is never a gate on the action.

#### `POST /cases/{case_id}/reassessment` → **200** `CaseResponse`
Auth: none. No body. Resets the reassessment clock without requiring a new observation.

#### `POST /cases/{case_id}/self-reported-worsening` → **200** `CaseResponse`
Auth: **none, by design.** Body `{"note": string | null}`.

#### `POST /cases/{case_id}/arrival` → **200** `CaseResponse` / **404** / **409**
Auth: none. Body `{"occurred_at": datetime | null}`. **409** if the case is not `PRE_ARRIVAL`.

#### `GET /cases/{case_id}/timeline` → **200** `EventResponse[]` / **404**
Auth: none. Every event for the case. `event_type` is one of 30 verified strings (§13.10) — treat unknown values as displayable-but-unstyled, never crash.

#### `GET /cases/{case_id}/conflicts?include_resolved=false` → **200** `DataConflictResponse[]` / **404**
Auth: none. Open conflicts by default.

#### `POST /cases/{case_id}/assign-resource` → **200** `ResourceResponse` / **404** / **409 capacity conflict**
Auth: none. Body `{"resource_type": "CLINICIAN"|"TREATMENT_SPACE"|"RESUSCITATION_BAY"}`.
Verified 409: `{"detail":"No TREATMENT_SPACE resource is available.","resource_type":"TREATMENT_SPACE","candidate_actions":["Expedite a discharge to free a space","Use an alternative space or resource type","Escalate to the on-call team"]}`

#### `POST /cases/{case_id}/tests` → **201** `DiagnosticTestResponse` / `GET /cases/{case_id}/tests` → **200** `DiagnosticTestResponse[]`
Auth: none. Body `{"test_type": string}` — free text, no enum.

#### `POST /cases/{case_id}/intake` → **200** `IntakeOutcome` / **404**
Auth: none. Body `{"text": string}`. **Always 200, even on failure** — inspect `llm_available` / `parse_succeeded` / `reason`.
Verified with no API key present: `{"llm_available":false,"parse_succeeded":false,"reason":"LLM_UNAVAILABLE","observations_created":[],"rejected":[],"model_version":null}`.
`reason` ∈ `LLM_DISABLED` | `LLM_UNAVAILABLE` | `PARSE_FAILED_AFTER_RETRY` | `null`. Extracted values are written as `AI_INFERRED` / tier 4, which legitimately lowers confidence. **Slow (up to `request_timeout_seconds`, default 20 s)** — show a spinner and do not block the rest of the page.

#### `GET /cases/{case_id}/explanation` → **200** `ExplanationResult` / **404**
Auth: none. **Always returns an explanation** — deterministic template when the LLM is off or ungrounded.
Verified fallback: `{"text":"Assessed as ESI 2. Respiratory rate scored 3 point(s) (26.0breaths/min); …","grounded":true,"fallback_used":true,"fallback_reason":"LLM_UNAVAILABLE","model_version":null,"generated_at":"..."}`
When `fallback_used === true`, label the panel "Rule-based explanation" rather than presenting it as AI output. Fetch this **after** the acuity is already painted (Phase 11.C: "LLM explanation streams in behind the already-displayed level") — never block the acuity render on it.

#### Ambulance: `GET /cases/{id}/eta`, `POST /cases/{id}/ambulance/delay`, `GET /cases/{id}/pre-alert`
Auth: none on all three. `GET /eta` → **404** `"No ambulance transport recorded for case {id}"` for a walk-in or an ambulance case created without `estimated_transport_minutes` — **this 404 is a normal state, not an error**; hide the ETA widget. `POST /ambulance/delay` body `{"additional_minutes": float (required), "reason": string|null}` → `ETARange`. `GET /pre-alert` works for any case.

#### Identity: `POST /cases/{id}/identity/propose` (no auth), `POST /cases/{id}/identity/confirm` (NURSE/DOCTOR/ADMIN)
Propose body: `{"candidate_mrn": string (required), "candidate_display_name": string|null, "confidence": float|null}`. Confirm body: `{"mrn": string (required), "display_name": string|null}`. Both → `CaseResponse`. There is **no candidate-search endpoint** — the UI must accept a typed MRN.

---

### 6.4 Queue

#### `GET /queue?hospital_profile_id=default` → **200** `QueueEntry[]`
Auth: none. **Pre-sorted. Has write side effects. Poll every 3 s.** Contains only `ACTIVE` cases of that profile.

#### `GET /queue/printable?hospital_profile_id=default` → **200** `text/plain`
Auth: none. Fixed-width plain text, no CSS/JS. Verified header: `PATIENTTRIAGE.AI -- PRINTED QUEUE SNAPSHOT (DEGRADED-MODE FALLBACK)`. **Do not parse it.** Open in a new tab, or render in a `<pre>` behind a print stylesheet.

---

### 6.5 Alerts

#### `GET /alerts?hospital_profile_id=default` → **200** `AlertResponse[]`
Auth: none. Side effects on read. Only three `alert_type` values exist; each has a distinct `payload` shape (§13.6). `payload` is `Record<string, unknown>` in the schema — **narrow it by `alert_type`, and guard every field access.**

#### `POST /alerts/{alert_id}/dismiss` → **200** `AlertResponse` / **400** (already dismissed) / **401** / **403** / **404**
Auth: NURSE/DOCTOR/ADMIN. Body `{"reason_code": AlertDismissalReasonCode (required), "free_text_reason": string|null}`. Dismissal always requires a reason.

#### `GET /alerts/budget?hospital_profile_id=default&nurses_on_shift=1.0&window_minutes=60` → **200** `AlertBudgetReport`
Auth: none. `nurses_on_shift` must be `> 0`, `window_minutes` `> 0`, else 422. Verified: `{"window_minutes":60,"nurses_on_shift":2.0,"interruptive_alerts_in_window":1,"alerts_per_nurse_per_hour":0.5,"target_alerts_per_nurse_per_hour":4.0,"within_budget":true,"breakdown_by_type":{"ACUITY_BAND_CROSSED_UPWARD":1}}`. `nurses_on_shift` has no roster to derive from — the UI must expose it as an input.

---

### 6.6 Control Tower, Ops, Resources, Tests

#### `GET /control-tower?hospital_profile_id=default` → **200** `ControlTowerResponse`
Auth: none. Exactly five tiles. Side effects on read (runs the stuck sweep).

#### `GET /ops/stuck-patients?hospital_profile_id=default` → **200** `StuckPatternResult[]`
Auth: none. Three `pattern_id` values: `TEST_ORDERED_NOT_COLLECTED` (route `NURSE_OPS`), `RESULT_NOT_REVIEWED` (`DOCTOR_QUEUE`), `ASSIGNED_SPACE_NOT_OCCUPIED` (`CHARGE_NURSE`). **These are operational, never clinical — render them on a separate list from the queue and never let them affect acuity display.**

#### Resources
- `POST /resources` → **201**. Body `{"resource_type": ResourceType (required), "label": string (required), "hospital_profile_id": string = "default"}`.
- `GET /resources?hospital_profile_id=&resource_type=&status=` → **200** `ResourceResponse[]`.
- `POST /resources/{resource_id}/confirm-occupancy` → **200** / **400** if not currently assigned / **404**.
- `POST /resources/{resource_id}/release` → **200** / **404**.
All unauthenticated. **A fresh database has zero resources** — the frontend needs a resource-setup screen or the capacity tile reads all-zero and every assignment 409s.

#### Diagnostic tests
`POST /tests/{test_id}/sample-collected`, `/result-available`, `/result-reviewed` → **200** `DiagnosticTestResponse` / **404**. No body, no auth. Lifecycle is `ORDERED → SAMPLE_COLLECTED → RESULT_AVAILABLE → RESULT_REVIEWED`.

---

### 6.7 Audit

#### `GET /overrides/flagged-for-review?hospital_profile_id=default` → **200** `HumanDecisionResponse[]`
Auth: NURSE/DOCTOR/ADMIN. Every de-escalation. **Read-only — there is no "mark this review complete" mutation** (§19 🟠-3), so the UI must not render a control that implies one.

#### `GET /overrides/monitoring?hospital_profile_id=default` → **200** `OverrideMonitoringReport`
Auth: **ADMIN only** (verified 403 as NURSE). Includes a mandatory `caveat` string that **must be rendered adjacent to the charts** — it states this is a standing measurement, not a fairness audit.

---

### 6.8 Demo

#### `POST /demo/seed?hospital_profile_id=default` → **200** `DemoScenario[]`
Auth: none. Creates the 20 scripted patients. **Not idempotent** — calling twice creates a second batch. Guard with a confirmation dialog. Each scenario carries `number`, `key`, `title`, `demonstrates`, `case_id`, `fidelity` (`"FULL"|"PARTIAL"`), `note`. **Render `fidelity` honestly** — two of the twenty are `PARTIAL`.

#### `POST /demo/surge?hospital_profile_id=default&baseline_count=10&multiplier=3` → **200** `SurgeSimulationResult`
Auth: none. `baseline_count ≥ 2`, `multiplier > 1`, else 422. Slow. Not idempotent.

#### `GET /health` → **200** `{"status":"ok"}`
Use for the connection indicator.

---

## 7. Frontend Architecture

### 7.1 Stack (follows architecture Phase 15)

| Concern | Choice | Rationale |
|---|---|---|
| Framework | **React 18** | Named in Phase 15 |
| Build | **Vite** | Named in Phase 15 |
| Language | **TypeScript (strict)** | The API has ~20 enums and deeply-shaped responses; strict typing is what prevents field hallucination |
| Styling | **Tailwind CSS** | Named in Phase 15 |
| Routing | **React Router v6** | Six distinct surfaces with URL-addressable cases |
| Server state | **TanStack Query v5** | Polling, cache invalidation, dedupe, loading/error states — the polling model *is* the state model here |
| Client state | **React Context** (auth + hospital profile only) | Everything else is server state. **No Redux/Zustand** |
| Forms | **react-hook-form + zod** | Mirrors the backend's Pydantic constraints client-side; zod schemas double as the parse layer |
| Charts | **Recharts** | Acuity-over-time, equity distributions |
| Icons | **lucide-react** | |
| Testing | **Vitest** + **React Testing Library** + **MSW** | MSW fixtures captured from real backend responses |

**Do not add:** a state-management library beyond the above, a component library that fights Tailwind, a websocket client, a service worker, or an i18n runtime.

### 7.2 Layering

```
pages/         route components — compose features, own no logic
  └── features/    domain feature components (QueueTable, OverrideModal, …)
        └── hooks/     TanStack Query hooks — one per endpoint, the ONLY callers of the api layer
              └── api/     typed fetch functions, one file per backend router
                    └── lib/http.ts   single fetch wrapper: base URL, auth header, error normalisation
```

**Rules:**
- A component never calls `fetch` directly. Ever.
- Every endpoint gets exactly one function in `api/` and one hook in `hooks/`.
- Types in `types/` are hand-mirrored from Section 13 **or** generated from `/openapi.json`; either way they are the only source of shape truth.
- Polling intervals live in one constants file, not scattered in components.

---

## 8. Directory Structure

```
frontend/
├── .env.example
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
├── tailwind.config.js
├── postcss.config.js
└── src/
    ├── main.tsx
    ├── App.tsx                       router + providers
    ├── config.ts                     env access, polling intervals, profile id
    │
    ├── lib/
    │   ├── http.ts                   fetch wrapper, ApiError, auth header injection
    │   ├── datetime.ts               parseBackendUtc / formatClock / formatMinutes  ← MANDATORY
    │   ├── acuity.ts                 acuity → colour/label token map (display only)
    │   ├── enums.ts                  human-readable labels for every backend enum
    │   └── cn.ts                     tailwind class merge helper
    │
    ├── types/
    │   ├── api.ts                    every response/request interface (Section 13)
    │   └── enums.ts                  string-literal unions for all backend enums
    │
    ├── api/
    │   ├── auth.ts        cases.ts        observations.ts   queue.ts
    │   ├── alerts.ts      controlTower.ts ops.ts            resources.ts
    │   ├── tests.ts       conflicts.ts    audit.ts          demo.ts
    │
    ├── hooks/
    │   ├── useAuth.ts                 context consumer
    │   ├── useQueue.ts                polls GET /queue
    │   ├── useCase.ts   useCaseTimeline.ts   useRiskAssessments.ts
    │   ├── useObservations.ts         useAddObservation.ts (mutation)
    │   ├── useOverride.ts             useEmergencyBypass.ts  useMarkReassessed.ts
    │   ├── useDoctorView.ts           useMarkReviewed.ts
    │   ├── usePatientView.ts          useSelfReportWorsening.ts
    │   ├── useAlerts.ts               useDismissAlert.ts     useAlertBudget.ts
    │   ├── useControlTower.ts         useStuckPatients.ts
    │   ├── useResources.ts            useAssignResource.ts
    │   ├── useConflicts.ts            useResolveConflict.ts
    │   ├── useExplanation.ts          useIntake.ts
    │   ├── usePreAlert.ts             useEta.ts
    │   ├── useAudit.ts                useDemo.ts
    │
    ├── contexts/
    │   ├── AuthContext.tsx            token, user, login, logout; localStorage sync
    │   └── ProfileContext.tsx         hospital_profile_id (single value, "default")
    │
    ├── components/                   presentational, domain-agnostic
    │   ├── layout/    AppShell.tsx  Header.tsx  RoleSwitcher.tsx  NavRail.tsx
    │   ├── ui/        Button Badge Card Modal Table Toast Spinner Tooltip
    │   │              Skeleton EmptyState ErrorState ConfirmDialog Select Input
    │   ├── clinical/  AcuityBadge ConfidenceBadge AttentionFlagChip
    │   │              WaitTimeRange StalenessDot TrendArrow VitalValue
    │   └── feedback/  LoadingBoundary QueryBoundary ConnectionBanner
    │
    ├── features/
    │   ├── auth/         RoleSelector.tsx
    │   ├── queue/        QueueTable QueueRow QueueRowActions QueueLegend
    │   ├── case/         CaseHeader CaseSummaryCard VitalsPanel RecordVitalsForm
    │   │                 RiskAssessmentPanel ComponentBreakdownTable
    │   │                 ExplanationPanel ConfidencePanel AcuityHistoryChart
    │   │                 TimelineList DecisionHistoryList ConflictList
    │   │                 OverrideControls DeEscalateModal EmergencyBypassButton
    │   │                 AssignResourcePanel CapacityConflictPanel
    │   │                 DiagnosticTestsPanel IntakeTextPanel
    │   ├── registration/ RegisterCaseForm
    │   ├── doctor/       DoctorCaseList DoctorCaseView ChangedSincePanel
    │   │                 TrendsPanel PendingActionsList
    │   ├── controltower/ ControlTower AcuityBandTile DeterioratingTile
    │   │                 StuckPatientsTile CapacityTile IncomingAmbulancesTile
    │   ├── alerts/       AlertFeed AlertCard DismissAlertModal AlertBudgetMeter
    │   ├── patient/      PatientStatusView FeelWorseButton
    │   ├── ambulance/    AmbulanceIntakeForm PreAlertCard EtaRange
    │   │                 IdentityMatchPanel TransportDelayForm
    │   ├── admin/        FlaggedReviewQueue OverrideMonitoringReport EquityCharts
    │   ├── ops/          StuckPatientList ResourceManager
    │   └── demo/         DemoConsole ScenarioList SurgeRunner SurgeResultPanel
    │
    └── pages/
        ├── LoginPage.tsx              /login
        ├── QueuePage.tsx              /queue
        ├── RegisterPage.tsx           /register
        ├── CaseDetailPage.tsx         /cases/:caseId
        ├── DoctorListPage.tsx         /doctor
        ├── DoctorCasePage.tsx         /doctor/:caseId
        ├── ControlTowerPage.tsx       /control-tower
        ├── OpsPage.tsx                /ops
        ├── AlertsPage.tsx             /alerts
        ├── AmbulancePage.tsx          /ambulance
        ├── AmbulanceCasePage.tsx      /ambulance/:caseId
        ├── PatientPage.tsx            /patient/:caseId       (public, no shell)
        ├── AdminPage.tsx              /admin
        ├── DemoPage.tsx               /demo
        └── NotFoundPage.tsx
```

---

## 9. Pages and Screens

| Route | Page | Auth gate | Polling | Backend endpoints |
|---|---|---|---|---|
| `/login` | Role selector | public | — | `POST /auth/login`, `GET /health` |
| `/queue` | **Nurse Guardian Queue** (primary) | authenticated | 3 s | `GET /queue`, `GET /alerts` (badge) |
| `/register` | Walk-in registration | authenticated | — | `POST /cases` |
| `/cases/:caseId` | Case detail / workspace | authenticated | 5 s | `GET /cases/{id}`, `/observations`, `/risk-assessments`, `/timeline`, `/decisions`, `/conflicts`, `/tests`, `/explanation`; POSTs for observations, override, bypass, reassessment, assign-resource, tests, intake |
| `/doctor` | Doctor case list | authenticated | 5 s | `GET /cases?status=ACTIVE` |
| `/doctor/:caseId` | Doctor view | authenticated | 5 s | `GET /cases/{id}/doctor-view`, `POST /cases/{id}/mark-reviewed` |
| `/control-tower` | Five-tile control tower | authenticated | 5 s | `GET /control-tower`, `GET /alerts/budget` |
| `/ops` | Stuck patients + resource registry | authenticated | 10 s | `GET /ops/stuck-patients`, `GET/POST /resources`, `POST /resources/{id}/*`, `POST /tests/{id}/*` |
| `/alerts` | Alert feed + budget meter | authenticated | 3 s | `GET /alerts`, `POST /alerts/{id}/dismiss`, `GET /alerts/budget` |
| `/ambulance` | Pre-arrival board | authenticated | 5 s | `GET /cases?status=PRE_ARRIVAL`, `POST /cases` |
| `/ambulance/:caseId` | Pre-alert + ETA + identity | authenticated | 3 s | `GET /cases/{id}/pre-alert`, `/eta`; `POST /ambulance/delay`, `/identity/propose`, `/identity/confirm`, `/arrival`, `/observations` |
| `/patient/:caseId` | **Patient status (public)** | **public, no app shell** | 10 s | `GET /cases/{id}/patient-view`, `POST /cases/{id}/self-reported-worsening` |
| `/admin` | Retrospective review + equity | **ADMIN** for monitoring | 30 s | `GET /overrides/flagged-for-review`, `GET /overrides/monitoring` |
| `/demo` | Demo console | authenticated | — | `POST /demo/seed`, `POST /demo/surge`, `GET /queue/printable` |

### 9.1 Nurse Guardian Queue — the screen that matters most

Phase 8.2 specifies **four persistent columns**. Implement exactly these, plus identity and actions:

| Column | Source field(s) | Rendering |
|---|---|---|
| Patient | `display_name`, `mrn` | Name, MRN muted below. `display_name: null` → "Unidentified" |
| **Acuity + confidence** | `final_acuity`, `confidence_band`, `should_abstain` | Large colour-banded ESI badge; confidence as a **band word** (High/Medium/Low), never a percentage. `should_abstain: true` → an "Awaiting nurse assessment" chip |
| **One-line presentation** | `one_line_presentation` | Truncate with a tooltip. `null` → muted "No presenting complaint recorded" |
| **Time in band vs target** | `waiting_minutes`, `reassessment.{interval_minutes, minutes_since_last_reassessment, is_due, minutes_overdue}` | `"18m waiting · 3m over 15m target"`. When `is_due`, the cell turns amber and shows `minutes_overdue`. `interval_minutes: null` → "no target" |
| **Primary attention flag** | `primary_attention_flag` | One chip only. `DETERIORATING` (red) / `REASSESSMENT_OVERDUE` (amber) / `UNKNOWN_VITALS` (slate) / `DATA_CONFLICT` (violet) / `NONE` (render nothing) |
| Actions | — | **Escalate** (one tap, no dialog, disabled at ESI 1) · **Mark reassessed** (one tap) · **Record vitals** (drawer) · **Open case** |

Additional row treatments:
- `emergency_bypass_active: true` → the row gets a persistent red left border and a "BYPASS" chip; sort position is untouched (the backend already ordered it).
- `deterioration_trend` → a small ↑ arrow for `WORSENING`; nothing for `STABLE`/`UNKNOWN`; ↓ for `IMPROVING`. **Never a colour that competes with acuity.**
- `wait_time_estimate` → render as `"~15–35 min"` with the `caveat` in a tooltip. **Never a single number.**
- **Never re-sort.** Array order is the clinical answer.

### 9.2 Patient view — the constrained screen

Single column, large type, at most four elements, in this order (Phase 8.1 hierarchy):
1. **Where you are** — `stage` rendered as a 4-step progress indicator (`PRE_ARRIVAL → WAITING → IN_TREATMENT → DISPOSED`).
2. **Estimated wait window** — `wait_time_estimate.lower_minutes`–`upper_minutes` as a range, with `caveat` shown as body text, **not** hidden in a tooltip. Omit the whole block when `wait_time_estimate` is `null`.
3. **What happens next** — `next_step_message` verbatim.
4. **"I feel worse" button** — full-width, large, single tap, no confirmation.

**Forbidden on this route:** any acuity number, any confidence band, any queue position, any other patient, any clinical term, and any call to an endpoint that returns acuity. Enforce this with a lint rule or a code-review checklist item — the API cannot enforce it if the frontend fetches `GET /cases/{id}` on this page.

---

## 10. Component Architecture

### 10.1 Shared clinical primitives (build these first — Checkpoint 2)

**`<AcuityBadge acuity={1..5} size abstaining? />`** — the single source of acuity colour in the app.

| ESI | Meaning | Suggested token |
|---|---|---|
| 1 | Immediate / resuscitation | red-600 on red-50, white text at `lg` |
| 2 | Emergent | orange-600 |
| 3 | Urgent | amber-500 |
| 4 | Less urgent | sky-600 |
| 5 | Non-urgent | slate-500 |

Colours must satisfy WCAG AA (4.5:1) and **must never be the only carrier of meaning** — always pair with the numeral and a text label.

**`<ConfidenceBadge band reasons />`** — `HIGH`/`MEDIUM`/`LOW` word + an info affordance listing `confidence_reasons[]` verbatim. **Never renders `confidence_score`.**

**`<AttentionFlagChip flag />`** — maps the 5 `NurseAttentionFlag` values; renders `null` for `NONE`.

**`<WaitTimeRange estimate />`** — `"~{lower}–{upper} min"`, `basis` as a subtle qualifier (`CONFIGURED_DEFAULT` → "estimate only"), `caveat` always reachable. **Refuses to render a single number** — if `lower === upper`, still show a range.

**`<StalenessDot observedAt conceptCode />`** — the profile defines `staleness_windows_minutes` per concept, but **that config is not exposed by any API endpoint** (§19 🟡-4). Instead, drive staleness from what the backend already tells you: a `rule_component_breakdown` entry with `is_missing: true` and `missing_reason: "STALE"`. Always render the absolute observation age next to every vital (Phase 9.4: "every displayed value carries its age").

**`<TrendArrow direction />`**, **`<VitalValue observation />`** (value + unit + source-type icon + reliability tier indicator + age).

### 10.2 Feature component contracts

- `QueueTable` receives `QueueEntry[]` and renders in given order. It owns no fetching.
- `RecordVitalsForm` posts observations **sequentially**, reports per-field success/failure, and never blocks the whole form on one 422.
- `OverrideControls` renders Accept / Escalate / De-escalate; Escalate fires immediately; De-escalate opens `DeEscalateModal`.
- `CapacityConflictPanel` is rendered by the 409 handler of `useAssignResource`, not by a generic error toast.
- `ExplanationPanel` is always mounted after the assessment renders, has its own independent loading state, and labels `fallback_used` output as rule-based.
- `ChangedSincePanel` groups `changed_since_last_review[]` by `event_type` with human labels from `lib/enums.ts`.

---

## 11. State Management

### 11.1 Three tiers

1. **Server state → TanStack Query.** Everything from the API. No copying into local state.
2. **Session state → React Context.** `AuthContext` (token, user) and `ProfileContext` (`hospital_profile_id`). Nothing else.
3. **UI state → `useState` locally.** Modals, drawers, form drafts, expanded rows.

### 11.2 Query keys

```ts
['health']
['queue', profileId]
['alerts', profileId]
['alert-budget', profileId, nursesOnShift, windowMinutes]
['control-tower', profileId]
['stuck-patients', profileId]
['resources', profileId, resourceType, status]
['cases', { status }]
['case', caseId]
['case-observations', caseId, conceptCode]
['case-risk-assessments', caseId]
['case-timeline', caseId]
['case-decisions', caseId]
['case-conflicts', caseId, includeResolved]
['case-tests', caseId]
['case-explanation', caseId]
['doctor-view', caseId, userId]     // identity-relative — userId MUST be in the key
['patient-view', caseId]
['pre-alert', caseId]
['eta', caseId]
['flagged-for-review', profileId]
['override-monitoring', profileId]
```

### 11.3 Polling intervals (`src/config.ts`)

```ts
export const POLL = {
  QUEUE: 3000,          // architecture-sanctioned 3s
  ALERTS: 3000,
  CASE: 5000,
  DOCTOR_VIEW: 5000,
  CONTROL_TOWER: 5000,
  ETA: 3000,            // must visibly narrow during the demo
  PRE_ALERT: 5000,
  OPS: 10000,
  PATIENT_VIEW: 10000,  // calm surface — do not flicker
  ADMIN: 30000,
  HEALTH: 15000,
} as const;
```

**Pause polling when `document.hidden`** (TanStack `refetchIntervalInBackground: false`) — these GETs mutate server state, so background tabs would keep sweeping the department.

### 11.4 Invalidation matrix

| Mutation | Invalidate |
|---|---|
| `POST /cases` | `['cases']`, `['queue']`, `['control-tower']` |
| `POST /cases/{id}/observations` | `['case',id]`, `['case-observations',id]`, `['case-risk-assessments',id]`, `['case-timeline',id]`, `['case-explanation',id]`, `['queue']`, `['alerts']`, `['control-tower']` |
| `POST /cases/{id}/override` | `['case',id]`, `['case-decisions',id]`, `['case-risk-assessments',id]`, `['case-timeline',id]`, `['queue']`, `['flagged-for-review']`, `['override-monitoring']` |
| `POST /cases/{id}/emergency-bypass` | `['case',id]`, `['queue']`, `['alerts']`, `['control-tower']` |
| `POST /cases/{id}/reassessment` | `['case',id]`, `['queue']` |
| `POST /cases/{id}/self-reported-worsening` | `['patient-view',id]`, `['case',id]`, `['queue']` |
| `POST /cases/{id}/arrival` | `['case',id]`, `['cases']`, `['queue']`, `['control-tower']`, `['pre-alert',id]` |
| `POST /cases/{id}/assign-resource` | `['case',id]`, `['resources']`, `['control-tower']`, `['queue']` (wait estimates shift), `['patient-view',id]` (stage → IN_TREATMENT) |
| `POST /alerts/{id}/dismiss` | `['alerts']`, `['alert-budget']` |
| `POST /conflicts/{id}/resolve` | `['case-conflicts',caseId]`, `['case',caseId]`, `['queue']` |
| `POST /cases/{id}/mark-reviewed` | `['doctor-view',id,userId]`, `['case',id]` |
| `POST /cases/{id}/tests` and `/tests/{id}/*` | `['case-tests',caseId]`, `['stuck-patients']`, `['doctor-view']` |
| `POST /cases/{id}/intake` | same set as observations |
| `POST /demo/seed` \| `/demo/surge` | **invalidate everything** (`queryClient.invalidateQueries()`) |

### 11.5 Optimistic updates

**Only two mutations may be optimistic:** alert dismissal (remove the card) and mark-reassessed (clear the overdue chip). **Never optimistically change an acuity, a confidence band, or a queue position** — those are backend computations and a wrong guess is a clinical misrepresentation.

---

## 12. API Integration Layer

### 12.1 `src/config.ts`

```ts
export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';
export const HOSPITAL_PROFILE_ID =
  import.meta.env.VITE_HOSPITAL_PROFILE_ID ?? 'default';
```
No URL is ever hardcoded in a component or an `api/` module.

### 12.2 `src/lib/http.ts` — the single fetch wrapper

Responsibilities, in order:
1. Prefix `API_BASE_URL`; serialise query params, **omitting `undefined`/`null`**.
2. Attach `Authorization: Bearer <token>` when the caller requests it (token read from the auth store, not passed through every call site).
3. Set `Content-Type: application/json` on requests with a body.
4. On non-2xx, throw a typed `ApiError`:

```ts
export class ApiError extends Error {
  status: number;
  detail: string | ValidationIssue[];   // string for 400/401/403/404/409, array for 422
  raw: unknown;                          // full body — 409 capacity conflict needs resource_type + candidate_actions
  isValidationError(): boolean;          // status === 422 && Array.isArray(detail)
  isCapacityConflict(): boolean;         // status === 409 && raw.candidate_actions is an array
  displayMessage(): string;              // strips the 404 repr quotes; joins 422 msgs
}
```
5. On 401, clear auth state and emit a `session-expired` event the router listens for.
6. Parse `text/plain` responses as text (for `/queue/printable`), everything else as JSON.
7. Handle a 200 with an empty body defensively — return `null` rather than throwing a JSON parse error.

### 12.3 One function per endpoint

Example (`src/api/cases.ts`):
```ts
export const createCase = (body: CaseCreateRequest) =>
  http.post<CaseResponse>('/cases', body);

export const getCase = (caseId: string) =>
  http.get<CaseDetailResponse>(`/cases/${caseId}`);

export const addObservation = (caseId: string, body: ObservationCreateRequest) =>
  http.post<ObservationResponse>(`/cases/${caseId}/observations`, body);

export const overrideCase = (caseId: string, body: OverrideRequest) =>
  http.post<HumanDecisionResponse>(`/cases/${caseId}/override`, body, { auth: true });
```

### 12.4 `src/lib/datetime.ts` — **MANDATORY, build in Checkpoint 1**

The backend emits **naive UTC datetimes with no `Z` and no offset** (verified: `"2026-08-28T18:48:46.312764"`). JavaScript parses these as *local* time. Without this helper every clock in the UI is silently wrong by the local UTC offset.

```ts
/** Every datetime string from this backend is naive UTC. Append Z before parsing. */
export function parseBackendUtc(s: string): Date {
  return new Date(/[Zz]|[+-]\d{2}:\d{2}$/.test(s) ? s : `${s}Z`);
}

/** Serialise for a request body. The backend accepts naive UTC. */
export function toBackendUtc(d: Date): string {
  return d.toISOString().replace(/\.\d{3}Z$/, '');
}
```

**Rule: no component may call `new Date(apiString)` directly.** Every parse goes through `parseBackendUtc`. Add an ESLint `no-restricted-syntax` rule for `new Date(` with a non-numeric argument if practical.

Also provide `formatClock(date)` (HH:mm), `formatRelative(date)` ("3 min ago"), and `formatMinutes(n)` (`18.4 → "18m"`, `95 → "1h 35m"`) — the API returns **fractional minutes** everywhere (`waiting_minutes: 0.00208`), so raw values must never be printed.

---

## 13. Data Types / Interfaces

All shapes below are copied from the Pydantic schemas and confirmed against live JSON. `?` marks a nullable/optional field.

### 13.1 `CaseResponse` / `CaseDetailResponse`
```ts
interface CaseResponse {
  case_id: string;
  hospital_profile_id: string;
  mrn: string | null;
  display_name: string | null;
  date_of_birth: string | null;      // YYYY-MM-DD
  age_years: number | null;
  sex: string | null;                // free string, no enum
  arrival_mode: 'WALK_IN' | 'AMBULANCE';
  status: 'PRE_ARRIVAL' | 'ACTIVE' | 'DISPOSED';
  identity_link_status: 'UNLINKED' | 'CANDIDATE_PROPOSED' | 'CONFIRMED';
  created_at: string;                // naive UTC
  arrived_at: string | null;
  emergency_bypass_active: boolean;
  emergency_bypass_first_activated_at: string | null;
  emergency_bypass_last_activated_at: string | null;
  emergency_bypass_last_reason: string | null;
  emergency_bypass_last_source: 'HUMAN' | 'PHYSIOLOGICAL' | 'TEXT_PATTERN' | null;
  emergency_bypass_last_trigger_id: string | null;
  last_reassessed_at: string | null;
  reassessment_overdue: boolean;
  reassessment_overdue_since: string | null;
}

interface CaseDetailResponse extends CaseResponse {
  current_observations: ObservationResponse[];
  latest_risk_assessment: RiskAssessmentResponse | null;
  wait_time_estimate: WaitTimeEstimate | null;
}
```

### 13.2 `ObservationResponse`
```ts
interface ObservationResponse {
  observation_id: string;
  case_id: string;
  concept_code: string;
  value_type: 'NUMERIC' | 'CODED' | 'BOOLEAN' | 'TEXT';
  value: number | boolean | string | null;   // NUMERIC comes back as a float: 26 → 26.0
  unit: string | null;
  source_type: 'DEVICE'|'NURSE'|'DOCTOR'|'PARAMEDIC'|'PATIENT'|'HISTORICAL_RECORD'|'AI_INFERRED';
  source_id: string | null;
  reliability_tier: 1 | 2 | 3 | 4;           // INTEGER, not a string
  measurement_status: 'MEASURED'|'NOT_MEASURED'|'UNOBTAINABLE'|'REFUSED'|'UNKNOWN'|'DEVICE_ERROR';
  observed_at: string;
  recorded_at: string;
  extraction_confidence: number | null;
  superseded_by: string | null;
  is_current: boolean;
}
```

### 13.3 `RiskAssessmentResponse`
```ts
interface RiskAssessmentResponse {
  assessment_id: string;
  case_id: string;
  computed_at: string;
  rule_engine_version: string;               // e.g. "rules-v1"
  rule_acuity: number;                       // 1..5
  rule_component_breakdown: ScoreComponent[];
  ml_model_version: string | null;           // e.g. "ml-challenger-v1"
  ml_probability: number | null;
  ml_suggested_acuity: number | null;
  hard_triggers_fired: HardTriggerResult[];
  final_acuity: number;                      // 1..5 — THE authoritative acuity
  deciding_layer: 'RULES' | 'ML' | 'OVERRIDE' | 'ABSTENTION';
  confidence_band: 'HIGH' | 'MEDIUM' | 'LOW';
  confidence_score: number;                  // 0-100 — technical detail only
  confidence_reasons: string[];              // plain-language, SHOW THESE
  should_abstain: boolean;
  abstention_message: string | null;
  input_snapshot_hash: string;
  input_observation_ids: string[];
}

interface ScoreComponent {                   // element of rule_component_breakdown
  concept_code: string;
  label: string;                             // human label, e.g. "Oxygen saturation (SpO2)"
  raw_value: number | boolean | string | null;
  unit: string | null;
  points: number | null;                     // null = excluded (missing/stale), NOT zero
  is_missing: boolean;
  missing_reason: string | null;             // "NO_OBSERVATION_RECORDED" | "NOT_MEASURED" | "STALE" | …
  observation_id: string | null;
  observed_at: string | null;
  reliability_tier: 1|2|3|4 | null;
}

interface HardTriggerResult {                // element of hard_triggers_fired
  trigger_id: string;                        // e.g. "CRITICAL_HYPOXIA"
  label: string;                             // e.g. "Critical hypoxia (SpO2 <= 85%)"
  concept_code: string;
  raw_value: number | boolean | string | null;
  target_esi_level: number;
}
```
**Rendering note:** the ML-refusal moment (demo patient #20) is exactly `ml_suggested_acuity > final_acuity && deciding_layer === 'RULES'`. Render this as an explicit callout: *"ML suggested ESI {ml_suggested_acuity}; the min() invariant held the level at ESI {final_acuity}."*

### 13.4 `QueueEntry`
```ts
interface QueueEntry {
  case_id: string;
  display_name: string | null;
  mrn: string | null;
  final_acuity: number;
  confidence_band: 'HIGH'|'MEDIUM'|'LOW' | null;
  should_abstain: boolean;
  time_critical_pathway_flag: boolean;       // ALWAYS false — no pathway engine exists. Do not build UI for it
  deterioration_trend: 'WORSENING'|'STABLE'|'IMPROVING'|'UNKNOWN';
  time_in_current_band_minutes: number | null;
  arrival_time: string;
  waiting_minutes: number;                   // fractional
  reassessment: {
    is_due: boolean;
    interval_minutes: number | null;
    minutes_since_last_reassessment: number;
    minutes_overdue: number | null;          // only when is_due
  };
  emergency_bypass_active: boolean;
  wait_time_estimate: WaitTimeEstimate;      // NOT nullable on a queue entry
  one_line_presentation: string | null;
  primary_attention_flag: 'DETERIORATING'|'REASSESSMENT_OVERDUE'|'UNKNOWN_VITALS'|'DATA_CONFLICT'|'NONE';
}
```

### 13.5 `WaitTimeEstimate`
```ts
interface WaitTimeEstimate {
  lower_minutes: number;
  upper_minutes: number;
  patients_ahead: number;
  available_capacity: number;
  basis: 'BAND_HISTORY' | 'GLOBAL_HISTORY' | 'CONFIGURED_DEFAULT';
  sample_size: number;
  caveat: string;                            // MUST be displayed
}
```

### 13.6 `AlertResponse` and its three payload shapes
```ts
interface AlertResponse {
  alert_id: string;
  hospital_profile_id: string;
  alert_type: 'CRITICAL_BYPASS_PATIENT' | 'ACUITY_BAND_CROSSED_UPWARD' | 'REASSESSMENT_OVERDUE_AGGREGATE';
  created_at: string;
  payload: Record<string, unknown>;          // narrow by alert_type below
  dismissed: boolean;
  dismissed_at: string | null;
  dismissed_by: string | null;               // user_id, or "SYSTEM" for auto-resolution
  dismissal_reason_code: AlertDismissalReasonCode | null;
  dismissal_free_text: string | null;
}

// CRITICAL_BYPASS_PATIENT
{ case_id: string; source: 'HUMAN'|'PHYSIOLOGICAL'|'TEXT_PATTERN'|null; reason: string|null }
// ACUITY_BAND_CROSSED_UPWARD
{ case_id: string; from_acuity: number; to_acuity: number; assessment_id: string }
// REASSESSMENT_OVERDUE_AGGREGATE
{ case_ids: string[]; count: number }
```

### 13.7 Dashboard shapes
```ts
interface ControlTowerResponse {
  patients_by_acuity_band: { acuity: number; case_count: number; overdue_count: number }[];
  deteriorating_patients: { case_id: string; display_name: string|null; from_acuity: number; to_acuity: number }[];
  stuck_patients: StuckPatternResult[];
  capacity: { resource_type: string; available: number; occupied: number; out_of_service: number; needed_estimate: number }[];
  incoming_ambulances: { case_id: string; display_name: string|null; predicted_acuity: number|null }[];
}

interface StuckPatternResult {
  pattern_id: 'TEST_ORDERED_NOT_COLLECTED' | 'RESULT_NOT_REVIEWED' | 'ASSIGNED_SPACE_NOT_OCCUPIED';
  label: string; case_id: string; minutes_overdue: number;
  route_to: 'NURSE_OPS' | 'DOCTOR_QUEUE' | 'CHARGE_NURSE';
}

interface DoctorCaseView {
  case_id: string; display_name: string | null;
  current_observations: ObservationResponse[];
  latest_risk_assessment: RiskAssessmentResponse | null;
  trends: { concept_code: string; previous_value: unknown; previous_observed_at: string;
            current_value: unknown; current_observed_at: string; delta: number | null }[];
  is_first_review: boolean;
  last_reviewed_at: string | null;
  changed_since_last_review: EventResponse[];
  pending_actions: { kind: 'RESULT_AWAITING_REVIEW' | 'UNRESOLVED_DATA_CONFLICT';
                     description: string; reference_id: string }[];
}

interface PatientCaseView {
  case_id: string; display_name: string | null;
  stage: 'PRE_ARRIVAL' | 'WAITING' | 'IN_TREATMENT' | 'DISPOSED';
  next_step_message: string;
  wait_time_estimate: WaitTimeEstimate | null;
}
```

### 13.8 Remaining shapes
```ts
interface EventResponse { event_id: string; case_id: string|null; event_type: string;
                          payload: Record<string, unknown>; occurred_at: string; recorded_at: string; }

interface HumanDecisionResponse { decision_id: string; case_id: string; clinician_id: string; role: string;
  timestamp: string; system_recommendation: number;
  clinician_action: 'ACCEPT'|'ESCALATE'|'DE_ESCALATE'|'MODIFY';
  resulting_acuity: number; reason_code: DeEscalationReasonCode|null;
  free_text_reason: string|null; linked_assessment_id: string; flagged_for_review: boolean; }

interface ResourceResponse { resource_id: string; hospital_profile_id: string;
  resource_type: 'CLINICIAN'|'TREATMENT_SPACE'|'RESUSCITATION_BAY'; label: string;
  status: 'AVAILABLE'|'OCCUPIED'|'OUT_OF_SERVICE';
  assigned_case_id: string|null; assigned_at: string|null; occupancy_stuck_flagged: boolean; }

interface CapacityConflictResponse { detail: string; resource_type: ResourceType; candidate_actions: string[] }

interface DiagnosticTestResponse { test_id: string; case_id: string; test_type: string;
  status: 'ORDERED'|'SAMPLE_COLLECTED'|'RESULT_AVAILABLE'|'RESULT_REVIEWED';
  ordered_at: string; sample_collected_at: string|null; result_available_at: string|null;
  result_reviewed_at: string|null; stuck_flagged: boolean; }

interface DataConflictResponse { conflict_id: string; case_id: string; concept_code: string;
  observation_ids: string[]; conservative_observation_id: string; detected_at: string;
  resolved: boolean; resolved_at: string|null; resolved_by: string|null;
  kept_observation_id: string|null; resolution_note: string|null; }

interface ETARange { lower_minutes: number; upper_minutes: number; arrived: boolean;
                     delayed_additional_minutes: number; caveat: string; }

interface PreAlertView { case_id: string; predicted_acuity_band: number|null;
  one_line_presentation: string|null;
  key_abnormal_vitals: { concept_code: string; label: string; raw_value: unknown;
                         unit: string|null; observed_at: unknown; points: number }[];
  interventions_already_performed: string[];   // ALWAYS [] — no intervention model exists. Render "not recorded"
  eta_range: ETARange | null;
  what_hospital_should_prepare: string; }

interface ExplanationResult { text: string; grounded: boolean; fallback_used: boolean;
  fallback_reason: string|null; model_version: string|null; generated_at: string; }

interface IntakeOutcome { llm_available: boolean; parse_succeeded: boolean; reason: string|null;
  observations_created: string[]; rejected: { concept_code: string; reason: string }[];
  model_version: string|null; }

interface AlertBudgetReport { window_minutes: number; nurses_on_shift: number;
  interruptive_alerts_in_window: number; alerts_per_nurse_per_hour: number;
  target_alerts_per_nurse_per_hour: number|null; within_budget: boolean|null;
  breakdown_by_type: Record<string, number>; }

interface OverrideMonitoringReport { total_cases: number; total_decisions: number;
  action_counts: Record<string, number>;
  overall_override_rate: number|null; overall_de_escalation_rate: number|null;
  flagged_for_review_count: number;
  by_age_band: SubgroupStats[]; by_sex: SubgroupStats[];
  caveat: string; }                              // MUST be rendered with the charts

interface SubgroupStats { subgroup: string; case_count: number;
  acuity_distribution: Record<string, number>;   // JSON object keys are strings: {"2": 3}
  decision_count: number; escalate_count: number; de_escalate_count: number;
  override_rate: number|null; }

interface DemoScenario { number: number; key: string; title: string; demonstrates: string;
  case_id: string; fidelity: 'FULL'|'PARTIAL'; note: string|null; }

interface SurgeSimulationResult { baseline_count: number; surge_count: number; total_cases: number;
  queue_length_before: number; queue_length_after: number; acuity_ordering_holds: boolean;
  reassessment_overdue_count: number; alerts_before: number; alerts_after: number;
  volume_multiplier: number; alert_multiplier_actual: number|null;
  alert_growth_held_below_volume_growth: boolean|null;
  capacity_conflict_demonstrated: boolean; capacity_conflict_detail: Record<string,unknown>|null;
  stuck_patient_count: number; escalated_case_id: string|null;
  escalated_from_acuity: number|null; escalated_to_acuity: number|null;
  escalated_jumped_newer_arrivals_count: number; narrative: string[]; }
```

### 13.9 Concept codes (`app/scoring/concepts.py`)

**Scored by NEWS2/PEWS** — these are what the vitals form must capture:

| `concept_code` | `value_type` | Unit | Allowed values |
|---|---|---|---|
| `RESP_RATE` | NUMERIC | breaths/min | |
| `SPO2` | NUMERIC | % | |
| `SUPPLEMENTAL_OXYGEN` | BOOLEAN | — | true/false |
| `SYSTOLIC_BP` | NUMERIC | mmHg | |
| `HEART_RATE` | NUMERIC | bpm | |
| `CONSCIOUSNESS_LEVEL` | CODED | — | `ALERT`, `NEW_CONFUSION`, `VOICE`, `PAIN`, `UNRESPONSIVE` |
| `TEMPERATURE` | NUMERIC | °C | |
| `WORK_OF_BREATHING` | CODED | — | `NORMAL`, `MILD`, `MODERATE`, `SEVERE` — **paediatric only** |
| `SYMPTOM_TEXT` | TEXT | — | Free text; scanned by the critical-phrase bypass detector |

**Read by the ML challenger only** (not scored by the rules): `SYMPTOM_ONSET_MINUTES` (NUMERIC), `HISTORY_CARDIAC`, `HISTORY_RESPIRATORY`, `HISTORY_DIABETES`, `SYMPTOM_CHEST_PAIN`, `SYMPTOM_BREATHLESSNESS`, `SYMPTOM_ALTERED_CONSCIOUSNESS` (all BOOLEAN).

**Note:** `SYMPTOM_TEXT` is what populates `one_line_presentation` on the queue. A case with no `SYMPTOM_TEXT` observation shows `null` there.

### 13.10 Event types (30 verified values)
`CASE_CREATED`, `PATIENT_ARRIVED`, `OBSERVATION_RECORDED`, `OBSERVATION_SUPERSEDED`, `RISK_ASSESSMENT_COMPUTED`, `HARD_TRIGGER_FIRED`, `EMERGENCY_BYPASS_ACTIVATED`, `REASSESSMENT_DUE`, `REASSESSMENT_COMPLETED`, `PATIENT_SELF_REPORTED_WORSENING`, `HUMAN_DECISION_RECORDED`, `IDENTITY_MATCH_PROPOSED`, `IDENTITY_MATCH_CONFIRMED`, `RESOURCE_ASSIGNED`, `RESOURCE_RELEASED`, `PATIENT_IN_SPACE`, `CAPACITY_CONFLICT_RAISED`, `TEST_ORDERED`, `SAMPLE_COLLECTED`, `RESULT_AVAILABLE`, `RESULT_REVIEWED`, `STUCK_PATIENT_DETECTED`, `DATA_CONFLICT_DETECTED`, `DATA_CONFLICT_RESOLVED`, `ALERT_RAISED`, `ALERT_DISMISSED`, `AMBULANCE_TRANSPORT_STARTED`, `AMBULANCE_TRANSPORT_DELAYED`, `AI_UNAVAILABLE`, plus any future value.
**Always render an unrecognised `event_type` as a plain row rather than crashing.**

### 13.11 Enum reference
```ts
type Role = 'NURSE' | 'DOCTOR' | 'ADMIN';
type DeEscalationReasonCode =
  | 'PATIENT_STABLE_ON_CLINICAL_REVIEW' | 'VITALS_IMPROVED_SINCE_ASSESSMENT'
  | 'SYMPTOM_RESOLVED' | 'INITIAL_ESCALATION_WAS_ERRONEOUS' | 'OTHER_CLINICAL_JUDGEMENT';
type AlertDismissalReasonCode =
  | 'ALREADY_ACTIONED' | 'NOT_ACTIONABLE_RIGHT_NOW' | 'FALSE_POSITIVE'
  | 'DUPLICATE' | 'RESOLVED_AUTOMATICALLY' | 'OTHER';
```
**`RESOLVED_AUTOMATICALLY` is written by the system, not by a human — exclude it from the dismissal dropdown** but handle it when reading an already-dismissed alert.

---

## 14. Forms and Validation

Mirror the backend's constraints with zod so the user gets inline feedback, but **treat the server as the authority** — always render the server's 422/400 alongside.

### 14.1 Register case (`POST /cases`)
- All fields optional at the API level. **The UI should still strongly encourage `age_years`** with an inline warning: *"Without an age the system cannot select a scoring framework and will hold this case at a safer level pending assessment."* That is literally what the backend does (`unknown_age_default_esi_level: 3`).
- `age_years`: integer, 0–130.
- `date_of_birth`: `YYYY-MM-DD`, not in the future.
- `arrival_mode: AMBULANCE` → reveal `estimated_transport_minutes` (positive number). For `WALK_IN`, do not send the field.

### 14.2 Record vitals (`POST /cases/{id}/observations` × N)
- Render one control per concept in §13.9, typed to its `value_type`.
- **`reliability_tier` and `source_type` should be set from a single "Who/what recorded this?" selector**, not two raw dropdowns: Device → `DEVICE`/1 · Nurse → `NURSE`/2 · Patient reported → `PATIENT`/3. Never let the UI send `AI_INFERRED` (that path belongs to the intake engine).
- `measurement_status` defaults to `MEASURED`; offer `UNOBTAINABLE`/`REFUSED`/`DEVICE_ERROR` explicitly. **Selecting a non-MEASURED status must still submit the observation** — recorded missingness is clinically meaningful and lowers confidence, which is the correct behaviour.
- `observed_at` defaults to now; allow back-dating.
- Client-side range hints (**advisory only — the backend does not range-check manual entry**): RR 0–80, SpO2 0–100, HR 0–300, SBP 0–300, Temp 25–45 °C. Warn, do not block: a genuinely extreme value is exactly what must reach the hard-trigger engine.
- **Type mismatch is a hard 422** — enforce it client-side (never send a string for a NUMERIC concept).

### 14.3 De-escalate override
- `target_acuity`: required; a select restricted to values **strictly greater** than the current `final_acuity` (max 5). Disable the whole action when current acuity is 5.
- `reason_code`: required, from the 5-value vocabulary with human labels.
- `free_text_reason`: optional textarea.
- Show a persistent notice in the modal: *"De-escalations are flagged for retrospective review and permanently recorded against your name."*

### 14.4 Escalate override
**No form.** One tap. Disabled when `final_acuity === 1`.

### 14.5 Dismiss alert
`reason_code` required (excluding `RESOLVED_AUTOMATICALLY`); `free_text_reason` optional, and required in the UI when `OTHER` is chosen.

### 14.6 Resolve data conflict
`kept_observation_id`: a radio group over the conflict's `observation_ids`, each option rendering the full observation (value, unit, source, tier, time). The `conservative_observation_id` is labelled *"currently used for scoring"*. `resolution_note` optional.

### 14.7 Assign resource
A single `resource_type` select. **The 409 path is a designed outcome, not a validation failure.**

### 14.8 Intake free text
Single textarea + submit. Long-running. On response, show `observations_created.length`, list `rejected[]` with reasons, and when `llm_available === false` show: *"AI extraction unavailable — use the structured vitals form."* with a direct link to it.

---

## 15. Loading / Error / Empty States

Every data surface needs all four. Antigravity must not ship a screen with only the success state.

### 15.1 Loading
- **First load:** skeletons matching final layout (queue → 5 skeleton rows; tiles → 5 skeleton cards). Never a bare centred spinner on a full page.
- **Polling refetch:** **no skeleton, no spinner, no layout shift.** A subtle "updated Xs ago" timestamp in the header only. A queue that flashes every 3 seconds is unusable on a wall display.
- **Mutations:** disable the specific control, show an inline spinner in it. Never block the page.
- **Slow endpoints** (`/cases/{id}/intake`, `/demo/seed`, `/demo/surge`): explicit "This can take a few seconds" copy plus an indeterminate progress bar.

### 15.2 Empty
| Surface | Empty condition | Copy |
|---|---|---|
| Queue | `[]` | "No active patients. Register a walk-in or seed the demo data." + both CTAs |
| Alerts | `[]` | "No interruptive alerts. The queue is the notification." |
| Timeline | `[]` | Impossible in practice (`CASE_CREATED` always exists) — still handle it |
| Trends (doctor) | `[]` | "No trends yet — each vital needs at least two readings." |
| Stuck patients | `[]` | "Nothing stuck. All expected next events are within their windows." |
| Conflicts | `[]` | "No unresolved data conflicts." |
| Resources | `[]` | **"No resources configured. Add clinicians and treatment spaces before assigning."** + a create form. This is the fresh-DB default |
| Incoming ambulances | `[]` | "No incoming ambulances." |
| Flagged for review | `[]` | "No de-escalations awaiting retrospective review." |
| Pre-alert `key_abnormal_vitals` | `[]` | "No abnormal vitals recorded yet." |
| `interventions_already_performed` | always `[]` | **"Interventions are not recorded by this system."** — do not render an empty list as if data were merely absent |

### 15.3 Error
- **Inline over modal.** A failed poll must not take over the screen — keep showing the last good data with a "Last updated HH:mm — reconnecting" banner.
- 400/409: show `detail` verbatim; it is written for a human.
- 404: an empty state with a "Back to queue" action.
- 403: hide the control; if it is reached anyway, an inline "Not available for your role".
- 422: map `loc` → field, show inline messages, keep the form populated.
- 409 capacity conflict: the dedicated panel (§5.11).

### 15.4 Connection failure
A global `ConnectionBanner` driven by `GET /health` (15 s): when it fails, a persistent bar reading *"Cannot reach the triage server. Showing last known data. [Retry] [Open printed queue]"* — with the printable snapshot as the honest degraded path. This directly serves the demo's closing moment (Phase 14.3, 6:30 — "Kill the LLM and the network live").

---

## 16. Frontend ↔ Backend Integration

### 16.1 CORS — read this before Checkpoint 1

**The backend registers no CORS middleware** (verified: no `CORSMiddleware` anywhere in `app/`). A Vite dev server on `http://localhost:5173` calling `http://localhost:8000` is a cross-origin request; the browser will block every response. **This blocks all frontend development.** See §19 🔴-1.

**Antigravity must not modify the backend to fix this.** Use the **Vite dev proxy**, which requires no backend change:

```ts
// vite.config.ts
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true,
                rewrite: (p) => p.replace(/^\/api/, '') },
    },
  },
});
```
Then set `VITE_API_BASE_URL=/api` in `.env.development`. Requests become same-origin and CORS never applies.

**Report the CORS gap to the backend owner** as the one change needed before any non-proxied deployment (a `CORSMiddleware` registration in `app/main.py`). Do not make that change unilaterally.

### 16.2 Integration checklist per endpoint

For every endpoint wired, verify all of:
1. **URL** exactly matches §6 (no trailing slash — FastAPI's `/cases` and `/cases/` differ and the latter redirects).
2. **Method** matches. Several read-shaped operations are POSTs (`/demo/seed`, `/cases/{id}/reassessment`).
3. **Payload** contains every required field with the right JSON type — especially `reliability_tier` as a **number**.
4. **Headers**: `Content-Type: application/json` on bodies; `Authorization` present on exactly the endpoints in §6.0 and absent elsewhere.
5. **Query params** serialised, `undefined` omitted (sending `status=undefined` yields a 422).
6. **Response parsed** into the §13 type; no field renamed, no field invented.
7. **Errors** hit the right branch (422 array vs 400/404 string vs 409 conflict object).
8. **Loading** state renders and clears.
9. **Cache invalidation** per §11.4 actually fires.
10. **Timestamps** parsed via `parseBackendUtc`.

### 16.3 Concrete integration test scenarios

Each is a manual (and ideally automated) check against a **live backend on a fresh database**.

| # | Scenario | Steps | Expected |
|---|---|---|---|
| **T1** | Health + CORS | Load the app | Connection banner absent; `GET /health` 200 through the proxy |
| **T2** | Login | Select each of the 3 roles | Token stored; header shows the right display name; ADMIN sees `/admin` monitoring, NURSE does not |
| **T3** | 401 handling | Corrupt the stored token, open `/doctor/:id` | Redirect to `/login`, no crash, no infinite loop |
| **T4** | 403 handling | Log in as NURSE, force-open the equity report | Inline "not permitted", not a redirect |
| **T5** | Register walk-in | Submit name + age 54 | 201; case detail shows an assessment with `should_abstain: true` and an `abstention_message` |
| **T6** | Vitals → rescore | Post RR 26, SpO2 92, HR 118, SBP 104, Temp 38.4, ALERT, O2 false | Acuity resolves to ESI 2 with `confidence_band: HIGH`; `rule_component_breakdown` shows 7 rows with points 3/2/0/1/2/0/1 |
| **T7** | Queue ordering | Have ESI 1, 2 and 4 cases present | Rendered order matches array order; the ESI 4 case never appears above the ESI 2 case regardless of wait |
| **T8** | ML refusal | Seed demo data, open the scenario keyed to ML disagreement | A case exists with `ml_suggested_acuity > final_acuity` and `deciding_layer: 'RULES'`; the callout renders |
| **T9** | Escalate | Tap Escalate on an ESI 3 case | 200; `resulting_acuity: 2`, `flagged_for_review: false`; row moves up within one poll |
| **T10** | Escalate at ESI 1 | Open a bypass/ESI-1 case | The Escalate control is **disabled**; no 400 is ever triggered |
| **T11** | De-escalate friction | Submit DE_ESCALATE with no `target_acuity` via devtools | 400 `"DE_ESCALATE requires an explicit target_acuity."`; the UI form prevents it reaching that state |
| **T12** | De-escalate audit | Complete a valid de-escalation | 200 `flagged_for_review: true`; the record appears on the case **and** in `/admin` |
| **T13** | Emergency bypass | Tap the panic button | `emergency_bypass_active: true` instantly; a `CRITICAL_BYPASS_PATIENT` alert within one poll |
| **T14** | Physiological bypass | Post SpO2 = 70 on an adult | Verified: bypass activates automatically, `final_acuity: 1`, `deciding_layer: 'ABSTENTION'` — the banner appears with no human action |
| **T15** | Capacity conflict | Assign a TREATMENT_SPACE with no resources configured | 409 with 3 `candidate_actions`; the conflict panel renders them; **acuity is unchanged** |
| **T16** | Resource happy path | Create a TREATMENT_SPACE, then assign it | 200 `ResourceResponse`; patient-view `stage` flips to `IN_TREATMENT` |
| **T17** | Patient view isolation | Open `/patient/:caseId` | Inspect the DOM and the network tab: **no acuity value present anywhere**, and no request to `/cases/{id}` or `/queue` |
| **T18** | I feel worse | Tap the button | 200; calm acknowledgement; nurse queue shows `REASSESSMENT_OVERDUE` within one poll |
| **T19** | Doctor "what changed" | Open doctor view, mark reviewed, add a vital, reopen | `is_first_review` false; `changed_since_last_review` contains only the new events |
| **T20** | Explanation fallback | With no `GROQ_API_KEY` set | 200 with `fallback_used: true`, `fallback_reason: "LLM_UNAVAILABLE"`; the panel is labelled rule-based, and the acuity rendered **before** it arrived |
| **T21** | Intake unavailable | Submit intake text with no API key | 200 `llm_available: false`; the UI shows the structured-form fallback, not an error toast |
| **T22** | 404 | Open `/cases/does-not-exist` | Empty state; the displayed message has **no stray single quotes** |
| **T23** | 422 | Send `value: "abc"` with `value_type: NUMERIC` | 422; inline field error; form values preserved |
| **T24** | Timezone | Compare a `created_at` in the UI against the backend value | No offset drift (this fails immediately if `parseBackendUtc` is bypassed) |
| **T25** | Network failure | Stop uvicorn with the queue open | Last good data retained; connection banner appears; no crash; printable-queue link offered |
| **T26** | Alert dedupe | Trigger two bypass detectors on one case | Exactly **one** `CRITICAL_BYPASS_PATIENT` alert |
| **T27** | Alert budget | Set `nurses_on_shift = 2` | `alerts_per_nurse_per_hour` matches `interruptive_alerts_in_window / 2`; `within_budget` compares against target 4 |
| **T28** | Surge | Run `POST /demo/surge` | `acuity_ordering_holds: true`; queue triples; alert growth stays below volume growth; the narrative renders |
| **T29** | Ambulance continuity | Create AMBULANCE case → add vitals → pre-alert → arrival | Pre-alert shows `predicted_acuity_band`; ETA narrows across polls; after arrival the **same `case_id`** appears in `/queue` |
| **T30** | ETA 404 | Open the ambulance panel on a walk-in | 404 handled as "no transport recorded"; the ETA widget is hidden, not an error |
| **T31** | Printable fallback | Open `/queue/printable` | `text/plain` renders in a `<pre>`; browser print produces a legible page |
| **T32** | Background polling | Switch tabs for 60 s | Polling pauses (`document.hidden`); resumes on focus with a fresh fetch |

---

## 17. Checkpoint-Based Implementation Plan

Checkpoints are in strict dependency order. **Do not begin a checkpoint until the previous one's pass criteria are met.** Every checkpoint assumes the backend is running: `cd AIC_backend && .venv/bin/uvicorn app.main:app --reload`.

---

### Checkpoint 1 — Foundation, API client, and auth

**Objective.** A running Vite app that can reach the backend through the dev proxy, log in as any of the three demo roles, and render an authenticated shell. This is the checkpoint that proves the integration path works at all.

**Dependencies.** Backend running on `:8000`. Node 18+.

**Files to create.**
```
frontend/package.json  vite.config.ts  tsconfig.json  tailwind.config.js
frontend/postcss.config.js  index.html  .env.example  .env.development
frontend/src/main.tsx  App.tsx  config.ts  index.css
frontend/src/lib/http.ts  lib/datetime.ts  lib/cn.ts  lib/enums.ts
frontend/src/types/api.ts  types/enums.ts
frontend/src/api/auth.ts  api/health.ts
frontend/src/contexts/AuthContext.tsx  contexts/ProfileContext.tsx
frontend/src/hooks/useAuth.ts  hooks/useHealth.ts
frontend/src/components/layout/AppShell.tsx  Header.tsx  RoleSwitcher.tsx  NavRail.tsx
frontend/src/components/ui/Button.tsx  Card.tsx  Spinner.tsx  Toast.tsx
frontend/src/components/feedback/ConnectionBanner.tsx
frontend/src/features/auth/RoleSelector.tsx
frontend/src/pages/LoginPage.tsx  QueuePage.tsx (placeholder)  NotFoundPage.tsx
```

**Files to modify.** None — the backend is untouched.

**Implementation tasks.**
1. Scaffold Vite + React + TypeScript (strict) + Tailwind.
2. **Configure the dev proxy exactly as in §16.1.** This is the single highest-risk item in the project; do it first and verify it before writing any other code.
3. Write `lib/datetime.ts` with `parseBackendUtc` / `toBackendUtc` / `formatClock` / `formatRelative` / `formatMinutes`, plus unit tests. **Do this in Checkpoint 1, not later** — retrofitting it means auditing every component.
4. Write `lib/http.ts` with the full `ApiError` contract from §12.2, including the 422-array vs string-detail distinction, the 409 capacity-conflict predicate, the 404 quote-stripping in `displayMessage()`, and `text/plain` handling.
5. Transcribe **all** of §13 into `types/api.ts` and `types/enums.ts`. Alternatively generate from `/openapi.json` and hand-check against §13.
6. Build `AuthContext`: `login(role)`, `logout()`, `user`, `token`, `hasRole(...roles)`; persist to `localStorage` under one key; rehydrate on boot; **decode the JWT `exp` and treat an expired token as logged out** before making any request.
7. Build `RoleSelector` — a dropdown explicitly labelled *"Demo shortcut — not a real login"*.
8. Build `AppShell` with header (app name, connection dot, user chip, role switcher, logout) and a left nav rail whose items are role-filtered.
9. Wire TanStack Query provider with sane defaults: `retry: 1`, `refetchOnWindowFocus: false`, `refetchIntervalInBackground: false`, `staleTime: 0`.
10. Add `ConnectionBanner` polling `GET /health` at 15 s.
11. Set up React Router with all routes from §9, most rendering placeholders. `/patient/:caseId` must render **outside** `AppShell`.

**Backend APIs involved.** `POST /auth/login`, `GET /health`.

**Expected behaviour.** Visiting `/` redirects to `/login`. Picking a role logs in and lands on that role's home. Refresh preserves the session. Stopping the backend shows the connection banner within 15 s.

**Validation.** Run T1, T2, T3 from §16.3. In devtools, confirm the login request goes to `/api/auth/login` (same-origin) and returns 200 — **not** a CORS error. Confirm a `parseBackendUtc` unit test asserts that `"2026-08-28T18:48:46.312764"` parses to 18:48 **UTC**.

**Pass criteria.**
- [ ] `npm run dev` serves with no TypeScript errors under `strict`.
- [ ] Login succeeds for all three roles; token and user persist across reload.
- [ ] No CORS error appears in the console for any request.
- [ ] `ApiError` correctly distinguishes 422 (array detail) from 404 (string detail) — proven by a test hitting `/cases/nope` and a deliberately malformed POST.
- [ ] `datetime.ts` unit tests pass.
- [ ] Stopping the backend shows the connection banner; restarting clears it.

**Integration risks.** Forgetting the proxy and hitting CORS (the single most likely blocker). Hardcoding `localhost:8000` in a component. Writing `new Date(apiString)` anywhere. Storing the token in a React state that is lost on reload.

---

### Checkpoint 2 — Design system and clinical primitives

**Objective.** Every shared visual and clinical primitive, built and visually verified in isolation, so no later checkpoint invents a second acuity colour scale.

**Dependencies.** Checkpoint 1.

**Files to create.**
```
src/lib/acuity.ts
src/components/ui/Badge.tsx Modal.tsx Table.tsx Tooltip.tsx Skeleton.tsx
                  EmptyState.tsx ErrorState.tsx ConfirmDialog.tsx Select.tsx Input.tsx
src/components/clinical/AcuityBadge.tsx ConfidenceBadge.tsx AttentionFlagChip.tsx
                        WaitTimeRange.tsx TrendArrow.tsx VitalValue.tsx StalenessDot.tsx
src/components/feedback/QueryBoundary.tsx LoadingBoundary.tsx
src/pages/StyleGuidePage.tsx     (dev-only route /styleguide)
```

**Implementation tasks.**
1. Define the acuity scale in `lib/acuity.ts` **once** (§10.1). Every consumer imports it.
2. Build each clinical primitive to the contracts in §10.1. `ConfidenceBadge` must be structurally incapable of rendering `confidence_score` — do not accept it as a prop.
3. `WaitTimeRange` always renders a range and always exposes `caveat`.
4. `QueryBoundary` is a single wrapper handling `isLoading` → skeleton, `isError` → `ErrorState` with retry, empty → `EmptyState` — so no page reimplements the four states.
5. Build `/styleguide` rendering every primitive across every enum value, in light conditions and at wall-display distance.
6. Verify contrast ratios (≥4.5:1) for all five acuity tokens and all confidence bands.

**Backend APIs involved.** None.

**Expected behaviour.** `/styleguide` shows every state of every primitive.

**Validation.** Visual review of `/styleguide` at 100% and 200% zoom; contrast checked with a tool; every primitive rendered with `null`/undefined inputs without crashing.

**Pass criteria.**
- [ ] Exactly one acuity colour map exists in the codebase (grep proves it).
- [ ] `ConfidenceBadge` has no prop that can carry a numeric score.
- [ ] All primitives handle `null` gracefully.
- [ ] Every acuity and flag conveys meaning through text as well as colour.
- [ ] `QueryBoundary` is used by the placeholder pages.

**Integration risks.** Colour-only encoding (accessibility failure). Building a "percentage" confidence display. Divergent acuity palettes between the queue and the control tower.

---

### Checkpoint 3 — Nurse Guardian Queue (the primary screen)

**Objective.** The live, polling, correctly-ordered nurse queue with its four persistent columns and its one-tap actions. After this checkpoint the product is demonstrable.

**Dependencies.** Checkpoints 1–2.

**Files to create.**
```
src/api/queue.ts  api/cases.ts (partial: list, get, reassessment)
src/hooks/useQueue.ts  useMarkReassessed.ts  useOverride.ts
src/features/queue/QueueTable.tsx QueueRow.tsx QueueRowActions.tsx QueueLegend.tsx
src/features/case/DeEscalateModal.tsx
src/pages/QueuePage.tsx  (replaces placeholder)
```

**Implementation tasks.**
1. `useQueue` polls `GET /queue?hospital_profile_id=default` at `POLL.QUEUE` (3000 ms) with `refetchIntervalInBackground: false` and **exactly one shared query key** (StrictMode-safe — the endpoint has write side effects).
2. `QueueTable` renders `data` **in array order**. Add an explicit code comment: *"Backend-sorted. Do not sort."*
3. `QueueRow` implements the column mapping table in §9.1 precisely.
4. Actions: **Escalate** (one tap, no dialog, `POST /cases/{id}/override {"action":"ESCALATE"}`, **disabled when `final_acuity === 1`**), **Mark reassessed** (`POST /cases/{id}/reassessment`), **Record vitals** (opens Checkpoint 4's drawer — stub it now), **Open case** (navigate).
5. `DeEscalateModal` per §14.3 (reachable from the row overflow menu and from case detail).
6. Empty state and error state per §15.
7. Refetch indicator: an "updated Xs ago" label only. **No skeleton on refetch.**
8. Header count chips: total, and a per-acuity breakdown derived from the same array (display aggregation of returned data is allowed; recomputation of clinical values is not).

**Backend APIs involved.** `GET /queue`, `POST /cases/{id}/override`, `POST /cases/{id}/reassessment`.

**Expected behaviour.** The queue updates every 3 s with no flicker. Escalating moves a row up within one tick. Marking reassessed clears the overdue chip.

**Validation.** T7, T9, T10, T18, T32. Additionally: seed demo data (`POST /demo/seed` via curl for now) and confirm ~20 rows render in acuity order. Watch the network tab for exactly one `/queue` request per 3 s — **two would mean a double sweep**.

**Pass criteria.**
- [ ] Rows render in exactly the order returned; no client-side sort exists.
- [ ] All four Phase 8.2 columns present and correct.
- [ ] Escalate is one tap with no confirmation, and disabled at ESI 1.
- [ ] De-escalate cannot be submitted without `target_acuity` **and** `reason_code`.
- [ ] Polling produces no visible flicker or layout shift.
- [ ] Exactly one `/queue` request per interval.
- [ ] Polling pauses on a hidden tab.
- [ ] Empty and error states render correctly.

**Integration risks.** Adding a "sort by column" header (breaks the clinical invariant). Double-polling from StrictMode. Skeleton-on-refetch flicker. Colour-only acuity. Firing an escalate at ESI 1 and surfacing a raw 400.

---

### Checkpoint 4 — Case detail and vitals capture

**Objective.** The full case workspace: observations, risk assessment with component breakdown, confidence, explanation, timeline, and the vitals-recording form that drives the whole rescoring loop.

**Dependencies.** Checkpoints 1–3.

**Files to create.**
```
src/api/observations.ts
src/hooks/useCase.ts useObservations.ts useAddObservation.ts useRiskAssessments.ts
          useCaseTimeline.ts useExplanation.ts useIntake.ts
src/features/case/CaseHeader.tsx CaseSummaryCard.tsx VitalsPanel.tsx RecordVitalsForm.tsx
                  RiskAssessmentPanel.tsx ComponentBreakdownTable.tsx ConfidencePanel.tsx
                  ExplanationPanel.tsx AcuityHistoryChart.tsx TimelineList.tsx
                  IntakeTextPanel.tsx EmergencyBypassButton.tsx OverrideControls.tsx
src/features/registration/RegisterCaseForm.tsx
src/pages/CaseDetailPage.tsx RegisterPage.tsx
```

**Implementation tasks.**
1. `RegisterCaseForm` per §14.1, including the age warning.
2. `CaseDetailPage` polls `GET /cases/{id}` at 5 s, with the timeline/assessments/explanation as separate queries so a slow explanation never blocks the acuity.
3. `RiskAssessmentPanel` renders `final_acuity` (hero), `deciding_layer`, `rule_acuity`, hard triggers, and — when `ml_suggested_acuity > final_acuity && deciding_layer === 'RULES'` — the **min() invariant callout** from §13.3. Put `ml_probability` and `confidence_score` behind a "Technical detail" disclosure, collapsed by default.
4. `ComponentBreakdownTable` renders every `rule_component_breakdown` row: label, raw value + unit, points, and for `is_missing: true` a distinct row style with `missing_reason` — **`points: null` must never render as `0`.**
5. `ConfidencePanel` shows the band plus `confidence_reasons[]` verbatim; when `should_abstain`, show `abstention_message` prominently with the explanation that a *safer* level is being held.
6. `ExplanationPanel` fetches after the assessment paints; labels `fallback_used` output as "Rule-based explanation"; renders `grounded: false` (if it ever occurs) with a caution note.
7. `RecordVitalsForm` per §14.2 — **sequential POSTs**, per-field results, one invalidation sweep at the end.
8. `AcuityHistoryChart` from `GET /cases/{id}/risk-assessments` — a step chart of `final_acuity` over `computed_at`, **Y axis inverted so ESI 1 is at the top**.
9. `TimelineList` with human labels for all 30 event types and a safe fallback for unknown ones.
10. `EmergencyBypassButton` — persistent, always visible on the case, red, **no confirmation dialog**.
11. `IntakeTextPanel` per §14.8.

**Backend APIs involved.** `POST /cases`, `GET /cases/{id}`, `GET/POST /cases/{id}/observations`, `GET /cases/{id}/risk-assessments`, `GET /cases/{id}/timeline`, `GET /cases/{id}/explanation`, `POST /cases/{id}/intake`, `POST /cases/{id}/emergency-bypass`, `POST /cases/{id}/override`.

**Expected behaviour.** Registering a case then entering the T6 vitals set yields ESI 2 / HIGH confidence with a 7-row breakdown. Posting SpO2 = 70 activates bypass with no human action.

**Validation.** T5, T6, T13, T14, T20, T21, T22, T23, T24.

**Pass criteria.**
- [ ] The T6 vitals set produces `final_acuity: 2`, `confidence_band: HIGH`, 7 breakdown rows with points 3/2/0/1/2/0/1.
- [ ] `points: null` renders as "not scored", never as 0.
- [ ] The acuity is painted before the explanation request resolves.
- [ ] `fallback_used: true` is labelled as rule-based, not as AI output.
- [ ] A 422 on one vital does not lose the other entered values.
- [ ] Emergency bypass fires with no confirmation dialog.
- [ ] Every displayed vital shows its age (Phase 9.4).
- [ ] `ml_probability` and `confidence_score` appear only inside the collapsed technical disclosure.

**Integration risks.** Rendering `points: null` as 0 (clinically misleading). Blocking the acuity on the LLM. Parallel observation POSTs producing a rescore against an incomplete vitals set. Adding a confirmation dialog to the panic button. Sending `reliability_tier` as a string.

---

### Checkpoint 5 — Overrides, conflicts, resources and diagnostics

**Objective.** Complete the clinician action surface: the full audit trail on the case, data-conflict resolution, resource assignment including the 409 conflict path, and the diagnostic-test lifecycle.

**Dependencies.** Checkpoints 1–4.

**Files to create.**
```
src/api/conflicts.ts resources.ts tests.ts
src/hooks/useConflicts.ts useResolveConflict.ts useResources.ts useAssignResource.ts
          useCaseDecisions.ts useCaseTests.ts useTestLifecycle.ts
src/features/case/DecisionHistoryList.tsx ConflictList.tsx ResolveConflictModal.tsx
                  AssignResourcePanel.tsx CapacityConflictPanel.tsx DiagnosticTestsPanel.tsx
src/features/ops/ResourceManager.tsx
src/pages/OpsPage.tsx  (resources half)
```

**Implementation tasks.**
1. `DecisionHistoryList` from `GET /cases/{id}/decisions` — every field of `HumanDecisionResponse`, with `flagged_for_review` prominently marked. This is Phase 14.1 patient #18's "full audit record shown on screen".
2. `ConflictList` + `ResolveConflictModal` per §14.6. Show both conflicting observations side by side with sources and times (Phase 9.3: "both appear on screen").
3. `AssignResourcePanel`: on success render the assignment; **on 409, render `CapacityConflictPanel`** with `detail` and `candidate_actions` as an action checklist, and an explicit line stating the patient's acuity was **not** changed.
4. `ResourceManager` on `/ops`: create resources, list by type/status, confirm occupancy, release. **This screen is mandatory** — a fresh DB has zero resources and without it every assignment 409s and every capacity tile reads zero.
5. `DiagnosticTestsPanel`: order a test, then advance `sample-collected` → `result-available` → `result-reviewed`, with the status lifecycle rendered as a stepper and `stuck_flagged` surfaced.

**Backend APIs involved.** `GET /cases/{id}/decisions`, `GET /cases/{id}/conflicts`, `POST /conflicts/{id}/resolve`, `POST /cases/{id}/assign-resource`, `POST /resources`, `GET /resources`, `POST /resources/{id}/confirm-occupancy`, `POST /resources/{id}/release`, `POST /cases/{id}/tests`, `GET /cases/{id}/tests`, `POST /tests/{id}/{sample-collected,result-available,result-reviewed}`.

**Expected behaviour.** With no resources, assignment surfaces the conflict panel. After creating a treatment space, assignment succeeds and the patient view stage becomes `IN_TREATMENT`.

**Validation.** T12, T15, T16. Plus: resolve a data conflict and confirm the case's `primary_attention_flag` stops being `DATA_CONFLICT` on the next queue poll.

**Pass criteria.**
- [ ] The 409 capacity conflict renders its dedicated panel with all `candidate_actions`, never a generic toast.
- [ ] The conflict panel explicitly states acuity was not changed.
- [ ] Resources can be created, assigned, occupancy-confirmed and released from the UI.
- [ ] A de-escalation's full audit record is visible on the case.
- [ ] Conflict resolution shows both observations with source and time before the human chooses.
- [ ] The test lifecycle advances through all four states.

**Integration risks.** Treating the 409 as a failure. Shipping without the resource-creation screen. Losing `candidate_actions` because `ApiError` discards the raw body.

---

### Checkpoint 6 — Doctor view

**Objective.** The physician surface, with "what changed since you last looked" as its hero element.

**Dependencies.** Checkpoints 1–5.

**Files to create.**
```
src/hooks/useDoctorView.ts useMarkReviewed.ts
src/features/doctor/DoctorCaseList.tsx DoctorCaseView.tsx ChangedSincePanel.tsx
                    TrendsPanel.tsx PendingActionsList.tsx
src/pages/DoctorListPage.tsx DoctorCasePage.tsx
```

**Implementation tasks.**
1. `DoctorCaseList` from `GET /cases?status=ACTIVE` (there is no doctor-assignment model — **do not invent one**; label the list "Active patients").
2. `useDoctorView` sends the bearer token and **includes `user.user_id` in the query key** — the response is identity-relative and caching it per-case only would show one doctor another's review window.
3. `ChangedSincePanel` is the top element. When `is_first_review`, show "First review — showing the complete history"; otherwise "Since your last review at {last_reviewed_at}" with the event list.
4. `TrendsPanel` renders `trends[]` with previous → current, `delta`, and both timestamps. Empty state: "each vital needs at least two readings."
5. `PendingActionsList` renders both `kind` values with a deep link via `reference_id` (test id or conflict id).
6. "Mark reviewed" button → `POST /cases/{id}/mark-reviewed`, then invalidate the doctor-view query.
7. Reuse `RiskAssessmentPanel`, `ComponentBreakdownTable`, `ConfidencePanel` from Checkpoint 4 — do not fork them.
8. **Deliberately absent, by architectural instruction:** differential diagnoses, treatment suggestions. The backend generates neither; do not add a placeholder that implies they are coming.

**Backend APIs involved.** `GET /cases?status=ACTIVE`, `GET /cases/{id}/doctor-view`, `POST /cases/{id}/mark-reviewed`.

**Expected behaviour.** First open shows the whole history; after marking reviewed and adding a vital, reopening shows only the new events.

**Validation.** T19. Also: log in as DOCTOR in one browser and NURSE in another, mark reviewed as the doctor, and confirm the nurse's doctor-view window is unaffected.

**Pass criteria.**
- [ ] `GET /doctor-view` always carries the bearer token; without it the UI shows the auth error, not a crash.
- [ ] The query key includes the user id.
- [ ] `changed_since_last_review` correctly narrows after marking reviewed.
- [ ] Trends omit single-reading concepts entirely (not shown as flat).
- [ ] No differential-diagnosis or treatment UI exists anywhere.

**Integration risks.** Caching the doctor view without the user id. Calling it unauthenticated (401). Rendering a single reading as a flat trend.

---

### Checkpoint 7 — Control tower, alerts, and the ops list

**Objective.** The anticipatory surfaces: five tiles, the three-alert interruptive feed with dismissal, the alert-budget meter, and the operational stuck-patient list kept strictly separate from the clinical queue.

**Dependencies.** Checkpoints 1–5.

**Files to create.**
```
src/api/alerts.ts controlTower.ts ops.ts
src/hooks/useControlTower.ts useAlerts.ts useDismissAlert.ts useAlertBudget.ts useStuckPatients.ts
src/features/controltower/ControlTower.tsx AcuityBandTile.tsx DeterioratingTile.tsx
                          StuckPatientsTile.tsx CapacityTile.tsx IncomingAmbulancesTile.tsx
src/features/alerts/AlertFeed.tsx AlertCard.tsx DismissAlertModal.tsx AlertBudgetMeter.tsx
src/features/ops/StuckPatientList.tsx
src/pages/ControlTowerPage.tsx AlertsPage.tsx  (+ ops half of OpsPage)
```

**Implementation tasks.**
1. `ControlTower` renders **exactly five tiles**, in the architecture's order. **Do not add a sixth.** Every tile is clickable through to the thing it describes.
2. `AlertCard` narrows `payload` by `alert_type` (§13.6) with a defensive fallback for an unrecognised type. Each card deep-links to its case.
3. `DismissAlertModal` per §14.5. Dismissal may be optimistic.
4. `AlertBudgetMeter` — `alerts_per_nurse_per_hour` against `target_alerts_per_nurse_per_hour`, with `within_budget` driving the colour and `breakdown_by_type` as a small stacked bar. Expose `nurses_on_shift` as an input (default 1). **This is the demo's headline metric — make it large and legible.**
5. `StuckPatientList` grouped by `route_to`, with an explicit banner: *"Operational only — these do not affect clinical acuity."*
6. A global alert badge in the header, driven by the same `['alerts']` query — **not a second poll**.

**Backend APIs involved.** `GET /control-tower`, `GET /alerts`, `POST /alerts/{id}/dismiss`, `GET /alerts/budget`, `GET /ops/stuck-patients`.

**Expected behaviour.** Bypassing a patient produces exactly one alert. Dismissal requires a reason. The budget meter tracks live.

**Validation.** T26, T27. Plus: confirm the control tower renders exactly five tiles, and that the alert badge and the alert page share one network request per interval.

**Pass criteria.**
- [ ] Exactly five control-tower tiles.
- [ ] All three alert payload shapes render correctly; an unknown type does not crash.
- [ ] Dismissal cannot be submitted without a reason code.
- [ ] `RESOLVED_AUTOMATICALLY` is absent from the dropdown but renders when read.
- [ ] Stuck patients are visually and textually separated from clinical acuity.
- [ ] The alert badge does not create an extra poll.
- [ ] Capacity tile handles the all-zero fresh-DB state with a link to resource setup.

**Integration risks.** Adding a sixth tile. Blind `payload.case_id` access on the aggregate alert (which has `case_ids`, plural). Letting stuck patients bleed into the clinical queue. Double-polling `/alerts` (which has write side effects).

---

### Checkpoint 8 — Patient view and kiosk mode

**Objective.** The public, constrained, clinically-silent patient surface with the "I feel worse" button.

**Dependencies.** Checkpoints 1–2 (deliberately independent of the clinician surfaces).

**Files to create.**
```
src/hooks/usePatientView.ts useSelfReportWorsening.ts
src/features/patient/PatientStatusView.tsx FeelWorseButton.tsx StageProgress.tsx
src/pages/PatientPage.tsx
```

**Implementation tasks.**
1. `/patient/:caseId` renders **outside `AppShell`** — no nav, no role chip, no clinician affordance, no login requirement.
2. Render exactly the four elements of §9.2, in that order, at large type.
3. `FeelWorseButton`: full width, minimum 64 px tall, single tap, no confirmation. After success show a calm acknowledgement and disable it for 60 s to prevent accidental repeats (a client-side courtesy only — the backend accepts repeats).
4. Poll at 10 s. **No flicker, no spinners after first load** — this screen is watched by an anxious person.
5. **Write an automated guard test** asserting that the patient page's rendered DOM contains no acuity value and that the page issues no request to `/cases/{id}`, `/queue`, or any endpoint returning `final_acuity`.
6. Add a `?kiosk=1` mode that hides browser-navigation affordances and enlarges type further.

**Backend APIs involved.** `GET /cases/{id}/patient-view`, `POST /cases/{id}/self-reported-worsening`.

**Expected behaviour.** A patient sees their stage, a wait range with its caveat, what happens next, and one button. Tapping it notifies the nurse within one queue poll.

**Validation.** T17, T18. Run T17 with devtools open and inspect **both** the DOM and the network tab.

**Pass criteria.**
- [ ] No acuity, confidence, probability, queue position, or other patient appears anywhere on this route.
- [ ] The page makes no request to any endpoint that returns `final_acuity`.
- [ ] The route works with no token at all.
- [ ] The wait-time `caveat` is visible body text, not a tooltip.
- [ ] The button is one tap with no confirmation.
- [ ] The automated leak-guard test passes.

**Integration risks.** Reusing a shared case component that pulls in acuity. Wrapping the route in the auth guard (kiosk mode must work logged out). Rendering the wait estimate as a single number or as a promise.

---

### Checkpoint 9 — Ambulance pre-arrival and pre-alert

**Objective.** The pre-arrival board, the three-second pre-alert card, the narrowing ETA, human-confirmed identity matching, and the arrival transition that preserves case continuity.

**Dependencies.** Checkpoints 1–4.

**Files to create.**
```
src/hooks/usePreAlert.ts useEta.ts useTransportDelay.ts useRecordArrival.ts useIdentityMatch.ts
src/features/ambulance/AmbulanceIntakeForm.tsx PreAlertCard.tsx EtaRange.tsx
                       IdentityMatchPanel.tsx TransportDelayForm.tsx ArrivalButton.tsx
src/pages/AmbulancePage.tsx AmbulanceCasePage.tsx
```

**Implementation tasks.**
1. `AmbulanceIntakeForm` → `POST /cases` with `arrival_mode: "AMBULANCE"` and `estimated_transport_minutes`.
2. `AmbulancePage` lists `GET /cases?status=PRE_ARRIVAL`, each row showing the pre-alert summary and ETA.
3. `PreAlertCard` — **scannable in three seconds**: predicted acuity band (large), one-line presentation, `key_abnormal_vitals` with times and points, `what_hospital_should_prepare` (prominent), ETA range. Render `interventions_already_performed` as **"Interventions are not recorded by this system"** — it is always `[]` by design, and an empty list must not read as "none were performed."
4. `EtaRange` polls at 3 s so the narrowing is visible during the demo. Handle `arrived: true` (0–0) as "Arriving now". Show `delayed_additional_minutes` when non-zero, with the `caveat`.
5. **Handle the ETA 404 as a normal state** — hide the widget, never show an error.
6. `TransportDelayForm` → `POST /cases/{id}/ambulance/delay` (unauthenticated).
7. `IdentityMatchPanel`: propose (typed MRN — there is **no search endpoint**, do not fake one), then confirm (requires bearer token). Show `identity_link_status` throughout, and never present auto-merge as an option.
8. `ArrivalButton` → `POST /cases/{id}/arrival`; handle 409 ("not awaiting arrival") gracefully. On success, navigate to the case and highlight that **the case_id is unchanged**.
9. Add vitals to a PRE_ARRIVAL case using the Checkpoint 4 form — this is what gives the pre-alert its predicted acuity.

**Backend APIs involved.** `POST /cases`, `GET /cases?status=PRE_ARRIVAL`, `GET /cases/{id}/pre-alert`, `GET /cases/{id}/eta`, `POST /cases/{id}/ambulance/delay`, `POST /cases/{id}/identity/{propose,confirm}`, `POST /cases/{id}/arrival`, `POST /cases/{id}/observations`.

**Expected behaviour.** An ambulance case appears on the pre-arrival board with a narrowing ETA. On arrival it moves into the Guardian Queue as the same case.

**Validation.** T29, T30.

**Pass criteria.**
- [ ] The pre-alert renders all six Phase 7.3 elements.
- [ ] The ETA range visibly narrows across successive polls and never shows a single number.
- [ ] A 404 from `/eta` hides the widget rather than erroring.
- [ ] `interventions_already_performed` is labelled as not-recorded, not as "none".
- [ ] Identity confirmation requires a token and is never automatic.
- [ ] After arrival the same `case_id` appears in `/queue`; no second case is created.
- [ ] Incoming ambulances appear in the control tower's fifth tile.

**Integration risks.** Treating the ETA 404 as an error. Presenting the empty interventions array as "no interventions performed". Building a candidate-search UI for an endpoint that does not exist. Creating a second case on arrival.

---

### Checkpoint 10 — Admin audit, equity monitoring, and the demo console

**Objective.** The oversight surface and the presenter's control panel, including the degraded-mode printed fallback.

**Dependencies.** Checkpoints 1–7.

**Files to create.**
```
src/api/audit.ts demo.ts
src/hooks/useAudit.ts useDemo.ts usePrintableQueue.ts
src/features/admin/FlaggedReviewQueue.tsx OverrideMonitoringReport.tsx EquityCharts.tsx
src/features/demo/DemoConsole.tsx ScenarioList.tsx SurgeRunner.tsx SurgeResultPanel.tsx
                  PrintableQueueView.tsx
src/pages/AdminPage.tsx DemoPage.tsx
```

**Implementation tasks.**
1. `FlaggedReviewQueue` from `GET /overrides/flagged-for-review` — full decision records. **Read-only: no "mark reviewed" control exists on the backend**, so add an explicit note that closing the loop is future work rather than a disabled button that implies otherwise.
2. `OverrideMonitoringReport` (ADMIN only): headline rates, `action_counts`, `flagged_for_review_count`, and `by_age_band` / `by_sex` subgroup tables. **Render `caveat` adjacent to the charts, not in a footnote.** Note that `acuity_distribution` keys arrive as JSON strings (`{"2": 3}`).
3. Handle a NURSE/DOCTOR reaching `/admin`: hide the monitoring section entirely rather than rendering a 403.
4. `DemoConsole`: seed button (with a "creates 20 more patients each time" confirmation), surge runner with `baseline_count`/`multiplier` inputs, and a link to the printable queue.
5. `ScenarioList` renders the 20 `DemoScenario` rows with `number`, `title`, `demonstrates`, `fidelity` and `note`, each deep-linking to its case. **Show `PARTIAL` fidelity honestly.**
6. `SurgeResultPanel` renders `narrative[]` as an ordered checklist alongside the numeric evidence for all six Phase 14.2 properties — `acuity_ordering_holds`, `queue_length_before/after`, `reassessment_overdue_count`, the alert-growth comparison, `capacity_conflict_demonstrated`, `stuck_patient_count`, and the escalation fields.
7. `PrintableQueueView` fetches `GET /queue/printable` as **text**, renders it in a `<pre>` with a print stylesheet, and offers "Open in new tab" and "Print". Also link it from the connection-failure banner.

**Backend APIs involved.** `GET /overrides/flagged-for-review`, `GET /overrides/monitoring`, `POST /demo/seed`, `POST /demo/surge`, `GET /queue/printable`.

**Expected behaviour.** An admin sees override rates and subgroup distributions with the caveat. The presenter can seed, surge, and print without a terminal.

**Validation.** T4, T28, T31. Confirm the equity charts render with real seeded data and that `caveat` is visible without scrolling past the charts.

**Pass criteria.**
- [ ] `/overrides/monitoring` is requested only when the user is ADMIN.
- [ ] The `caveat` renders adjacent to the equity charts.
- [ ] `acuity_distribution` string keys are handled correctly.
- [ ] Seeding is guarded by a confirmation that states it is not idempotent.
- [ ] The surge panel shows evidence for all six Phase 14.2 properties.
- [ ] The printable queue renders as text and prints legibly.
- [ ] The flagged-review queue makes clear it is read-only.

**Integration risks.** Requesting the ADMIN endpoint as a nurse and showing a 403 error. Parsing the printable text as JSON. Rendering the equity report as if it were a fairness conclusion. Double-seeding without warning.

---

### Checkpoint 11 — Accessibility, responsiveness, and end-to-end hardening

**Objective.** Make the whole application demo-safe: keyboard-navigable, screen-reader-sane, correct at wall-display and tablet sizes, and resilient to every failure mode.

**Dependencies.** Checkpoints 1–10.

**Files to modify.** All feature and component files, as needed.

**Files to create.**
```
src/components/ui/VisuallyHidden.tsx
src/hooks/useDocumentTitle.ts
src/test/e2e/*.spec.ts        (or an equivalent manual runbook)
frontend/README.md
```

**Implementation tasks.**
1. **Keyboard:** every action reachable by keyboard; visible focus rings; modals trap focus and restore it on close; Escape closes modals. The queue table is arrow-key navigable with Enter to open.
2. **Screen readers:** the queue is a real `<table>` with `<th scope="col">`; acuity badges carry `aria-label="ESI 2, emergent"`; polling regions use `aria-live="polite"`; the emergency-bypass banner uses `role="alert"`.
3. **Colour independence:** every acuity, confidence band and attention flag carries a text label. Verify with a greyscale filter.
4. **Contrast:** ≥4.5:1 for all text, ≥3:1 for UI boundaries.
5. **Responsive:** the queue is a table ≥1024 px and a card list below; the control tower is 5 across ≥1440 px, 2 across on tablet, 1 on phone; the patient view is phone-first; **verify the queue at 1920×1080 from three metres** (it is a wall display).
6. **Motion:** respect `prefers-reduced-motion`; no animation on the polling refresh path.
7. **Error boundaries:** one per page region so a single failing panel cannot blank the case workspace.
8. **Document titles** per route.
9. Run every scenario T1–T32 in §16.3 end to end and record results.
10. Write `frontend/README.md`: prerequisites, `.env` setup, how to start the backend, how to start the frontend, the demo runbook mapped to the Phase 14.3 seven-minute arc, and known limitations copied from §19.

**Validation.** Full T1–T32 pass. Lighthouse accessibility ≥ 90 on `/queue`, `/patient/:id`, `/control-tower`. Full keyboard-only walkthrough of the seven-minute demo.

**Pass criteria.**
- [ ] T1–T32 all pass against a live backend.
- [ ] Lighthouse accessibility ≥ 90 on the three key routes.
- [ ] Complete keyboard-only demo run.
- [ ] Greyscale render remains fully interpretable.
- [ ] No console errors or unhandled promise rejections during a 10-minute session with polling active.
- [ ] Killing the backend mid-demo degrades gracefully and the printed queue is one click away.
- [ ] `README.md` lets someone else run the whole demo unaided.

**Integration risks.** Deferring accessibility to the end and finding the queue table needs restructuring. Animations that fight the 3-second poll. A single error boundary at the app root that blanks everything.

---

## 18. Validation and Testing Strategy

### 18.1 Layers

| Layer | Tool | Scope |
|---|---|---|
| Unit | Vitest | `lib/datetime.ts`, `lib/acuity.ts`, `lib/http.ts` error normalisation, zod schemas |
| Component | RTL + MSW | Each clinical primitive across every enum value; each feature component in loading/error/empty/success |
| Integration | RTL + MSW | Full page flows with **fixtures captured from real backend responses** |
| End-to-end | Manual runbook (Playwright optional) | T1–T32 against a live backend |

### 18.2 Fixtures — capture, do not invent

Record real responses once and commit them:
```bash
cd AIC_backend && .venv/bin/uvicorn app.main:app &
curl -s -X POST localhost:8000/demo/seed          > ../frontend/src/test/fixtures/demo-seed.json
curl -s localhost:8000/queue                       > ../frontend/src/test/fixtures/queue.json
curl -s localhost:8000/control-tower               > ../frontend/src/test/fixtures/control-tower.json
curl -s localhost:8000/alerts                      > ../frontend/src/test/fixtures/alerts.json
curl -s localhost:8000/cases/<id>                  > ../frontend/src/test/fixtures/case-detail.json
```
**Never hand-write a fixture.** A hand-written fixture is how invented fields enter a codebase.

### 18.3 Required regression tests

1. **Queue order preservation** — given a fixture with a deliberately non-monotonic acuity sequence, assert the rendered order equals the input order exactly.
2. **Patient-view leak guard** — assert the rendered patient page contains no digit matching an acuity and issues no request to an acuity-bearing endpoint.
3. **Datetime** — `parseBackendUtc("2026-08-28T18:48:46.312764").getUTCHours() === 18`.
4. **`points: null`** — a breakdown fixture with a null-points row renders "not scored", never "0".
5. **Error discrimination** — 422 array detail, 404 string detail, 409 capacity object all take distinct branches.
6. **Escalate disabled at ESI 1.**
7. **De-escalate blocked** without both `target_acuity` and `reason_code`.
8. **Alert payload narrowing** — all three types, plus an unknown type that must not throw.

### 18.4 Demo rehearsal

The full Phase 14.3 arc must be runnable from the UI alone: ambulance pre-alert → ambiguous walk-in with abstention → paediatric vs geriatric comparison → the ML min() refusal → mid-wait deterioration → de-escalation audit → surge → kill the network and print. Rehearse it end to end at least twice before demo day.

---

## 19. Backend Integration Issues

Findings from auditing the backend **specifically from a frontend-integration perspective**. **Antigravity must not fix these unilaterally.** Report them; work around them as described.

### 🔴 Blocking

**🔴-1 — No CORS middleware.**
`app/main.py` registers no `CORSMiddleware`; a grep for `CORS`/`allow_origins` across `app/` returns nothing. Any browser calling the API from a different origin (a Vite dev server on `:5173`, or any deployed frontend host) will have every response blocked.
*Impact:* blocks all browser-based frontend work without mitigation.
*Frontend workaround (use this):* the Vite dev proxy in §16.1 — same-origin requests, no backend change, works for the entire hackathon.
*Backend fix required before any non-proxied deployment (owner's call, not Antigravity's):* register `CORSMiddleware` with the frontend origin allowlisted.

### 🟠 Important

**🟠-1 — Datetimes are naive UTC with no timezone marker.**
Verified: `"created_at": "2026-08-28T18:48:46.312764"`. Every timestamp in every response is affected. `new Date(...)` in a browser interprets these as local time, silently shifting every displayed clock, every "minutes ago", and every trend timestamp by the local UTC offset.
*Impact:* wrong times everywhere, in a system whose entire value proposition is time intelligence. Silent — nothing errors.
*Frontend workaround:* the mandatory `parseBackendUtc` helper (§12.4), applied universally, plus the regression test in §18.3.

**🟠-2 — `POST /cases/{id}/self-reported-worsening`, `/ambulance/delay` and `/identity/propose` are unauthenticated, and `case_id` is a guessable-length UUID.**
These are documented, deliberate design decisions (kiosk/caregiver mode and paramedic actions must be frictionless, and no PATIENT or PARAMEDIC role exists in the three-role mock). They are correctly scoped — none of them changes acuity.
*Impact:* acceptable for a prototype; would need a scoped patient token in production.
*Frontend action:* none. Do not add a login gate to the patient view — that would break a stated requirement.

**🟠-3 — No "close the loop" mutation on the flagged-for-review queue.**
`GET /overrides/flagged-for-review` is read-only; `EventStore` has no method to mark a flagged de-escalation as reviewed. The backend documents this as deliberately unscoped follow-on work.
*Impact:* the retrospective-review queue grows monotonically and cannot be cleared from the UI.
*Frontend action:* render it read-only with an explicit note. **Do not add a disabled "Mark reviewed" button** implying a missing feature.

**🟠-4 — No case disposition / discharge endpoint.**
`CaseStatus.DISPOSED` exists in the enum, but no route or store method ever sets it. Every seeded case stays `ACTIVE` forever.
*Impact:* the queue only grows during a demo; wait-time "service minutes" are approximated from resource assignment rather than a real completion event (documented in `app/ops/wait_time.py`); Phase 6.3's fifth stuck pattern ("disposition decided, not executed") cannot exist.
*Frontend action:* do not build a discharge button. If the demo needs a shorter queue, use `POST /resources/{id}/release` and a fresh database.

### 🟡 Minor

**🟡-1 — 404 detail strings carry embedded single quotes.**
`NotFoundError` extends `KeyError`, so `str(exc)` yields `"'No case nope'"` — verified live. Displaying it raw shows stray quotes.
*Frontend workaround:* strip leading/trailing quotes in `ApiError.displayMessage()`, or use a generic "Not found" message.

**🟡-2 — `GET /cases` has no `hospital_profile_id` filter.**
`EventStore.list_cases` filters only by `status`. Every other list endpoint is profile-scoped.
*Impact:* nil today (only the `default` profile exists) but inconsistent, and it will silently mix profiles if a second one is ever added.
*Frontend workaround:* filter client-side on `hospital_profile_id` when building any case list.

**🟡-3 — No batch observation endpoint.**
Recording a full vitals set is 7 sequential POSTs, each triggering a full bypass evaluation and rescore.
*Impact:* ~7 round trips and 7 intermediate `RiskAssessment` rows per vitals entry; the acuity visibly "settles" as the fields land. Correct, just chatty — and arguably a good demo of continuous re-evaluation.
*Frontend workaround:* post sequentially, show one aggregate progress indicator, invalidate once at the end. **Never post in parallel** — that risks a rescore against a partial set.

**🟡-4 — The hospital profile is not exposed over HTTP.**
`default.yaml` holds staleness windows, reassessment intervals, acuity band tables, dismissal vocabularies and the alert budget target, but there is no `GET /hospital-profile` endpoint.
*Impact:* the frontend cannot show "SpO2 goes stale after 30 minutes" or the per-acuity reassessment targets except where a response already includes them.
*Frontend workaround:* use only what responses carry — `reassessment.interval_minutes` on a `QueueEntry`, `target_alerts_per_nurse_per_hour` on the budget report, and `missing_reason: "STALE"` on a breakdown row. **Do not hardcode the YAML values into the frontend**; they are hospital-configurable by design and a copy would silently drift.

**🟡-5 — `time_critical_pathway_flag` is always `false`.**
Documented: no pathway-flagging engine (STEMI/stroke/sepsis) exists; the sort key is wired for a future one.
*Frontend action:* do not build UI for it. Do not render a "no time-critical pathway" indicator.

**🟡-6 — `HumanDecisionAction.MODIFY` always returns 400.**
It is a schema-complete enum value with no defined behaviour.
*Frontend action:* exclude it from every override control.

**🟡-7 — `POST /demo/seed` and `/demo/surge` are unauthenticated and non-idempotent.**
Repeated calls create additional batches.
*Frontend workaround:* a confirmation dialog stating this explicitly, and keep the demo console off the default nav for non-presenter roles.

### 🔵 Observations (no action needed)

**🔵-1 — Four GET endpoints have documented write side effects** (`/queue`, `/alerts`, `/ops/stuck-patients`, `/control-tower`). This substitutes for a scheduler and is thoroughly documented in the backend's own module docstrings. It is why polling is load-bearing rather than merely convenient. Frontend consequence: single shared query keys, no aggressive retry, pause on hidden tab.

**🔵-2 — No real-time transport.** Polling at 3 s is the architecture's own sanctioned alternative.

**🔵-3 — No pagination on any list endpoint.** Fine at demo scale.

**🔵-4 — `sex` is a free string with no enum.** Feeds equity subgroup reporting; the UI should offer a consistent set of options so subgroups do not fragment, while still accepting what the backend returns.

**🔵-5 — Resource registry starts empty.** Not a bug — but it means capacity tiles read zero and every assignment 409s until the ops screen is used. Checkpoint 5 addresses this.

**🔵-6 — LLM endpoints degrade to 200 with a status flag, never an error status.** `IntakeOutcome` and `ExplanationResult` both carry explicit availability/fallback fields. This is a well-designed contract; render the flags rather than treating absence as failure.

**🔵-7 — `interventions_already_performed` is always `[]` by construction** (no intervention data model exists). The field is present so the Phase 7.3 shape is complete. Must be labelled as not-recorded, never as "none performed".

**🔵-8 — 312 backend tests pass** (`.venv/bin/python -m pytest -q` → `312 passed`). The API surface is stable to build against.

---

## 20. Environment Configuration

### 20.1 Backend (already configured; for reference)

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite:///<repo>/patienttriage.db` | SQLAlchemy DSN |
| `AUTH_SECRET_KEY` | `dev-only-insecure-secret-DO-NOT-USE-IN-PRODUCTION` | JWT HS256 signing key |
| `GROQ_API_KEY` | unset | LLM key. **Unset is a supported state** — intake and explanation fall back deterministically |

Start command: `cd AIC_backend && .venv/bin/uvicorn app.main:app --reload` (serves on `http://127.0.0.1:8000`).

### 20.2 Frontend

`frontend/.env.example` (commit this; never commit a real `.env`):
```bash
# Base URL for API calls. In dev this is the Vite proxy prefix, NOT the backend URL.
VITE_API_BASE_URL=/api

# Hospital profile every profile-scoped endpoint is called with.
# "default" is the only profile that exists (app/config/hospital_profiles/default.yaml).
VITE_HOSPITAL_PROFILE_ID=default

# Backend origin the Vite dev proxy forwards to. Used by vite.config.ts only.
VITE_BACKEND_ORIGIN=http://localhost:8000
```

`.env.development` mirrors the above. For a build served from the same origin as the API, set `VITE_API_BASE_URL` to the API root; for any cross-origin deployment, **backend CORS is required first** (§19 🔴-1).

**Rules:** no URL literal outside `config.ts` and `vite.config.ts`; no secret of any kind in the frontend (there is no frontend-held credential in this system — the JWT comes from the login response); `.env*` files other than `.env.example` are gitignored.

### 20.3 Local run order

```bash
# terminal 1
cd AIC_backend
.venv/bin/uvicorn app.main:app --reload

# terminal 2 (optional, once, for demo data)
curl -X POST 'http://localhost:8000/demo/seed?hospital_profile_id=default'

# terminal 3
cd frontend
npm install
npm run dev        # http://localhost:5173
```

**To reset the demo:** stop uvicorn, delete `AIC_backend/patienttriage.db`, restart, re-seed. There is no reset endpoint.

---

## 21. Final End-to-End Workflow

The complete verified path, matching the architecture's Phase 11.C journey and Phase 11.H continuous loop.

```
1.  Presenter opens the app        → GET /health              → connection dot green
2.  Selects "Nurse"                → POST /auth/login         → token + Nurse Priya Nair
3.  Seeds the demo                 → POST /demo/seed          → 20 DemoScenario rows
4.  Opens /queue                   → GET /queue (3s poll)     → 20 rows, acuity-ordered
5.  Registers a walk-in            → POST /cases              → 201, ACTIVE, initial abstention
6.  Records 7 vitals               → 7× POST .../observations → bypass check + rescore per write
7.  Queue updates                  → GET /queue               → new row appears at its acuity position
8.  Opens the case                 → GET /cases/{id}          → acuity + confidence painted immediately
9.  Explanation streams in         → GET .../explanation      → labelled AI or rule-based per fallback_used
10. ML disagreed downward          → (same assessment)        → min() invariant callout rendered
11. Nurse escalates                → POST .../override        → instant, no reason, row moves up
12. Nurse de-escalates another     → POST .../override        → target + reason required, flagged_for_review
13. Audit record shown             → GET .../decisions        → full record on screen
14. Patient taps "I feel worse"    → POST .../self-reported-worsening → REASSESSMENT_OVERDUE on the queue
15. Doctor opens their view        → GET .../doctor-view      → "what changed since you last looked"
16. Doctor marks reviewed          → POST .../mark-reviewed   → cursor advances for that doctor only
17. Charge nurse assigns a space   → POST .../assign-resource → 409 → conflict panel + candidate actions
18. Creates a space, reassigns     → POST /resources, assign  → 200; patient stage → IN_TREATMENT
19. Ambulance case opens           → POST /cases (AMBULANCE)  → PRE_ARRIVAL, ETA clock starts
20. Paramedic adds vitals          → POST .../observations    → provisional acuity computed
21. ED reads the pre-alert         → GET .../pre-alert, /eta  → predicted band + narrowing range
22. Identity confirmed by a human  → propose → confirm        → identity_link_status: CONFIRMED
23. Patient arrives                → POST .../arrival         → same case_id enters the queue
24. Control tower watched          → GET /control-tower       → five tiles, all actionable
25. Alerts monitored               → GET /alerts, /alerts/budget → 3 alert types, live budget meter
26. Surge triggered                → POST /demo/surge         → queue triples, ordering holds, alerts stay flat
27. Ops list checked               → GET /ops/stuck-patients  → operational only, acuity untouched
28. Admin reviews equity           → GET /overrides/monitoring → subgroup stats + mandatory caveat
29. Network killed                 → GET /health fails        → banner + last good data retained
30. Paper fallback printed         → GET /queue/printable     → plain-text snapshot, printed
```

Every arrow above corresponds to an endpoint verified to exist in §6.

---

## 22. Definition of Done

The frontend is complete when **all** of the following hold.

**Functional**
- [ ] All 11 checkpoints pass their own pass criteria.
- [ ] All 14 routes in §9 implemented and reachable.
- [ ] Every endpoint the plan assigns to a screen is wired; **no endpoint outside §6 is called.**
- [ ] All three roles log in and see correctly-scoped navigation.
- [ ] The full 30-step workflow in §21 runs from the UI with no terminal use except starting the servers.

**Clinical safety**
- [ ] The queue is never client-sorted.
- [ ] Acuity, confidence, trend, wait time and attention flags are never recomputed client-side.
- [ ] The patient view leaks no clinical interpretation (automated test proves it).
- [ ] `ml_probability` and `confidence_score` appear only in an explicit technical disclosure.
- [ ] Escalate is one tap; de-escalate requires target + reason; `MODIFY` is never offered.
- [ ] The capacity conflict is presented as a decision, never as a downgrade.
- [ ] `points: null` never renders as `0`.
- [ ] Every displayed vital carries its age.

**Integration**
- [ ] No CORS error in any environment used (dev proxy configured).
- [ ] All timestamps parsed via `parseBackendUtc`; no raw `new Date(apiString)` in the codebase.
- [ ] 400 / 401 / 403 / 404 / 409 / 409-capacity / 422 each take a distinct, correct branch.
- [ ] The four side-effecting GETs are polled once per interval, pause when hidden, and are not aggressively retried.
- [ ] Cache invalidation matches §11.4.

**Quality**
- [ ] T1–T32 all pass against a live backend, results recorded.
- [ ] Every data surface has loading, empty, error and success states.
- [ ] Lighthouse accessibility ≥ 90 on `/queue`, `/patient/:id`, `/control-tower`.
- [ ] Full keyboard-only demo run completed.
- [ ] Greyscale render fully interpretable.
- [ ] `tsc --noEmit` clean under `strict`; no `any` in `types/api.ts`.
- [ ] No console errors during a 10-minute polling session.
- [ ] `frontend/README.md` lets an unfamiliar person run the demo.

**Backend integrity**
- [ ] **Zero files changed under `AIC_backend/app/`.** `git diff` (or a file-mtime check) proves it.
- [ ] Any newly-discovered backend gap is appended to §19 with a severity, not silently patched.

---

## 23. Important Instructions for Antigravity

1. **Do not modify the backend.** Not one file under `app/`. If something appears missing, re-read the relevant route file first — this API is denser than it looks. If it is genuinely missing, append it to §19 with a severity classification and build the documented workaround.

2. **Section 6 is the complete list of endpoints. Section 13 is the complete list of fields.** If you are about to call something not in §6 or read a field not in §13, stop — you are hallucinating. Re-derive from the source: `grep -rn "@router" app/api/` and the matching file in `app/schemas/`.

3. **Verify against the live backend, not against this document.** Start uvicorn, hit `/docs`, and check the shape yourself before wiring a screen. This document was accurate at the time of writing; the code is always the truth.

4. **Solve CORS with the Vite proxy before writing any other code** (§16.1). Everything else is blocked behind it.

5. **Write `lib/datetime.ts` in Checkpoint 1** (§12.4). Retrofitting it means auditing every component that displays a time — which is most of them.

6. **Never sort the queue.** The array order from `GET /queue` is a clinical decision the backend already made. Add the comment; keep it there.

7. **Never recompute a clinical value.** Acuity, confidence, trend, wait time, attention flag, one-line presentation — all arrive pre-computed. Render them.

8. **The patient view is a hard boundary.** No acuity, no confidence, no probability, no queue position, no other patient, and no request to an endpoint that returns any of those. Write the automated leak-guard test in Checkpoint 8.

9. **Escalate has no friction; de-escalate has a lot.** That asymmetry is a deliberate safety design (Phase 9.6) enforced server-side. Do not add a confirmation dialog to escalate, and do not try to make de-escalate smoother.

10. **The emergency-bypass button has no confirmation dialog.** It is the software equivalent of a physical panic button.

11. **A 409 capacity conflict is a designed outcome, not an error.** Render the panel with `candidate_actions`. Never suggest downgrading the patient to fit capacity — that is precisely the failure the backend refuses to make.

12. **LLM absence is a first-class state, not a failure.** `llm_available: false` and `fallback_used: true` are normal, expected, and worth showing honestly. The system is designed to work with no LLM at all, and the demo's strongest moment depends on that being visible.

13. **Poll; do not build a websocket.** There is no real-time transport, and 3-second polling is the architecture's own recommendation.

14. **Respect the side-effecting GETs.** One shared query key per endpoint, pause on hidden tabs, no aggressive retry.

15. **Capture fixtures from the real backend.** Never hand-write one — that is how invented fields get in.

16. **Build in checkpoint order.** Checkpoint 3 (the queue) is the first point at which the product is demonstrable; do not skip ahead to secondary screens before it is solid.

17. **Where you must guess, say so.** Mark any assumption in a code comment as `[Assumption]`, matching the backend's own convention. Do not silently invent a threshold, a colour meaning, or a clinical label.

18. **Read these before starting:** `app/api/cases.py` (the largest surface), `app/schemas/` (every response shape), `app/models/enums.py` (every vocabulary), `app/queue/models.py` (the queue row), and Phase 8 of `patienttriage-round2-architecture-review.md` (what each screen is for). Budget an hour; it will save a day.

---

## Appendix A — Accuracy audit

Performed before finalising this document.

| Check | Result |
|---|---|
| Every endpoint mentioned exists | ✅ Cross-checked against the app's own `/openapi.json` (49 operations); every endpoint in §6 appears there and no invented path is referenced |
| Every request field exists | ✅ Read from `app/schemas/*.py` and `app/auth/models.py`; required/optional status taken from the Pydantic defaults |
| Every response field exists | ✅ Read from the schema classes and confirmed against live JSON from a `TestClient` run |
| No non-existent endpoint invented | ✅ |
| No frontend feature depends on an unsupported backend capability | ✅ Discharge/disposition, doctor assignment, candidate identity search, intervention tracking, batch observations, hospital-profile read, and flagged-review closure were all considered and **excluded**, each documented in §19 |
| User workflow matches the architecture | ✅ §5 and §21 follow Phase 11.C (patient journey) and Phase 11.H (continuous loop); screens follow Phase 8.1–8.5 |
| Frontend does not duplicate backend logic | ✅ §2 rule 3 and §11.5 forbid recomputing any clinical value; the queue-order and no-recompute constraints are pass criteria |
| Backend responsibilities stay in the backend | ✅ Scoring, confidence, abstention, ordering, wait time, alerting, staleness and conflict detection are all consumed, never reimplemented |
| Frontend responsibilities stay in the frontend | ✅ Presentation, navigation, form validation UX, polling cadence, cache invalidation, accessibility |
| Error statuses verified | ✅ 401, 403, 404, 400 (three distinct override messages), 409 (capacity, with body), 422 all reproduced live |
| Enum values verified | ✅ Copied from `app/models/enums.py`, `app/auth/roles.py` |
| Concept codes verified | ✅ Copied from `app/scoring/concepts.py` |
| Event types verified | ✅ Extracted from `app/store/event_store.py` (29 store-emitted values) plus `AI_UNAVAILABLE` from `app/llm/intake.py` |
| Backend test suite | ✅ `312 passed` |

**Marked `UNVERIFIED` in this document:**
- `PS.pdf` as a source of frontend requirements — not machine-read for this plan.
- Runtime language switching (`language_set: [en, hi]` exists in config, but no endpoint serves translated strings).
- The exact production deployment origin, and therefore the exact CORS allowlist the backend would need.

**Nothing else in this document is unverified.** Every endpoint, field, status code and enum value was read from the source and, where reachable, exercised live.
