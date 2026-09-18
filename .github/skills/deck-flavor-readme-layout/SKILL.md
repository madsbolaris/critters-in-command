---
name: deck-flavor-readme-layout
description: 'The shared structural layout for a flavor-narrative deck README, enforced as hard errors by check_readmes.py: a plain "# <Commander>" title, a metadata table, a "## <Deck Name>" narrative header, and a "## The Deck" mosaic section before "## Deck Resources". Use when restructuring an existing README''s layout/headers, when check_readmes.py reports a layout error, or when starting a new README''s scaffold before writing prose.'
---

# README Structural Layout

This is a distinct concern from the narrative *content* skeleton (see
`deck-flavor-readme-recon`) — it's about the file's headers and sections,
not the story. It's fully mechanical and checker-enforced
(`check_readme_layout` in `scripts/check_readmes.py`), so get it right by
running the checker, not by eyeballing it against a reference file.

## The required shape, in order

1. `# <Commander>` — the commander's plain card name only. No flavor
   subtitle, no em dash. (Wrong: `# Finneas, Ace Archer — Somebunny's On the
   Menu`. Right: `# Finneas, Ace Archer`.)
2. A metadata table immediately after, with exactly these rows in this
   order — **Commander**, **Colors**, **Archetype**, **Good against**,
   **Struggles against**:
   ```
   | | |
   |---|---|
   | **Commander** | [Name](scryfall link) |
   | **Colors** | <Guild/wedge name> (Color / Color) |
   | **Archetype** | <short phrase> |
   | **Good against** | <short phrase> |
   | **Struggles against** | <short phrase> |
   ```
3. `## <Deck Name>` — the narrative section header. **This must be exactly
   the deck's own flavor name**, i.e. the part of the deck's folder name
   after the " – " separator (e.g. "Somebunny Said I Do" for the folder
   "Ms. Bumbleflower – Somebunny Said I Do"). Do not invent a different pun
   or title for this header — this was gotten wrong twice in one session
   before the rule was made explicit. `scripts/check_readmes.py`'s
   `deck_flavor_name()` derives the required value from the folder name;
   when in doubt, check what it computes rather than guessing.
4. The narrative prose.
5. `## The Deck` followed by the mosaic preview image
   (`![Deck mosaic](deck_mosaic_preview.jpg)`). This image must appear here
   and nowhere else in the file (no dangling copy at the end after
   `## Deck Resources`).
6. `## Deck Resources` — must come after `## The Deck`, with the existing
   bullet list of decklist/analysis links.

## Verify

```
python3 scripts/check_readmes.py <deck-slug>
```
Layout errors are hard errors, named specifically (missing/misordered table
rows, title mismatch, narrative header mismatch, missing/misplaced mosaic
image, wrong section ordering) — fix exactly what's named rather than
re-deriving the shape from scratch each time.

## Scope note

Not every deck in the repo has been migrated to this layout yet. Only
restructure a deck the user actually asked about — a repo-wide sweep to make
every deck pass this check is a separate, larger task, not an implicit side
effect of fixing one deck.
