# Somebunny vs the Meta — EDHREC Bracket‑4 Matchup Analysis

How the three party decks (Baylen, Ms. Bumbleflower, Finneas) fare against the
**top‑20 most‑popular commanders' EDHREC "optimized" (bracket‑4‑tier) average
decks**.

## Methodology

- **Opponents:** the current top‑20 commanders on EDHREC by deck count, each
  using its **optimized** average decklist (EDHREC's high‑power / bracket‑4 tier),
  pulled as actual lists from EDHREC's `_next/data` API on **2026‑07‑24**.
- **My decks:** the actual `decklist.dck` lists in this repo.
- **Baylen update (2026‑07‑25):** the Baylen list was revised (−Faith's Reward,
  −Rabbit Battery, −Beastmaster Ascension, −Caretaker's Talent, −Smothering Tithe;
  +Secure the Wastes, +Call the Coppercoats, +Springleaf Parade, +Awaken the Woods,
  +Farmer Cotton) and **re‑scored**. The Finneas/Bumbleflower columns are unchanged
  from 2026‑07‑24.
- **Scoring:** one analysis per opponent, rating each of my three decks' win
  likelihood on a **1–5** scale.
- **Caveats:** #8 **Ms. Bumbleflower** and #20 **Baylen** share a commander with
  my decks but are *different archetypes* in EDHREC's build — judged as distinct
  decks, **not mirrors**.

---

## 1v1

**Scale:** 1 = Not at all · 2 = Unfavored · 3 = Coin‑flip · 4 = Favored · 5 = Slam dunk.

| # | Opponent (optimized) | Archetype | Baylen | Bumbleflower | Finneas | Best |
|---|---|---|:--:|:--:|:--:|---|
| 1 | The Ur-Dragon | 5c dragon ramp/beatdown | 4 | 4 | 5 | Finneas |
| 2 | Edgar Markov | Mardu vampire aristo‑aggro | 3 | 4 | 4 | Finneas |
| 3 | Y'shtola, Night's Blessed | Esper pillow/lifedrain | 3 | 3 | 4 | Finneas |
| 4 | Atraxa, Praetors' Voice | 4c infect/proliferate | 3 | 3 | 4 | Finneas |
| 5 | Krenko, Mob Boss | Mono‑R goblin aggro‑combo | 3 | 4 | 3 | Bumbleflower |
| 6 | Kaalia of the Vast | Mardu cheat‑in fatties | 2 | 4 | 4 | Bumbleflower |
| 7 | Vivi Ornitier | Izzet storm/spellslinger | 2 | 4 | 3 | Bumbleflower |
| 8 | Ms. Bumbleflower* | Simic +1/+1 counters value | 3 | 4 | 5 | Finneas |
| 9 | Sauron, the Dark Lord | Grixis reanimator/amass | 3 | 3 | 4 | Finneas |
| 10 | Teval, the Balanced Scale | Sultai graveyard value | 4 | 3 | 5 | Finneas |
| 11 | Pantlaza, Sun-Favored | Naya dino ramp‑beatdown | 4 | 4 | 5 | Finneas |
| 12 | Fire Lord Azula | Grixis storm/burn | 2 | 4 | 4 | Finneas |
| 13 | Lathril, Blade of the Elves | Golgari elf go‑wide/drain | 4 | 4 | 5 | Finneas |
| 14 | Giada, Font of Hope | Mono‑W angels aggro | 2 | 4 | 5 | Finneas |
| 15 | The Wise Mothman | Sultai rad‑mill/proliferate | 4 | 3 | 5 | Finneas |
| 16 | Jodah, the Unifier | 5c legends value | 4 | 3 | 5 | Finneas |
| 17 | Yuriko, the Tiger's Shadow | Dimir ninja tempo/burn | 2 | 4 | 3 | Bumbleflower |
| 18 | Nekusar, the Mindrazer | Grixis wheels/draw‑burn | 4 | 4 | 5 | Finneas |
| 19 | Kenrith, the Returned King | 5c protected Thoracle combo | 2 | 3 | 2 | Bumbleflower |
| 20 | Baylen, the Haymaker* | Naya tokens + ping reach | 3 | 4 | 5 | Finneas |

\*Same commander as one of my decks, **different archetype** — not a mirror.

### 1v1 overall stack rank

| Rank | Deck | Avg (of 20) | Best‑deck count | Floor |
|---|---|:--:|:--:|---|
| **1** | **Finneas** | **4.25** | 13 sole | ~28 redundant combos beat spot disruption; only loses to a *faster* combo (Kenrith) |
| 2 | **Bumbleflower** | 3.65 | 4 sole | combo‑control; best vs fast tempo/combo (Krenko, Vivi, Yuriko, Kenrith) |
| 3 | Baylen | 3.05 | 0 sole | fair go‑wide; 2s vs fast combo / storm / angels |

### 1v1 synthesis

- **Finneas (best overall, by a clear margin):** ~28 redundant infinite combos on a
  ~12‑card core (see below) make it extremely consistent and **near‑impossible to
  disrupt with spot removal** — kill one piece, twenty other lines remain. Heliod +
  Spike Feeder infinite life invalidates every damage/drain/burn/aggro deck, and it
  kills turn 4‑6. Only real hole: a *faster* protected combo (Kenrith Thoracle) and
  hyper‑aggro/tempo that races it (Krenko, Vivi, Yuriko).
- **Bumbleflower (combo‑control, re‑rated):** not a durdle — it's a tutorable combo
  deck (≈6 redundant mill kills, Approach + Windfall/Mystical Tutor, Mind Over Matter
  engines) wrapped in counters. It preys on commander‑reliant tempo/aggro/storm (Krenko,
  Kaalia, Vivi, Yuriko) *and* now beats the slower decks it used to only stall — incl.
  **Nekusar (4), because the *mill* kills need no self‑draw**. It only dips vs graveyard
  decks it would have to mill (Sauron/Teval → 3, winning on Approach not mill) and the
  faster protected Kenrith combo (3).
- **Baylen (weakest 1v1):** a fair, slow go‑wide deck is on the wrong side of nearly
  every 1v1 axis — pillow fort/pings go over it, wipes reset it, faster combos kill
  first. Only "favored" vs slow, wipe‑light creature decks.

### 1v1 takeaways

1. For a gauntlet vs this field, register **Finneas** — most universally resilient.
2. **Bumbleflower** is a genuine second deck, not just a counter‑pick: a tutorable
   combo‑control deck that's strong across the field 1v1 (incl. Nekusar). Only real
   soft spots: graveyard decks (win via Approach, not mill) and faster combo (Kenrith).
3. **Baylen** is the "fun" deck, not the competitive 1v1 pick — it wants a
   multiplayer table where pressure is split.

---

## 4‑player (pod)

Each opponent is modeled as a **4‑player free‑for‑all**: you + **three** opponents,
all three piloting that commander's optimized deck.

**Scale (pod, baseline "fair share" = 25%):** 1 = almost never wins ·
2 = below fair share · 3 = ~fair 25% share · 4 = pod favorite · 5 = dominant.

| # | Opponent (optimized) ×3 | Archetype | Baylen | Bumbleflower† | Finneas | Best |
|---|---|---|:--:|:--:|:--:|---|
| 1 | The Ur-Dragon | 5c dragon ramp/beatdown | 3 | 4 | 4 | Finneas |
| 2 | Edgar Markov | Mardu vampire aristo‑aggro | 3 | 3 | 4 | Finneas |
| 3 | Y'shtola, Night's Blessed | Esper pillow/lifedrain | 2 | 3 | 4 | Finneas |
| 4 | Atraxa, Praetors' Voice | 4c infect/proliferate | 3 | 3 | 4 | Finneas |
| 5 | Krenko, Mob Boss | Mono‑R goblin aggro‑combo | 3 | 2 | 4 | Finneas |
| 6 | Kaalia of the Vast | Mardu cheat‑in fatties | 3 | 3 | 4 | Finneas |
| 7 | Vivi Ornitier | Izzet storm/spellslinger | 2 | 2 | 3 | Finneas |
| 8 | Ms. Bumbleflower* | Simic +1/+1 counters value | 4 | 4 | 4 | Finneas |
| 9 | Sauron, the Dark Lord | Grixis reanimator/amass | 3 | 2 | 4 | Finneas |
| 10 | Teval, the Balanced Scale | Sultai graveyard value | 3 | 2 | 5 | Finneas |
| 11 | Pantlaza, Sun-Favored | Naya dino ramp‑beatdown | 3 | 4 | 5 | Finneas |
| 12 | Fire Lord Azula | Grixis storm/burn | 2 | 2 | 4 | Finneas |
| 13 | Lathril, Blade of the Elves | Golgari elf go‑wide/drain | 3 | 3 | 4 | Finneas |
| 14 | Giada, Font of Hope | Mono‑W angels aggro | 2 | 4 | 4 | Finneas |
| 15 | The Wise Mothman | Sultai rad‑mill/proliferate | 4 | 2 | 5 | Finneas |
| 16 | Jodah, the Unifier | 5c legends value | 3 | 3 | 5 | Finneas |
| 17 | Yuriko, the Tiger's Shadow | Dimir ninja tempo/burn | 2 | 3 | 4 | Finneas |
| 18 | Nekusar, the Mindrazer | Grixis wheels/draw‑burn | 4 | 2 | 5 | Finneas |
| 19 | Kenrith, the Returned King | 5c protected Thoracle combo | 1 | 2 | 2 | Bumbleflower |
| 20 | Baylen, the Haymaker* | Naya tokens + ping reach | 3 | 2 | 5 | Finneas |

\*Same commander as one of my decks, **different archetype** — not a mirror.

† **Bumbleflower column revised** after two re‑evaluations — group‑hug/politics and
its full combo suite (see below).

### 4‑player overall stack rank

| Rank | Deck | Avg (of 20) | Pod‑favorite count | Notes |
|---|---|:--:|:--:|---|
| **1** | **Finneas** | **4.15** | 18 / 20 | infinite life walls the pod; ~28‑combo density makes it near‑un‑disruptable |
| 2 | Baylen | 2.80 | 0 / 20 | reliably ~fair share; one Craterhoof can kill the table, but capped by 3× wipe density |
| 3 | Bumbleflower† | **2.75** | ~0 / 20 | **combo re‑rate** (table‑wide Bruvac+Maddening mill) lifts it to a near‑tie with Baylen; still capped by graveyard + fast‑combo pods |

### 4‑player synthesis

- **Finneas (even more dominant in pods):** Heliod + Spike Feeder infinite life
  hard‑walls an *entire table* of damage/drain/burn at once, and Scurry Oak/Rosie/
  Ashnod's infinite tokens → overrun kills all three opponents in one swing. Pod
  favorite in 18 of 20; its only stumble is a faster protected combo (Kenrith).
- **Baylen (rises to 2nd, but never a favorite):** a protected Craterhoof/Finale
  one‑shots the table, and Aura Shards is premium vs pings/pillow — but three
  opponents means ~3× board‑wipe density and it holds no counters, capping it at
  "fair share." Best (4) vs slow value/counters decks it can race (Ms. Bumbleflower,
  Wise Mothman, Nekusar); worst vs fast combo/pillow (Vivi, Azula, Giada, Yuriko,
  Kenrith).
- **Bumbleflower (3rd, but closer after re‑evaluation):** a 1v1 control/mill deck is
  still poorly suited to a pod, but its real multiplayer plan — **threat deflection**
  (never the target), **letting the other three cannibalize each other**, **weaponized
  gifts** (Forced Fruition/Psychic Corrosion turn charity into mill), and
  **board‑agnostic inevitability** (Approach, Jace, Bruvac‑mill) — lifts it to ~fair
  share vs **aggressive creature pods** (Kaalia, Pantlaza, Lathril, Ur‑Dragon) and
  **slow value/superfriends pods** (Atraxa, Jodah, Ms. Bumbleflower), and to a
  pod‑favorite vs **Giada** (mono‑white, no counters, angels race each other). It stays
  low where politics can't help: **combo** (gifts raise storm count — Vivi *drops* to
  2), **graveyard** (mill feeds them — Sauron 1, Teval/Mothman 2), and
  **draw‑punishers** (its own draw is suicidal — Nekusar 1).

