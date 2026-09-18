---
description: "Audit a flavor-narrative deck README for redundant beats — multiple cards making the same narrative point back to back instead of trimming to the strongest one."
agent: "agent"
argument-hint: "(optional) deck folder path/slug, or the specific sentence that prompted this — omit to audit the README currently open/under discussion"
---
Run the **redundant beats** lens (`deck-flavor-readme-editorial-audit` skill, §4) on the ENTIRE narrative of the relevant deck README${input:target: (deck: )} — not just one sentence.

This is a standalone check: run it directly, with no other phase/prompt required first.

Find every place where multiple cards make the same narrative point and trim to the strongest one instead of stacking near-duplicates. Scan the whole document; don't stop at the first instance.

Propose the fixed prose directly (not a menu of options) for review.

Then validate and follow commit discipline per `deck-flavor-readme-validation-commit`:
```
python3 scripts/check_readmes.py <deck-slug>
python3 -m pytest tests/ -q
```
