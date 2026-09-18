---
description: "Audit a flavor-narrative deck README for causality and information stated out of order — cause→effect chains written backwards, a reveal presupposed too early, restating already-known info instead of advancing, or dangling connectives ('then', 'still') with no established antecedent."
agent: "agent"
argument-hint: "(optional) deck folder path/slug, or the specific sentence that prompted this — omit to audit the README currently open/under discussion"
---
Run the **causality and information ordering** lens (`deck-flavor-readme-editorial-audit` skill, §2) on the ENTIRE narrative of the relevant deck README${input:target: (deck: )} — not just one sentence.

This is a standalone check: run it directly, with no other phase/prompt required first.

Track precisely what the reader knows at every point in the document. Check all four symptoms across the whole document, not just the sentence that prompted this:
- Cause stated after effect — cards describing an escalating chain (e.g. "every X triggers a Y") must appear in true cause → effect order, not reversed.
- Presupposition before the reveal/pivot has earned it (a noun phrase presupposing loss, hidden knowledge stated outright, a payoff word with no antecedent yet).
- Restating information the reader already has instead of advancing with something new — this can happen anywhere in the document, not only at the very end.
- Dangling connectives ("then", "still", "already") that presuppose a prior state/action never actually established in the text.

Foreshadowing (planting a detail the reader can only reinterpret in hindsight, without naming/confirming it) is fine and distinct from these — don't flag it.

Propose the fixed prose directly (not a menu of options) for review.

Then validate and follow commit discipline per `deck-flavor-readme-validation-commit`:
```
python3 scripts/check_readmes.py <deck-slug>
python3 -m pytest tests/ -q
```
