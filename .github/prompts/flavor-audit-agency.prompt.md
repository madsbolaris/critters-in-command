---
description: "Audit a flavor-narrative deck README for misattributed agency — a character/card framed as the cause/architect of something they should merely be caught up in, or vice versa."
agent: "agent"
argument-hint: "(optional) deck folder path/slug, or the specific character/sentence that prompted this — omit to audit the README currently open/under discussion"
---
Run the **agency and causality attribution** lens (`deck-flavor-readme-editorial-audit` skill, §7) on the ENTIRE narrative of the relevant deck README${input:target: (deck: )} — not just one character.

This is a standalone check: run it directly, with no other phase/prompt required first.

For every notable action in the story, check who's actually framed as causing it versus who's merely experiencing/witnessing it. Flag any character or card mis-cast as the architect/mastermind of something they should just be caught up in — or, conversely, an actual instigator framed as an innocent bystander. Scan the whole cast across the whole document, not just one character.

Propose the fixed prose directly (not a menu of options) for review.

Then validate and follow commit discipline per `deck-flavor-readme-validation-commit`:
```
python3 scripts/check_readmes.py <deck-slug>
python3 -m pytest tests/ -q
```
