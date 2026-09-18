---
description: "Audit a flavor-narrative deck README for plain-English readability — part-of-speech mismatches (a card name used as the wrong word class) and inanimate subjects doing person-things."
agent: "agent"
argument-hint: "(optional) deck folder path/slug, or the specific sentence that prompted this — omit to audit the README currently open/under discussion"
---
Run the **plain-English readability** lens (`deck-flavor-readme-editorial-audit` skill, §6) on the ENTIRE narrative of the relevant deck README${input:target: (deck: )} — not just one sentence.

This is a standalone check: run it directly, with no other phase/prompt required first.

Read every sentence aloud (mentally) and check for: a card whose name is one part of speech (e.g. a verb) being used as if it were another (e.g. a noun/gerund); an inanimate subject doing a person-thing, where it's unclear who/what is actually the subject. Scan the whole document; don't stop at the first instance.

Propose the fixed prose directly (not a menu of options) for review.

Then validate and follow commit discipline per `deck-flavor-readme-validation-commit`:
```
python3 scripts/check_readmes.py <deck-slug>
python3 -m pytest tests/ -q
```
