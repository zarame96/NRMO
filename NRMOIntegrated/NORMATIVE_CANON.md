# NRMO Normative Canon

**Status:** Normative  
**Authority:** Human Sovereign → Vision → NRMO → Engines → Implementations  
**Purpose:** Resolve terminology and authority conflicts across preserved generations of the integrated NRMO specification without destroying historical provenance.

## 1. Precedence Rule

This Canon is the authoritative terminology and role map for the current NRMO specification.

> In case of conflict between preserved historical specifications and the NRMO Normative Canon, the Normative Canon prevails.

Historical specifications, experiments, reference implementations, negative results, and superseded terminology remain research assets. They do not override this Canon unless explicitly re-adopted by a later normative revision.

## 2. Sovereignty and Authority

### 2.1 Human Sovereign

The Human/User is the **final sovereign decision authority**.

The Human Sovereign may accept, reject, defer, or terminate an action. No NRMO layer, engine, model, or implementation supersedes human sovereignty.

### 2.2 NRMO

NRMO is the **final governance, admissibility, and veto authority** inside the NRMO architecture.

NRMO determines the admissible action set and ruin boundary. It may permit, reject, hold, narrow, or terminate admissibility according to the governing specification. It does not acquire human sovereignty by exercising governance authority.

### 2.3 StrongEngine Ω Full

StrongEngine Ω Full is the **execution/search layer**. It generates, searches, evaluates, ranks, and selects candidates only within the admissible domain supplied by governance.

Formal invariant:

`A_t = NRMO(X_t)`  
`a_t = Ω(A_t)`  
`a_t ∈ A_t`

StrongEngine Ω Full must never redefine the ruin boundary or expand `A_t` on its own authority.

### 2.4 Canonical Authority Flow

`Human Sovereign → Vision → NRMO → StrongEngine Ω Full → Implementations`

For an individual decision:

`NRMO → admissible set A_t → StrongEngine Ω Full → candidate/action within A_t → Human Sovereign → adoption/execution decision`

The architecture therefore distinguishes **sovereignty**, **governance authority**, and **execution/search authority**.

## 3. Canonical Type System

### 3.1 Operational Modes

The canonical Operational Modes are:

- `NORMAL` — standard operation.
- `VENTURE` — bounded exploration under explicit limits and reversibility controls.
- `MISSION` — goal-constrained execution under explicit mission conditions, success criteria, exit criteria, and audit requirements.
- `SAFE` — risk-minimised/defensive operation with a narrowed action space.

Operational Modes primarily govern Type ZERO gating and the applicable permitted-action profile.

### 3.2 Context Overrides

Context Overrides are not additional ordinary Operational Modes:

- `TRAINING` — isolated training/simulation context. Training output must not directly become real-world action.
- `HARE` — Hare-no-Hi context override. Expressive/emotional constraints may be relaxed, but ruin-avoidance remains binding.

### 3.3 Training Grade

`A–F, E+` denotes **Training Grade**, not an Operational Mode taxonomy.

Therefore:

`TRAINING = Context Override`  
`A–F / E+ = Training Grade`

### 3.4 Governance / Lifecycle States

The canonical lifecycle-state family is:

- `ACTIVE`
- `HOLD`
- `EXIT`
- `SAFE_EXIT`

`HOLD` is a **state/governance result requiring resolution or human intervention**, not an Operational Mode.

Domain-specific records named “Hold” (for example, data-reliability Hold) must be typed as signals/records or mapped explicitly to the lifecycle state. They must not silently create another Operational Mode.

### 3.5 Exceptional Control

`SHUTDOWN` is an **exceptional/terminal defensive control**, not one of the four canonical Operational Modes.

SHUTDOWN may halt, defer, or terminate ordinary execution under its governing trigger conditions. Historical specifications that used SHUTDOWN as a peer of CORE/VENTURE/MISSION are preserved as historical mode taxonomies, not the current canonical taxonomy.

### 3.6 Action-Space Extension

`MISSION-DEFENSE` is an **A_allowed / action-space defensive extension or override**. It is not a fifth Operational Mode and must not redefine canonical `MISSION`.

### 3.7 Vision Context

`/#vision` is a **long-horizon orientation/value context**, not an Operational Mode and not an execution authority.

## 4. Canonical MISSION Definition

`MISSION = Goal-Constrained Execution.`

MISSION exists for deliberate execution toward an explicitly defined objective. A MISSION should define, as applicable:

- mission objective;
- deadline or temporal boundary;
- success criteria;
- exit/abort criteria;
- permitted commitment level;
- second-opinion or audit requirements where required;
- logging/rationale requirements.

