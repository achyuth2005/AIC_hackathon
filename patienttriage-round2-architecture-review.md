# PatientTriage.ai — Round 2 Architecture Critique and Improved Design

Accenture Innovation Challenge 2026, Problem Track 2.
Prepared as a critique-first review of the existing concept, followed by the strengthened architecture.

**How to read this:** Phases 1 to 10 are the critique and component-level redesign. Phase 11 is the consolidated final architecture. Phases 12 to 20 are the pitch and build layer. If you are short on time, read the Executive Summary, Phase 3, Phase 11, Phase 13 and Phase 19.

**Convention used throughout:** anything stated as clinical fact is sourced in the References section. Anything not sourced is labelled **[Assumption]** or **[Requires clinical validation]**. No performance numbers, cost savings, or thresholds have been invented.

---

## Executive Summary — the five changes that matter most

Your concept is strong and the scope is coherent. It does not need replacing. Five changes carry almost all the value:

**1. Invert the AI hierarchy. Rules set the floor, ML can only raise.**
Right now severity flows out of an LLM at the end of the pipeline. That is the single most attackable design choice in the whole system. Replace it with a deterministic, age-banded, published-framework scoring engine that produces the acuity level, and let the ML model act as a *challenger* that can escalate a patient but can never place them below the deterministic floor. This one invariant simultaneously solves explainability, pediatric safety, the missing-training-data problem, the under-triage asymmetry and the "what if the AI is wrong" question. Everything else in this document is downstream of it.

**2. Waiting time must never change acuity. It must trigger a re-look.**
The naive rule you correctly flagged (longest waiting patient eventually wins) is avoided not by weighting time more cleverly, but by removing time from the acuity calculation entirely. Waiting time orders patients *within* an acuity band and forces mandatory reassessment when a band's target is exceeded. A patient only moves up because new information says so. Pitch line: **waiting does not make you sicker, waiting makes us look again.**

**3. Your real innovation is not the triage score. It is what happens after it.**
Triage scoring is a solved and commoditised problem, and judges know it. Continuous re-triage of the waiting room, separating clinical deterioration from operational stalling, and treating time as a monitored asset are much less well served by existing tools. Lead the pitch with the Guardian Queue and Stuck Patient Detection, not with "we built an AI that scores patients."

**4. Cut roughly a third of the scope.**
Medication inventory, prescriptions, in-hospital turn-by-turn navigation, ambulance dispatch and full bed management belong to the hospital information system, not to a triage assistant. They add build cost, integration risk and judge-facing attack surface without improving Time-to-Right-Care. Removing them out loud, with reasoning, reads as product maturity.

**5. Design the failure mode first.**
The system must still be useful when there are no connected devices, no internet, and no LLM. If the AI layer is removed, you should be left with a digital triage form, a timer, and a queue that still catches overdue reassessments. That degraded mode is the version most Indian district hospitals would actually run, and it is also your answer to the hardest judge question.

---

# PHASE 1 — Your existing architecture, reconstructed

Before critiquing, here is your solution restated precisely so you can confirm I have it right.

### Core concept
PatientTriage.ai is not a triage scoring model. It is a **centralised emergency-care coordination platform** built around a single longitudinal patient case that begins at first contact (which may be in an ambulance, before the hospital has ever seen the patient) and continues until disposition. AI is used for rapid information synthesis, preliminary risk estimation, prioritisation, continuous monitoring and coordination. Clinicians retain all decision authority. The optimisation target is **Time-to-Right-Care**, not diagnostic accuracy.

### Users and surfaces
- **Patient / caregiver** — conversational symptom capture, stage visibility, wait window, worsening report.
- **Nurse** — prioritised queue, AI summaries, risk and confidence, data entry, override, escalation.
- **Doctor** — assigned patients, synthesised history, trends, results, pending actions, final authority.
- **Paramedic** — pre-hospital capture, vitals, interventions, ETA, pre-alert.
- **ED operations / control tower** — department-level situational awareness (implied fifth surface).

### Inputs
- **A. Historical** — prior conditions, visits, allergies, medications, diagnoses, treatments. Empty for first-time patients. Intended to be relevance-filtered rather than dumped into an LLM.
- **B. Live** — patient-reported (speech, text, multilingual), nurse-observed, doctor-entered, machine-measured vitals.
- **C. Pre-hospital** — paramedic voice and structured entry, ambulance monitor data where available, ETA.

### AI components (as currently specified)
Transcription, natural-language understanding, symptom extraction, free-text to structured schema conversion, adaptive follow-up questioning, summarisation, a single ML risk-scoring model, LLM interpretation of the risk score, and LLM-generated explanation of severity.

### Non-AI components
Event-sourced patient state store, time tracking, queue management, resource repository, waiting-time estimation, emergency bypass path, audit and override logging, notifications.

### Data flow
`history + live + pre-hospital → LLM → structured record → ML risk model → risk score → prioritisation logic → LLM explanation → clinician recommendation`, with the clinician's response feeding back as new input.

### Clinical workflow
Arrival (walk-in or ambulance) → intake capture → risk estimation → severity assignment → queue placement → nurse review with accept/modify/override → doctor assignment → investigation and treatment → disposition. Overridable at every point.

### Operations workflow
Resource repository (staff, rooms, bays, beds, ICU, diagnostics, inventory) feeds assignment, routing, wait prediction, bottleneck detection and ambulance preparation, surfaced through a control tower view.

### Feedback loops (three, and they are the interesting part)
1. **Active Triage** — system identifies the highest-value missing information, requests it, recalculates on arrival of that information.
2. **Guardian Queue** — every waiting patient is continuously re-evaluated against new data, trends, elapsed time and overdue reassessment.
3. **Override loop** — clinician correction updates state, which triggers recalculation and is logged.

### Time logic
Time is a first-class input: onset, arrival, waiting, since-last-reassessment, since-last-vitals, since-last-clinician-contact, per-stage duration, result latency, next-action due, ambulance ETA.

### Ambulance integration
Case created pre-arrival, paramedic capture, pre-alert to hospital, ETA estimated from outbound journey duration.

**If any of the above misstates your intent, correct it before using the rest of this document, because Phases 2 to 20 build on it.**

---

# PHASE 2 — Critical evaluation

## 2.1 Component-level critique

| Component | What is strong | Problem / risk | Severity | Recommended response |
|---|---|---|---|---|
| **Single longitudinal patient case (event-sourced)** | The best decision in your architecture. Gives audit, replay, trend detection, and multi-source reconciliation for free. Correctly refuses to let the LLM "remember" the patient. | Event schema is not yet specified, so "AI-inferred" and "machine-measured" facts risk being stored at equal weight. | Medium | Add source, reliability tier and measurement status to every observation (Phase 4). Keep the design. |
| **LLM → ML → LLM pipeline** | Reasonable first sketch; separates understanding from scoring. | The final LLM stage assigns or interprets severity. A generative model is non-deterministic, uncalibrated, and cannot be validated as a medical decision component. Also adds latency exactly where you can least afford it. | **Critical** | Severity becomes deterministic. LLM narrates, never decides (Phase 3). |
| **Single ML risk model for all ages** | Simple, buildable. | The problem statement explicitly names this as a silent safety risk. Adult-calibrated physiology applied to a 3-year-old or an 85-year-old is unsafe, and this is the failure mode a clinical judge will test first. | **Critical** | Age-band routing to distinct scoring logic and reference ranges before any model runs (Phase 3.3). |
| **Emergency bypass** | Correctly identified as necessary. Correctly refuses to make care wait for AI. | Undefined trigger mechanism. Keyword matching is brittle; LLM detection is unreliable for a life-critical path. | **Critical** | Three redundant, escalation-only detectors with a human-first affordance (Phase 3.5). |
| **Patient conversational intake** | Genuinely reduces nurse data-gathering load and is demo-friendly. | Assumes a distressed, possibly elderly, possibly non-literate patient will complete a chat flow in an ED lobby. Also risks being perceived as the system giving clinical advice. | High | Keep, but reposition as optional pre-registration with kiosk and nurse fallback. Never blocks triage. Never shows the patient a risk output (Phase 8.1). |
| **Adaptive / Active Triage** | The strongest genuinely differentiating idea in the concept. Information-value-driven data collection is real and underused. | If the LLM freely chooses what to ask or when to repeat vitals, the system is effectively practising medicine. | High | Deterministic policy engine picks *what* to ask from a hospital-configured list; LLM only phrases it (Phase 3.4). |
| **Time as first-class input** | Correct and underrated. Most triage tools ignore time after the initial score. | "Time influences priority" is currently unspecified. Any weighted-sum formulation eventually lets a low-acuity patient outrank a critical one. | High | Lexicographic ordering, and time drives reassessment rather than acuity (Phase 5). |
| **Guardian Queue** | Directly answers a mandatory Round 2 requirement (monitoring the waiting queue). Strong differentiator. | Risk of alert fatigue if every state change notifies. Evidence from paediatric early-warning literature shows how quickly added trigger criteria multiply alerts (see References, Bell et al.). | High | Alert budget, tiered notification, ambient-by-default surfacing (Phase 8.5). |
| **Stuck Patient Detection** | Excellent, and rare. Separating operational delay from clinical deterioration is a genuine insight. | Currently a list of examples rather than a rule set. Needs a definition of "stuck." | Medium | Define as: expected next event has not occurred within its configured window. Route to ops, never to acuity (Phase 6.3). |
| **Hospital resource repository** | Useful for routing and the control tower. | Scope creep. Medication inventory, full bed management and equipment tracking are HIS functions, not triage functions. Each adds integration burden with no Time-to-Right-Care benefit. | High | Cut to three MVP resources (Phase 6.1). |
| **Waiting-time prediction** | Real patient-experience value; reduces reception load. | A wrong estimate is a trust-destroying, potentially unsafe output. Estimating consultation duration requires history you do not have. | Medium | Show a widening range with an explicit "may change" caveat, computed from a simple queue model, not ML (Phase 6.4). |
| **Ambulance ETA from outbound trip time** | Cheap and requires no integration. | The assumption is unsound. Outbound legs are often driven under emergency conditions, return legs frequently are not; traffic is directional and time-varying; on-scene time is highly variable and is not part of either leg. | Medium | GPS plus routing API, degrading to paramedic-declared ETA bands (Phase 7.2). |
| **Prescriptions in the patient app** | Patient-friendly. | Out of scope. Prescribing, dispensing and medico-legal record-keeping belong to the HIS/EMR. Adds regulatory exposure with no triage benefit. | Medium | Remove from MVP and from the pitch. |
| **Override logging** | Correctly specified fields. | Treats upward and downward overrides symmetrically, which contradicts the asymmetric-cost principle you correctly stated elsewhere. | Medium | Asymmetric override friction (Phase 9.6). |
| **Control tower** | Strong for the leadership-facing part of the pitch. | Easy to over-build into a dashboard with 15 tiles nobody reads. | Low | Five tiles maximum, all actionable (Phase 8.4). |

