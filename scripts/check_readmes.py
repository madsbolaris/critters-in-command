#!/usr/bin/env python3
"""
Validate every deck ``README.md`` against its authoritative ``decklist.dck``.

This is a static, offline linter. It does not call the Scryfall API — every
check is derived purely from the two files sitting next to each other in the
repository, so it runs instantly and never flakes on network access.

Checks performed for each ``README.md`` (paired with the ``decklist.dck`` in
the same folder):

* Every markdown link's URL is well-formed. Bare/unlinked URLs and stray
  ``[``/``]`` characters left over from a broken link (e.g. a stray space
  between ``]`` and ``(``) are reported as errors.
* Relative links (decklists, analysis files, mosaic images, "back to all
  decks", etc.) must resolve to a file that actually exists.
* ``scryfall.com`` links must be shaped like ``/card/<set>/<number>[/slug]``;
  ``/search?q=...`` links are a hard error, since they don't pin down a
  specific printing and can show the wrong art for the card the story means.
  Link directly to the card's own page instead.
* For ``/card/<set>/<number>`` links: if that exact printing (set + collector
  number) is used by a *different* card in the decklist, that's a hard
  error — it means the story text and the decklist disagree about what that
  Scryfall page actually is (a real bug, e.g. a copy/paste or collector
  number typo). Link text may be shortened to the card name's trailing
  word(s) (e.g. "Tutelage" for "Teferi's Tutelage") since the set/number
  already pins down the exact card unambiguously. Link text may also be
  shortened to just the character name before the comma (e.g. "Teferi" for
  "Teferi, Time Raveler") — unless another card in the decklist shares that
  same character name, in which case the shorthand is ambiguous and is a
  hard error even though the URL itself is unambiguous.
* Any external link outside of scryfall.com / deckcheck.co is flagged as a
  warning (not necessarily wrong, just worth a human look).
* A card named in the README that isn't found anywhere in the decklist (by
  name) is a hard error. Every card a story links to must actually be in the
  99 — fix the README (link the real card) or fix the decklist (the card
  belongs in the deck) rather than treating it as a harmless namedrop. This
  check also accepts the character-name shorthand described above (e.g. a
  link's text can be "Teferi" for "Teferi, Time Raveler"), with the same
  ambiguity error when more than one deck card shares that name.
* Every deck's featured "thematic borderless" cards — the ones pinned to the
  front of its generated mosaic via ``[mosaic_order]`` in ``deckcheck.toml``
  — must be **bolded** wherever the README links to them (e.g.
  ``**[Wedding Ring](...)**``). A matching link that isn't wrapped in ``**``
  is a hard error.
* The README's overall layout must match the shared house style:
  - A ``# <Commander>`` title with just the commander's plain name (no
    flavor subtitle).
  - Immediately after, a metadata table with exactly these rows, in this
    order: **Commander**, **Colors**, **Archetype**, **Good against**,
    **Struggles against**.
  - A ``## <Deck Name>`` narrative section header whose text matches the
    deck's flavor name — the part of the deck's folder name after the
    " – " separator (e.g. "Somebunny Said I Do" for
    "Ms. Bumbleflower – Somebunny Said I Do").
  - A ``## The Deck`` section containing the mosaic preview image, which
    must come before a final ``## Deck Resources`` section. The mosaic
    preview image must not appear anywhere else in the file.
  Any deviation from this layout is a hard error.

Also reported, as a non-fatal ``INFO`` diagnostic, is the reverse gap: cards
that are in the decklist but never get a mention in the README at all (basic
lands excluded). This never fails the run — it's just a coverage list to help
when writing or reworking a deck's flavor text. Each card is annotated with how
many *other* decks in the repository also play it, sorted fewest-shared-first,
so the cards most unique to this particular deck bubble to the top.

Every run also writes a per-deck ``readme_check_report.md`` (gitignored) next
to each README with the same information, so it can be referenced while
editing without re-running the script. In that report, the uncovered-card list
is also grouped by card type (Creature, Sorcery, Instant, Artifact,
Enchantment, Land) using the local Scryfall bulk-data cache already maintained
by ``scripts/shopping_list.py`` (``scripts/.cache/scryfall_default_cards.json``).
If that cache hasn't been populated yet, the list falls back to ungrouped —
run ``scripts/shopping_list.py`` once to populate it (still no network call
from this script itself).

Usage:
    python scripts/check_readmes.py                  # every deck
    python scripts/check_readmes.py baylen bumbleflower  # by folder-name substring
    python scripts/check_readmes.py --strict          # warnings also fail the run
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
import unicodedata
import urllib.parse
from dataclasses import dataclass
from pathlib import Path

REPO_DIR = Path(__file__).parent.parent
DECKS_DIR = REPO_DIR / "decks"
CACHE_DIR = REPO_DIR / "scripts" / ".cache"
BULK_FILE = CACHE_DIR / "scryfall_default_cards.json"
TYPE_INDEX_FILE = CACHE_DIR / "card_type_index.json"
DECKCHECK_CONFIG = REPO_DIR / "deckcheck.toml"

ALLOWED_EXTERNAL_DOMAINS = {"scryfall.com", "deckcheck.co"}

# [link text](url) — url has no whitespace/parens, which every link in these
# READMEs satisfies (Scryfall/deckcheck URLs and repo-relative paths alike).
LINK_RE = re.compile(r"\[([^\[\]]+)\]\(([^\s()]+)\)")
BARE_URL_RE = re.compile(r"https?://\S+")

# Forge .dck lines look like "1 Card Name|SET|[collector]" (set/collector optional).
DCK_CARD_LINE = re.compile(r"^\s*(\d+)\s+(.+?)\s*$")
DCK_SECTION = re.compile(r"^\s*\[([^\]]+)\]\s*$")
DCK_SECTIONS = {"commander", "main", "sideboard", "attractions"}

SCRYFALL_SET_RE = re.compile(r"^[a-z0-9]+$")

# Some printings (Secret Lair / Universes Beyond crossover treatments, mostly)
# carry an alternate "flavor name" printed on the card itself, distinct from
# the card's real (Oracle) name stored in the decklist. The README should use
# whichever name is actually printed on the physical card, so a link pinned to
# one of these exact (set, collector number) printings may use the flavor name
# in place of the deck name.
FLAVOR_NAMES: dict[tuple[str, str], str] = {
    ("sld", "2205"): "Cordyceps Rat King",  # Mycoloth's The Last of Us treatment
}

_QUOTE_MAP = str.maketrans({"\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"'})


def normalize_name(name: str) -> str:
    """Fold smart quotes/whitespace so decklist and README spellings compare equal."""
    name = unicodedata.normalize("NFKC", name.translate(_QUOTE_MAP))
    return " ".join(name.split()).strip().lower()


def is_shortened_name_match(link_text: str, deck_name: str) -> bool:
    """Allow link text that's just the trailing word(s) of the real card name.

    e.g. "Tutelage" matches "Teferi's Tutelage". Only called once a /card/<set>/<num>
    link has already pinned the exact printing to one deck card, so there's no
    ambiguity about which card the shortened text refers to.
    """
    link_words = normalize_name(link_text).split(" ")
    deck_words = normalize_name(deck_name).split(" ")
    if not link_words or len(link_words) > len(deck_words):
        return False
    return deck_words[-len(link_words):] == link_words


def character_name(name: str) -> str:
    """The portion of a card name before the first comma, e.g. "Teferi" from "Teferi, Time Raveler"."""
    return name.split(",", 1)[0].strip()


def is_character_name_match(link_text: str, deck_name: str) -> bool:
    """True if link_text is exactly the character-name portion of deck_name (before the comma)."""
    if "," not in deck_name:
        return False
    return normalize_name(link_text) == normalize_name(character_name(deck_name))


def is_flavor_name_match(link_text: str, set_code: str, collector: str) -> bool:
    """True if link_text is the alternate flavor name printed on this exact
    (set, collector number) printing, e.g. "Cordyceps Rat King" for Mycoloth's
    sld/2205 treatment. See FLAVOR_NAMES.
    """
    flavor = FLAVOR_NAMES.get((set_code.lower(), collector.lower()))
    return flavor is not None and normalize_name(link_text) == normalize_name(flavor)


def scryfall_card_printing(url: str) -> tuple[str, str] | None:
    """(set code, collector number) parsed from a scryfall.com /card/<set>/<num> URL, or None."""
    parsed = urllib.parse.urlparse(url)
    if parsed.netloc != "scryfall.com":
        return None
    path_parts = [p for p in parsed.path.split("/") if p]
    if len(path_parts) < 3 or path_parts[0] != "card":
        return None
    return (urllib.parse.unquote(path_parts[1]).lower(), urllib.parse.unquote(path_parts[2]).lower())


@dataclass(frozen=True)
class Issue:
    level: str  # "ERROR" or "WARNING"
    message: str


@dataclass(frozen=True)
class DeckCards:
    # normalized card name -> (raw name, set code, collector number)
    by_name: dict
    # (lowercase set code, lowercase collector number) -> (raw name, set code, collector number)
    by_printing: dict
    # normalized character name (before the comma) -> raw names of every card sharing it
    character_names: dict
    # raw name(s) of the card(s) in the decklist's [Commander] section, in declared order
    commander_names: list


def parse_decklist(path: Path) -> DeckCards:
    by_name: dict = {}
    by_printing: dict = {}
    character_names: dict = {}
    commander_names: list = []
    section = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        header = DCK_SECTION.match(raw_line)
        if header:
            section = header.group(1).strip().lower()
            continue
        if section not in DCK_SECTIONS:
            continue
        match = DCK_CARD_LINE.match(raw_line)
        if not match:
            continue
        parts = match.group(2).split("|")
        name = parts[0].strip()
        if not name:
            continue
        set_code = parts[1].strip() if len(parts) > 1 else ""
        collector = parts[2].strip().strip("[]") if len(parts) > 2 else ""
        entry = (name, set_code, collector)
        by_name[normalize_name(name)] = entry
        if "," in name:
            character_names.setdefault(normalize_name(character_name(name)), []).append(name)
        if set_code and collector:
            by_printing[(set_code.lower(), collector.lower())] = entry
        if section == "commander":
            commander_names.append(name)
    return DeckCards(by_name=by_name, by_printing=by_printing, character_names=character_names,
                      commander_names=commander_names)


def require_in_deck(link_text: str, cards: DeckCards, issues: list[Issue]) -> None:
    normalized = normalize_name(link_text)
    if normalized in cards.by_name:
        return
    sharers = cards.character_names.get(normalized)
    if sharers:
        if len(set(sharers)) > 1:
            issues.append(Issue(
                "ERROR",
                f"Ambiguous character name: '{link_text}' could be any of "
                f"{', '.join(sorted(set(sharers)))} in this decklist. Use a fuller "
                "name (or the card's epithet) to say which one it is.",
            ))
        return
    issues.append(Issue(
        "ERROR",
        f"'{link_text}' is linked in the README but is not in the decklist. "
        "Every card the story references must actually be in the 99.",
    ))


def check_scryfall_link(link_text: str, url: str, parsed: urllib.parse.ParseResult,
                         cards: DeckCards) -> list[Issue]:
    issues: list[Issue] = []
    path_parts = [p for p in parsed.path.split("/") if p]

    if not path_parts:
        issues.append(Issue("ERROR", f"Malformed scryfall.com link (no path): {url}"))
        return issues

    matched_by_printing = False
    if path_parts[0] == "card":
        if len(path_parts) < 3:
            issues.append(Issue("ERROR", f"Malformed scryfall card link (missing set/number): {url}"))
            return issues
        set_code = urllib.parse.unquote(path_parts[1]).lower()
        number = urllib.parse.unquote(path_parts[2]).lower()
        if not SCRYFALL_SET_RE.match(set_code):
            issues.append(Issue("ERROR", f"Malformed scryfall set code '{set_code}' in link: {url}"))
        entry = cards.by_printing.get((set_code, number))
        if entry is not None:
            deck_name, deck_set, deck_number = entry
            if (normalize_name(link_text) == normalize_name(deck_name)
                    or is_shortened_name_match(link_text, deck_name)
                    or is_flavor_name_match(link_text, set_code, number)):
                matched_by_printing = True
            elif is_character_name_match(link_text, deck_name):
                sharers = cards.character_names.get(normalize_name(character_name(deck_name)), [])
                if len(set(sharers)) > 1:
                    issues.append(Issue(
                        "ERROR",
                        f"Ambiguous character name: [{link_text}]({url}) could be any of "
                        f"{', '.join(sorted(set(sharers)))} in this decklist. Use a fuller "
                        "name (or the card's epithet) to say which one it is.",
                    ))
                else:
                    matched_by_printing = True
            else:
                issues.append(Issue(
                    "ERROR",
                    f"Printing collision: [{link_text}]({url}) points to {set_code}/{number}, "
                    f"but the decklist has '{deck_name}' at that exact printing "
                    f"({deck_set} {deck_number}). The story text and decklist disagree about "
                    "what that Scryfall page is — one of the two names is wrong.",
                ))
    elif path_parts[0] == "search":
        issues.append(Issue(
            "ERROR",
            f"Scryfall search link not allowed: {url}. Link directly to the card's "
            "own page (/card/<set>/<number>) so the art shown matches the printing "
            "the story means.",
        ))
    else:
        issues.append(Issue("ERROR", f"Unrecognized scryfall.com link shape (expected /card/ or /search): {url}"))

    if not matched_by_printing:
        require_in_deck(link_text, cards, issues)
    return issues


def check_link(link_text: str, url: str, deck_dir: Path, cards: DeckCards) -> list[Issue]:
    parsed = urllib.parse.urlparse(url)

    if parsed.scheme in ("http", "https"):
        domain = parsed.netloc.lower()
        if domain == "scryfall.com":
            return check_scryfall_link(link_text, url, parsed, cards)
        if domain == "deckcheck.co":
            return []
        return [Issue("WARNING", f"Unexpected external domain '{domain}' in [{link_text}]({url})")]

    if parsed.scheme:
        return [Issue("WARNING", f"Unexpected URL scheme '{parsed.scheme}' in [{link_text}]({url})")]

    # Local, repo-relative link (decklist exports, analysis files, mosaic images, ...).
    rel_path = urllib.parse.unquote(parsed.path)
    if not rel_path:
        return [Issue("ERROR", f"Empty local link target in [{link_text}]({url})")]
    resolved = (deck_dir / rel_path).resolve()
    if not resolved.exists():
        return [Issue("ERROR", f"Broken local link [{link_text}]({url}) -> {resolved} does not exist")]
    return []


def load_mosaic_order() -> dict[Path, list[str]]:
    """Deck directory -> its featured card names, from ``[mosaic_order]`` in
    ``deckcheck.toml``. These are the deck's thematic borderless/showcase
    treatments pinned to the front of its generated mosaic, and every README
    mention of them must be bolded.
    """
    if not DECKCHECK_CONFIG.exists():
        return {}
    with DECKCHECK_CONFIG.open("rb") as config_file:
        config = tomllib.load(config_file)
    mosaic_order = config.get("mosaic_order", {})
    paths = config.get("paths", {})
    result: dict[Path, list[str]] = {}
    for slug, names in mosaic_order.items():
        relative = paths.get(slug)
        if not relative:
            continue
        result[DECKS_DIR / relative] = list(names)
    return result


def check_featured_cards_are_bold(text: str, featured_names: list[str],
                                   cards: DeckCards | None = None) -> list[Issue]:
    """Every README link to one of the deck's featured mosaic_order cards must be
    wrapped in ``**bold**`` (e.g. ``**[Wedding Ring](...)**``) so these thematic
    borderless treatments stand out from the rest of the story text.
    """
    issues: list[Issue] = []
    for match in LINK_RE.finditer(text):
        link_text = match.group(1)
        for name in featured_names:
            is_match = (normalize_name(link_text) == normalize_name(name)
                        or is_shortened_name_match(link_text, name)
                        or is_character_name_match(link_text, name))
            if not is_match and cards is not None:
                printing = scryfall_card_printing(match.group(2))
                if printing is not None:
                    entry = cards.by_printing.get(printing)
                    if (entry is not None and normalize_name(entry[0]) == normalize_name(name)
                            and is_flavor_name_match(link_text, *printing)):
                        is_match = True
            if not is_match:
                continue
            before = text[max(0, match.start() - 2):match.start()]
            after = text[match.end():match.end() + 2]
            if before != "**" or after != "**":
                issues.append(Issue(
                    "ERROR",
                    f"[{link_text}]({match.group(2)}) refers to '{name}', one of this deck's "
                    "featured cards (mosaic_order in deckcheck.toml) — wrap it in bold: "
                    f"**[{link_text}]({match.group(2)})**.",
                ))
            break
    return issues


# Required metadata-table rows, in order, right after the "# <Commander>" title.
LAYOUT_TABLE_LABELS = ["Commander", "Colors", "Archetype", "Good against", "Struggles against"]

HEADING_RE = re.compile(r"^(#{1,6})[ \t]+(.+?)[ \t]*$", re.MULTILINE)
TABLE_HEADER_SEP_RE = re.compile(r"^\|\s*\|\s*\|\s*$\n^\|[-\s]+\|[-\s]+\|\s*$", re.MULTILINE)
TABLE_ROW_LABEL_RE = re.compile(r"^\|\s*\*\*(.+?)\*\*\s*\|", re.MULTILINE)
IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]+\)")


def deck_flavor_name(deck_dir: Path) -> str | None:
    """The deck's flavor title: the part of its folder name after the
    " – " separating it from the commander's name (e.g. "Somebunny Said I Do"
    from "Ms. Bumbleflower – Somebunny Said I Do"). ``None`` if the folder
    name doesn't follow that convention.
    """
    parts = deck_dir.name.split(" \u2013 ", 1)
    return parts[1].strip() if len(parts) == 2 else None


def check_readme_layout(text: str, deck_dir: Path, cards: DeckCards) -> list[Issue]:
    """Enforce the shared house layout: a plain "# <Commander>" title, a
    metadata table, a "## <Deck Name>" narrative header, and a "## The Deck"
    section (holding the mosaic preview image) before a final
    "## Deck Resources" section. See the module docstring for the full shape.
    """
    issues: list[Issue] = []
    headings = [(len(m.group(1)), m.group(2).strip(), m.start()) for m in HEADING_RE.finditer(text)]
    if not headings:
        issues.append(Issue("ERROR", "README has no headings at all; expected a '# <Commander>' title."))
        return issues

    title_level, title_text, title_pos = headings[0]
    commander_name = cards.commander_names[0] if cards.commander_names else None
    if title_level != 1:
        issues.append(Issue(
            "ERROR",
            f"README must start with a level-1 '# <Commander>' title; found '{'#' * title_level} {title_text}'.",
        ))
    elif commander_name and title_text != commander_name:
        issues.append(Issue(
            "ERROR",
            f"README title '# {title_text}' should be just the commander's plain name: '# {commander_name}'.",
        ))

    next_pos = headings[1][2] if len(headings) > 1 else len(text)
    table_block = text[title_pos:next_pos]
    if not TABLE_HEADER_SEP_RE.search(table_block):
        issues.append(Issue(
            "ERROR",
            "Missing metadata table (`| | |` header row + `|---|---|` separator) right after the title.",
        ))
    row_labels = TABLE_ROW_LABEL_RE.findall(table_block)
    if row_labels != LAYOUT_TABLE_LABELS:
        missing = [label for label in LAYOUT_TABLE_LABELS if label not in row_labels]
        if missing:
            issues.append(Issue(
                "ERROR",
                f"Metadata table is missing row(s): {', '.join(missing)}. "
                f"Expected rows in order: {', '.join(LAYOUT_TABLE_LABELS)}.",
            ))
        else:
            issues.append(Issue(
                "ERROR",
                f"Metadata table rows are out of order. Expected: {', '.join(LAYOUT_TABLE_LABELS)}; "
                f"found: {', '.join(row_labels)}.",
            ))

    if len(headings) < 2:
        issues.append(Issue(
            "ERROR", "README is missing a '## <Deck Name>' narrative header after the metadata table."
        ))
    else:
        narrative_level, narrative_text, _narrative_pos = headings[1]
        if narrative_level != 2:
            issues.append(Issue(
                "ERROR",
                "Expected a level-2 narrative header right after the metadata table; found "
                f"'{'#' * narrative_level} {narrative_text}'.",
            ))
        flavor_name = deck_flavor_name(deck_dir)
        if flavor_name and narrative_text != flavor_name:
            issues.append(Issue(
                "ERROR",
                f"Narrative header '## {narrative_text}' should match the deck's name: '## {flavor_name}'.",
            ))

    the_deck = next(((i, h) for i, h in enumerate(headings) if h[0] == 2 and h[1] == "The Deck"), None)
    deck_resources = next(
        ((i, h) for i, h in enumerate(headings) if h[0] == 2 and h[1] == "Deck Resources"), None
    )
    if the_deck is None:
        issues.append(Issue("ERROR", "Missing '## The Deck' section with the mosaic preview image."))
    if deck_resources is None:
        issues.append(Issue("ERROR", "Missing '## Deck Resources' section."))
    if the_deck is not None and deck_resources is not None and the_deck[1][2] > deck_resources[1][2]:
        issues.append(Issue("ERROR", "'## The Deck' must come before '## Deck Resources'."))

    the_deck_span = None
    if the_deck is not None:
        idx, (_level, _title, pos) = the_deck
        end = headings[idx + 1][2] if idx + 1 < len(headings) else len(text)
        the_deck_span = (pos, end)
        if not IMAGE_RE.search(text[pos:end]):
            issues.append(Issue(
                "ERROR",
                "'## The Deck' section must contain the mosaic preview image "
                "(e.g. ![Deck mosaic](deck_mosaic_preview.jpg)).",
            ))

    for image in IMAGE_RE.finditer(text):
        if the_deck_span is None or not (the_deck_span[0] <= image.start() < the_deck_span[1]):
            issues.append(Issue(
                "ERROR",
                f"Mosaic image {image.group(0)} found outside the '## The Deck' section; move it there.",
            ))

    return issues


def check_readme(readme_path: Path, deck_dir: Path, cards: DeckCards,
                  featured_names: list[str] | None = None) -> list[Issue]:
    issues: list[Issue] = []
    text = readme_path.read_text(encoding="utf-8")

    matches = list(LINK_RE.finditer(text))
    url_spans = [match.span(2) for match in matches]

    for bare in BARE_URL_RE.finditer(text):
        if not any(start <= bare.start() < end for start, end in url_spans):
            snippet = bare.group(0)[:80]
            issues.append(Issue("ERROR", f"Unlinked or malformed URL: {snippet}"))

    remainder = LINK_RE.sub("", text)
    for lineno, line in enumerate(remainder.splitlines(), start=1):
        if "[" in line or "]" in line:
            issues.append(Issue(
                "ERROR",
                f"Stray '[' or ']' outside a recognized markdown link (line {lineno}): {line.strip()[:100]}",
            ))

    for match in matches:
        issues.extend(check_link(match.group(1), match.group(2), deck_dir, cards))

    if featured_names:
        issues.extend(check_featured_cards_are_bold(text, featured_names, cards))

    issues.extend(check_readme_layout(text, deck_dir, cards))

    return issues


BASIC_LAND_NAMES = {"plains", "island", "swamp", "mountain", "forest", "wastes"}


def build_global_card_counts(deck_dirs: list[Path]) -> dict[str, int]:
    """Normalized card name -> number of decks (repo-wide) that play it."""
    counts: dict[str, int] = {}
    for deck_dir in deck_dirs:
        cards = parse_decklist(deck_dir / "decklist.dck")
        for normalized in cards.by_name:
            counts[normalized] = counts.get(normalized, 0) + 1
    return counts


def find_uncovered_cards(readme_text: str, cards: DeckCards,
                          global_card_counts: dict[str, int] | None = None) -> list[tuple[str, int]]:
    """Decklist cards (basic lands excluded) that no README link mentions by name.

    Returns (card name, other-decks-playing-it count) pairs, sorted with the
    most deck-unique cards (fewest other decks) first.
    """
    global_card_counts = global_card_counts or {}
    covered_links = [(match.group(1), match.group(2)) for match in LINK_RE.finditer(readme_text)]
    covered_texts = [text for text, _url in covered_links]
    covered = {normalize_name(text) for text in covered_texts}
    uncovered = []
    for normalized, (raw_name, set_code, number) in cards.by_name.items():
        if normalized in BASIC_LAND_NAMES or normalized in covered:
            continue
        if any(is_shortened_name_match(text, raw_name) or is_character_name_match(text, raw_name)
               for text in covered_texts):
            continue
        if set_code and number and any(
                scryfall_card_printing(url) == (set_code.lower(), number.lower())
                and is_flavor_name_match(text, set_code, number)
                for text, url in covered_links):
            continue
        uncovered.append((raw_name, global_card_counts.get(normalized, 1) - 1))
    uncovered.sort(key=lambda item: (item[1], item[0].lower()))
    return uncovered


def discover_decks() -> list[Path]:
    return sorted(
        {dck.parent for dck in DECKS_DIR.rglob("decklist.dck") if (dck.parent / "README.md").exists()}
    )


# Display order for the report's grouped uncovered-card section.
TYPE_GROUPS = ["Creature", "Sorcery", "Instant", "Artifact", "Enchantment", "Land"]
# Priority order for classifying a type_line that spans multiple of the above
# (e.g. "Artifact Creature", "Land Creature") — first match wins.
_TYPE_CLASSIFY_ORDER = ("Land", "Creature", "Artifact", "Enchantment", "Instant", "Sorcery")


def _build_type_index() -> dict[str, str]:
    with BULK_FILE.open(encoding="utf-8") as f:
        bulk_cards = json.load(f)
    index: dict[str, str] = {}
    for card in bulk_cards:
        name = card.get("name")
        type_line = card.get("type_line")
        if not name or not type_line:
            continue
        # Also index the front-face name, for split/DFC/adventure cards.
        for key in {normalize_name(name), normalize_name(name.split(" // ")[0])}:
            index.setdefault(key, type_line)
    return index


def load_type_index() -> dict[str, str] | None:
    """Normalized card name -> Scryfall ``type_line``, read from the local bulk-data
    cache that ``scripts/shopping_list.py`` maintains. Never calls the network;
    returns ``None`` if that cache hasn't been populated yet.

    The full ~600 MB bulk file is distilled into a small name->type_line
    side-car (``card_type_index.json``) so repeat runs stay fast.
    """
    if not BULK_FILE.exists():
        return None
    if TYPE_INDEX_FILE.exists() and TYPE_INDEX_FILE.stat().st_mtime >= BULK_FILE.stat().st_mtime:
        with TYPE_INDEX_FILE.open(encoding="utf-8") as f:
            return json.load(f)
    index = _build_type_index()
    TYPE_INDEX_FILE.write_text(json.dumps(index), encoding="utf-8")
    return index


def classify_card_type(type_line: str) -> str:
    for group in _TYPE_CLASSIFY_ORDER:
        if group in type_line:
            return group
    return "Other"


def group_uncovered_by_type(
    uncovered: list[tuple[str, int]], type_index: dict[str, str] | None
) -> list[tuple[str, list[tuple[str, int]]]] | None:
    """Bucket an already-sorted uncovered list by card type. ``None`` if types
    aren't available (no local bulk-data cache yet)."""
    if type_index is None:
        return None
    buckets: dict[str, list[tuple[str, int]]] = {}
    for name, count in uncovered:
        type_line = type_index.get(normalize_name(name), "")
        group = classify_card_type(type_line) if type_line else "Unknown"
        buckets.setdefault(group, []).append((name, count))
    order = TYPE_GROUPS + ["Other", "Unknown"]
    return [(group, buckets[group]) for group in order if group in buckets]


