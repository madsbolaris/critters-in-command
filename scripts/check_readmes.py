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
* ``scryfall.com`` links must be shaped like ``/card/<set>/<number>[/slug]``
  or ``/search?q=...``; anything else is a malformed-link error.
* For ``/card/<set>/<number>`` links: if that exact printing (set + collector
  number) is used by a *different* card in the decklist, that's a hard
  error — it means the story text and the decklist disagree about what that
  Scryfall page actually is (a real bug, e.g. a copy/paste or collector
  number typo).
* Any external link outside of scryfall.com / deckcheck.co is flagged as a
  warning (not necessarily wrong, just worth a human look).
* A card named in the README that isn't found anywhere in the decklist (by
  name) is a hard error. Every card a story links to must actually be in the
  99 — fix the README (link the real card) or fix the decklist (the card
  belongs in the deck) rather than treating it as a harmless namedrop.

Also reported, as a non-fatal ``INFO`` diagnostic, is the reverse gap: cards
that are in the decklist but never get a mention in the README at all (basic
lands excluded). This never fails the run — it's just a coverage list to help
when writing or reworking a deck's flavor text. Each card is annotated with how
many *other* decks in the repository also play it, sorted fewest-shared-first,
so the cards most unique to this particular deck bubble to the top.

Every run also writes a per-deck ``readme_check_report.md`` (gitignored) next
to each README with the same information, so it can be referenced while
editing without re-running the script.

Usage:
    python scripts/check_readmes.py                  # every deck
    python scripts/check_readmes.py baylen bumbleflower  # by folder-name substring
    python scripts/check_readmes.py --strict          # warnings also fail the run
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
import urllib.parse
from dataclasses import dataclass
from pathlib import Path

REPO_DIR = Path(__file__).parent.parent
DECKS_DIR = REPO_DIR / "decks"

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

_QUOTE_MAP = str.maketrans({"\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"'})


def normalize_name(name: str) -> str:
    """Fold smart quotes/whitespace so decklist and README spellings compare equal."""
    name = unicodedata.normalize("NFKC", name.translate(_QUOTE_MAP))
    return " ".join(name.split()).strip().lower()


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


def parse_decklist(path: Path) -> DeckCards:
    by_name: dict = {}
    by_printing: dict = {}
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
        if set_code and collector:
            by_printing[(set_code.lower(), collector.lower())] = entry
    return DeckCards(by_name=by_name, by_printing=by_printing)


def require_in_deck(link_text: str, cards: DeckCards, issues: list[Issue]) -> None:
    if normalize_name(link_text) not in cards.by_name:
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
            if normalize_name(link_text) != normalize_name(deck_name):
                issues.append(Issue(
                    "ERROR",
                    f"Printing collision: [{link_text}]({url}) points to {set_code}/{number}, "
                    f"but the decklist has '{deck_name}' at that exact printing "
                    f"({deck_set} {deck_number}). The story text and decklist disagree about "
                    "what that Scryfall page is — one of the two names is wrong.",
                ))
    elif path_parts[0] == "search":
        query = urllib.parse.parse_qs(parsed.query)
        q_values = query.get("q")
        if not q_values or not q_values[0].strip():
            issues.append(Issue("ERROR", f"Malformed scryfall search link (missing/empty q= param): {url}"))
    else:
        issues.append(Issue("ERROR", f"Unrecognized scryfall.com link shape (expected /card/ or /search): {url}"))

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


def check_readme(readme_path: Path, deck_dir: Path, cards: DeckCards) -> list[Issue]:
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
    covered = {normalize_name(match.group(1)) for match in LINK_RE.finditer(readme_text)}
    uncovered = [
        (raw_name, global_card_counts.get(normalized, 1) - 1)
        for normalized, (raw_name, _set, _number) in cards.by_name.items()
        if normalized not in covered and normalized not in BASIC_LAND_NAMES
    ]
    uncovered.sort(key=lambda item: (item[1], item[0].lower()))
    return uncovered


def discover_decks() -> list[Path]:
    return sorted(
        {dck.parent for dck in DECKS_DIR.rglob("decklist.dck") if (dck.parent / "README.md").exists()}
    )


REPORT_FILENAME = "readme_check_report.md"


def render_report(rel: Path, errors: list[Issue], warnings: list[Issue],
                   uncovered: list[tuple[str, int]]) -> str:
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
    if uncovered:
        for name, count in uncovered:
            label = "deck" if count == 1 else "decks"
            lines.append(f"- {name} ({count} other {label})")
    else:
        lines.append("None.")
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
        issues = check_readme(readme_path, deck_dir, cards)
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

        (deck_dir / REPORT_FILENAME).write_text(render_report(rel, errors, warnings, uncovered), encoding="utf-8")

        had_errors = had_errors or bool(errors)

    return 1 if had_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