## 2.2 Direct answers to your questions

**What is already strong.** The single live patient state. The three feedback loops. Time as a first-class citizen. Pre-arrival continuity. The explicit refusal to replace clinicians. Framing the objective as Time-to-Right-Care rather than triage accuracy, which is a better product thesis than most teams will bring.

**What is genuinely innovative.** Active Triage (information-value-driven collection), Guardian Queue (continuous re-triage), and Stuck Patient Detection (clinical versus operational delay separation). Everything else in the concept exists commercially in some form.

**What is weak.** Severity produced by an LLM. One risk model across all ages. Undefined emergency bypass. Time influencing priority through an unspecified mechanism. Patient chat assumed to be the default intake path.

**What is missing.** A defined confidence model. An abstention path. A degraded mode when AI or connectivity fails. Handling of contradictory inputs. Data staleness rules. Subgroup performance measurement. Identity matching for the ambulance-to-ED handover. A configuration layer that lets the same product run in a 100-visit and a 500-visit ED.

**What could fail technically.** LLM latency in the intake path. Schema drift from unconstrained LLM output. Event ordering when device timestamps disagree with server time. WebSocket state divergence during a surge demo.

**What could fail clinically.** Silent under-triage in paediatric and geriatric patients. Missing data imputed as normal. Patient under-reporting of pain, which the ESI handbook itself flags as a real triage bias issue. Over-trust in a confidently phrased LLM summary.

**Unrealistic assumptions.** That most hospitals have device integration. That patients will reliably complete a chat intake. That an outbound ambulance leg predicts the return leg. That you can train a credible clinical risk model on synthetic data.

**Where you are over-engineering.** Medication inventory, prescriptions, navigation, bed management, doctor-level service-time modelling, differential diagnosis generation.

**Where you are under-engineering.** Confidence and abstention. Failure modes. Age stratification. Configuration and multi-hospital flexibility.

**What introduces unnecessary latency.** LLM in the critical path before a severity level exists. Fix by scoring deterministically first and streaming the narrative afterwards.

**What creates safety risk.** Any path where a generative model can lower a patient's priority.

**What causes alert fatigue.** Notifying on every priority recomputation.

**What is hard to demo.** Device integration, real ambulance GPS, multilingual speech, ML validation. Simulate all four and say so.

**What distracts from the core idea.** Inventory, prescriptions, navigation, and any claim about diagnosis.

**What judges will challenge immediately.** "Why is this better than ESI plus a nurse?", "What was your model trained on?", "Who is liable when it under-triages?" All three are answered in Phase 19.

---

# PHASE 3 — Challenging the AI architecture

## 3.1 The governing principle

> **Deterministic logic sets the floor. Machine learning may raise the level. Generative AI may only describe, question and structure. It may never decide.**

Formally, with 1 as most urgent:

```
final_acuity = min(rule_based_acuity, ml_suggested_acuity, override_acuity_if_escalating)
```

The ML model can move a patient from level 3 to level 2. It cannot move them from 2 to 3. The LLM appears nowhere in this expression. This is a one-line safety property you can put on a slide and defend against any question in the room.

## 3.2 Responsibility assignment

| Responsibility | Correct owner | Reasoning |
|---|---|---|
| Speech to text | **Dedicated ASR service** | Streaming latency, medical and Indic vocabulary, offline fallback, and cost. Routing audio through a general LLM is slower and harder to swap out. |
| Language detection and translation | ASR / translation service | Same reasoning. Keep it a replaceable component. |
| Clinical entity extraction from free text | **LLM, schema-constrained** | This is the task LLMs are genuinely best at. Force structured JSON output and validate it against a schema; reject and retry rather than accept malformed output. |
| Mapping extracted terms to coded concepts | **Deterministic lookup** over a curated vocabulary subset | The LLM proposes candidates; a controlled terminology table decides. Prevents invented concepts entering the clinical record. |
| Converting text to numerical model features | **Deterministic code** | An LLM must never emit a number that feeds the risk model unvalidated. Values pass through range checks and unit normalisation. |
| Vital sign abnormality flagging | **Deterministic, age-banded tables** | Must be inspectable, reproducible and configurable per hospital. |
| Base acuity level | **Deterministic published framework** | Auditable, defensible, already clinically accepted. See 3.3. |
| Supplementary risk estimate | **ML, escalation-only** | Adds trend and pattern sensitivity that fixed rules lack, without owning the decision. |
| Choosing the next question or measurement | **Rules/policy engine**, phrased by LLM | Deciding what clinical information to gather next is a clinical act; phrasing it is not. |
| Confidence computation | **Deterministic formula** | A model self-reporting its own confidence in prose is not calibration. |
| Severity / priority assignment | **Deterministic policy** | See 3.1. |
| Explanation and summary | **LLM, evidence-grounded** | Constrained to narrate only structured facts passed in the prompt. No new clinical content. |
| Differential diagnosis suggestions | **Nobody. Out of scope.** | Turns a prioritisation tool into a diagnostic device, with the regulatory and liability profile that implies. Saying "we deliberately do not do this" is a strength in the pitch, not a gap. |
| Queue ordering, timers, stuck detection | **Deterministic code** | No AI required. This is where much of your actual value sits. |

## 3.3 The risk model: what to actually build

**Do not build one model.** Build a layered scoring stack:

**Layer 1 — Age-band router (deterministic).**
Patient is routed by age into paediatric, adult or geriatric logic before anything else happens. Each band has its own reference ranges and its own escalation triggers. This is not an optimisation, it is a safety requirement, and it directly answers a complexity the problem statement calls out by name.

**Layer 2 — Published framework backbone (deterministic).**
Adopt an existing, citable framework rather than inventing one:
- **Adults:** NEWS2 (Royal College of Physicians, 2017), which aggregates respiratory rate, oxygen saturation, systolic blood pressure, pulse, consciousness or new confusion, and temperature, with additional points for supplemental oxygen. Note it was developed for non-pregnant adults aged 16 and over, which is precisely why you need the age router.
- **Paediatrics:** a PEWS-family score. NHS England has been standardising PEWS in paediatrics, and PEWS variants combine age-specific vital sign thresholds with qualitative signs such as work of breathing and consciousness. The ED-PEWS variant has been evaluated specifically in emergency-department and low- and middle-income-country settings, which is relevant if you assume an Indian deployment.
- **Acuity banding:** ESI version 5, a five-level scale from 1 (most urgent) to 5 (least urgent), structured around four decision points: does the patient need immediate life-saving intervention, is this a patient who should not wait, how many resources will be needed, and what do the vital signs show. ESI is maintained by the Emergency Nurses Association.

Use these as the interpretable backbone. **[Requires clinical validation]** for any local adaptation, and do not reproduce the copyrighted scoring charts in your deck; cite and link them.

**Layer 3 — ML challenger (escalation-only).**
A calibrated classifier estimating probability of a critical outcome, using features the fixed frameworks ignore: vital *trends* rather than single readings, time since onset, arrival mode, history flags, symptom co-occurrence, and explicit missingness indicators. Output is a probability plus a suggested level. If it suggests a *higher* acuity than the rules, it escalates and the reason is shown. If it suggests lower, the suggestion is logged for evaluation and discarded operationally.

**Layer 4 — Hard escalation triggers (deterministic, override everything).**
A small set of hospital-configured single-parameter triggers that force top acuity regardless of aggregate score. This mirrors how real early-warning systems work: persistent single-parameter abnormalities warrant escalation even when the aggregate score is low.

**Handling missing data.** Never impute missing values to normal. Every field carries a measurement status. Missingness *reduces confidence and increases escalation propensity*. A patient with no vitals recorded is an unknown, and unknown is treated as potentially dangerous, not as fine.

**First-time versus returning patients.** History is an *additive* signal only. The model must perform acceptably with the history block entirely absent, because roughly half of arrivals will have no record. Build and evaluate the no-history case first, then measure how much history adds.

**Hackathon recommendation:** build Layers 1, 2 and 4 properly, and Layer 3 as a simple calibrated model (logistic regression or gradient boosting) that is honestly presented as a mechanism demonstration. **Production recommendation:** Layer 3 retrained on retrospective ED data with clinician-adjudicated labels, validated in silent shadow mode before it is ever allowed to escalate a real patient.

