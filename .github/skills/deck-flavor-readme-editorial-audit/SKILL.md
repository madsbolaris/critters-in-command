---
name: deck-flavor-readme-editorial-audit
description: 'Phase 4 of building a flavor-narrative deck README: nine independent prose-quality lenses (mechanics, causality and information ordering, transitions, redundancy, placement, readability, agency, grounding, beat cohesion). Each lens audits the ENTIRE narrative, not one sentence. Use when revising an existing flavor narrative, when the user flags any kind of awkward/backwards/clunky/out-of-order/off-tone phrasing, or before finalizing any draft.'
---

# Phase 4: Editorial Audit

Nine independent lenses. Each one is a general, recurring failure mode — not
a one-off fix for the specific sentence that first exposed it. When the user
flags a single instance of a problem, identify which lens it belongs to and
re-run *that whole lens* across the *entire* document, not just the flagged
sentence — the same category of mistake is rarely isolated to one spot. All
lenses except placement (#5) are also usable completely standalone (e.g. via
their own prompt): they don't require any other phase to have run first, and
need no additional input beyond the README text itself — extra context (a
specific line, a deck slug) only narrows focus, it's never required.

### Working a single flagged sentence to convergence

A single awkward sentence can take many rounds of user feedback to fix.
Handle that loop deliberately instead of guessing forever:

- **Two failed micro-edits (swapping a word/preposition) on the same spot
  is the signal to stop patching and rewrite the clause/sentence from
  scratch with a different shape.** Vague negative feedback like "still
  awful", "sounds clunky", or "still reads weird" after you've already
  tried a word-level fix means the problem is structural (who's the
  subject, what order are the clauses in), not lexical — another synonym
  swap won't fix it.
