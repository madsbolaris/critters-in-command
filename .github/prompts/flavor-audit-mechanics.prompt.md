---
description: "Audit a flavor-narrative deck README for game-mechanic leakage — prose or reasoning that depends on what a card does rather than its name/title/flavor."
agent: "agent"
argument-hint: "(optional) deck folder path/slug, or the specific sentence that prompted this — omit to audit the README currently open/under discussion"
---
Run the **mechanic audit** lens (`deck-flavor-readme-editorial-audit` skill, §1) on the ENTIRE narrative of the relevant deck README${input:target: (deck: )} — not just one sentence.

This is a standalone check: run it directly, with no other phase/prompt required first.

For every sentence, ask: does its logic depend on knowing what the card does in a game of Magic? Include your own reasoning/justifications in this audit too, not just the shipped prose — a fix that "reads fine" can still smuggle in a mechanic through an invented, undefined detail. Scan the whole document; this rarely stops at one sentence.

Propose the fixed prose directly (not a menu of options) for review. If you're not confident a given fix is clean, propose ~10-12 concrete alternative phrasings instead of guessing once.

Then validate and follow commit discipline per `deck-flavor-readme-validation-commit`:
```
python3 scripts/check_readmes.py <deck-slug>
python3 -m pytest tests/ -q
```
