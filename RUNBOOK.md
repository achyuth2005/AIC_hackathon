# PatientTriage.ai — End-to-End Operational Runbook & Demonstration Guide

This runbook provides complete instructions for initializing, demonstrating, and evaluating **PatientTriage.ai**, an emergency department clinical decision-support and time-engine platform built according to `FRONTEND_IMPLEMENTATION_PLAN.md`.

---

## 1. System Startup

### Prerequisites
- **Python 3.10+** (with virtual environment support)
- **Node.js 18+** & **npm**

---

### A. macOS & Linux Startup

Open two terminal tabs in the repository root directory (`/AIC_backend`):

#### Terminal 1: FastAPI Backend
```bash
# 1. Activate Python virtual environment
source .venv/bin/activate

# 2. Install backend dependencies (if not already installed)
pip install -r requirements.txt

# 3. Start the FastAPI backend server (Port 8000)
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
*Backend health check:* `http://127.0.0.1:8000/health`

#### Terminal 2: Vite React Frontend
```bash
# 1. Navigate to frontend directory
cd frontend

# 2. Install frontend dependencies (if not already installed)
npm install

# 3. Start the Vite development server (Port 5173 with proxy /api -> :8000)
npm run dev -- --host 127.0.0.1 --port 5173
```
*Frontend URL:* `http://127.0.0.1:5173`

---

### B. Windows (PowerShell / Command Prompt) Startup

#### Terminal 1: FastAPI Backend
```powershell
# 1. Activate Python virtual environment
.venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start FastAPI server
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

#### Terminal 2: Vite React Frontend
```powershell
# 1. Navigate to frontend directory
cd frontend

# 2. Install dependencies
npm install

# 3. Start Vite dev server
npm run dev -- --host 127.0.0.1 --port 5173
```

---

## 2. Demo Initialization & Role Selection

### Step 1: Open the Application
Navigate your browser to `http://localhost:5173`. You will land on the **Role Selection** screen.

### Step 2: Choose a Demo Role
Select any of the three pre-configured clinical personas:
- **Triage Nurse (Sister Sarah Jenkins, RN):** Guardian Queue triage, vitals capture, 1-tap emergency escalations, and reassessment management.
- **Attending Physician (Dr. Marcus Vance, MD):** Doctor worklist, "What Changed Since Last Review" hero, vital trend sparks, and 1-click diagnostic sign-offs.
- **ED Administrator (Director Elena Rostova, MHA):** Control Tower, standing demographic equity evaluations, and 20-scenario benchmark runner.

*Note: You can hot-switch roles at any time using the role dropdown in the top-right header.*

### Step 3: Seed the 20 Synthetic Clinical Patients
To populate the database with the Phase 14.1 clinical test scenarios:
1. Switch to the **Admin & Demo** role or navigate to `/demo`.
2. Click **"Seed 20 Demo Patients"**.
3. *Alternative via terminal (cURL):*
   ```bash
   curl -X POST http://127.0.0.1:8000/demo/seed
   ```

---

## 3. Interface Breakdown & Feature Capabilities

### 1. Nurse Guardian Queue (`/queue`)
- **Primary Function:** Continuous, real-time prioritization of active emergency department patients.
- **Core Invariant:** The queue order is **strictly computed by the backend time-engine** (`final_acuity ASC, time_critical_flag DESC, deterioration_trend DESC, time_in_current_band DESC, arrival_time ASC`). **Never sorted client-side.**
- **Key Actions:**
  - **1-Tap Escalate:** Escalates urgency instantly with zero friction.
  - **De-escalate Level:** Gated by a modal requiring `target_acuity > current` and a structured justification code (flagged for retrospective audit).
  - **Reset Reassessment Clock:** 1-tap "Mark Reassessed" to reset overdue alarms when vitals are confirmed stable.

---

### 2. Physician Workspace & Doctor View (`/doctor`, `/doctor/:caseId`)
- **Primary Function:** Fast-context physician worklist answering *"What changed since I last looked?"*
- **Key Features:**
  - **"What Changed" Hero Banner:** Highlights new vitals, deterioration alerts, and unreviewed diagnostic results.
  - **Vital Trend Sparks:** Inline mini-sparklines displaying physiological trajectory (e.g., HR: 98 -> 118 bpm, worsening).
  - **1-Click Diagnostic Sign-off:** Sign off on pending lab/imaging results directly from the banner.
  - **Review Cursor Progression:** Clicking *"Mark Case Reviewed"* advances the physician's cursor timestamp and clears reviewed alerts.

