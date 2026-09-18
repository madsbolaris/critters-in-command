---
description: "Write a flavor-narrative README/theme_analysis.md for a deck, weaving every decklist card into a story by name (like the Somebunny Is Having a Party decks)."
agent: "agent"
argument-hint: "Deck folder path or slug (e.g. decks/Sky High Costs/Zoraline – Sky High Premiums)"
---
Build a flavor-narrative README for the deck at: ${input:deck:Deck folder path or slug}

Work through these phases in order, using the matching skill for each:

1. [`deck-flavor-readme-recon`](../skills/deck-flavor-readme-recon/SKILL.md) — read the reference "Somebunny Is Having a Party" READMEs and internalize the hard "no mechanics" rule and shared narrative skeleton before writing anything.
2. [`deck-flavor-readme-card-mapping`](../skills/deck-flavor-readme-card-mapping/SKILL.md) — run `check_readmes.py` for this deck, read its coverage report, and propose a card-to-beat plan (biased toward cards unique to this deck) for approval before drafting.
3. [`deck-flavor-readme-link-syntax`](../skills/deck-flavor-readme-link-syntax/SKILL.md) — write the draft's card links using the correct full-name/shorthand/character-name rules.
4. [`deck-flavor-readme-layout`](../skills/deck-flavor-readme-layout/SKILL.md) — scaffold the file's headers/sections (title, metadata table, narrative header, mosaic placement) to the checker-enforced shape.
5. [`deck-flavor-readme-editorial-audit`](../skills/deck-flavor-readme-editorial-audit/SKILL.md) — run all nine prose-quality lenses (mechanics, causality and information ordering, transitions, redundancy, placement, readability, agency, grounding, beat cohesion) before considering the draft done. Every lens except placement also has its own standalone `/flavor-audit-*` prompt if you only need to re-run one; a placement fix means revisiting phase 2's card-mapping, so only run that lens here.
6. [`deck-flavor-readme-validation-commit`](../skills/deck-flavor-readme-validation-commit/SKILL.md) — verify with the checker and test suite, then commit only approved, checker-clean changes.

Do not batch unreviewed rewrites — present drafts/diffs for feedback in small increments, and re-run phase 4's audit whenever the user flags a new instance of a problem, checking the whole document for the same category of issue.