REPORT_FILENAME = "readme_check_report.md"


def render_report(rel: Path, errors: list[Issue], warnings: list[Issue],
                   uncovered: list[tuple[str, int]], type_index: dict[str, str] | None) -> str:
    lines = [
        f"# README check report — {rel.name}",
        "",
        "Generated by `scripts/check_readmes.py`. Gitignored; regenerated on every run.",
        "",
        f"Status: {'FAIL' if errors else 'OK'} "
        f"({len(errors)} error(s), {len(warnings)} warning(s), {len(uncovered)} uncovered card(s))",
        "",
    ]

    lines.append("## Errors" if errors else "## Errors\n\nNone.")
    for issue in errors:
        lines.append(f"- {issue.message}")
    lines.append("")

    lines.append("## Warnings" if warnings else "## Warnings\n\nNone.")
    for issue in warnings:
        lines.append(f"- {issue.message}")
    lines.append("")

    lines.append("## Cards not mentioned in the README (most deck-unique first)")
    if not uncovered:
        lines.append("None.")
        lines.append("")
        return "\n".join(lines)

    grouped = group_uncovered_by_type(uncovered, type_index)
    if grouped is None:
        lines.append("_Card-type grouping unavailable — run `scripts/shopping_list.py` once to populate the "
                      "local Scryfall cache, then re-run this checker._")
        lines.append("")
        for name, count in uncovered:
            label = "deck" if count == 1 else "decks"
            lines.append(f"- {name} ({count} other {label})")
        lines.append("")
    else:
        for group, cards_in_group in grouped:
            lines.append(f"### {group}")
            for name, count in cards_in_group:
                label = "deck" if count == 1 else "decks"
                lines.append(f"- {name} ({count} other {label})")
            lines.append("")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("decks", nargs="*", help="Deck folder-name substrings to check (default: all).")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as errors.")
    args = parser.parse_args()

    deck_dirs = discover_decks()
    if not deck_dirs:
        print("No decks with both README.md and decklist.dck found.", file=sys.stderr)
        return 1

    # Card-uniqueness counts always span the whole repo, independent of any --decks filter below.
    global_card_counts = build_global_card_counts(deck_dirs)
    mosaic_order = load_mosaic_order()

    type_index = load_type_index()
    if type_index is None:
        print("Note: scripts/.cache/scryfall_default_cards.json not found; the uncovered-card report "
              "section won't be grouped by type. Run scripts/shopping_list.py once to populate it.",
              file=sys.stderr)

    if args.decks:
        wanted = [needle.lower() for needle in args.decks]
        deck_dirs = [d for d in deck_dirs if any(needle in d.name.lower() for needle in wanted)]
        if not deck_dirs:
            print("No decks matched the given filters.", file=sys.stderr)
            return 1

    had_errors = False
    for deck_dir in deck_dirs:
        cards = parse_decklist(deck_dir / "decklist.dck")
        readme_path = deck_dir / "README.md"
        issues = check_readme(readme_path, deck_dir, cards, mosaic_order.get(deck_dir))
        uncovered = find_uncovered_cards(readme_path.read_text(encoding="utf-8"), cards, global_card_counts)

        errors = [i for i in issues if i.level == "ERROR"]
        warnings = [i for i in issues if i.level == "WARNING"]
        if args.strict:
            errors, warnings = errors + warnings, []

        rel = deck_dir.relative_to(REPO_DIR)
        print(f"\n{rel}")
        if not errors and not warnings:
            print("  OK")
        for issue in errors:
            print(f"  ERROR: {issue.message}")
        for issue in warnings:
            print(f"  WARNING: {issue.message}")
        if uncovered:
            formatted = [f"{name} ({count} other {'deck' if count == 1 else 'decks'})" for name, count in uncovered]
            print(f"  INFO: {len(uncovered)} deck card(s) not mentioned in the README "
                  f"(most deck-unique first): {', '.join(formatted)}")

        (deck_dir / REPORT_FILENAME).write_text(
            render_report(rel, errors, warnings, uncovered, type_index), encoding="utf-8"
        )

        had_errors = had_errors or bool(errors)

    return 1 if had_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