---

### 3. Executive Control Tower & Alerts Feed (`/control-tower`, `/alerts`)
- **Primary Function:** Anticipatory department operations and interruptive alert fatigue management.
- **5 Anticipatory Tiles:**
  1. *Tile 1 — Acuity Bands:* ESI 1..5 distribution with highlighted overdue counts.
  2. *Tile 2 — Deteriorating Patients:* Cases whose physiology crossed acuity thresholds.
  3. *Tile 3 — Stuck Patients:* Flow bottlenecks (e.g. tests ordered but sample uncollected).
  4. *Tile 4 — Capacity & Beds:* Spaces and clinicians free vs needed.
  5. *Tile 5 — Inbound Ambulances:* En-route transports with predicted arrival acuity.
- **Alert Fatigue Budget Meter:** Measures interruptive alerts per nurse per hour against configured fatigue targets.
- **Web Audio Alarm Cues:** Subtle dual-tone clinical chime for critical bypass alerts (can be toggled in header).

---

### 4. Ambulance Inbound Board & Pre-Arrival Workflow (`/ambulance`, `/ambulance/:caseId`)
- **Primary Function:** Pre-arrival telemetry, predicted acuity, and identity matching.
- **Key Features:**
  - **Simulated ETA Countdown:** Displays narrowing arrival interval (e.g., 6–10 mins).
  - **Paramedic Transport Delay Simulation:** Add +5m, +10m, or custom delay notes.
  - **Identity Matching Prompt (Phase 7.1):** Candidate EHR records proposed with match probability, but cases run strictly unlinked until clinical staff confirms via `POST /cases/{id}/identity/confirm` (guarantees zero silent merges).
  - **1-Tap Arrival Transition:** Single-tap `POST /cases/{id}/arrival` transitions patient from `PRE_ARRIVAL` to `ACTIVE` ED triage.

---

### 5. Patient & Family Transparent Waiting Room Portal (`/patient/:caseId`)
- **Primary Function:** Patient/caregiver waiting room companion app (kiosk or mobile).
- **Strict Information Isolation (Phase 8.1 / CP15):** Absolutely **0 clinical acuity scores, 0 ESI numbers, 0 confidence metrics, and 0 clinician notes** are accessible or exposed in this view.
- **Key Features:**
  - **4-Stage Progress Tracker:** `In Transit` -> `Triage & Waiting` -> `In Treatment Area` -> `Care Completed`.
  - **Estimated Wait Range:** Displays estimated wait window with dynamic emergency caveat and `patients_ahead` indicator.
  - **"I Feel Worse" Button:** Single-tap patient escalation affordance that immediately flags the patient on the Nurse Guardian Queue without altering clinical physiology.

---

### 6. Admin Governance & Demo Runner (`/admin`, `/demo`)
- **Standing Demographic Equity Panel (Phase 9.7):** Measures acuity distribution and override rate by age band (Adult, Paediatric, Geriatric) and sex.
- **Retrospective Review Queue (Phase 9.6):** Audit table of all de-escalation decisions with clinician identity, timestamps, and reason codes.
- **20-Scenario Benchmark Catalog:** Complete interactive library of Phase 14.1 scenarios.
- **Mass-Casualty Surge Simulator:** Triggers a 3x burst arrival to demonstrate queue stability and sub-linear alert scaling.

---

## 4. The 7-Minute Demo Script & Feature Walkthrough

Follow this step-by-step presentation arc during the live hackathon evaluation:

### Step 1: Walk-In Registration & ML Challenger Refusal (Minute 0:00 – 1:30)
1. **Action:** Click **"Register Patient"** in the sidebar.
2. **Action:** Enter:
   - *Name:* "Arthur Dent"
   - *Age:* 48
   - *Complaint:* "Chest tightness and severe shortness of breath after climbing stairs."
