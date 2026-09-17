# Somebunny Is Having a Party

A little family of rabbit-flavored Commander decks.

They all begin the same way—*somebunny’s having a party*—but no two parties end alike. One overruns the meadow with an adorable stampede. One drags her wedding guests around the world until their bank accounts empty. One serves a magnificent feast where the guests are also the ingredients.

Choose your host carefully. Each deck has its own README, decklists, and generated card mosaics.

## The Decks

### Somebunny Is Having a Party

* [Baylen, the Haymaker — *Somebunny Brought the Whole Warren*](decks/Somebunny%20Is%20Having%20a%20Party/Baylen%20%E2%80%93%20Somebunny%20Brought%20the%20Whole%20Warren/README.md)
* [Finneas, Ace Archer — *Somebunny’s On the Menu*](decks/Somebunny%20Is%20Having%20a%20Party/Finneas%20%E2%80%93%20Somebunny%E2%80%99s%20On%20the%20Menu/README.md)
* [Ms. Bumbleflower — *Somebunny Said I Do*](decks/Somebunny%20Is%20Having%20a%20Party/Ms.%20Bumbleflower%20%E2%80%93%20Somebunny%20Said%20I%20Do/README.md)

### Nuts About Capatalism

* [Camellia, the Seedmiser — *Nuts About Consumption*](decks/Nuts%20About%20Capatalism/Camellia%20%E2%80%93%20Nuts%20About%20Consumption/README.md)
* [Chatterfang, Squirrel General — *Nuts About AI*](decks/Nuts%20About%20Capatalism/Chatterfang%20%E2%80%93%20Nuts%20About%20AI/README.md)
* [Hazel of the Rootbloom — *Nuts About Replication*](decks/Nuts%20About%20Capatalism/Hazel%20%E2%80%93%20Nuts%20About%20Replication/README.md)

### Dumpster Diving

* [Bello, Bard of the Brambles — *Dumpster Dig*](decks/Dumpster%20Diving/Bello%20%E2%80%93%20Dumpster%20Dig/README.md)
* [Muerra, Trash Tactician — *Dumpster Fire*](decks/Dumpster%20Diving/Muerra%20%E2%80%93%20Dumpster%20Fire/README.md)

### Cold-Blooded Monsters

* [Clement, the Worrywort — *Cold-Blooded Calculations*](decks/Cold-Blooded%20Monsters/Clement%20%E2%80%93%20Cold-Blooded%20Calculations/README.md)

### Sky High Costs

* [Zoraline, Cosmos Caller — *Sky High Premiums*](decks/Sky%20High%20Costs/Zoraline%20%E2%80%93%20Sky%20High%20Premiums/README.md)

## Repository Layout

```
decks/
  <group>/
    <commander> – <title>/
      README.md              # deck overview and local resources
      decklist.dck           # authoritative Forge decklist
      decklist.txt / decklist_moxfield.txt  # generated plain-text exports
      deck_mosaic.png / deck_mosaic_preview.jpg  # generated card mosaics
      party.toml             # optional mosaic and theme metadata
      theme_analysis.md      # optional per-card theme evaluation
      power_analysis.md      # optional strategy and power analysis
```

| Path | Description |
|------|-------------|
| [decks/](decks/) | One folder per host, each a self-contained party |
| [decks/Somebunny Is Having a Party/](decks/Somebunny%20Is%20Having%20a%20Party/) | Baylen, Ms. Bumbleflower, and Finneas |
| [decks/Nuts About Capatalism/](decks/Nuts%20About%20Capatalism/) | Camellia, Hazel, and Chatterfang |
| [decks/Dumpster Diving/](decks/Dumpster%20Diving/) | Muerra and Bello |
| [decks/Cold-Blooded Monsters/](decks/Cold-Blooded%20Monsters/) | Clement |
| [decks/Sky High Costs/](decks/Sky%20High%20Costs/) | Zoraline |
| [scripts/generate_mosaic.py](scripts/generate_mosaic.py) | Generates mosaics for every deck (`python scripts/generate_mosaic.py [slug]`) |
| [scripts/dck_to_text.py](scripts/dck_to_text.py) | Exports decklists to plain text |
| [scripts/dck_to_moxfield.py](scripts/dck_to_moxfield.py) | Exports decklists to Moxfield/Archidekt set-code format |
| [card_images/](card_images/) | Shared cache of card images from Scryfall |
| [.github/workflows/update-mosaics.yml](.github/workflows/update-mosaics.yml) | Automatically regenerates and commits deck images on card changes |

## Syncing from DeckCheck

DeckCheck is the source of truth for deck membership and printings. Map each
stable slug to its grouped directory under `[paths]` and its public URL under
`[folders]` in [deckcheck.toml](deckcheck.toml):

```toml
[paths]
baylen = "Somebunny Is Having a Party/Baylen – Somebunny Brought the Whole Warren"

[folders]
baylen = "https://deckcheck.co/app/decklist/PUBLIC_ID"
```

`[mosaic_order]` gives the exact order of every non-commander visually
borderless treatment at the beginning of each deck mosaic. Generation fails if
a first-bucket card is missing from that list or a configured card no longer
uses a qualifying treatment.

`[image_language]` optionally overrides the language used for a selected
printing's mosaic image, for example `"set/collector" = "ja"`. Language-specific
images use cache names such as `card_images/set_collector_ja.jpg`; Forge decklists
remain language-neutral.

Preview or apply the sync with:

```bash
python3 scripts/sync_deckcheck.py --dry-run
python3 scripts/sync_deckcheck.py
python3 scripts/sync_deckcheck.py --deck dumpster-dig
```

The script uses DeckCheck's documented, keyless public-deck endpoint and writes
each deck directly to the grouped directory configured under `[paths]` in
[deckcheck.toml](deckcheck.toml) as `decklist.dck`. The exact card images
selected in DeckCheck are downloaded
to the shared `card_images/<set>_<collector>.jpg` cache unless `--no-images` is
passed. Text exports and mosaics are regenerated after a successful sync unless
`--no-artifacts` is passed. Fetch, configuration, deck size, visibility, format,
image, and artifact errors exit with status 2.

DeckCheck does not document a public profile or folder-list endpoint, and its
API policy disallows scraping. Consequently, newly published decks must be
added to [deckcheck.toml](deckcheck.toml) before the supported API can sync them.