## 3.4 Active Triage without letting the LLM practise medicine

The next-information decision is made by a deterministic policy:

1. Build the set of fields relevant to the presenting complaint category, from a hospital-configured template.
2. Filter to fields currently unknown, stale, or flagged unreliable.
3. Rank by information value: how much would knowing this change the acuity level or the confidence band? For the rules backbone this is directly computable, since you can recompute the score across the plausible range of the missing value and see whether the band changes.
4. Filter by feasibility: is the equipment available, is the patient able, has the minimum re-measurement interval elapsed.
5. Emit the top one or two requests. The LLM converts them into patient-appropriate or nurse-appropriate phrasing.

This is defensible, explainable, and it is the version of "adaptive AI triage" that survives contact with a clinician.

## 3.5 Emergency bypass: three redundant detectors, escalation only

Keyword matching alone is not sufficient. Neither is an LLM. Use three independent paths, any of which can fire, none of which can cancel another:

1. **Human affordance (primary).** A persistent, single-tap Immediate Escalation control on the nurse, paramedic and reception screens. No AI involved, zero latency, and it is how this actually works today. Any AI-first design that does not have this is answering the wrong question.
2. **Deterministic physiological triggers.** Configured single-parameter red flags evaluated the instant any vital arrives, from device or manual entry. Pure arithmetic, sub-millisecond, no network dependency.
3. **Constrained pattern detection on text.** A curated critical-phrase list plus, optionally, an LLM classifier restricted to a binary escalate/do-not-escalate output. Runs in parallel, never blocks, and can only escalate.

The bypass is not a triage decision. It is an **alert plus a state flag**: the case is marked critical, the resuscitation team is notified, the patient skips all queues, and information gathering continues in parallel while care begins. **Clinical care never waits for the pipeline to finish.**

## 3.6 Should the risk score go back into an LLM before severity assignment?

**No.** Three reasons.

*Determinism.* The same inputs must always produce the same level. A generative model does not guarantee this, and inter-rater reliability is a property triage systems are formally evaluated on.

*Latency.* Deterministic scoring is effectively instantaneous. An LLM call in the critical path adds seconds to a decision that the problem statement says must be made in seconds.

*Accountability.* "The system assigned level 2 because respiratory rate and oxygen saturation each contributed points and the aggregate crossed the configured threshold" is a defensible statement. "The language model considered the context and concluded level 2" is not.

The LLM's correct position is **after** the level exists, generating the human-readable explanation from the structured evidence that produced it. It can even stream in after the level is already on screen, so the nurse never waits for prose.

---

# PHASE 4 — Data architecture

## 4.1 The core principle

**Missing is not normal. Reported is not measured. Inferred is not observed.**

Most clinical AI failures at the data layer come from collapsing these distinctions. Your schema must keep them apart at the storage level, not just in the UI.

## 4.2 Observation record

```
Observation {
  observation_id
  case_id
  concept_code              // controlled vocabulary, not free text
  value                     // numeric | coded | boolean | text
  unit
  source_type               // DEVICE | NURSE | DOCTOR | PARAMEDIC |
                            // PATIENT | HISTORICAL_RECORD | AI_INFERRED
  source_id                 // device serial or staff identity
  reliability_tier          // 1 machine-measured
                            // 2 clinician-observed
                            // 3 patient/caregiver-reported
                            // 4 AI-inferred from unstructured input
  measurement_status        // MEASURED | NOT_MEASURED | UNOBTAINABLE |
                            // REFUSED | UNKNOWN | DEVICE_ERROR
  observed_at               // when it happened in the world
  recorded_at               // when it entered the system
  extraction_confidence     // only for AI_INFERRED
  superseded_by             // never mutate, always supersede
  is_stale                  // derived from concept-specific staleness window
}
```

Three details that matter more than they look:

- **`observed_at` separate from `recorded_at`.** A vital taken in the ambulance and entered on arrival is not a current reading. Without this split, trend detection silently corrupts.
- **Supersession instead of mutation.** Corrections create new records. The original stays. This is what makes your audit trail legally meaningful rather than decorative.
- **`reliability_tier` as a first-class field.** A patient saying their pain is mild and a monitor reporting a saturation value are not the same kind of fact, and the model, the confidence calculation and the UI all need to know that.

## 4.3 Derived and predicted records

Kept separate from observations, and immutable:

```
RiskAssessment {
  assessment_id, case_id, computed_at,
  rule_engine_version, rule_acuity, rule_component_breakdown,
  ml_model_version, ml_probability, ml_suggested_acuity,
  hard_triggers_fired[],
  final_acuity, deciding_layer,
  confidence_band, confidence_reasons[],
  input_snapshot_hash, input_observation_ids[]
}
```

`input_snapshot_hash` plus `input_observation_ids` is what lets you say, months later: *this is exactly what the system saw at 14:32, and this is exactly why it said what it said.* That is the difference between an audit trail and a log file.

```
HumanDecision {
  decision_id, case_id, clinician_id, role, timestamp,
  system_recommendation, clinician_action,   // ACCEPT | ESCALATE | DE_ESCALATE | MODIFY
  resulting_acuity, reason_code, free_text_reason,
  linked_assessment_id
}
```

## 4.4 Event stream

Your event list is good. Keep it, and add: `PATIENT_ARRIVED` (ambulance-to-ED transition, not a new case), `REASSESSMENT_DUE`, `REASSESSMENT_COMPLETED`, `CONFIDENCE_DEGRADED`, `DATA_CONFLICT_DETECTED`, `AI_UNAVAILABLE`, `PATIENT_SELF_REPORTED_WORSENING`.

Every engine in the system is a consumer of this stream. That is what makes the architecture coherent rather than a collection of features.

---

# PHASE 5 — Time intelligence

## 5.1 Three clocks, three consequences

| Clock | Measures | May it change **clinical acuity**? | May it change **operational routing**? | May it raise an alert? |
|---|---|---|---|---|
| **Clinical time** | Symptom onset, deterioration rate, time-critical pathway windows, physiological trend slope | **Yes** | Yes | Yes |
| **Queue time** | Arrival, waiting duration, time in current acuity band, time since last reassessment | **No** | Yes (ordering within band) | Yes (reassessment due) |
| **Operational time** | Time stalled at a process step, result awaiting review, room awaiting cleaning, disposition delay | **Never** | Yes | Yes |

## 5.2 Why waiting time must not touch acuity

Any weighted-sum priority of the form `priority = w1·acuity + w2·wait_time` has a mathematical property that is clinically unacceptable: for a large enough wait, a level 5 patient outranks a level 1 patient. You can tune the weights to make this unlikely, but you cannot make it impossible, and "unlikely" is the wrong safety standard for the highest-severity case in the department.

**Use lexicographic ordering instead:**

```
sort by:
  1. final_acuity                          ascending   (1 first)
  2. time_critical_pathway_flag            descending
  3. deterioration_trend_direction         descending
  4. time_in_current_acuity_band           descending   (fairness, within band only)
  5. arrival_time                          ascending
```

Waiting is now a strict tiebreaker inside a band. A level 4 patient can never overtake a level 2 patient, regardless of how long they have waited. This is provable, trivially explainable to a nurse in one sentence, and it removes an entire class of judge question.

## 5.3 How waiting actually escalates a patient (the legitimate path)

Each acuity band has a hospital-configured reassessment interval. When a patient exceeds it:

1. `REASSESSMENT_DUE` fires. The patient surfaces on the nurse's overdue list.
2. Reassessment collects new observations.
3. New observations re-run the scoring stack.
4. If the patient has deteriorated, acuity rises **because of the physiology, not because of the wait**.

> **Waiting does not make you sicker. Waiting makes us look again.**

That sentence is your entire time-priority defence, and it directly satisfies the Round 2 requirement that the system trigger re-assessment when wait time exceeds safe thresholds for a severity level.

## 5.4 Deterioration trend

Trend is where the ML challenger earns its place. Two readings in the same acuity band moving in the wrong direction is a signal no single-point score captures. Treat trend as clinical time: it may escalate. **[Requires clinical validation]** for any specific slope threshold; make it configurable rather than hard-coded.

---

# PHASE 6 — Resource and operations engine

## 6.1 Scope decision

| Resource | Verdict | Reasoning |
|---|---|---|
| Clinician availability (on shift, current load) | **Essential (MVP)** | Directly determines who sees the patient next. |
| Treatment spaces (bays, cubicles, consultation rooms) | **Essential (MVP)** | The binding constraint on flow in nearly every ED. |
| Resuscitation bay availability | **Essential (MVP)** | Required for the emergency bypass path to mean anything. |
| Diagnostics queue and turnaround | Useful, optional | The dominant driver of stuck patients, but needs integration. Include as a manually updated status in the demo. |
| Inpatient bed / ICU availability | Useful, optional | Read-only signal for disposition planning. Do not attempt to manage it. |
| Staff rostering | Future | HR system territory. |
| Equipment tracking | Future | Low triage value, high integration cost. |
| **Medication inventory** | **Out of scope** | Named in your own document as possible scope creep. It is. Pharmacy is a separate system and a separate problem. Cutting it is the right call and worth saying explicitly in the pitch. |
| **Prescriptions and dispensing** | **Out of scope** | Regulated clinical documentation, belongs in the EMR. |
| **In-hospital turn-by-turn navigation** | **Out of scope** | A nice patient feature that has nothing to do with Time-to-Right-Care and will consume disproportionate build time. Replace with a simple "go to: Bay 4" instruction. |

## 6.2 The capacity safety constraint

