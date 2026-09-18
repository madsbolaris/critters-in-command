---
name: deck-flavor-readme-link-syntax
description: 'Phase 3 of building a flavor-narrative deck README: deterministic Markdown link and shorthand rules enforced by check_readmes.py (full-name links, trailing-word shorthand, character-name shorthand, pronoun placement). Use when writing or fixing card links in a deck README, or when check_readmes.py reports invalid-link or not-in-decklist errors.'
---

# Phase 3: Card Link Syntax

These are mechanical, checker-enforced rules — get them right before doing
the editorial pass.

## Full name links

`[Card Name](https://scryfall.com/card/set/number)` — the default form.

## Trailing-word shorthand

For `/card/` links, the link text may be just the trailing word(s) of the
real card name, as long as the surrounding sentence reads naturally in
English. Example: link text "Tutelage" for the card *Teferi's Tutelage*.

Apply the exact phrasing the user asks for — if they give a specific
before/after example of how they want a link shortened, match it literally
rather than approximating your own shorter form.

## Character-name shorthand

For a Legendary Creature named "X, Description", link text may be shortened
to just "X" anywhere in the prose (not only after a first full mention), as
long as it's unambiguous. If two different decklist cards share the same
leading character name, that is a hard error — both need disambiguating
text, not a bare shorthand.

## Never use `/search` links

`scryfall.com/search?q=...` links are a hard error, full stop — no shorthand
exception, no exploratory-namedrop exception. They don't pin down a specific
printing, so the art shown can silently mismatch the printing the story
means. Always link the card's own page: `/card/<set>/<number>`.

## Pronouns and articles go outside the link

Words like "his", "her", "the" that are not literally part of the card name
belong **outside** the link brackets:
```
under his [Tutelage]      ← correct
under [his Tutelage]      ← wrong, "his" isn't part of the card name
```

## Never treat a missing card as acceptable

Every card named in the README must be a real, current member of that deck's
`decklist.dck`. There is no "flavor-only namedrop" exception — the checker
treats this as a hard error, and it should stay that way.

## Verify

After any link change, re-run:
```
python3 scripts/check_readmes.py <deck-slug>
```
It must report `OK` (zero errors) before moving on.

## Next phase

Once links are structurally correct, do the prose-quality pass: see the
`deck-flavor-readme-editorial-audit` skill.
