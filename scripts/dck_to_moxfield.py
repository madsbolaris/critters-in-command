#!/usr/bin/env python3
"""
Convert Forge ``.dck`` decklists into the set-code export format used by
Moxfield / Archidekt, with a collector number on every line::

    Commander
    1 Baylen, the Haymaker (BLB) 205

    10 Hare Apparent (FDN) 15
    1 Sol Ring (TMC) 59
    ...

Collector numbers (and set codes) are read from the Scryfall links in
``THEME_ANALYSIS.md`` (``scryfall.com/card/<set>/<collector>/...``), keyed by
card name. Any card missing from the analysis is resolved via the Scryfall API
so that every line ends up with a number.

Usage:
    python scripts/dck_to_moxfield.py                             # all decks -> stdout
    python scripts/dck_to_moxfield.py path/to/decklist.dck          # one deck -> stdout
    python scripts/dck_to_moxfield.py --write                     # write <deck>_moxfield.txt
    python scripts/dck_to_moxfield.py --no-sideboard             # omit the sideboard
    python scripts/dck_to_moxfield.py --no-scryfall             # don't hit the network
"""

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

REPO_DIR = Path(__file__).parent.parent

CARD_LINE = re.compile(r"^\s*(\d+)\s+(.+?)\s*$")
SECTION = re.compile(r"^\s*\[([^\]]+)\]\s*$")
# First markdown table cell -> card name.
MD_NAME = re.compile(r"^\|\s*(.+?)\s*\|")
# scryfall.com/card/<set>/<collector>/...
MD_SCRYFALL = re.compile(r"scryfall\.com/card/([^/|)]+)/([^/|)]+)")
# Trailing "×12" / "x12" copy count in the analysis name cell.
COPY_SUFFIX = re.compile(r"\s*[×x]\s*\d+\s*$")

SCRYFALL_DELAY = 0.12  # be polite: ~100ms between API calls


def normalize(name: str) -> str:
    return COPY_SUFFIX.sub("", name).strip().lower()


def find_theme_file(directory: Path) -> Path | None:
    for candidate in ("THEME_ANALYSIS.md", "theme_analysis.md"):
        path = directory / candidate
        if path.exists():
            return path
    return None


def load_collectors(theme_path: Path) -> dict[str, tuple[str, str]]:
    """Map normalized card name -> (set_code, collector) from analysis links."""
    collectors: dict[str, tuple[str, str]] = {}
    for raw in theme_path.read_text(encoding="utf-8").splitlines():
        link = MD_SCRYFALL.search(raw)
        name_match = MD_NAME.match(raw)
        if not (link and name_match):
            continue
        key = normalize(name_match.group(1))
        if key and key not in collectors:
            collectors[key] = (link.group(1).upper(), link.group(2))
    return collectors


_scryfall_cache: dict[tuple[str, str], tuple[str, str] | None] = {}


def scryfall_lookup(name: str, set_code: str) -> tuple[str, str] | None:
    """Fetch (set, collector) from Scryfall, preferring the deck's set."""
    cache_key = (name.lower(), set_code.lower())
    if cache_key in _scryfall_cache:
        return _scryfall_cache[cache_key]

    def query(url: str) -> tuple[str, str] | None:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "dck-to-moxfield/1.0"})
            time.sleep(SCRYFALL_DELAY)
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.load(resp)
            return data["set"].upper(), str(data["collector_number"])
        except Exception:
            return None

    base = "https://api.scryfall.com/cards/named?exact=" + urllib.parse.quote(name)
    result = None
    if set_code:
        result = query(f"{base}&set={urllib.parse.quote(set_code.lower())}")
    if result is None:
        result = query(base)
    _scryfall_cache[cache_key] = result
    return result


def parse_dck(path: Path) -> dict[str, list[tuple[int, str, str, str]]]:
    """Return {section: [(count, name, dck_set, dck_collector), ...]}."""
    sections: dict[str, list[tuple[int, str, str, str]]] = {
        "commander": [], "main": [], "sideboard": [], "attractions": [],
    }
    current = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        header = SECTION.match(raw)
        if header:
            current = header.group(1).strip().lower()
            continue
        if current not in sections:
            continue
        match = CARD_LINE.match(raw)
        if not match:
            continue
        parts = match.group(2).split("|")
        name = parts[0].strip()
        dck_set = parts[1].strip() if len(parts) > 1 else ""
        dck_collector = parts[2].strip().strip("[]") if len(parts) > 2 else ""
        if name:
            sections[current].append((int(match.group(1)), name, dck_set, dck_collector))
    return sections


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert Forge .dck files to Moxfield set-code text with collector numbers.")
    parser.add_argument("files", nargs="*", type=Path,
                        help="One or more .dck files (default: every decklist.dck under decks/).")
    parser.add_argument("--write", action="store_true",
                        help="Write <deck>_moxfield.txt next to each .dck instead of printing.")
    parser.add_argument("--no-sideboard", dest="sideboard", action="store_false",
                        help="Omit the sideboard from the output.")
    parser.add_argument("--no-scryfall", dest="scryfall", action="store_false",
                        help="Do not use the Scryfall API to fill missing collector numbers.")
    args = parser.parse_args()

    files = args.files or sorted((REPO_DIR / "decks").rglob("decklist.dck"))
    if not files:
        print("No .dck files found.", file=sys.stderr)
        return 1

    collectors: dict[str, tuple[str, str]] = {}
    _collector_cache: dict[Path, dict[str, tuple[str, str]]] = {}

    def resolve(name: str, dck_set: str, dck_collector: str) -> tuple[str, str] | None:
        if dck_set and dck_collector:
            return dck_set.upper(), dck_collector
        hit = collectors.get(normalize(name))
        if hit:
            return hit
        if args.scryfall:
            return scryfall_lookup(name, dck_set)
        return None

    def card_line(count: int, name: str, dck_set: str, dck_collector: str) -> str:
        info = resolve(name, dck_set, dck_collector)
        if info:
            set_code, collector = info
            return f"{count} {name} ({set_code}) {collector}"
        print(f"WARNING: no collector number for '{name}'.", file=sys.stderr)
        return f"{count} {name}" + (f" ({dck_set})" if dck_set else "")

    for i, path in enumerate(files):
        if not path.exists():
            print(f"Skipping missing file: {path}", file=sys.stderr)
            continue

        host_dir = path.parent
        if host_dir not in _collector_cache:
            theme_path = find_theme_file(host_dir)
            loaded = load_collectors(theme_path) if theme_path else {}
            _collector_cache[host_dir] = loaded
        collectors = _collector_cache[host_dir]

        sections = parse_dck(path)

        blocks: list[str] = []
        if sections["commander"]:
            blocks.append("Commander\n" + "\n".join(card_line(*c) for c in sections["commander"]))
        if sections["main"]:
            blocks.append("\n".join(card_line(*c) for c in sections["main"]))
        if args.sideboard and sections["sideboard"]:
            blocks.append("Sideboard\n" + "\n".join(card_line(*c) for c in sections["sideboard"]))
        if sections["attractions"]:
            blocks.append("Attractions\n" + "\n".join(card_line(*c) for c in sections["attractions"]))
        text = "\n\n".join(blocks) + "\n"

        if args.write:
            out = path.with_name(f"{path.stem}_moxfield.txt")
            out.write_text(text, encoding="utf-8")
            print(f"Wrote {out}", file=sys.stderr)
        else:
            if len(files) > 1:
                if i:
                    print()
                print(f"// {path.name}")
            sys.stdout.write(text)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
