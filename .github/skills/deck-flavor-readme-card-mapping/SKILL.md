---
name: deck-flavor-readme-card-mapping
description: 'Phase 2 of building a flavor-narrative deck README. Use the check_readmes.py coverage report to plan which decklist cards go in which narrative beat, biasing toward cards unique to the deck, and propose the plan for user review before writing any prose. Use when asked to "strategize" card placement, decide which README errors to fix first, or map decklist cards to a story before drafting.'
---

# Phase 2: Card-to-Narrative Planning

Analysis phase that feeds directly into a full draft (Phase 3/4). The output
of this phase is a completed rewrite for the user to react to — not a menu
of questions. Make the structural calls yourself; the user reviews the
result, the same way line-edits get reviewed after drafting. Only stop to
ask first when the answer depends on information you cannot infer (e.g. the
user's actual preference between two equally valid *deck-identity* changes,
not a matter of narrative craft).

## Get the current state

Run the checker to get a baseline before proposing anything:
```
python3 scripts/check_readmes.py <deck-slug>
```
This writes a gitignored `readme_check_report.md` in the deck folder,
containing:
- **Errors**: invalid Scryfall links, cards named that aren't in
  `decklist.dck` (never acceptable as an "intentional flavor-only namedrop"
  — that excuse was rejected once and should never be used again; every
  named card must be a real, current decklist member).
- **Cards not mentioned in the README**, grouped by type (creature, sorcery,
  instant, artifact, enchantment, land), sorted by a "uniqueness" count — how
  many *other* decks in the repo also contain that card, fewest first.

## Plan, don't draft

When asked to strategize:
1. Pick the deck with the fewest existing errors first if choosing among
   several decks to fix.
2. Classify every error before proposing anything — the fix is completely
   different depending on the class (see below).
3. For every card the user explicitly asked to weave in, propose a specific
   narrative beat/paragraph for each one, using only the card's name/title/
   flavor — never mention what it does mechanically, even in this planning
   text (see the hard "no mechanics" rule from the recon phase).
4. Bias card selection for "filling out" the story toward unique cards
   (low other-deck count) over generic staples. **Don't rely on memory or
   "this feels niche" instinct — verify with real numbers before writing
   any candidate into prose:**
   ```
   python3 -c "
   import sys; sys.path.insert(0, 'scripts'); import check_readmes as cr
   counts = cr.build_global_card_counts(cr.discover_decks())
   print(counts.get(cr.normalize_name('Card Name'), 0) - 1)
   "
   ```
   This applies to every new card you add — including ones filling a hole
   left by a Class B removal and any "for color/completeness" additions
   that aren't fixing a flagged problem at all (don't add those unless
   they're actually deck-unique; a clean `check_readmes.py` run proves
   nothing about uniqueness, it only proves the absence of hard errors).
5. Make the call on every structural question yourself (trim vs. merge vs.
   rebuild, which new card anchors a rebuilt beat) and go straight into
   drafting the full rewrite — do not stop and present a list of options
   for the user to pick from. Producing the finished draft **is** the plan
   presentation; the user reviews and corrects the result, they don't
   pre-approve your reasoning first.

## Two very different error classes — do not conflate them

**Class A — mis-linked but still a real decklist card** (wrong printing,
"The" vs no "The", a nickname used as link text instead of the real name).
This is a pure correction: the card is still there, just point the link at
it correctly or move a nickname outside the brackets. No narrative impact.

**A printing collision needs a diagnosis step before any fix.** When the
checker reports `Printing collision: [X] points to set/number, but the
decklist has 'Y' at that exact printing`, do not assume which side is wrong.
There are two distinct causes:
1. X is a mistaken/invented name and Y is correct — rewrite the whole beat
   around Y's real identity (name, art, printed flavor text), the same
   effort as a Class B replacement. Do not just swap the label into the
   old sentence and leave everything else built around the wrong image.
2. **X is the card's own, officially printed alternate name** — check
   `https://api.scryfall.com/cards/<set>/<number>`'s `flavor_name` field
   before concluding anything. Secret Lair and Universes Beyond crossover
   treatments frequently print a different name on the card itself (see
   `FLAVOR_NAMES` in `scripts/check_readmes.py`). If `flavor_name` matches
   X, the prose was already correct — add the `(set, number)` printing to
   `FLAVOR_NAMES` instead of touching a single word of the README.
Always check the Scryfall API before editing anything — guessing wrong
here means "fixing" prose that was never broken. (This happened twice in
one session with `The Party Tree` / `ltc/348`: it turned out to be case 2 —
`The Party Tree` is The Great Henge's actual printed flavor name on that
Lord of the Rings Commander printing — but it was first mis-diagnosed as
case 1 and the correct prose was rewritten unnecessarily.)

**Class B — the named card is no longer in the decklist at all** (the
decklist changed since the README was written). **This is never a
find-a-synonym exercise.** Do NOT hunt for a new card that can be dropped
into the same grammatical slot with the same sentence shape — that produces
a Frankenstein narrative optimized for "the checker passes" instead of "the
story makes sense." A red flag you're doing this wrong: proposing
replacement-card tables shaped like `broken card → new card, same clause`.

Instead, for every Class B card, analyze it at the **beat** level:
1. **What was the beat, not just the sentence?** What role did this
   paragraph/moment play in the overall arc (e.g. "first hint something's
   wrong", "the trap closes", "the dark centerpiece image")?
2. **Does the beat still function without this card?** If the surrounding
   cards in that paragraph already carry the idea, the fix may be to simply
   trim the clause — not replace it with anything.
3. **Is the beat now hollow or broken?** If a card was carrying the *only*
   support for a beat (e.g. the sole "central image" of a paragraph), that
   beat needs to be rebuilt or merged into an adjacent one — propose a
   structural change (cut, merge, shorten, or rebuild with a new card that
   changes what the paragraph is actually about), not a word swap.
4. **Separately, what NEW beats do the newly-available unique cards
   suggest?** Read the uncovered-card list on its own merits — some of these
   cards may not belong in place of anything lost; they might support an
   entirely new moment the story doesn't currently have. Don't force them
   into an existing hole just because a hole exists.
5. **Check the adjacent paragraphs' jobs before proposing a card for a
   beat that's missing an item.** Each paragraph should keep to the single
   purpose established in beat cohesion (editorial-audit lens #9) — don't
   recommend a card whose flavor actually belongs to the next or previous
   paragraph's role (e.g. a paragraph about the conspiracy's
   innocent-looking surface activity shouldn't get a card that reads as
   "handling objectors/removal" — that's the next paragraph's job). Reread
   what beat comes right before and after before drafting options.
6. Decide, per paragraph, whether to trim, merge, or rebuild — then write
   the rebuilt sentences immediately as part of the same pass. A one-line
   rationale per paragraph (in your response, not the README) is useful
   context for the reviewer, but it accompanies the finished draft; it does
   not substitute for one or replace it with a question.

## Next phase

Once the plan is approved, move to actually writing links and prose: see the
`deck-flavor-readme-link-syntax` skill for link mechanics and the
`deck-flavor-readme-editorial-audit` skill for prose-quality rules.
