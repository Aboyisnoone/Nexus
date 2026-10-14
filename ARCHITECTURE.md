# NEXUS Project Constitution & Architecture (v0.1)

This document represents the **frozen architectural boundaries** for NEXUS v0.1.

> **Architectural changes require an explicit specification defect or must be treated as v0.2 work.**

## Core Principles

1. **Scenario is Immutable:** The agent operates inside the scenario. It cannot modify the scenario, the initial state, or the evaluation criteria.
2. **Hard Constraints Are Deterministic:** The LLM cannot override hard constraints. All timezone math, overlap checks, and policy rules are deterministic.
3. **LLM Produces Structured Data Only:** The LLM does not execute instructions or mutate state directly. It outputs a strictly validated JSON structure (`PROPOSE_TIMES` or `DECLINE`).
4. **Evaluator is Independent:** The evaluation engine is separate from the agent. There is no LLM-as-a-judge in v0.1; evaluation relies on a typed assertion DSL.
5. **Privacy is Structural:** Knowledge does not imply permission to communicate. Privacy acts as an output capability boundary enforced via structural data schemas. Free-form communication is explicitly banned in v0.1 in favor of bounded templates.
6. **Simulated Time is Authoritative:** All temporal behavior relies strictly on scenario-defined simulated time. No domain decision may depend on wall-clock time (`datetime.now()`, `time.time()`).
7. **Canonical Time & IANA Timezones:** All internal domain decisions are compared in canonical UTC. However, local time boundaries require full IANA timezone rules (`zoneinfo`), not static fixed offsets, to strictly respect historical daylight saving transitions (DST).
8. **No Hidden Retries:** If an LLM call fails schema validation or policy checks, the run fails with a structured error.

## Memory Strictness

* **OBSERVED** -> **INFERRED** -> **CONFIRMED**
* `INFERRED` memory cannot silently become `CONFIRMED`. It requires an explicit confirmation event.
* Overrides during decision-making do not automatically mutate long-term memory.

## Live vs Replay Identity

* **Live Run:** Calls the LLM and records identity, prompt, and response.
* **Replay Run:** 100% deterministic. Intercepts the LLM call using `replay_of_run_id` and sequential call indexing.

## Infrastructure Exclusions (v0.1)

* No LangGraph or arbitrary agent frameworks.
* No vector databases (Pinecone, Chroma, etc.).
* No real external integrations (Google Calendar, Outlook, Gmail).
* No `eval()` execution for assertions.

## Scheduling Constraints

* **Mathematical Candidates:** The Constraint Engine deterministically generates *all* mathematically valid slots based on constraints (window, duration, granularity). It never selects "the best" slots—that is left to the Decision Engine.
* **Interval Semantics:** All calendar checking relies on half-open intervals [start, end). A candidate meeting starting exactly when an event ends is structurally valid.
* **Working Hours & Timezones:** Working boundaries are explicit inputs. Meetings are validated to strictly fit within localized working hour bounds. The Constraint Engine performs all internal overlap and boundary iteration in absolute UTC, preserving IANA zone context for local representations.

## Agent Actions & Privacy Boundary

* **Discriminated Union:** Agent decisions are serialized strictly as one of a finite set of structural actions (PROPOSE_TIMES or DECLINE).
* **Validation Layers:** Validation occurs offline in two deterministic steps: **Schema Validation** (enforcing Pydantic strictness, extra='forbid', and type safety) and **Policy Validation** (enforcing permitted templates, public reasons, and valid candidate option boundaries).
* **Structural Privacy:** Privacy is not enforced by searching for restricted keywords. It is enforced because the schema completely lacks an unrestricted text channel. The agent must choose from a strict menu of communication.template and public_reason values. Protected knowledge (e.g., preference_basis) serves purely as internal provenance.
* **Option Integrity:** The LLM ranks candidate slots, but the Policy Validator deterministically rejects any hallucinated slot ID that was not provided by the mathematical Constraint Engine.

## Simulation & State Transition

* **Simulator Purity:** The Simulator is a pure function (State + ValidatedAction = Result(NewState)). It strictly avoids mutating the original Scenario or the input SimulationState, generating entirely new deeply immutable state models.
* **No Booking Semantics:** The v0.1 agent makes decisions (PROPOSE_TIMES or DECLINE); it does not actually book calendar slots or modify external participants' states. The simulator faithfully respects this by recording the action structurally in the ction_history without mutating the underlying calendar.

## Typed Assertion Evaluator

* **Independence:** The evaluator acts as the final judge of the simulation, verifying structured assertions deterministically without using LLM judgements or string evaluation hooks.
* **Strict Taxonomy:** Only explicitly supported DSL assertions can evaluate scenarios (ction_type_equals, 
o_calendar_overlap, etc).
* **PASS / FAIL / ERROR Semantics:** 
  - **FAIL** denotes the agent made a decision that structurally conflicts with the scenario expectations.
  - **ERROR** exclusively denotes an internal failure where the evaluator structurally lacked the temporal context or candidate data to execute the test.