### Group‑hug / politics re‑evaluation (Bumbleflower)

The first pass scored the group‑hug as a flat liability. A second pass weighting its
actual multiplayer plan (deflection · let‑them‑fight · weaponized gifts · inevitability
wins) moved **8 matchups up (+1)**, **1 down (−1)**, and confirmed the floors:

- **Up (+1):** Ur‑Dragon 2→3, Atraxa 2→3, Kaalia 2→3, Ms. Bumbleflower 2→3,
  Pantlaza 2→3, Lathril 2→3, Giada 3→**4**, Jodah 2→3.
- **Down (−1):** **Vivi 3→2** — gifting cards literally raises the storm deck's count;
  politics can't fix arming your killer.
- **Unchanged floors:** Nekusar **1** (self‑draw = suicide), Sauron **1** (mill feeds
  reanimation, Notion Thief/Bowmasters punish draw), plus Edgar/Krenko/Y'shtola/Teval/
  Mothman/Kenrith/Baylen where deflection is offset by drain, non‑combat pings, or
  graveyard synergy.

Revised pod average: **2.50** (was 2.15). **Ranking unchanged** — still 3rd behind
Finneas (3.90) and Baylen (2.85), but the gap to Baylen narrows and Bumbleflower is
now genuinely competitive‑for‑best in a handful of pods (Giada, Yuriko, Kenrith).