**Clinical urgency and resource availability are computed independently and stored separately. Capacity never modifies acuity.**

When a level 2 patient exists and no appropriate space is free, the system does not quietly downgrade them or reorder around the constraint. It raises a **capacity conflict** to the charge nurse: here is a patient who needs a space, here is why none is available, here are the candidate actions (expedite a discharge, use an alternative space, escalate to the on-call team). The system surfaces the conflict. A human resolves it.

Any architecture where a full department makes patients appear less sick is unsafe, and a clinical judge will look for exactly this.

## 6.3 Stuck patient detection

Define it precisely: **an expected next event has not occurred within its configured window.**

| Pattern | Expected event | Configured window | Route to |
|---|---|---|---|
| Test ordered, no sample collected | `SAMPLE_COLLECTED` | Per test type | Nurse ops list |
| Result available, not reviewed | `RESULT_REVIEWED` | Per acuity band | Doctor queue |
| Disposition decided, not executed | `PATIENT_MOVED` | Per destination | Charge nurse |
| Assigned space never occupied | `PATIENT_IN_SPACE` | Fixed | Charge nurse |
| Reassessment overdue | `REASSESSMENT_COMPLETED` | Per acuity band | Nurse (clinical, not ops) |

Note the last row: an overdue reassessment is the one item on this list that is a **clinical** signal, and it is routed differently. That distinction is the whole point of the feature and is worth calling out in the demo.

## 6.4 Waiting-time prediction

Do not use machine learning here. A simple queue model is more defensible and easier to explain:

```
estimated_wait = f(patients ahead in same or higher band,
                   rolling median service time per band,
                   count of available clinicians and spaces)
```

Present it as a **range that widens with uncertainty**, always accompanied by the statement that a more urgent arrival can change it. Never present a single number, and never present it as a commitment. A confidently wrong wait time destroys patient trust faster than no wait time at all.

---

# PHASE 7 — Ambulance architecture

## 7.1 Case continuity

The pre-hospital case and the ED case are **the same record from creation**. Arrival is an event (`PATIENT_ARRIVED`), not a new case. This is the correct design and you already have it.

The gap is **identity matching**. When a paramedic supplies a name or an ABHA identifier, the system must never silently merge into an existing patient record on a fuzzy match. Wrong-patient record merging is one of the most serious errors a health system can make. Design it as: system proposes candidate matches with confidence, a human confirms, the confirmation is logged, and until confirmed the case runs as unlinked. Unlinked simply means the history block is empty, which the model already handles because half your patients arrive that way.

## 7.2 The ETA assumption

**Your assumption that outbound travel time predicts return travel time does not hold**, for four independent reasons:

1. The outbound leg is often driven under emergency response conditions; the return leg frequently is not, and may be deliberately slower for patient stability.
2. Traffic is directional and time-varying. An outbound leg at 17:00 and a return leg at 17:40 are different journeys even on the same road.
3. On-scene time (extrication, stabilisation, loading) is highly variable and belongs to neither leg.
4. The return destination may differ from the origin, for example diversion to a facility with a free resuscitation bay.

**Recommended mechanism, in order of preference:**

- **Production:** periodic GPS position from the paramedic's device plus a routing API ETA, refreshed on an interval, surfaced to the hospital as a **range** rather than a point. Add a paramedic-controlled "delayed" flag.
- **Degraded:** paramedic selects a coarse ETA band (under 10 minutes, 10 to 20, 20 to 40, over 40) and updates it once en route. No integration required, works on any phone, and is honest about its precision.
- **Hackathon:** simulate a GPS trace along a route and show the ETA range narrowing as the vehicle approaches. This demos in fifteen seconds and needs no real API key or network dependency on stage.

Do not build dispatch optimisation or fleet routing. That is a different product.

## 7.3 What the pre-alert should contain

Not the full case. A pre-alert should be scannable in three seconds: predicted acuity band, one-line presentation, key abnormal vitals with times, interventions already performed, ETA range, and what the hospital should prepare. Everything else stays one tap away.

---

# PHASE 8 — Interfaces

## 8.1 Patient

**Objective:** reduce anxiety and reduce reception load. Not to triage.

**Hierarchy:** where you are in the process → estimated wait window → what happens next → "I feel worse" button.

**Never show:** risk score, acuity level, probability, differential considerations, any clinical interpretation. A patient reading "level 4, low risk" and going home is a catastrophic failure mode, and it is entirely preventable by simply never rendering that number.

**Notification philosophy:** at most, stage changes and "please come to X". Nothing else.

**The one feature worth building:** the **I feel worse** button. It is one tap, it creates a `PATIENT_SELF_REPORTED_WORSENING` event, it forces a reassessment prompt, and it turns waiting patients into active sensors. It is more valuable than the entire chat interface and takes an afternoon to build.

**Accessibility:** the patient app must be optional at every step. Kiosk mode, caregiver mode, and a nurse-entered path must all exist, because a meaningful fraction of ED arrivals cannot use a phone app at that moment.

## 8.2 Nurse

**Objective:** scan the department in five seconds, act in one tap.

**Layout:** a single prioritised list, colour-banded by acuity, with four persistent columns of information per row: acuity plus confidence, one-line presentation, time in band against target, and the flag that most needs attention (deteriorating, overdue, unknown vitals, conflict).

**Actions, all one tap:** escalate, mark reassessed, record vitals, open case.

**Do not show:** model probabilities, feature contributions, technical confidence percentages, raw ML output. Show a confidence band with a plain-language reason: *low confidence: no vitals recorded, symptoms self-reported only.*

## 8.3 Doctor

**Objective:** decision support, not information dumping.

**Hierarchy:** assigned patients → synthesised summary with source attribution → trends over raw values → what changed since last review → pending actions and results.

**The high-value element is "what changed since you last looked at this patient."** That is the thing a longitudinal event store can do that a paper chart cannot, and it is worth building before anything else on this screen.

**Do not show:** differential diagnoses, treatment suggestions, anything that positions the system as a clinical decision *maker*.

## 8.4 Control tower

**Objective:** anticipate, not report. Five tiles maximum, every tile actionable:

1. Patients by acuity band, with overdue reassessments highlighted
2. Deteriorating patients
3. Stuck patients (operational)
4. Capacity: spaces and clinicians free versus needed
5. Incoming ambulances with predicted acuity

If a tile does not change what someone does in the next fifteen minutes, cut it.

## 8.5 Preventing notification overload

This is a scored criterion in disguise, because alert fatigue is named explicitly in the problem statement. Evidence from paediatric early-warning systems shows how sharply added trigger criteria multiply alert volume: one retrospective study of a digital paediatric early-warning tool found that adding upper-limit single-parameter triggers increased cumulative medical-emergency-team alerts by 229 percent, and concluded the resulting workload was not justified (see References, Bell et al.). That is the trap, quantified, in a real hospital.

**Design response:**

- **The queue is the notification.** Position and colour carry almost all the information. Ambient by default.
- **Only three things interrupt:** a new critical-bypass patient, a patient crossing into a higher acuity band, and a reassessment past its hard limit.
- **Alert budget as a measured design constraint.** Set a target for interruptive alerts per nurse per hour, measure it in the demo, and show it on a slide. Judges will remember that you measured it. **[Assumption]** for any specific target value; the point is that the number is a design parameter you own, not an emergent property you discover in production.
- **Aggregate, never repeat.** Three overdue reassessments is one notification, not three.
- **Every alert is dismissible with a reason,** and dismissal reasons feed the tuning loop.

---

# PHASE 9 — Safety, explainability and trust

## 9.1 Confidence

Deterministic, composed of four inputs, surfaced as three bands with reasons:

| Input | Effect |
|---|---|
| Data completeness against the presenting-complaint template | Fewer known high-value fields lowers confidence |
| Agreement between rules and ML | Divergence lowers confidence |
| Distance from a band boundary | Borderline scores lower confidence |
| Reliability tier of the inputs used | Self-reported-only lowers confidence |

**Low confidence never means low acuity.** It means the system says less and asks for more, while holding the patient at the safer level.

## 9.2 Abstention

The system must be able to say: **"insufficient information for a recommendation. Nurse assessment required."** When it abstains it does not fall back to a default low level. It holds a configured minimum band until a human assesses. Abstention is a feature to demo deliberately, because most teams will not have one.

## 9.3 Contradictory information

Do not average, do not silently pick one. Flag both values with their sources and times, surface a `DATA_CONFLICT_DETECTED` event, and compute acuity from the more conservative value until a human resolves it. Example: patient reports mild discomfort, monitor reports a markedly abnormal value. The monitor wins for scoring, both appear on screen, and the discrepancy itself is clinically informative.

## 9.4 Stale data

Every displayed value carries its age. Values past a concept-specific staleness window are visually degraded, excluded from automatic escalation logic, and generate a reassessment request. A saturation reading from ninety minutes ago is not a current fact about the patient.

## 9.5 Failure modes

| Failure | Behaviour |
|---|---|
| LLM API unavailable | Structured entry forms replace conversational capture. Rules engine unaffected. Explanations replaced by the rule component breakdown, which is arguably clearer anyway. Banner shown. |
| ML model unavailable | Rules-only acuity. Confidence band drops. Banner shown. |
| Devices unavailable | Manual vital entry, which is the default path in most hospitals regardless. |
| Network unavailable | Local-first entry with queued sync. Timers and queue logic run locally. |
| Total system failure | Printed queue snapshot with acuity, arrival time and reassessment-due time. Print this in the demo. It is a five-second moment that wins trust. |

