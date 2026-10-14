# NEXUS: Autonomous Scheduling Agent Reliability & Evaluation Lab

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-cyan.svg)](https://react.dev)
[![Vite](https://img.shields.io/badge/Vite-6-purple.svg)](https://vitejs.dev)
[![Architecture: Frozen Specification](https://img.shields.io/badge/Architecture-Sealed-darkgreen.svg)](#architecture)

> **"John the recruiter will gladly take a call with CEO Jill at 7:00 AM in the morning, but not with his peer."**  
> *How do you build autonomous scheduling agents that reliably navigate subtle social hierarchies, implicit flexibilities, memory contradictions, and hard calendar math without hallucinating invalid slots or leaking private context?*

**NEXUS** is an end-to-end evaluation laboratory and reliability testbed designed to make autonomous AI agents production-ready. Instead of treating scheduling as an unstructured text prompt, NEXUS isolates deterministic calendar constraints, timezone transitions, and memory provenance from probabilistic LLM ranking.

---

## 🏛️ System Architecture

NEXUS enforces a strict unidirectional execution flow with auditable boundaries:

```text
       Scenario & Context
               │
               ▼
   [ Isolated Memory Retrieval ]
         (OBSERVED → INFERRED → CONFIRMED)
               │
               ▼
[ Deterministic Candidate Generator ]
 (Zero hallucinations: slots are computed mathematically)
               │
               ▼
     [ LLM Decision Engine ]
 (Ranks valid options, selects bounded communication templates)
               │
               ▼
   [ Deterministic Policy Validator ]
  (Validates candidate integrity, template authorization)
               │
               ▼
      [ State Transition ]
               │
               ▼
   [ Independent Evaluator ]
 (Audits assertions: calendar overlap, action match, template match)
```

### Key Architectural Invariants
1. **The LLM Never Generates Time Slots:** The Deterministic Candidate Generator computes all valid slot boundaries. The LLM only ranks and selects among validated candidates.
2. **Deterministic Replayability:** Every prompt, input hash, and LLM output is persisted. Any historical run can be replayed byte-for-byte to distinguish between LLM drift and code regressions.
3. **Auditable Evidence-Backed Memory:** Memory transitions strictly through `OBSERVED → INFERRED → CONFIRMED` with attached run-level evidence. Contradictions trigger explicit resolution states.
4. **Evaluation Independence:** The Evaluator is isolated from the simulation runtime. Traces are append-only audit artifacts, never domain state sources.

---

## 🧪 Core 10 Evaluation Benchmark

NEXUS comes bundled with the **Core 10 Suite**, exercising the hardest edge cases in multi-party coordination:

| Scenario | Name | Core Test |
|---|---|---|
| **01** | `core_01_happy_path` | Basic acceptance & template bounds across open candidate slots |
| **02** | `core_02_hard_conflict` | Inescapable calendar conflict requiring graceful, deterministic decline |
| **03** | `core_03_privacy_conflict` | Private conflict details scrubbed before external communication |
| **04** | `core_04_soft_preference` | Ranking valid options according to internal soft preferences |
| **05** | `core_05_explicit_override` | **VIP flex logic**: VIP priority overriding an existing internal hold |
| **06** | `core_06_timezone_conflict`| Multi-party timezone normalization and safe offset calculation |
| **07** | `core_07_dst_edge_case` | Scheduling safely across Daylight Saving Time clock shifts |
| **08** | `core_08_stale_memory` | Overriding stale preferences with fresh explicit directives |
| **09** | `core_09_privacy_paraphrase`| Abstracting internal meeting titles into generic client-safe labels |
| **10** | `core_10_no_perfect_option`| Handling constrained availability and proposing alternative windows |

---

## 🖥️ Developer Debugger UI

NEXUS includes a 3-panel developer inspection dashboard built with React, Vite, and TailwindCSS:

- **Left Panel (Scenario Manifest & Controls):** Choose deterministic test scenarios, switch between `LIVE` (real LLM) and `REPLAY` (hash-verified audit) execution modes.
- **Middle Panel (Trace Timeline):** Visualizes the full step-by-step pipeline: `STATE_BEFORE` ➔ `MEMORY` ➔ `VALID_OPTIONS` ➔ `LLM_ACTION` ➔ `VALIDATION` ➔ `STATE_AFTER`.
- **Right Panel (Evaluation Scorecard):** Instant breakdown of all assertion outcomes (`action_type_equals`, `no_calendar_overlap`, `communication_template_equals`).

---

## 🚀 Quickstart

### Prerequisites
- Python 3.10+
- Node.js 18+ (for frontend)
- (Optional) `GEMINI_API_KEY` for live LLM mode

### Local Setup
```bash
# 1. Clone repository
git clone https://github.com/<your-username>/nexus.git
cd nexus

# 2. Setup Python environment
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

pip install -e ".[dev]"

# 3. Initialize Database & Scenarios
alembic upgrade head
python ingest_db.py

# 4. Build Frontend
cd frontend
npm install
npm run build
cd ..

# 5. Run Server (Single Port 8000 serves API + Debugger UI)
export GEMINI_API_KEY="your-api-key"
uvicorn nexus.api.main:app --host 127.0.0.1 --port 8000
```
Open **`http://localhost:8000/`** in your browser.

---

## 🐳 Docker Deployment

NEXUS is packaged as a multi-stage Docker container that compiles the frontend and runs the backend in one lightweight image:

```bash
docker build -t nexus-lab .
docker run -p 8000:8000 -e GEMINI_API_KEY="your-key" nexus-lab
```

### 1-Click Cloud Deployment
- **Render / Railway / Fly.io:** Connect your repository and deploy. NEXUS includes `render.yaml` for automatic provisioning.

---

## 🧪 Running Tests & Regression Engine

```bash
# Run full unit & integration test suite (116 tests)
pytest

# Run regression test comparing two agent versions
python -m nexus.cli.main eval --suite core_10 --compare v0.1 v0.2
```

---

## 📜 License
MIT License. Built as an autonomous coordination reliability laboratory.