## DecisionTrace & Observability

* **Immutable Provenance:** DecisionTrace is an immutable historical record of execution provenance. It strictly records structural steps (STATE_BEFORE, MEMORY, VALID_OPTIONS, LLM_ACTION, VALIDATION, STATE_TRANSITION, STATE_AFTER, EVALUATION).
* **Offline Recording:** It does not execute decisions, query databases, determine evaluation truth, or act as an orchestration engine.
* **No Chain-of-Thought:** It intentionally excludes hidden reasoning steps or prompt templates. It guarantees a clear record of structural state mapping constraints to structured decisions.
* **Failure Tracing:** Traces successfully reflect terminal states (e.g. ERR_NO_VALID_OPTIONS) securely mapping valid paths without enforcing artificial success loops.

## Persistence Layer

* **Isolated JSONB Mappings:** The database serves solely as an audit and storage mechanism via SQLAlchemy and PostgreSQL JSONB. The database models do not dictate or pollute domain behavior.
* **Serialization Integrity:** Domain objects (DecisionTrace, Scenario, MemoryItem) undergo strict Pydantic serialization going out, and strict TypeAdapter validation coming in. The application fundamentally never manipulates untyped dictionaries.
* **Immutability Perserved:** The database decision_traces and llm_recordings implement immutable insert semantics. Trace entries cannot be overwritten through application behavior, guaranteeing offline audit integrity.

## Database Testing Boundaries

* **Offline vs. Integration:** Serialization boundaries and logic are validated instantly offline via SQLite in-memory databases (	est_persistence.py). 
* **PostgreSQL Validation:** Structural and type constraints (like JSONB mappings) are explicitly validated against a real instance in 	est_postgres_integration.py (via NEXUS_TEST_DATABASE_URL). These tests are explicitly skipped rather than silently replaced with SQLite when a database isn't available.

## Decision Pipeline (Task 010)

The core runner loop relies on a simple synchronous DecisionPipeline handling the execution of a Scenario.
It orchestrates stages: STATE_BEFORE -> MEMORY -> VALID_OPTIONS -> LLM_ACTION -> VALIDATION -> STATE_TRANSITION -> STATE_AFTER.
Execution can happen in LIVE mode (injectable LLM client calls are made and recorded via call_index) or REPLAY mode (creates a new run, retrieving deterministic responses from source llm_recordings without invoking the network). Replays enforce strict equivalence without using similarity heuristics or wall-clock times.

### Execution Failures
The runner categorizes domain errors strictly into trace FailureSteps, including specifically:
- ERR_LLM_SCHEMA: Malformed structural output from the LLM.
- ERR_INVALID_ACTION: Action requested illegal option.
- ERR_POLICY_VIOLATION: Authorized template/privacy constraint boundary violated.
- ERR_MISSING_CONSTRAINTS: Missing mandatory scheduling constraints in scenario payloads (no hidden default behaviors exist).
- ERR_MISSING_RECORDING: (Replay-specific) Could not find source run recording mapping for the given call index.
- ERR_REPLAY_INPUT_MISMATCH: (Replay-specific) The generated deterministic prompt hash mismatch against the historically saved prompt hash during a replay execution.
- ERR_SYSTEM: Catch-all restricted exclusively to infrastructure/runtime breakdowns, NOT masking domain errors.

## Memory Subsystem (Task 011)

The memory subsystem is responsible for persisting long-lived, cross-session facts and preferences. 
It cleanly separates **runtime context** (ephemeral facts relevant to the current scenario) from **long-term memory** (reusable facts supported by evidence).

### Memory States
- **OBSERVED**: A fact supported directly by evidence (e.g., user moved a meeting).
- **INFERRED**: A hypothesis derived from evidence.
- **CONFIRMED**: A preference explicitly validated by a confirmation event.

### State Transitions and Confirmation
- OBSERVED -> INFERRED -> CONFIRMED
- A memory can only transition to CONFIRMED via an explicit, typed ConfirmationEvent. Silent confirmations or arbitrary heuristic confidence scores are strictly prohibited.
- CONFIRMED memories are durable and cannot be silently demoted back to OBSERVED or INFERRED.

### Contradiction Handling
When new observations conflict with a CONFIRMED memory, the system does NOT silently overwrite the authoritative preference. 
Instead, it records an explicit, auditable Contradiction against the memory version while preserving the CONFIRMED value. 
During runtime, a user's direct instruction can temporarily *override* this preference for the current decision, but the override does not mutate the long-term memory record itself.

### Evidence and Provenance
Every memory must contain traceable, immutable Evidence explicitly linking to historical executions (e.g., source_run_id). Evidence supports a memory but is not automatically a memory itself.

### Post-Run Updates and Determinism
Memory updates are processed exclusively post-run via pply_post_run_updates() to strictly prevent memory contamination during an active simulation. Retrieval is structural, 100% deterministic, explicitly scoped by context_id and key, and stable-ordered without relying on vector search, fuzzy matching, or LLMs.

