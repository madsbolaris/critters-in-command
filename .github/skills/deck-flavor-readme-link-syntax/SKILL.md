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

## Plural shorthand

For `/card/` links, the link text may be the regular English plural of the
real card name (`+s` or `+es`), for prose describing more than one
copy/instance of the same named thing, e.g. `[Delighted Halflings](.../ltr/158/delighted-halfling)`
for a wheelbarrow full of them. Only the regular plural is recognized —
irregular plurals still need the literal singular card name as link text.

## Character-name shorthand

For a Legendary Creature named "X, Description", link text may be shortened
to just "X" anywhere in the prose (not only after a first full mention), as
long as it's unambiguous. If two different decklist cards share the same
leading character name, that is a hard error — both need disambiguating
text, not a bare shorthand.

## Italicize non-borderless foil cards

If a card is bought as foil for the deck but its specific purchased printing
is **not borderless** (`border_color != "borderless"`), its README link text
must be *italicized*: `*[Card Name](...)*`.

This does not apply to the commander or the three `[mosaic_order]` featured
cards in `deckcheck.toml` — those are always borderless printings and are
bolded instead (never both bold and italic on the same link).

The authoritative source for "is this card foil" is deckcheck.co's own live
per-card data — fetched via `scripts/sync_deckcheck.py`'s `fetch_deck()` /
`board_entries()` helpers. Each entry has `entry["isFoil"]` (bool) and
`entry["finish"]` (`"foil"` / `"nonFoil"`), reflecting the card's real
current finish. There is no local override file for this (`party.toml` no
longer tracks foil status) — always check live.

`scripts/check_readmes.py` enforces this rule automatically now (both
directions: missing italics on a foil/non-borderless card, and stray
italics on a card that isn't currently foil, are both hard errors). **Just
run the checker** (`python scripts/check_readmes.py <deck-slug>`) instead of
writing a one-off scan script — it already does the live fetch + bulk-cache
lookup below. Use `--offline` to skip this one live-network check if
deckcheck.co isn't reachable.

Because this is live, real-world data (the user's actual purchased/owned
finish per card), it can and does change between runs as the user updates
their collection on deckcheck.co — a card italicized correctly last week can
legitimately need de-italicizing today, and vice versa. Never trust a
previous answer or a previously-generated report; always re-run the checker
fresh before reporting which cards currently qualify.

To find which cards qualify (what the checker does internally):
1. Fetch the deck live (`fetch_deck(source)`) and walk `board_entries()` for
   `commanders` and `mainboard`. Skip the commander and the three
   `[mosaic_order]` featured cards — always borderless, always bold, never
   italic.
2. For every other entry, check `entry["isFoil"]`. If it's not `True`,
   the card is not currently foil — do not italicize it.
3. For entries where `isFoil` is `True`, look up that entry's `card["setCode"]`
   + `card["collectorNumber"]` in the Scryfall bulk cache
   (`scripts/.cache/scryfall_default_cards.json`) for `border_color`. If it
   isn't `"borderless"`, italicize every README link to that card.

Example: Baylen's "Finale of Devastation" (`cmm/289`) currently reports
`finish: "nonFoil"` on deckcheck.co, so it is **not** italicized. Harvestrite
Host (`blb/15`) reports `finish: "foil"` and a black `border_color`, so it
**is** italicized: `*[Harvestrite Host](https://scryfall.com/card/blb/15/harvestrite-host)*`.

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