**The invariant:** removing every AI component leaves a working digital triage form, a working timer, and a working queue. That is the honest floor of the product, and it is a floor most competing solutions do not have.

## 9.6 Override, with deliberate asymmetry

This operationalises the under-triage/over-triage asymmetry the problem statement demands you demonstrate explicitly:

- **Escalating override (making a patient more urgent): one tap. No reason required. No friction. Applied instantly.**
- **De-escalating override (making a patient less urgent): requires a structured reason code, records clinician identity, and is flagged for retrospective review.**

The system never blocks either. But the friction is deliberately asymmetric, which means the *interface itself* encodes the safety principle rather than merely documenting it. This is a small design choice with a large signalling value in front of a clinical judge.

Every override logs: original recommendation and its full assessment record, clinician action, resulting acuity, identity and role, timestamp, reason code, and subsequent patient state. Override rate and override direction become your primary model-monitoring signals in production.

## 9.7 Bias and equity

Worth one slide, because it is the question a serious clinical judge asks that nobody prepares for. The ESI handbook itself references published findings of under-triage in minority populations. Any triage system, human or automated, can encode this. **Design response:** measure acuity distribution and override rate by demographic subgroup as a standing evaluation output, not as a one-off fairness audit. State that you measure it. Do not claim you have solved it.

---

# PHASE 10 — Privacy and security

## 10.1 Stated regulatory assumption

**Assumed jurisdiction: India.** Two instruments are relevant:

- **The Digital Personal Data Protection Act, 2023** (Act 22 of 2023), India's first cross-sector personal data protection law. Its provisions are commencing in phases, with parts in force from November 2025 and remaining provisions scheduled later, so a 2026 deployment sits inside a live transition. It creates data fiduciary obligations, consent requirements, and a general framework covering health data, which is treated as personal data under the Act rather than under a dedicated sectoral statute.
- **The ABDM Health Data Management Policy**, issued under the Ayushman Bharat Digital Mission and administered by the National Health Authority, which sets health-specific data handling expectations and defines the ABHA identifier and consent architecture.

**Two things worth saying accurately in the pitch:** India does not currently have a sector-specific health data statute directly comparable to HIPAA in the US or the GDPR's health-specific provisions in the EU, and the DPDP Act contemplates processing in medical emergencies involving a threat to life. Both points are directly relevant to an emergency triage product, and both are the kind of specificity that separates a serious submission from a generic one. **[Requires legal validation]** for any operational compliance claim. Do not state obligations more precisely than the sources support.

## 10.2 Proportionate controls for a prototype

| Control | Prototype implementation |
|---|---|
| Authentication | Role-based login, three roles (nurse, doctor, admin). No SSO build. |
| Authorisation | Least privilege by role. Patients see only their own case. Nurses see the department. Doctors see assigned plus department. |
| Break-glass access | Emergency access permitted, always logged, flagged for review. Required in an ED, and demoing it shows operational realism. |
| Encryption | TLS in transit, encryption at rest, identifiers stored in a separate encrypted table. |
| **LLM data minimisation** | **A deterministic redaction layer sits between the patient state store and every LLM call.** Names, contact details, identifiers and addresses are stripped and replaced with tokens before the prompt is constructed, and re-hydrated in the response on the way back. The LLM sees "a 67-year-old patient", never a name. |
| LLM retention | Use a zero-retention API configuration. State this explicitly. |
| Audit | Append-only, immutable, covering every access, recommendation, override and export. |
| Retention | Stated policy with a defined period and a purge job. State it even if the prototype never runs it. |
| Consent | Standard capture at registration; emergency processing path where consent cannot be obtained, logged as such. |

The redaction shim is worth building and worth demoing. It is concrete, it takes an hour, and it is the single most convincing privacy artefact you can show in ninety seconds.

---

# PHASE 11 — The improved architecture

## A. One-sentence concept

PatientTriage.ai is a continuous emergency-department triage and flow assistant that scores every arriving patient with auditable clinical rules, keeps watching them for as long as they wait, and separates who is getting sicker from who is merely stuck, while every decision stays reversible by a clinician.

## B. Elevator pitch

Emergency departments do not fail at the moment of triage. They fail in the hours afterwards, when a patient who was correctly assessed as stable at 10am deteriorates at noon and nobody looks again, or when a patient's test result sits unreviewed for forty minutes because no system was tracking that it should have been. PatientTriage.ai treats triage as a continuous process rather than a single classification. It captures information from the ambulance onward, scores acuity using published clinical frameworks that are age-appropriate and fully auditable, uses machine learning only where it can escalate a patient and never to reassure, and then keeps every waiting patient under active watch: re-scoring on new vitals, forcing reassessment when a band's safe interval is exceeded, and flagging patients whose care has stalled operationally rather than clinically. Clinicians override anything with one tap. The system optimises for a single number, Time-to-Right-Care, and it is designed to keep working in a hospital with no connected devices, no integration, and no internet.

## C. End-to-end patient journey

**Walk-in**

```
Arrival → registration (30s, staff or kiosk)
  → optional patient symptom capture (chat, voice, or nurse-entered)
  → parallel: emergency bypass detectors run continuously from first keystroke
  → vitals captured (device or manual)
  → Age Router → deterministic framework scoring → hard triggers checked
  → ML challenger runs (escalation only)
  → acuity + confidence appear on nurse queue  [target: seconds, no LLM in path]
  → LLM explanation streams in behind the already-displayed level
  → nurse reviews: accept (1 tap) / escalate (1 tap) / de-escalate (reason required)
  → patient enters Guardian Queue
      ↺ new vitals → rescore
      ↺ reassessment interval exceeded → REASSESSMENT_DUE → nurse prompted
      ↺ patient taps "I feel worse" → forced reassessment
      ↺ Active Triage requests the next highest-value missing observation
  → doctor assignment when space + clinician available (capacity never alters acuity)
  → investigation → results → stuck-patient monitoring on every expected next event
  → disposition → case closed → outcome recorded for evaluation
```

**Ambulance**

```
Dispatch → paramedic opens case (voice + structured entry)
  → same case_id as the eventual ED record, from this moment
  → vitals entered or streamed → provisional acuity computed
  → identity match proposed, human-confirmed, never auto-merged
  → pre-alert pushed to ED: acuity band, one-line presentation,
    abnormal vitals with times, interventions done, ETA range
  → ED prepares space and team before arrival
  → PATIENT_ARRIVED event → same case continues, no re-entry, no second record
```

## D. Backend architecture

```
┌──────────────── INPUT LAYER ─────────────────────────────────────┐
│  Patient (text/voice)   Nurse    Doctor    Paramedic             │
│  Devices/monitors       Hospital records (FHIR where available)  │
└───────────────┬──────────────────────────────────────────────────┘
                │
        ┌───────▼────────┐        ┌──────────────────────────────┐
        │ INTAKE ENGINE  │        │  EMERGENCY BYPASS            │
        │ ASR → LLM      │───────▶│  (3 redundant detectors,     │
        │ extraction     │        │   escalation-only, parallel, │
        │ → schema       │        │   never blocked by pipeline) │
        │   validation   │        └──────────┬───────────────────┘
        └───────┬────────┘                   │ immediate alert
                │                            │ + state flag
        ┌───────▼──────────────────────────────────────────────────┐
        │  PATIENT STATE STORE   (event-sourced, append-only)      │
        │  observations · assessments · decisions · audit          │
        └───────┬──────────────────────────────────────────────────┘
                │  (every engine below is a consumer of this stream)
    ┌───────────┼───────────┬─────────────┬──────────────┐
    ▼           ▼           ▼             ▼              ▼
┌────────┐ ┌─────────┐ ┌─────────┐ ┌───────────┐ ┌────────────┐
│ AGE    │ │  TIME   │ │ GUARDIAN│ │ FLOW/OPS  │ │ PRIVACY /  │
│ ROUTER │ │ ENGINE  │ │  QUEUE  │ │  ENGINE   │ │ REDACTION  │
│   ↓    │ │ 3 clocks│ │ re-scan │ │ resources │ │ (gates all │
│ RULES  │ │         │ │ + timers│ │ + stuck   │ │  LLM calls)│
│ ENGINE │ └─────────┘ └─────────┘ │ detection │ └────────────┘
│   ↓    │                         └───────────┘
│ HARD   │
│TRIGGERS│      final_acuity = min(rules, ml, escalating_override)
│   ↓    │      ── ML may raise. ML may never lower. ──
│  ML    │
│CHALLENGER
│   ↓    │
│CONFIDENCE + ABSTENTION
└───┬────┘
    │
    ▼
┌──────────────────────┐      ┌───────────────────────────────┐
│ EXPLANATION LAYER    │      │  HUMAN REVIEW                 │
│ (LLM, evidence-      │─────▶│  accept / escalate (1 tap)    │
│  grounded, streams   │      │  de-escalate (reason required)│
│  in after the level) │      └──────────┬────────────────────┘
└──────────────────────┘                 │
                                         ▼
                          writes HumanDecision → back to state store
                          → triggers recomputation → loop continues
```

## E. AI versus non-AI responsibilities

| Function | LLM | ML | Rules / deterministic | Database | Human |
|---|:--:|:--:|:--:|:--:|:--:|
| Speech to text | | ● (ASR) | | | |
| Symptom extraction from free text | ● | | validation | | |
| Mapping to coded concepts | proposes | | ● decides | ● vocabulary | |
| Feature construction | | | ● | ● | |
| Age band routing | | | ● | | |
| Base acuity score | | | ● | | |
| Hard escalation triggers | | | ● | | |
| Supplementary risk estimate | | ● | bounded by rules | | |
| Final acuity assignment | | | ● | | ● override |
| Confidence and abstention | | inputs | ● formula | | |
| Choosing next observation | phrasing | | ● selection | | ● can request |
| Explanation and summary | ● | | | ● evidence | |
| Emergency bypass | assists | | ● | | ● primary |
| Queue ordering | | | ● | | |
| Timers and reassessment | | | ● | ● | |
| Stuck detection | | | ● | ● | |
| Wait estimation | | | ● queue model | ● | |
| Diagnosis and treatment | | | | | ● only |
| Audit | | | | ● | |