## LLM Decision Engine (Task 012)
The LLM Decision Engine acts purely as a contextual ranking engine, strictly constrained between deterministic candidate generation and deterministic schema/policy validation.
- **Inputs**: It receives a deterministic prompt (PromptBuilder, labeled with decision_prompt_v1) containing structurally serialized options (via slot_id), memory records (preserving explicitly CONFIRMED vs INFERRED state), and scenario instructions. It does NOT see evaluator assertions or criteria.
- **Constraints**: It cannot generate options or mutate state. It must output a strict JSON conforming to AgentAction.
- **Integrity**: Prompt injection is contained natively. Even if prompt injection successfully coerces the LLM to select an illegal option (e.g. slot_fake), the surrounding pipeline guarantees an immutable failure (ERR_INVALID_ACTION).
- **One-Shot**: For v0.1, the engine executes one model call per decision without hidden retry loops, making every failure transparent and measurable.

### Schema vs. Policy Failures
- **ERR_LLM_SCHEMA**: The LLM output failed structural schema validation (e.g., missing required fields, entirely non-object JSON shapes like arrays/primitives, or mismatched enums).
- **ERR_INVALID_ACTION**: The LLM output passed structural schema validation perfectly but contained invalid contextual selections (e.g. attempting to select a hallucinated slot_fake that is not part of the deterministic candidate options).

## Core 10 Evaluation Suite & Idempotency
- **Experimental Integrity**: Ten independent evaluations form the baseline test suite. Scenarios strictly separate deterministic setup (memory seeds, calendar, context) from LLM-executed prompt paths.
- **Run-Isolated Seeding**: To enforce cross-run evaluation integrity, scenario seed memories are prefixed with their namespace (e.g., `{run_id}_`) before persistent repository injection. The prefix is cleanly stripped upon memory service retrieval. This protects long-term memory while guaranteeing mathematical determinism inside SimulationState.

## Regression and Version Comparison (Task 014)
NEXUS implements a deterministic regression-comparison layer that evaluates structural behavior changes between agent versions.

### Code Regression Semantics
A **pure code regression** occurs strictly when the same recorded LLM response is processed by two code versions, resulting in differing structural outcomes. It guarantees that any measured failure or improvement is derived entirely from downstream software logic (e.g. constraints, policy, parsing) and not from LLM stochasticity.

### Replay Compatibility and Input Hashes
The replay input hash is the authoritative gatekeeper for comparison. If a candidate version structurally alters the effective LLM input (e.g. prompt text, version label, context payload), the prompt_hash diverges. This immediately results in an INCOMPATIBLE_INPUT classification. The system will NEVER bypass this check or silently accept a mismatch to force a comparison. 

### Prompt and Model Changes
A change to the LLM model identity or a change to the underlying prompt template (e.g. decision_prompt_v1 -> decision_prompt_v2) is fundamentally an agent-input change, not a downstream code regression. The regression system properly isolates these by enforcing INCOMPATIBLE_INPUT, requiring developers to record new live baseline fixtures before measuring their impact.

### Suite and Assertion-Level Comparison
Comparisons strictly consume PipelineRunResult.simulation_result to evaluate structured output deterministically. 
* **Suite Summaries:** The comparator outputs exact counts of Unchanged, Improved, Regressed, Incompatible, and Error outcomes. It does not consolidate results into a weighted or subjective "agent quality score."
* **Assertion Granularity:** For every regression, the exact expected vs. actual values of individual assertions are preserved and surfaced (e.g. ction_type_equals: PASS -> FAIL).

### Missing Fixtures
If a LIVE recording does not exist for a requested baseline scenario, the system halts with an explicit ERROR rather than implicitly executing a live LLM run or fabricating a comparison.


## API Layer (Task 015)
NEXUS exposes its core capabilities through a lightweight, stateless HTTP API powered by FastAPI.
The API strictly serves as a transport/serialization boundary and contains zero domain logic (no scheduling math, validation logic, or evaluator rules). It delegates entirely to the existing DecisionPipeline and NexusRepository.

### Route Mapping
* **Execution:** POST /api/v1/scenarios/{id}/run?mode={LIVE|REPLAY} triggers the pipeline. It surfaces domain errors natively in structured responses rather than collapsing them to HTTP 500s.
* **Audit:** GET /api/v1/runs/{id}/trace streams the immutable serialized DecisionTrace. It strictly avoids reconstructing the domain SimulationResult from historical snapshots.
* **Memory Inspection:** GET /api/v1/memory/{context_id} directly fetches isolated context memories, preserving deterministic order and evidence state mappings.

### Error Taxonomy
* **HTTP Errors:** Used for transport and validation (e.g. 400 missing replay parameter, 404 scenario not found, 422 malformed schema, 500 database disconnection).
* **Domain Errors:** Used for structured simulation outcomes (e.g., ERR_INVALID_ACTION, ERR_POLICY_VIOLATION, ERR_REPLAY_INPUT_MISMATCH). The API often returns a 200 HTTP status alongside a domain-level status=FAILED response body, distinguishing a successful request processing from a failed agent evaluation scenario.