3. **Action:** Click **"Create Emergency Case"**.
4. **Action:** On the Case Detail workspace, click **"Autofill T6 Set (NEWS2 Rescore)"** on the vitals form and click **"Save Vitals & Rescore"**.
5. **Presentation Point:** Point out the **Risk Assessment Hero Banner**:
   - The clinical rule engine scores NEWS2 = 7 (ESI 2).
   - The ML Challenger model suggests ESI 3 (lower urgency).
   - The system executes the architectural defense: `final_acuity = min(rules_acuity, ml_acuity) = 2`.
   - The ML lower suggestion is **strictly refused** with an on-screen callout: *"Rules override ML challenger to prevent unsafe under-triage."*

---

### Step 2: 1-Tap Emergency Bypass (Minute 1:30 – 2:45)
1. **Action:** In the Case Detail header, click the red glowing **"EMERGENCY BYPASS (ESI 1)"** button.
2. **Action:** Confirm the single tap.
3. **Presentation Point:** 
   - Observe the instant transition to **ESI 1 IMMEDIATE RESUSCITATION (Glowing Red Hero)**.
   - Navigate to the **Nurse Guardian Queue** (`/queue`).
   - Show that this patient has jumped to the very top of the queue in **0.00 seconds with zero latency**.
   - Navigate to **Real-Time Alerts** (`/alerts`) to show the `CRITICAL_BYPASS_PATIENT` alert.

---

### Step 3: Simulate 3x Patient Surge Burst (Minute 2:45 – 4:15)
1. **Action:** Switch role to **ED Administrator** and navigate to **Demo Runner** (`/demo`) or **Operations** (`/ops`).
2. **Action:** Click **"Run 3x Surge Simulation"**.
3. **Presentation Point:** Observe the **Surge Proof Panel**:
   - **Queue Scaling:** Queue grows from baseline to 30+ arrivals without sorting inversions.
   - **Sub-Linear Alert Growth:** Alert rate increases sub-linearly (preventing alert fatigue).
   - **409 Capacity Conflict Surface:** Click on an unassigned patient and attempt to assign a Resuscitation Bay—the system returns an HTTP 409 conflict and renders the `CapacityConflictPanel` with structured candidate mitigation actions while guaranteeing **no acuity downgrade**.

---

### Step 4: Transparent Patient Waiting Room View (Minute 4:15 – 5:30)
1. **Action:** Copy any active case ID from the queue and navigate to `/patient/:caseId`.
2. **Presentation Point:**
   - Note the **complete absence of ESI numbers or clinical acuity**.
   - Show the 4-stage **Care Pathway Progress Tracker**.
   - Show the **Estimated Wait Interval** with the mandatory caveat: *"Estimates update dynamically based on department emergencies"*.
3. **Action:** Click the red **"I Feel Worse"** button and submit the note: *"Feeling sharp chest pain and dizzy."*
4. **Action:** Switch back to the **Nurse Guardian Queue** (`/queue`).
5. **Presentation Point:** Show that the patient's card now has a pulsing **DETERIORATING** chip and has moved to the top of the overdue reassessment priority list.

---

### Step 5: Degraded-Mode Printable Fallback Queue (Minute 5:30 – 7:00)
1. **Action:** Open a new browser tab and navigate directly to:
   ```
   http://127.0.0.1:8000/queue/printable
   ```
   *(Or via terminal: `curl http://127.0.0.1:8000/queue/printable`)*
2. **Presentation Point:**
   - This endpoint renders a **100% dependency-free plain-text printable queue snapshot**.
   - Contains patient names, current acuity, arrival timestamps, and reassessment-due deadlines with manual clinician checkboxes.
   - **Invariant Highlight:** Proves that if the hospital suffers a catastrophic network outage or JavaScript frontend crash, staff can print this snapshot directly to paper to maintain emergency department operations without clinical disruption.

---

## 5. Test Suite Verification

Run the automated test suite at any time to verify all clinical invariants:

```bash
# Frontend Vitest suite (8 unit tests for ISO datetime parsing & API errors)
cd frontend && npm run test

# Frontend TypeScript compiler check
cd frontend && npx tsc --noEmit

# Backend Pytest suite (covering age router, NEWS2, PEWS, bypass, & time engine)
pytest
```
