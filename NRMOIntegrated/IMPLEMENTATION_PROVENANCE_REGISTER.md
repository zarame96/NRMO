# NRMO Implementation Provenance Register

Status: Supporting provenance record for Normative Canon repair  
Parent issue: #6  
Phase: C — implementation provenance and Norn naming boundary  
Authority: Subordinate to `NORMATIVE_CANON.md`

## Purpose

The integrated monograph preserves implementation snapshots from multiple generations. A concrete module path or source listing in the monograph is evidence about the snapshot from which that text was produced; it is not, by itself, evidence that the same module exists in the current checked-in implementation.

This register separates four different claims that must not be conflated:

1. **Normative architecture** — controlled by `NORMATIVE_CANON.md`.
2. **Current checked-in implementation** — established by files actually present in the repository at the audited ref.
3. **Historical/reference implementation snapshot** — preserved code/layout reproduced from earlier uploaded archives or source bundles.
4. **Archive/generated evidence** — useful for lineage, but non-controlling for current implementation claims.

## Phase C repository-state audit

Audit date: 2026-09-14  
Phase C base: `main` at `a7b62742dc43f000879b10f5a1835202db45c4bb`

The checked-in directory `NRMOIntegrated/v52_codebase/engine/` contains:

- `__init__.py`
- `omega_full.py`
- `strong_engine.py`

It does **not** contain:

- `norn.py`
- `shinobi.py`
- `map_layer.py`
- `omega_v52_adapter.py`

Therefore, Part X / §43.6-style repository layouts that list those files must be read as a **historical/reference implementation snapshot**, not as a live inventory of the current checked-in `v52_codebase`.

## Part X implementation chapter

`chapters/ch_part10_implementation.tex` identifies its source as uploaded implementation archives and reproduces a layout containing modules not present in the current checked-in `v52_codebase/engine/` directory.

Canonical interpretation:

- the chapter remains valuable as historical/reference engineering evidence;
- its concrete file tree is not current-repository authority;
- current implementation existence claims must be verified against the checked-in tree at the relevant ref;
- normative architectural claims remain subordinate to the Normative Canon even when reproduced source comments use older terminology.

The PDF build path now inserts an explicit provenance notice immediately before this chapter.

## Appendix A code listing

`appendices/A_code_listing.tex` preserves full/reference source listings, including a historical `engine/norn.py` whose comments describe Norn/Skuld task-manager behaviour.

That listing is **historical implementation evidence**. It does not establish that `engine/norn.py` exists in the current checked-in implementation.

The PDF build path now inserts an explicit provenance notice immediately before Appendix A.

## Norn naming boundary

### Canonical Norn

Under `NORMATIVE_CANON.md`, `Norn` is the **interpretive governance perspective**. It organises context, preserves structural consistency, and surfaces conceptual drift.

Canonical Norn is not:

- the Human Sovereign;
- final governance/admissibility/veto authority;
- StrongEngine execution/search;
- a task scheduler;
- a failover manager;
- a general alert dispatcher.

### Historical implementation Norn / Skuld

Historical/reference names such as:

- `engine/norn.py`;
- `NornTaskManager`;
- task assignment across execution units;
- Norn/Skuld primary/backup or failover behaviour;
- alerting, mirroring, or restoration logic;

are implementation artifacts with **overloaded naming**.

They must not be used to redefine canonical Norn. If such implementation components are retained or reintroduced as current code, their rename is an implementation task and must be handled separately from this specification/provenance repair.

## Evidence priority for implementation claims

When documents disagree about whether a module exists or what a current file tree contains, use this order:

1. actual checked-in repository tree at the stated ref;
2. current implementation documentation tied to that ref;
3. historical/reference source snapshots;
4. generated PDFs or copied code listings.

This priority is for **implementation existence/provenance claims only**. It does not replace the Normative Canon for architectural authority.

## No-delete / no-fiction rule

Phase C does not delete historical code listings and does not invent missing current modules to make the monograph appear consistent. It labels the provenance mismatch explicitly.
