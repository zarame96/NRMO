# NRMO Integrated System v7.2 rev2 — Current Package Manifest

Publication family: **NRMO Integrated System v7.2**  
Current integrated source revision: **v7.2 rev2**  
Normative authority: `NORMATIVE_CANON.md`  
Runtime source-of-truth: `IMPLEMENTATION_SOURCE_OF_TRUTH.md`

## What this repository currently contains

`zarame96/NRMO` is the specification / monograph / research-provenance repository.

Current checked-in package content includes:

- publication sources: `NRMO_Complete_v5_5.tex`, `chapters/`, `parts/`, `frontmatter/`, `appendices/`, `assets/`;
- generated/integrated publication artefacts preserved in the repository;
- Normative Canon and Issue #6 repair/provenance records;
- historical/reference implementation material such as `v52_codebase/` and archived source evidence;
- research/validation records that are explicitly labelled by provenance.

The legacy master filename `NRMO_Complete_v5_5.tex` is a retained build-root/source-lineage name. It does not define the publication version.

## What this repository intentionally does not contain

The current executable NRMO/StrongEngine runtime is **not bundled under `NRMOIntegrated/code/` in this repository**.

The repository `.gitignore` intentionally excludes:

```text
NRMOIntegrated/code/
NRMOIntegrated/world_sim_v50/
```

and states that the executable engine implementation is managed on the DecisionCompass side.

Therefore older package statements that describe `code/python/nrmo_v72_phase1/`, current C++/frontend runtime files, or its validation suite as locally bundled are superseded as current package-inventory claims.

Those records remain useful as development history, but current runtime existence/behavior must be verified in the runtime source-of-truth repository.

## Runtime source-of-truth

Current executable implementation repository:

- repository: `zarame96/DecisionCompass`
- Phase E audited commit: `ae00f9fd23760a6b4dd078723a1eed74ef7bffc9`
- runtime root at that commit: `NRMOIntegrated/code/python/nrmo_v72_phase1/`

See `IMPLEMENTATION_SOURCE_OF_TRUTH.md` for the controlling provenance rule and the current Phase E conformance snapshot.

The audited SHA is intentionally pinned. `main` is not a substitute for the recorded evidence after it moves.

## Current specification / implementation relationship

The repaired specification authority is:

```text
Human Sovereign
  -> Vision held by Human
  -> NRMO governance / admissibility / veto
  -> Engines search/select inside admitted space
  -> implementations
```

The implementation audit at the pinned DecisionCompass ref currently records:

- PASS: Aallowed narrowing-only behavior;
- PASS: NRMO hard filter before StrongEngine final selection;
- PASS: selected action constrained to the admitted set;
- PASS: Passive Ruin v7.2.1 narrows rather than enlarges the admitted set;
- PASS: HOLD and terminal Shutdown control are distinct;
- PASS: MISSION selection is goal/mission driven rather than legacy defensive-only MISSION;
- OPEN: DecisionCompass #113 — TRAINING/HARE Context Override typing;
- OPEN: DecisionCompass #114 — Type ZERO normative gating responsibility;
- OPEN: DecisionCompass #115 — Norn/Skuld task-manager naming collision.

These findings are tied to the pinned commit above and must be re-audited after implementation changes.

## Validation

### NRMO repository validation

The NRMO repository can validate its own specification/provenance structure without pretending that ignored runtime files are present.

Use:

```bash
python NRMOIntegrated/validate_nrmo_integrated_v72.py --check-provenance
```

This is **not** a runtime FULL PASS.

### Runtime validation against DecisionCompass

To run the delegated runtime validation, first check out the exact DecisionCompass commit being audited, then point the NRMO validator at the repository root:

```bash
git clone https://github.com/zarame96/DecisionCompass.git
cd DecisionCompass
git checkout ae00f9fd23760a6b4dd078723a1eed74ef7bffc9
cd ../NRMO
python NRMOIntegrated/validate_nrmo_integrated_v72.py \
  --runtime-root ../DecisionCompass \
  --expected-runtime-sha ae00f9fd23760a6b4dd078723a1eed74ef7bffc9
```

The validator must refuse to label a different SHA as the pinned Phase E snapshot unless the caller explicitly supplies that different expected SHA and records a new conformance snapshot.

## Build

The monograph build root remains:

```bash
cd NRMOIntegrated
pdflatex -shell-escape -interaction=nonstopmode NRMO_Complete_v5_5.tex
bibtex NRMO_Complete_v5_5
makeindex NRMO_Complete_v5_5.idx
pdflatex -shell-escape -interaction=nonstopmode NRMO_Complete_v5_5.tex
pdflatex -shell-escape -interaction=nonstopmode NRMO_Complete_v5_5.tex
```

Build success does not constitute runtime conformance proof.

## Historical implementation claims

Historical descriptions of Omega Full, Shinobi, MAPLayer, Loom, Norn/Skuld, C++/frontend adapters, domain harnesses, and older validation counts are preserved elsewhere for lineage. They must not be read as a current local-file inventory unless verified against the stated repository/ref.

For current implementation claims, follow `IMPLEMENTATION_SOURCE_OF_TRUTH.md`. For current normative semantics, follow `NORMATIVE_CANON.md`.
