---
description: "Audit a flavor-narrative deck README for ungrounded language — invented idioms that aren't real English, or generic vague filler used instead of a concrete detail already established in the story."
agent: "agent"
argument-hint: "(optional) deck folder path/slug, or the specific phrase that prompted this — omit to audit the README currently open/under discussion"
---
Run the **grounding** lens (`deck-flavor-readme-editorial-audit` skill, §8) on the ENTIRE narrative of the relevant deck README${input:target: (deck: )} — not just one phrase.

This is a standalone check: run it directly, with no other phase/prompt required first.

Every descriptive phrase, idiom, or transition must be grounded in either real, natural English usage or a detail already established elsewhere in this story. Check the whole document for both symptoms:
- Invented idioms that aren't real, attested English (if it doesn't sound like something a person would actually say, cut it rather than dress it up).
- Generic vague filler used where a concrete detail already established in the story could anchor the sentence instead.

Propose the fixed prose directly (not a menu of options) for review.

Then validate and follow commit discipline per `deck-flavor-readme-validation-commit`:
```
python3 scripts/check_readmes.py <deck-slug>
python3 -m pytest tests/ -q
```
