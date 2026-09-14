# NRMO Publication / Baseline / Implementation Provenance

Status: Phase D consistency record under Issue #6  
Authority: subordinate to `NORMATIVE_CANON.md`

## Publication identity

- Publication family/version: **NRMO Integrated System v7.2**.
- Current integrated source revision: **v7.2 revision 2 (rev2)**, because Part XV (Universal Adapter Framework) is included in the current master build.
- The filename `NRMO_Complete_v5_5.tex` is a **legacy build-root/source-lineage filename** retained for continuity. It is not the publication version and must not be read as meaning the current volume is v5.5.

Revision 2 is a publication/source revision inside the v7.2 family; it is not, by itself, a new theory version.

## Baseline lineage

The monograph is cumulative. Different Parts retain different historical baselines:

- Parts I–VI preserve/reconstruct substantial v4/v5-era material.
- Parts VII–XII were added during later mathematical, simulation, engineering, empirical, and methodological reconstruction.
- Part XIII records the v5.0–v7.1 world-simulation development path.
- Part XIV is the v7.2 Loom v3.1 / Sociable Shadow culmination.
- Part XV is the v7.2 rev2 Universal Adapter Framework.

A baseline version identifies source lineage. It does **not** grant older terminology precedence over the current Normative Canon.

## Issue #6 consistency-repair overlay

In 2026-09, Issue #6 introduced a specification-consistency repair overlay across preserved material:

- Phase A repaired current normative authority/mode/type wording.
- Phase B labelled conflicting historical specifications as superseded/non-controlling while preserving lineage.
- Phase C separated current checked-in implementation evidence from historical/reference implementation snapshots and clarified canonical Norn vs overloaded implementation naming.
- Phase D performs the full mechanical consistency audit and publication/version provenance repair.

Therefore statements such as “Parts I–XIII carry forward unchanged” refer only to their **baseline lineage before the Issue #6 editorial/specification repair overlay**. They are not literal claims that no source text has changed since v7.1.

## Implementation provenance

Publication version, baseline version, and implementation version are separate dimensions.

- Normative architecture is controlled by `NORMATIVE_CANON.md`.
- Current implementation existence claims are controlled by the checked-in repository tree at the stated ref.
- Historical/reference code listings remain lineage evidence and are not live repository manifests.
- `v52_codebase`, `world_sim_*`, Loom versions, and other implementation/experiment labels do not redefine the monograph publication version.

See `IMPLEMENTATION_PROVENANCE_REGISTER.md` for the implementation-evidence rules.

## Reading rule

When two labels appear to disagree, identify which dimension each label belongs to:

1. publication version/revision;
2. Part/source baseline lineage;
3. normative Canon status;
4. implementation/experiment version;
5. archive/generated-artifact provenance.

Do not collapse these into a single version number.
