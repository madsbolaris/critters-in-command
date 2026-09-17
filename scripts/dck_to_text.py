#!/usr/bin/env python3
"""
Convert Forge ``.dck`` decklists into plain copy/paste text for deck-analysis
sites (Moxfield, Archidekt, EDHREC, Deckstats, TappedOut, etc.).

It strips the Forge ``|SET|[collector]`` suffixes and emits clean ``<count> <name>``
lines, grouped as: commander, then mainboard, then (optionally) sideboard.

Usage:
    python scripts/dck_to_text.py                             # all decks -> stdout
    python scripts/dck_to_text.py path/to/decklist.dck          # one deck -> stdout
    python scripts/dck_to_text.py --write                     # write <deck>.txt next to each .dck
    python scripts/dck_to_text.py --moxfield                 # sideboard as "SB:" lines (Moxfield)
    python scripts/dck_to_text.py --no-sideboard            # omit the sideboard entirely
"""

import argparse
import re
import sys
from pathlib import Path

REPO_DIR = Path(__file__).parent.parent

# A card line looks like:  "10 Hare Apparent|FDN"  or  "1 Plains|BLB|[369]"
CARD_LINE = re.compile(r"^\s*(\d+)\s+(.+?)\s*$")
# A section header looks like:  "[main]"
SECTION = re.compile(r"^\s*\[([^\]]+)\]\s*$")


def parse_dck(path: Path) -> dict[str, list[tuple[int, str]]]:
    """Return {section: [(count, name), ...]} for commander/main/sideboard."""
    sections: dict[str, list[tuple[int, str]]] = {
        "commander": [],
        "main": [],
        "sideboard": [],
        "attractions": [],
    }
    current = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        header = SECTION.match(raw)
        if header:
            current = header.group(1).strip().lower()
            continue
        if current not in sections:
            # Skip [metadata] and anything we don't emit.
            continue
        match = CARD_LINE.match(raw)
        if not match:
            continue
        count = int(match.group(1))
        # Card name is everything before the first "|" (set / collector data).
        name = match.group(2).split("|", 1)[0].strip()
        if name:
            sections[current].append((count, name))
    return sections


def render(sections: dict[str, list[tuple[int, str]]], *,
           include_sideboard: bool, moxfield: bool) -> str:
    """Build the copy/paste text for one deck."""
    def lines(cards: list[tuple[int, str]], prefix: str = "") -> list[str]:
        return [f"{prefix}{count} {name}" for count, name in cards]

    blocks: list[str] = []

    if sections["commander"]:
        blocks.append("\n".join(lines(sections["commander"])))

    if sections["main"]:
        blocks.append("\n".join(lines(sections["main"])))

    if include_sideboard and sections["sideboard"]:
        if moxfield:
            # Moxfield reads "SB:" prefixed lines as the sideboard.
            blocks.append("\n".join(lines(sections["sideboard"], prefix="SB: ")))
        else:
            blocks.append("Sideboard\n" + "\n".join(lines(sections["sideboard"])))

    if sections["attractions"]:
        blocks.append("Attractions\n" + "\n".join(lines(sections["attractions"])))

    # Blank line between blocks keeps the commander distinct for importers.
    return "\n\n".join(blocks) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert Forge .dck files to plain decklist text.")
    parser.add_argument("files", nargs="*", type=Path,
                        help="One or more .dck files (default: every decklist.dck under decks/).")
    parser.add_argument("--write", action="store_true",
                        help="Write <deck>.txt next to each .dck instead of printing.")
    parser.add_argument("--no-sideboard", dest="sideboard", action="store_false",
                        help="Omit the sideboard from the output.")
    parser.add_argument("--moxfield", action="store_true",
                        help='Emit sideboard as "SB:" lines (Moxfield bulk-import style).')
    args = parser.parse_args()

    files = args.files or sorted((REPO_DIR / "decks").rglob("decklist.dck"))
    if not files:
        print("No .dck files found.", file=sys.stderr)
        return 1

    for i, path in enumerate(files):
        if not path.exists():
            print(f"Skipping missing file: {path}", file=sys.stderr)
            continue
        sections = parse_dck(path)
        text = render(sections, include_sideboard=args.sideboard,
                      moxfield=args.moxfield)

        if args.write:
            out = path.with_suffix(".txt")
            out.write_text(text, encoding="utf-8")
            print(f"Wrote {out}", file=sys.stderr)
        else:
            if len(files) > 1:
                # "//" comments are ignored by Moxfield/Archidekt if pasted along.
                if i:
                    print()
                print(f"// {path.name}")
            sys.stdout.write(text)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