The LLM owns three things: understanding messy input, phrasing questions, and narrating decisions it did not make. That is a defensible position, and it is far stronger in front of judges than claiming the LLM does everything.

## F. System engines

1. **Intake Engine** — ASR, schema-constrained extraction, validation, normalisation.
2. **Age Router** — directs to paediatric, adult or geriatric logic before any scoring.
3. **Clinical Scoring Engine** — published-framework rules plus hard triggers. Deterministic, versioned, configurable per hospital.
4. **Risk Challenger** — calibrated ML, escalation-only, trend-aware.
5. **Confidence and Abstention Engine** — deterministic banding, holds at safer level when uncertain.
6. **Time Engine** — three clocks, three distinct consequences.
7. **Guardian Queue** — continuous re-evaluation, reassessment scheduling, deterioration watch.
8. **Flow / Operations Engine** — resources, routing, stuck detection, wait estimation, capacity conflicts.
9. **Explanation Engine** — evidence-grounded narrative generation.
10. **Privacy and Redaction Layer** — gates every outbound LLM call.
11. **Audit and Override Service** — immutable, reproducible, subgroup-reportable.

## G. Dashboards

Patient (reassurance and self-report), Nurse (prioritisation and action), Doctor (synthesis and decision), Control Tower (anticipation). Detailed in Phase 8.

## H. The continuous loop, stated precisely

```
new information arrives (any source, any actor)
  → written as an immutable observation with source, tier, status, both timestamps
  → state store emits event
  → Guardian Queue and Time Engine consume it
  → scoring stack re-runs: age router → rules → hard triggers → ML challenger
  → final_acuity = min(rules, ml, escalating_override)
  → confidence recomputed from completeness, agreement, boundary distance, reliability
  → if band changed OR hard trigger fired OR reassessment overdue → notify (tiered)
  → otherwise update ambiently in the queue
  → clinician reviews and may override
  → override written as a decision record → re-enters the loop as new information
```

Nothing in this loop requires the LLM to be available.

---

# PHASE 12 — Differentiation

## What is not a differentiator (say this out loud)

Conversational symptom intake, LLM summarisation, speech-to-text, dashboards, and a triage risk score. All of these exist commercially. Claiming novelty here invites a judge to name three products that already do it. Concede them confidently and spend the time elsewhere.

## The top five, ranked by memorability

**1. Guardian Queue — triage that does not end at triage**
*What:* every waiting patient stays under continuous re-evaluation, with band-specific reassessment intervals, automatic re-scoring on any new observation, and a patient-triggered worsening path.
*Why it matters:* the deterioration that harms patients usually happens in the waiting room, after the score was correct.
*Why feasible:* it is timers and event handlers over data you already collect. No new sensors, no new integration.
*Why better than today:* current practice relies on a busy nurse remembering to re-check. This makes forgetting structurally impossible.

**2. Rules-floor, ML-ceiling — a safety property, not a promise**
*What:* `final_acuity = min(rules, ml, escalating_override)`. ML can only escalate.
*Why it matters:* it makes "what if the AI is wrong" answerable in one line. A wrong ML output causes over-triage, which is the survivable error.
*Why feasible:* it is a `min()`.
*Why better than today:* most AI triage proposals ask clinicians to trust a black box. This one is bounded by construction.

**3. Stuck Patient Detection — separating deterioration from delay**
*What:* the system distinguishes "this patient is getting sicker" from "this patient's care has stalled" and routes them to different people.
*Why it matters:* both cause harm, they have completely different remedies, and no triage tool addresses the second.
*Why feasible:* every event is already timestamped. This is threshold logic over an existing stream.
*Why better than today:* operational stalls are currently invisible until someone complains.

**4. Pre-arrival continuity — one case, ambulance to disposition**
*What:* the ambulance case and the ED case are the same record. No re-entry, no lost pre-hospital vitals, no second chart.
*Why it matters:* handover is a well-recognised point of information loss.
*Why feasible:* it is a design decision about identifiers, not a technology.
*Why better than today:* pre-hospital observations frequently arrive verbally and are never captured as structured data.

**5. Graceful degradation — designed for the hospital you actually have**
*What:* full value with FHIR and connected monitors; core value with a tablet, manual entry and no internet.
*Why it matters:* it is the difference between a demo and a deployable product, especially across the range of Indian hospitals.
*Why feasible:* it follows from putting the deterministic engine at the centre rather than the LLM.
*Why better than today:* most AI health tools assume a level of digital maturity that most emergency departments do not have.

**Pitch structure suggestion:** lead with 1 and 3 (the product insight), support with 2 and 5 (the engineering credibility), and use 4 as the demo opener because pre-arrival is visually dramatic.

---

# PHASE 13 — Hackathon MVP scope

### MUST BUILD (without these there is no demo)
- Event-sourced patient state store with the observation schema from Phase 4
- Age router and deterministic framework-based scoring with hard triggers
- Confidence computation and abstention path
- Guardian Queue: lexicographic ordering, reassessment timers, automatic re-scoring
- Nurse dashboard with one-tap escalate and reason-gated de-escalate
- Immutable audit and override log, viewable in the UI
- 20 synthetic patients plus a 3x surge simulator
- Emergency bypass with the human affordance and deterministic triggers

### SHOULD BUILD (these are what make it feel like AI)
- LLM extraction from free text into the validated schema
- LLM explanation layer, streaming in after the level is displayed
- ML challenger model with escalation-only enforcement, visibly demonstrated
- Patient "I feel worse" button
- Stuck patient detection with two or three patterns
- Privacy redaction shim on LLM calls

### NICE TO HAVE
- Ambulance pre-arrival case with simulated GPS ETA range
- Control tower with five tiles
- Voice input on one screen
- Patient status view

### FUTURE (say these are future, do not build)
- Real FHIR integration and device streams
- Multi-hospital configuration management
- Model retraining pipeline
- Diagnostics, bed management, inventory, prescriptions

**The discipline:** if a feature does not appear in the demo script in Phase 14, do not build it. A finished MUST plus SHOULD beats a half-built everything, and judges can tell the difference within thirty seconds.

---

# PHASE 14 — Prototype scenario design

## 14.1 The twenty synthetic patients

Design each one to teach a specific thing. Vital sign values should be generated from the reference tables of whichever published framework you adopt, not invented. **[Assumption]** applies to all synthetic patients; state clearly in the deck that no real patient data is used.

| # | Profile | Demonstrates |
|---|---|---|
| 1 | Adult, obvious critical presentation | Emergency bypass, sub-second, no LLM involved |
| 2 | Adult, clearly minor complaint | Correct low acuity without over-triage |
| 3 | **Ambiguous:** vague symptoms, borderline vitals, self-reported only | Low confidence band, abstention, holds at safer level |
| 4 | **Paediatric:** 3-year-old with fever | Age router changes the interpretation entirely versus adult logic |
| 5 | **Paediatric:** infant, subtle presentation | Qualitative signs (work of breathing) matter more than numbers |
| 6 | **Geriatric:** 78-year-old, atypical presentation, blunted vitals | Why adult-calibrated thresholds under-triage the elderly |
| 7 | **Zero history:** first-time patient, no record | System functions fully without the history block |
| 8 | Returning patient, rich relevant history | History as an additive signal, relevance-filtered not dumped |
| 9 | Patient whose repeat vitals worsen | Guardian Queue auto-escalation on trend |
| 10 | Patient who taps "I feel worse" | Patient-triggered reassessment |
| 11 | Patient whose reassessment interval lapses | REASSESSMENT_DUE, and the fact that this does *not* itself change acuity |
| 12 | **Operationally stuck:** result available, unreviewed | Ops alert, routed to a different person, acuity unchanged |
| 13 | Contradictory data: patient reports mild, device reports abnormal | Conflict flag, conservative value used for scoring |
| 14 | Missing vitals entirely | Missingness lowers confidence and raises escalation propensity, never treated as normal |
| 15 | **Ambulance pre-arrival**, high acuity | Pre-alert, ETA range, team prepared before arrival |
| 16 | Ambulance patient with unconfirmed identity match | Human-confirmed matching, runs unlinked until confirmed |
| 17 | **Clinician escalating override** | One tap, no friction, instant |
| 18 | **Clinician de-escalating override** | Reason code required, full audit record shown on screen |
| 19 | Multilingual / voice intake | Intake engine flexibility |
| 20 | ML challenger disagrees *downward* with rules | The min() invariant visibly refusing to lower the level. **Build the demo around this one.** |

## 14.2 The surge demo

Trigger 3x arrival volume. What the audience should see, in order:

1. Queue length triples. **Acuity ordering does not degrade.** Level 2 patients stay above level 4 patients regardless of arrival time.
2. Reassessment intervals start lapsing across the low-acuity bands. Overdue counts climb visibly.
3. **The alert count does not triple.** Aggregation holds interruptive notifications roughly flat while ambient indicators absorb the load. Put a live alerts-per-nurse-per-hour counter on screen. This is the single most sophisticated thing you can show, because it demonstrates you understood alert fatigue as an engineering constraint rather than a bullet point.
4. Capacity conflict fires: a high-acuity patient with no available space. The system surfaces the conflict and candidate actions. It does not reorder around it and it does not downgrade anyone.
5. Stuck patients accumulate as diagnostics back up, and they surface on the ops list, entirely separately from the clinical list.
6. One waiting patient deteriorates mid-surge and auto-escalates past newer arrivals.

