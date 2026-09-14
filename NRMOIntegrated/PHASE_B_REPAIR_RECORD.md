# Phase B Repair Record

Parent issue: #6  
Branch: `fix/issue-6-phase-b-historical-provenance`  
Scope: preserved historical specification provenance only

## Completed in this phase

- Marked the legacy Type ZERO `CORE / VENTURE / MISSION / SHUTDOWN` table as superseded for current mode semantics.
- Added canonical translation guidance to the historical action-space procedure.
- Marked the legacy SOP OS mode and permission tables as historical/non-controlling.
- Explicitly prevented the old `MISSION = only A` permission rule from redefining current goal-constrained MISSION.
- Typed HARE as Context Override, not Operational Mode.
- Retyped both HST-N `Hold Mode` headings as Hold state/data-reliability signal semantics.
- Removed wording that could imply HST-N or SOP acquires sovereign/governance authority from Hold.
- Added `HISTORICAL_PROVENANCE_REGISTER.md` to classify remaining legacy terminology and prevent blind global rewrites.

## Intentionally not changed

- No implementation code.
- No archive/version snapshot rewriting.
- No deletion of historical specification text.
- No global search-and-replace of `CORE`, `MISSION`, `SHUTDOWN`, `HOLD`, or related terms.
- No Phase C module/file provenance repair.
- No DecisionCompass implementation alignment.

## Canonical interpretation preserved

- Human/User = final sovereign decision authority.
- NRMO = final governance/admissibility/veto authority.
- StrongEngine Omega Full = search/selection inside the NRMO-admitted set.
- Operational Modes = `NORMAL / VENTURE / MISSION / SAFE`.
- MISSION = Goal-Constrained Execution.
- MISSION-DEFENSE = action-space / `A_allowed` defensive extension or override.
- HOLD = state/result/signal, not Operational Mode.
- HARE/TRAINING = Context Overrides.
- SHUTDOWN = exceptional/terminal control when it truly means halt.
