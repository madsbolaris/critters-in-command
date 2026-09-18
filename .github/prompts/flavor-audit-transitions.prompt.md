---
description: "Audit a flavor-narrative deck README's tonal turns for a missing/misplaced transition — a pivot (usually positive → negative) with no explicit contrast marker, or landing at the wrong point in the escalation."
agent: "agent"
argument-hint: "(optional) deck folder path/slug, or the specific sentence that prompted this — omit to audit the README currently open/under discussion"
---
Run the **transitions** lens (`deck-flavor-readme-editorial-audit` skill, §3) on the ENTIRE narrative of the relevant deck README${input:target: (deck: )} — not just one sentence.

This is a standalone check: run it directly, with no other phase/prompt required first.

Find every major tonal turn in the story and verify it has an explicit contrast word or clause (but/although/until/soon) rather than an abrupt unmarked jump, and that it's placed where the story's escalation actually calls for a turn — not earlier or later just because a card needed a home. Scan the whole document; don't stop at one turn.

Propose the fixed prose directly (not a menu of options) for review.

Then validate and follow commit discipline per `deck-flavor-readme-validation-commit`:
```
python3 scripts/check_readmes.py <deck-slug>
python3 -m pytest tests/ -q
```