### Combo re‑evaluation (Bumbleflower)

A later pass corrected the biggest error: Bumbleflower had been scored as a slow
durdle‑mill, but it's a **tutorable combo‑control deck** with a deep, redundant kill
suite (per Commander Spellbook):

- **~6 mill kills**, several *pod‑wide*: Bruvac + Maddening Cacophony (kicked) and
  Riverchurn Monument + Maddening deck the **whole table** at once; Bruvac + Traumatize,
  Traumatize/Maddening + Fraying Sanity, and Riverchurn + Traumatize kill one opponent.
- **Deterministic wins:** Approach of the Second Sun + Windfall / + Mystical Tutor.
- **Engines → Jace WoM:** Mind Over Matter + Temple Bell / The One Ring / Selvala /
  (Folio + Smothering Tithe); Wedding Ring + Consecrated Sphinx.

Because the **mill** kills need no self‑draw, they're even safe vs Nekusar — the single
biggest correction (**1v1 Nekusar 2→4**). Net effect:

- **1v1: 3.20 → 3.65** (+0.45). Ups: Nekusar 2→4, Baylen 3→4, plus Edgar / Atraxa /
  Ms. Bumbleflower / Sauron / Teval / Jodah. Now a clear #2, close to Finneas.
- **4p: 2.50 → 2.75** (+0.25). Table‑wide mill lifts Ur‑Dragon / Edgar / Y'shtola /
  Ms. Bumbleflower / Pantlaza / Sauron / Nekusar; but a more honest read of the
  *storm/tempo* pods drops Azula 3→2 and Yuriko 4→3 (three combo/counter decks go
  off first).
