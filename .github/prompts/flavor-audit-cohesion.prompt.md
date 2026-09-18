---
description: "Audit a flavor-narrative deck README for beat cohesion — a paragraph blending two different narrative purposes/tones that should be split into two, each with its own cards."
agent: "agent"
argument-hint: "(optional) deck folder path/slug, or the specific paragraph that prompted this — omit to audit the README currently open/under discussion"
---
Run the **beat cohesion** lens (`deck-flavor-readme-editorial-audit` skill, §9) on the ENTIRE narrative of the relevant deck README${input:target: (deck: )} — not just one paragraph.

This is a standalone check: run it directly, with no other phase/prompt required first.

Check every paragraph for whether it serves exactly one narrative purpose/tone. Flag any paragraph blending two different jobs or incompatible tones (e.g. innocent-seeming hospitality mixed with sinister containment), and split it into two paragraphs, each anchored by its own cards, rather than leaving them combined. Scan the whole document; don't stop at the first instance.

Propose the fixed prose directly (not a menu of options) for review.

Then validate and follow commit discipline per `deck-flavor-readme-validation-commit`:
```
python3 scripts/check_readmes.py <deck-slug>
python3 -m pytest tests/ -q
```
