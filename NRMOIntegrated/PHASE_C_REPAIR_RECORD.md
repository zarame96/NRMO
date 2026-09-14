# Phase C Repair Record

Parent issue: #6  
Branch: `fix/issue-6-phase-c-implementation-provenance`  
Scope: implementation provenance and Norn naming boundary only

## Findings established before repair

- Part X describes a reference `nrmo_full/engine/` tree containing `omega_full.py`, `shinobi.py`, `norn.py`, `map_layer.py`, and `omega_v52_adapter.py`.
- The current checked-in `NRMOIntegrated/v52_codebase/engine/` directory at the Phase C base contains only `__init__.py`, `omega_full.py`, and `strong_engine.py`.
- Therefore the Part X concrete module tree is not a current checked-in repository manifest.
- Appendix A preserves a historical `engine/norn.py` source listing whose comments describe Norn/Skuld task-manager behaviour.
- The Normative Canon defines canonical Norn as an interpretive governance perspective, so the historical task-manager name is overloaded.

## Completed in this phase

- Added `IMPLEMENTATION_PROVENANCE_REGISTER.md`.
- Added a PDF-visible provenance notice immediately before Part X implementation content.
- Added a PDF-visible provenance notice immediately before Appendix A code listings.
- Explicitly separated current checked-in implementation evidence from historical/reference implementation snapshots.
- Explicitly separated canonical Norn from historical Norn/Skuld task-manager implementation names.
- Established evidence priority for implementation-existence claims.

## Intentionally not changed

- No Python or other implementation code.
- No historical code listing deleted or rewritten.
- No invented `norn.py`, `shinobi.py`, `map_layer.py`, or `omega_v52_adapter.py` files.
- No rename of current or historical implementation classes.
- No DecisionCompass changes.
- No Phase D publication/version repair.
- No Phase E implementation conformance changes.

## Canonical boundary preserved

- Human/User = final sovereign decision authority.
- NRMO = final governance/admissibility/veto authority.
- StrongEngine Omega Full = execution/search within the admitted set.
- Canonical Norn = interpretive governance perspective.
- Historical task-manager Norn/Skuld = overloaded implementation artifact, not canonical Norn.