**The closing line for the demo:** during a surge, human attention is the scarcest resource in the department, and this is the moment the system is actually for.

## 14.3 Demo narrative arc (7 minutes)

1. **0:00** Ambulance case opens. Pre-alert lands. Team prepares. (Patient 15)
2. **1:00** Walk-in intake, ambiguous presentation. Low confidence, system abstains and asks for a specific observation. (Patient 3)
3. **2:00** Paediatric case scored beside a physiologically similar adult, showing divergent outcomes. (Patients 4 and 6)
4. **3:00** ML suggests lowering a patient's level. The min() invariant refuses. (Patient 20)
5. **4:00** Waiting patient deteriorates and auto-escalates. (Patient 9)
6. **5:00** Clinician de-escalates a patient; the audit record is shown in full. (Patient 18)
7. **5:30** Surge triggered. Run 14.2.
8. **6:30** Kill the LLM and the network live. Show the system still triaging, still timing, still queueing. Print the paper fallback.

That last thirty seconds is the moment the judges will remember.

---

# PHASE 15 — Technology stack

| Layer | Recommendation | Why | Simpler alternative |
|---|---|---|---|
| Frontend | React + Vite + Tailwind | Fast iteration, dense data tables, easy real-time updates | A single HTML page with vanilla JS if the team is not React-fluent |
| Backend | FastAPI (Python) | Same language as the ML layer, no cross-service marshalling, fast to write | Node/Express if the team is stronger in JS, but then the ML runs as a separate script |
| Database | PostgreSQL, append-only events table with JSONB payloads | Event sourcing fits naturally; JSONB avoids premature schema lock-in | SQLite, which is genuinely fine for a demo and removes a deployment dependency |
| Real-time updates | Server-sent events or WebSocket | Queue must update live for the surge demo to land | Poll every 3 seconds. Nobody in the audience can tell, and it will not break on stage |
| LLM | Claude via API, JSON-schema-constrained output | Strong structured extraction, and constrained output prevents schema drift | Rules-only extraction path, which you must build anyway as the fallback |
| Speech to text | Whisper API, or an Indic-focused ASR service if you demo a regional language | Latency and vocabulary handling | Typed input. Do not let ASR be a demo dependency |
| ML | scikit-learn (logistic regression and gradient boosting) with probability calibration | Interpretable, trains in seconds, calibration is the point | Skip Layer 3 entirely and present rules-only. The architecture still holds |
| Synthetic data | Seeded Python generator with an explicitly documented generative process | Reproducible, and honest about what the model learned | Hand-authored JSON for 20 patients |
| Auth | JWT with three hard-coded roles | Demonstrates RBAC without consuming a day | Role selector dropdown, clearly labelled as a demo shortcut |
| Deployment | **Run locally.** Optionally mirror to Railway or Render | Conference wifi has ended more demos than bad code | If deploying, have a local fallback ready and rehearsed |

**Do not use:** a vector database (you have no retrieval problem worth one), Kubernetes, a microservice split, an agent framework, or a graph database. Every one of these will cost you demo-day hours and none will earn a point.

---

# PHASE 16 — Risk model development strategy

## 16.1 Target

Predict **probability of a critical outcome within a defined short horizon**, where critical outcome is a composite label defined in your synthetic generator (for example: required immediate intervention, required resuscitation-area care, or required critical-care admission). Define the label explicitly and put the definition on a slide. An undefined target is the fastest way to lose a technical judge.

## 16.2 Features

Age band; age-normalised vital signs; **vital trend deltas** (this is where ML beats a fixed score); time since symptom onset, banded; arrival mode; structured symptom flags; relevant history flags; and **explicit missingness indicators for every field**. The missingness indicators are not a technicality: they let the model learn that absent information is itself informative, rather than being handed a silent imputed normal.

## 16.3 Synthetic data, handled honestly

State the circularity plainly: **a model trained on data you generated has learned your generator, not clinical reality.** Do not hide this. Use it correctly:

- The synthetic model demonstrates the *mechanism*: that a calibrated probability can be produced, bounded by the rules floor, and surfaced with confidence.
- Document the generative process, including the assumed relationships between features and outcomes, and seed it for reproducibility.
- Deliberately generate a realistic class imbalance rather than a balanced set. Balanced synthetic data produces meaningless calibration.

Saying "this model is not clinically validated and here is exactly the path by which it would be" is a stronger answer than any accuracy figure you could quote.

## 16.4 Production validation path

Retrospective ED data with clinician-adjudicated labels → offline evaluation including subgroup performance → **silent shadow mode**, where the model runs on live patients, its outputs are logged and never shown → clinician review of disagreements → limited escalation-only deployment → prospective evaluation. The model never influences a real patient before shadow-mode evaluation. Put this five-stage path on a slide; it is exactly what a clinical judge is listening for.

## 16.5 Metrics

**Do not report accuracy.** With realistic class imbalance it is meaningless and a knowledgeable judge will say so.

| Metric | Priority | Why |
|---|---|---|
| **Sensitivity / recall on the critical class** | **Primary** | Missing a critical patient is the failure that matters |
| **False negative rate and count** | **Primary** | State it as a count, not a rate. "Three missed critical patients" is what a clinician hears |
| **Calibration curve and Brier score** | **Primary** | An escalation-only design depends on the probability meaning something |
| **Per-age-band metrics** | **Primary** | Aggregate performance can hide complete paediatric failure. This is non-negotiable given the problem statement |
| AUPRC | Secondary | Appropriate under class imbalance, more informative than AUROC here |
| Specificity and precision | Secondary | Governs over-triage load and therefore alert fatigue |
| Confusion matrix | Secondary | Show it. It communicates the asymmetry visually |
| Cost-weighted metric with an explicit FN:FP ratio | Secondary | Forces you to state the asymmetry as a number. **[Requires clinical validation]** for the ratio itself; choose it with a clinician and say who |

Report subgroup metrics as a standing output, not an appendix. **Do not invent or quote any performance numbers you have not measured.**

---

# PHASE 17 — Feasibility

| Dimension | Prototype feasibility | Production challenge | Mitigation |
|---|---|---|---|
| **Technical** | High. Rules engine, event store and queue are ordinary software | Real-time device integration, HL7/FHIR variability, uptime | Start manual-entry-first. Devices are an enhancement, never a dependency |
| **Clinical** | Low as evidence, high as demonstration. Cannot be clinically validated in a hackathon | Requires prospective validation and clinical governance sign-off | Shadow mode. Escalation-only bounding. Named clinical partner. Say clearly what is unvalidated |
| **Operational** | High. The workflow mirrors what nurses already do | Adoption by fatigued staff who have been burned by previous tools | Reduce clicks below the current paper baseline. One-tap accept. If it is slower than paper, it will not be used, and this is the most common cause of failure for tools like this |
| **Financial** | High. Free or cheap tooling throughout | LLM cost per case at 500 visits/day, plus integration and support cost | Rules engine is free per call. LLM used only for extraction and explanation, both cacheable and both optional. Show cost-per-case as a function of LLM usage |
| **Data** | Medium. Synthetic only | Access to retrospective ED data requires ethics approval and institutional partnership | Design so that the deterministic layer needs no training data at all. Only Layer 3 does |
| **Integration** | Low in prototype, and that is fine | EMR vendors, legacy HIS, no standard API | Standalone-first with optional FHIR adapters. Never require integration to deliver value |
| **Scalability** | High. Thousands of patients is trivial compute | Multi-site configuration, versioning, per-hospital clinical governance | Hospital profile as configuration, not as code forks (Phase 18) |

The honest summary: the **engineering** is very feasible, the **clinical validation** is the hard part, and pretending otherwise is what will cost you credibility. Owning it will gain you credibility.

---

# PHASE 18 — Scalability

## 18.1 The hospital profile

One product, one codebase, per-site configuration:

```
HospitalProfile {
  acuity_framework            // which published scale
  age_band_definitions
  vital_reference_tables      // per age band
  hard_trigger_definitions
  reassessment_intervals      // per acuity band
  staleness_windows           // per concept
  available_integrations      // devices, EMR, none
  resource_types_enabled
  alert_budget_targets
  language_set
  clinical_governance_contact
}
```

No code forks per hospital. Every clinical parameter is data, reviewed and owned by that hospital's clinical governance. This is also what makes the audit trail defensible: you can show which configuration version produced which decision.

## 18.2 Across ED size

**~100 visits/day.** The binding constraint is staff, not compute. Value comes from the reassessment timer and stuck detection, because a small team is more likely to lose track of a waiting patient than to be overwhelmed by volume. Runs on one machine, likely one tablet at triage.

**~500+ visits/day.** Queue and timer volume grow, not model complexity. The scaling work is in the interface (the nurse cannot scan 200 rows) and in alert aggregation. Add filtered views by zone and by assigned clinician. Compute remains trivial; a rules engine over a few hundred active cases is nothing.

## 18.3 The degradation ladder

| Tier | Hospital has | System provides |
|---|---|---|
| 4 | EMR integration, connected monitors, ABDM linkage | Everything, largely automatic |
| 3 | Some digital records, manual vitals | Full triage, full Guardian Queue, manual entry |
| 2 | Nothing digital, tablets and staff only | Digital triage, timers, queue, reassessment, audit |
| 1 | No internet during an outage | Local scoring and timers, queued sync, printable snapshot |