- **Unchanged caps:** graveyard pods (mill feeds them — Sauron/Teval/Mothman) and the
  faster protected Kenrith combo. Ranking holds: 3rd, but now essentially tied with
  Baylen (2.75 vs 2.80).

### Combo re‑evaluation (Finneas)

Finneas's combos were central from the start, but the first pass loaded only 3; the deck
actually runs **~28 documented infinite combos on a ~12‑card core** (2‑card token loops,
Heliod/Archangel + Spike Feeder infinite life, ~16 three‑card lifegain engines, and
Kitchen Finks + Ashnod's Altar persist lines for infinite mana/draw). Weighting the full
density mainly raises its **disruption‑resistance**: matchups previously capped at 4 by
"no counters, one removal could stop the combo" rise to **5 vs low‑interaction decks**.

- **1v1: 3.85 → 4.25** (+0.40). Ups to 5: Ur‑Dragon, Ms. Bumbleflower, Teval, Lathril,
  Giada, Jodah, Baylen (+ Kaalia 3→4). Held: speed‑capped 3s (Krenko, Vivi, Yuriko) and
  **Kenrith 2** (a *faster* protected combo goes off first).
- **4p: 3.90 → 4.15** (+0.25). Ups to 5: Teval, Pantlaza, Mothman, Jodah, Baylen.
- **Ranking unchanged** — Finneas was already #1; it's now #1 by a wider margin.

---

## 1v1 vs 4‑player — the big picture

| Deck | 1v1 avg | 1v1 rank | 4p avg | 4p rank | Takeaway |
|---|:--:|:--:|:--:|:--:|---|
| **Finneas** | 4.25 | 1st | 4.15 | 1st | Best in **both** by a clear margin — a ~28‑combo deck that's very hard to disrupt. |
| **Baylen** | 3.05 | 3rd | 2.80 | 2nd | The "party" deck: relatively better in multiplayer, but never a pod favorite. |
| **Bumbleflower** | 3.65 | 2nd | 2.75 | 3rd | **Combo‑control** (re‑rated): a real threat 1v1 (close to Finneas), near‑tied with Baylen in pods. |

**Bottom line:** Finneas is the clear best deck against this meta in every seat count —
a ~28‑combo engine that's fast (turn 4‑6), resilient (infinite life), and very hard to
disrupt, losing only to a *faster* protected combo (Kenrith). **Bumbleflower** is a
tutorable combo‑control deck, the #2 in 1v1 (3.65) and essentially tied with Baylen in
pods. **Baylen** is the flavor/fun deck: fine at a multiplayer table (~fair share) but
never a front‑runner.

