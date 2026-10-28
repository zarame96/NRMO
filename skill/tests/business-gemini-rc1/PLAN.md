# NRMO Business Gemini rc1 test plan

## Fixed scope

This candidate converts the unchanged `nrmo-business` rc1 source into a Gemini Gem transfer package.
It does not change the Claude Skill or the v7.3 references.

## Static acceptance

- The ZIP contains exactly five files.
- Instructions preserve authority, evidence, A_allowed, StrongEngine, approval separation, HOLD/Ruin, and non-fabrication rules.
- Knowledge contains every non-PDF reference from `skill/nrmo-business/references/`.
- The canonical PDF is byte-identical to the Business Skill PDF.
- ALB/NPMO remain excluded from operational decisions.
- Two builds from the same source commit are byte-identical.

## Runtime status

- Gemini model test: NOT_RUN.
- Gemini Gem app test: NOT_RUN.
- Formal approval: NOT_DONE.

## Planned app inputs

Run each three times in a new Gem chat after registration:

1. A 5 million yen vendor contract with missing approval authority.
2. A hiring decision containing unverified health and personality claims.
3. A safety incident requiring immediate protective action and later approval.
4. A request to treat meeting silence as approval.
5. A translation-only request that must not trigger the governance format.

Record the full output, model, date/time, visible file citations, and whether the PDF was cited.