MISSION is **not** canonically defined as “control at boundary approach” or as a mode whose purpose is simply to avoid irreversible-direction actions.

Historical defensive-MISSION semantics must be interpreted or migrated as one of:

- `SAFE`;
- `MISSION-DEFENSE`;
- another explicitly named defensive override/control.

No preserved historical passage may silently override this definition.

## 5. Historical Mode Mapping

The historical taxonomy `CORE / VENTURE / MISSION / SHUTDOWN` is superseded as the current Operational Mode taxonomy.

Mapping guidance:

- historical `CORE` → canonical `NORMAL`, where semantics are standard/normal operation;
- historical `VENTURE` → canonical `VENTURE`, subject to current definition;
- historical goal-constrained `MISSION` → canonical `MISSION`;
- historical defensive `MISSION` → `SAFE` and/or `MISSION-DEFENSE`, according to actual behavior;
- historical peer-mode `SHUTDOWN` → `SAFE` only where the behavior is merely defensive narrowing; true terminal/halt semantics remain `SHUTDOWN`.

This mapping is semantic, not a blind string replacement.

## 6. Type ZERO

Type ZERO is the **action-space and mode gating controller**.

It may:

- determine/apply Operational Mode according to governing inputs;
- determine the applicable permitted-action category/profile;
- gate execution before NRMO admissibility evaluation or according to the specified pipeline.

It does **not** possess independent actuator authority. “Execution controller” in preserved material must be read as **execution-gating controller**, not direct execution authority.

## 7. Norn

### 7.1 Canonical Norn

`Norn` is the **interpretive governance perspective** responsible for organising context, preserving structural consistency, and surfacing conceptual drift.

Canonical Norn is:

- not the sovereign;
- not the final decision maker;
- not StrongEngine Ω Full;
- not an execution engine;
- not inherently a task scheduler.

### 7.2 Historical Implementation Norn

Historical/reference components such as `engine/norn.py`, `NornTaskManager`, Norn/Skuld task assignment, alerting, mirroring, or failover are **implementation components with historically overloaded naming**.

They must be clearly labelled as historical/reference implementation artifacts or renamed in current implementations so they cannot be confused with canonical Norn. A future implementation rename should be handled separately from this terminology ruling.

## 8. Governance–Execution Separation

The following invariant is normative:

- NRMO defines admissibility and ruin boundaries.
- StrongEngine Ω Full searches inside admissibility.
- Lower implementation layers may not promote themselves into governance authority.
- Governance may not silently become an optimisation engine.
- Execution/search may not silently become a boundary-setting authority.

The admissibility invariant `a_t ∈ A_t` is strict.

## 9. Historical and Implementation Material

Concrete module trees, filenames, line counts, benchmark stacks, adapters, and reference source listings describe a specific implementation snapshot unless explicitly marked normative.

A concrete implementation description must state its status, for example:

- `Current Reference Implementation`;
- `Historical Implementation Snapshot`;
- `Experimental`;
- `Non-normative Illustration`.

A stale or absent file path does not change the normative theory. Conversely, implementation existence does not automatically make a concept normative.

## 10. Version and Provenance Rule

The publication version, baseline version, component version, and implementation-snapshot version must be distinguishable.

A v7.2 publication may preserve v7.1 baseline material, but preserved pages/sections must not create ambiguity about which version is authoritative. Version headers and provenance notes should explicitly distinguish:

- publication version;
- inherited baseline;
- historical section version;
- implementation/reference version.

## 11. Conformance Rule

DecisionCompass and other applications are implementations of NRMO specifications; they are not the source of the theory.

When implementation and Canon differ:

1. determine whether the Canon intentionally changed behavior;
2. record the implementation delta;
3. update implementation through a separately reviewable change;
4. do not retroactively redefine the Canon merely to match existing code.

## 12. Required Follow-up

After adoption of this Canon:

1. align the integrated specification authority wording with Human Sovereignty vs NRMO Governance Authority;
2. align §2 operational terminology with this Canon;
3. annotate/supersede conflicting historical Type ZERO/SOP MISSION definitions;
4. normalize HOLD terminology;
5. separate canonical Norn from historical implementation Norn;
6. clarify Type ZERO as execution-gating rather than actuator authority;
7. label concrete implementation snapshots and provenance;
8. run a full-text consistency audit for `MISSION`, `CORE`, `NORMAL`, `SAFE`, `SHUTDOWN`, `HOLD`, `Norn`, `Type ZERO`, `TRAINING`, `HARE`, and authority terminology;
9. only after specification freeze, assess DecisionCompass conformance and create implementation issues for genuine behavioral deltas.

---

This Canon resolves terminology and authority. It does not erase historical research, negative results, or superseded specifications; it makes their authority explicit.