**Tiers 2 and 1 are the deployment reality for a large share of hospitals, and the architecture must be designed for tier 2 and enhanced upward, not designed for tier 4 and degraded downward.** That ordering is a design decision you should state explicitly, because it inverts what most teams will present.

---

# PHASE 19 — What judges will attack

**1. Why should a clinician trust the model?**
They should not trust the ML model, and the architecture does not ask them to. Acuity is set by deterministic, published, citable clinical frameworks that produce an inspectable component breakdown. ML only escalates, never lowers. Trust is placed in bounded logic, not in a model's judgement.

**2. What happens when the AI is wrong?**
The `min()` invariant means an ML error can only over-triage, which is the survivable direction. An LLM error affects extraction or phrasing, both visible on screen and both correctable in one tap. No generative output can lower a patient's priority. That is a structural guarantee, not a policy statement.

**3. Why use an LLM at all?**
For exactly three things: understanding unstructured speech and text, phrasing questions, and narrating decisions made elsewhere. Remove it and the system still triages. That is deliberate.

**4. Why not just use ESI or NEWS2 with a nurse?**
We do use them, as the scoring backbone. What existing frameworks do not do is watch the patient for the next three hours, re-score automatically on every new observation, force reassessment when a band's interval lapses, or tell you that a result has been sitting unreviewed for forty minutes. We are not competing with the scale, we are operationalising it continuously.

**5. How do you validate clinical safety?**
We do not claim to have. We have designed the validation path: retrospective evaluation, subgroup analysis, silent shadow mode, clinician adjudication of disagreements, then escalation-only deployment. Nothing in the prototype is clinically validated and we label it that way throughout.

**6. How do paediatric patients work?**
Age routing happens before any scoring. Paediatric patients are scored with a PEWS-family framework using age-specific reference ranges and qualitative signs such as work of breathing, not with adult thresholds. Metrics are reported per age band, because aggregate performance can conceal complete failure in one band.

**7. What if data is missing?**
Missing is never imputed as normal. Every field carries a measurement status. Missingness lowers confidence and raises escalation propensity. With no vitals at all the system abstains, holds at a safer level, and requests the specific observation that would most change the assessment.

**8. How does waiting time affect priority?**
It does not affect acuity at all. Ordering is lexicographic, so a lower-acuity patient can never overtake a higher-acuity one. Waiting orders patients within a band and triggers mandatory reassessment. A patient escalates only because new information says they should.

**9. How do you avoid alert fatigue?**
The queue is the notification; almost everything is ambient. Three event types interrupt. Alerts aggregate rather than repeat. We treat alerts-per-nurse-per-hour as a measured design constraint and show it live during the surge demo. The paediatric early-warning literature shows how quickly added triggers multiply alert volume, and we designed against that specifically.

**10. What is actually innovative?**
Not the score. Continuous re-triage of the waiting room, the separation of clinical deterioration from operational stalling, and a bounded safety architecture in which ML can only escalate. We are explicit that conversational intake and LLM summarisation are commodity capabilities.

**11. Can hospitals actually integrate this?**
They do not have to. The system delivers its core value standalone with manual entry on a tablet. Integration is an enhancement tier, not a prerequisite. That is the opposite of how most clinical AI is built and it is why this can deploy in a district hospital.

**12. What can you really build in a hackathon?**
The full deterministic engine, the Guardian Queue, the audit trail, the nurse interface, twenty patients and the surge, all working. The ML challenger demonstrates mechanism on synthetic data and is labelled as such. We would rather show a complete safe core than a partial everything.

**13. Does this increase staff workload?**
It must not, and that is the adoption make-or-break. Accept is one tap. Escalate is one tap. Only de-escalation adds friction, deliberately. The benchmark is the paper form: if triage takes longer than paper, staff will work around it and the product fails.

**14. What happens with no internet or no device integration?**
Manual entry is the default path, not the fallback. The rules engine runs locally. Timers and queue logic run locally. Total failure produces a printed queue snapshot with acuity, arrival time and reassessment-due time. We demonstrate this live.

**15. Who is legally accountable?**
The clinician, unchanged. The system produces a recommendation, never a decision. Every recommendation is reversible in one tap, every override is logged with identity, time, reason and the full input snapshot that produced the original recommendation. We deliberately do not generate diagnoses or treatment recommendations, which keeps the system a prioritisation aid rather than a diagnostic device. Regulatory classification would require legal and clinical review before deployment. **[Requires legal validation]**

---

# PHASE 20 — Final recommendation

## KEEP
Single longitudinal event-sourced patient case. Active Triage. Guardian Queue. Stuck Patient Detection. Time as a first-class input. Pre-arrival continuity. Control tower. Human-in-the-loop framing. Time-to-Right-Care as the objective. Four dashboards.

## CHANGE
- Severity assignment moves from LLM to deterministic rules. **(Highest priority change.)**
- One risk model becomes a layered stack with an age router in front.
- ML becomes escalation-only, bounded by `min()`.
- Waiting time drives reassessment, never acuity. Lexicographic ordering.
- Emergency bypass becomes three redundant escalation-only detectors with a human-first control.
- Ambulance ETA moves from outbound-leg inference to GPS-plus-routing, degrading to declared bands.
- Patient chat becomes optional pre-registration, never a blocking path.
- Override friction becomes asymmetric.

## REMOVE
Medication inventory. Prescriptions and dispensing. In-hospital navigation. Full bed management. Equipment tracking. Differential diagnosis generation. Any claim of clinical validation. Any invented performance number.

## ADD
Deterministic confidence and abstention. Measurement status and reliability tier on every observation. Staleness rules. Contradictory-data handling. Degraded and offline modes with a printable fallback. Hospital profile configuration. Subgroup performance reporting. LLM redaction shim. Alert budget as a measured constraint. Identity-match confirmation for ambulance cases.

## The architecture to build and pitch, in one paragraph

Build an event-sourced patient state store as the single source of truth. In front of it, put an age router feeding a deterministic scoring engine based on published clinical frameworks, with hard escalation triggers that override everything. Behind that, a calibrated ML challenger that may raise a patient's acuity and never lower it, enforced by a single `min()`. Wrap both in a deterministic confidence and abstention layer that holds patients at the safer level when information is thin. Around the state store, run four engines that need no AI at all: a time engine with three separate clocks, a Guardian Queue that re-scores continuously and forces reassessment when intervals lapse, a flow engine that separates clinical deterioration from operational stalling, and an audit service that can reproduce exactly what the system saw at any moment. Use the LLM in three bounded places: understanding messy input, phrasing the next question, and narrating a decision it did not make, always behind a redaction layer. Give nurses one-tap escalation and reason-gated de-escalation. Then make the whole thing degrade cleanly to a tablet with no internet, and show that on stage.

**The one sentence to close the pitch with:** we did not build an AI that decides who is sickest, we built a system that never stops checking.

---

# References

Sources used for factual clinical and regulatory claims. Everything not sourced here is labelled as an assumption or as requiring validation.

- **NEWS2:** Royal College of Physicians, *National Early Warning Score (NEWS) 2: Standardising the assessment of acute-illness severity in the NHS*, updated report of a working party, 2017. https://www.rcp.ac.uk/media/a4ibkkbf/news2-final-report_0_0.pdf — six physiological parameters plus supplemental oxygen; developed for non-pregnant adults aged 16 and over. Note the RCP holds copyright on the charts; cite and link rather than reproducing them.
- **ESI:** Agency for Healthcare Research and Quality, *Emergency Severity Index (ESI): A Triage Tool for Emergency Departments*. https://www.ahrq.gov/patient-safety/settings/emergency-dept/esi.html — five-level scale, 1 most urgent to 5 least urgent; acquired by the Emergency Nurses Association in 2019.
- **ESI Handbook (v5):** Emergency Nurses Association, *Emergency Severity Index Handbook*, fifth edition. https://media.emscimprovement.center/documents/Emergency_Severity_Index_Handbook.pdf — four decision points; pediatric considerations; references published findings of under-triage in minority populations.
- **PEWS:** Royal College of Paediatrics and Child Health, *UK Paediatric Early Warning Systems*. https://www.rcpch.ac.uk/resources/UK-paediatric-early-warning-systems — track-and-trigger systems combining age-specific vital signs and observations with standardised escalation responses.
- **ED-PEWS in LMIC settings:** Validation of the Emergency Department-Paediatric Early Warning Score for use in low- and middle-income countries, multicentre observational study. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10956749/
- **Alert fatigue evidence:** Bell et al., retrospective review of adding upper-limit single-trigger thresholds to a paediatric early warning tool. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11257883/ — cumulative medical-emergency-team alerts increased by 229 percent; the authors concluded the added workload was not justified.
- **DPDP Act:** Digital Personal Data Protection Act, 2023 (Act 22 of 2023), India. Phased commencement, with provisions in force from November 2025 and remaining provisions scheduled later.
- **India health data context:** *Examining the significance of the Digital Personal Data Protection Act, 2023 in the context of the healthcare industry*, Discover Public Health, 2025. https://link.springer.com/article/10.1186/s12982-025-00757-6
- **ABDM Health Data Management Policy:** administered by the National Health Authority under the Ministry of Health and Family Welfare; defines ABHA identifiers and consent architecture within the ABDM ecosystem.
- **Note:** India does not currently have a sector-specific health data statute directly comparable to HIPAA (US) or the GDPR's health-specific provisions (EU). Health data is governed under the general DPDP framework plus ABDM policy.
