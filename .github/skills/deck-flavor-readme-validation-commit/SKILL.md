---
name: deck-flavor-readme-validation-commit
description: 'Phase 5 of building a flavor-narrative deck README: validation and commit discipline. Run check_readmes.py and the test suite, compare against the pre-existing baseline error count, and get user approval per change before committing. Use after drafting or editing any flavor-narrative README, or before committing changes to scripts/check_readmes.py.'
---

# Phase 5: Validation and Commit Discipline

## Validate

Always finish a round of edits with both:
```
python3 scripts/check_readmes.py            # full repo
python3 -m pytest tests/ -q                  # must stay green
```

The target deck's own check must report `OK` (zero errors). For the
full-repo run, compare the error count against the known pre-existing
baseline — other decks may already have unrelated, known errors; don't treat
those as regressions you introduced. Only new errors relative to baseline
are your responsibility to fix.

## Commit discipline

- Get explicit user approval for a change before committing it. Don't batch
  several unreviewed rewrites into a single commit — this repo's narrative
  work was iterated turn by turn, with the user reviewing each diff before
  it landed.
- Commit only once the checker is clean and tests pass for that change.
- If you changed `scripts/check_readmes.py` itself (e.g. to relax a link
  rule or add a new check), make sure its own unit tests
  (`tests/test_check_readmes.py`) are updated and passing alongside the
  README change that motivated it.
- Adding a new hard-error rule to the checker (e.g. a layout or link-shape
  requirement) will often make previously-clean decks newly fail — that's
  expected, not a regression to silently patch. Report the before/after
  count honestly and let the user decide whether/when the other decks get
  migrated; don't rewrite decks nobody asked you to touch.

## Quick reference: full pipeline

1. `deck-flavor-readme-recon` — learn the rule and skeleton.
2. `deck-flavor-readme-card-mapping` — plan cards-to-beats from the checker
   report, get the plan approved.
3. `deck-flavor-readme-link-syntax` — write structurally correct links.
4. `deck-flavor-readme-editorial-audit` — pass the prose-quality checklist.
5. `deck-flavor-readme-validation-commit` — this phase: verify and commit.