- If the user names a specific narrative **beat** they want kept (e.g. "the
  invitation", "the turn from good to bad"), treat the *beat* as the
  invariant, not its exact wording or which clause/sentence hosts it. It can
  relocate across rewrites as long as the underlying idea survives.
- If the user states explicit causality ("X answering causes Y", "X because
  of Y"), the clause order in the rewritten sentence must mirror that
  causality (cause-clause before effect-clause) — don't just coordinate
  both ideas with "and" and assume order is irrelevant.
- If the user hands you an exact rewrite ("try: ..."), apply it close to
  verbatim first — fix only what's needed for validity (links, casing,
  punctuation). Don't creatively embellish on top of a literal dictation.

## 1. Mechanic audit

Re-read every sentence and ask: **does this sentence's logic depend on
knowing what the card does in a game of Magic?** If yes, it's a violation,
regardless of how natural the prose reads. Rewrite from the name/title/
flavor only. This applies to fixes too, not just first drafts — a fix that
"reads fine" can still smuggle in a mechanic through an invented, undefined
detail (e.g. patching an awkward line by inventing "the same lesson every
morning" to gesture at a mill mechanic without ever naming it — still a
violation, because the *reasoning* depends on the mechanic). When you're not
confident a fix is clean, don't guess once and move on — propose ~10-12
concrete alternative phrasings and let the user pick.

## 2. Causality and information ordering

The crux: track precisely what the reader knows at every point in the
document, and never let a sentence's meaning depend on knowledge the reader
doesn't have yet *or* waste a moment restating knowledge they already do.
This one lens covers four symptoms of the same underlying problem:

- **Cause stated after effect.** Cards describing an escalating chain (e.g.
  "every X triggers a Y") must appear in the sentence in true cause →
  effect order, not reversed — this is a special case of presupposition:
  the effect is stated before the reader has any reason to expect it.
- **Presupposition before it's earned.** Once a draft has a reveal/pivot,
  check every sentence *before* it individually — don't skim for vibe. Red
  flags: a noun phrase presupposing loss/absence ("the remaining guests")
  before anyone's shown as missing; a character's hidden knowledge or
  betrayal stated outright ("never suspecting that X") before the reader has
  any reason to suspect something's wrong; a payoff word with no antecedent
  yet ("ready" — ready for what?). If a word/phrase only makes sense in
  light of information revealed later, it's misplaced. After the pivot,
  dramatic irony is fine — payoff words should land there, not earlier.
- **Restating instead of advancing.** This isn't just a closing-line
  problem — it can happen at any point in the document. If a sentence (a
  closer or otherwise) just restates information the reader already has,
  that's a wasted beat. Find something genuinely new to land on instead
  (e.g. paying off *who* instead of re-stating an already-revealed *why*).
- **Dangling connectives.** Words like "then", "still", "already", "only
  now" presuppose a prior state or action. If that antecedent was never
  actually established in the text, the sentence isn't self-contained —
  rewrite it to stand on its own instead of gesturing at context that isn't
  there.
- Foreshadowing is distinct from all of the above and is allowed: it plants
  an image/detail the reader can only reinterpret in hindsight, without
  naming or confirming the thing itself. If in doubt, ask: "could a
  first-time reader misread this sentence as pure hospitality/normalcy?" If
  no, move it later.
- When the user flags one instance, re-run this check on the whole
  document — it's rarely isolated to one sentence.

## 3. Transitions

Any major tonal turn (most commonly positive → negative) needs an explicit
contrast word or clause (but/although/until/soon) — never an abrupt unmarked
jump. Also verify the turn is placed where the story's escalation actually
calls for it, not earlier or later just because a card needs a home.

## 4. Redundant beats

If multiple cards make the same narrative point, trim to the strongest one
instead of stacking near-duplicates back to back. This also applies at the
phrase level: cut filler flourishes/qualifiers that only restate or
intensify a point already made (e.g. "burrow to burrow", "delight too warm
to be an act") rather than adding new information — if the plain word
already conveys the idea, the extra phrase is a redundant beat in miniature.
This also covers a repeated *joke/premise* told via two different cards in
nearby sentences (e.g. two separate clauses both landing "nobody remembers
who was invited") — even with completely different wording, it's the same
punchline twice. Keep it in the strongest single spot and let the other
sentence do different narrative work.

## 5. Placement matches the card's own theme

A card literally named after a specific thing (e.g. visiting a sphinx)
belongs in the sentence about that specific thing, not repurposed elsewhere
just because a slot is open.

**Not standalone.** Unlike the other lenses, this one is NOT exposed as its
own prompt. Relocating a misplaced card usually displaces whatever card
was already in its rightful sentence, which means re-deciding beat
assignments — that's card-mapping (Phase 2) work, not an isolated prose
edit, and an isolated audit prompt has no visibility into the rest of the
plan. Only run this lens as part of the full build (`deck-flavor-readme`
prompt) or a deliberate revisit of card-mapping, never in isolation.

## 6. Plain-English readability

- Watch for part-of-speech mismatches — e.g. a card whose name is a verb
  ("Tempt") shouldn't be used as if it were a noun/gerund. Read the sentence
  aloud.
- Watch for inanimate subjects doing person-things ("the days themselves
  fall under Tutelage") — reread for who/what is actually the subject.
- A gerund-phrase card name (e.g. "Stocking the Pantry") cannot itself be
  the grammatical subject performing another verb ("Stocking the Pantry
  keeps the larder full" is a category error — the phrase describes an
  action, not an actor). Give it a real agent as the subject ("the staff
  are always Stocking the Pantry...") or make the card name the object of a
  preposition — never let it double as an unnamed doer.
- The same failure applies to any card name that reads as an abstract
  description rather than a concrete noun (e.g. "Finale of Devastation" —
  literally "a final act of devastation"). Sentences like "the Finale of
  Devastation sends out one final invitation" or "...reaches out for one
  final guest" read as broken English, because an abstract description
  can't perform a verb. Give a real actor (a character, another card) the
  action, and use the abstract-phrase name as a descriptive/prepositional
  tag instead ("...and in a Finale of Devastation, nothing survives").
- Default to active voice when fixing a sentence like this. Rewriting a
  passive construction ("the larder is kept full by Stocking the Pantry")
  removes the grammar error but trades it for passive voice, which is its
  own readability defect — check the fix isn't just relocating the problem.
- Match the described scope precisely to what's intended (e.g. "every
  guest" vs. a narrower, uninstructed subset like "every latecomer") —
  don't silently narrow or widen who/what a sentence covers.
- Watch for a word echo: the same root word appearing twice in one
  sentence or its immediate neighbor for no reason other than that a card
  name contains it (e.g. "Warren Warleader marshals the warren" repeats
  "warren"). This is distinct from lens #4 (redundant *beats*) — this is a
  literal word-level repetition, fixed by swapping the second occurrence
  for a synonym (e.g. "marshals the burrow").
- The same word-echo check also catches a verb applied twice to two
  different subjects in one sentence (e.g. "Farmer Cotton rolls in ... and
  a Springleaf Parade rolls in right behind them") — even though nothing
  is grammatically wrong, it reads like a copy-paste artifact. Vary the
  second verb ("follows right behind them").
- A connector/transition word must match the real logical relationship,
  not just sound literary. "Until" implies a stopping point/limit and is
  wrong when the described action keeps going past it; "where" suits a
  spatial handoff into a reaction; "so"/causal phrasing suits a direct
  consequence. If the user rejects a connector without saying why, ask
  which relationship (spatial/causal/temporal-limit) it should express
  rather than guessing another synonym.

## 7. Agency and causality attribution

For every notable action, check who's actually framed as the cause versus
the target/experiencer. A character or card can get mis-cast as the
architect/mastermind of something they should merely be caught up in (or
the reverse — an actual instigator framed as an innocent bystander). This is
a distinct check from causality-and-information-ordering (#2, which is
about sentence-level cause→effect sequencing and reveal timing) — this one
is about *who* holds the causal role at the story level, across the whole
cast.

## 8. Grounding

Every descriptive phrase, idiom, or transition must be grounded in either
real, natural English usage or a detail already established elsewhere in
*this* story. Two symptoms of the same problem:
- **Invented idioms.** Don't paper over an awkward line by inventing a
  phrase that isn't real, attested English ("elbows and all"). If it
  doesn't sound like something a person would actually say, cut it rather
  than dress it up.
- **Generic vague filler.** Don't reach for a placeholder-quality phrase
  ("but by the time anyone notices") when a concrete detail already
  established in the story could anchor the sentence instead ("but by the
  time Byrke solves the case").

## 9. Beat cohesion

Each paragraph should serve exactly one narrative purpose/tone. If a
paragraph is actually doing two different jobs or blending incompatible
tones (e.g. innocent-seeming hospitality beats mixed with sinister
containment beats), split it into two paragraphs, each anchored by its own
cards, rather than blending them into one undifferentiated block.

## Next phase

Once the draft passes the relevant lens(es), move to validation and commit
discipline: see the `deck-flavor-readme-validation-commit` skill.
