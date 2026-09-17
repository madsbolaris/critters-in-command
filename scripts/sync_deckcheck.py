#!/usr/bin/env python3
"""Sync known public DeckCheck decks into this repository.

DeckCheck's open API can fetch a public deck by URL without an API key, but it
does not provide public account or folder discovery. Deck URLs therefore live
in ``deckcheck.toml`` under ``[folders]``, with local deck directories
configured under ``[paths]``.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = REPO / "deckcheck.toml"
API_URL = "https://deckcheck.co/api/external/deck"
IMAGE_DIR = REPO / "card_images"
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class SyncError(Exception):
    pass


@dataclass(frozen=True)
class DeckSource:
    slug: str
    url: str
    directory: Path


def load_sources(path: Path) -> list[DeckSource]:
    try:
        with path.open("rb") as config_file:
            config = tomllib.load(config_file)
    except FileNotFoundError as error:
        raise SyncError(f"Config not found: {path}") from error
    except tomllib.TOMLDecodeError as error:
        raise SyncError(f"Invalid TOML in {path}: {error}") from error

    folders = config.get("folders")
    if not isinstance(folders, dict):
        raise SyncError(f"{path} must contain [folders]")
    paths = config.get("paths")
    if not isinstance(paths, dict):
        raise SyncError(f"{path} must contain a [paths] table")

    sources: list[DeckSource] = []
    for slug, url in sorted(folders.items()):
        if not SLUG_RE.fullmatch(slug):
            raise SyncError(f"Invalid deck slug {slug!r}; use lowercase kebab-case")
        if not isinstance(url, str) or not url.startswith("https://deckcheck.co/"):
            raise SyncError(f"{slug} must be a DeckCheck HTTPS URL")
        directory_value = paths.get(slug)
        if not isinstance(directory_value, str) or not directory_value:
            raise SyncError(f"No local path configured for {slug!r} in [paths]")
        directory = Path(directory_value)
        if directory.is_absolute() or ".." in directory.parts:
            raise SyncError(f"Invalid local path for {slug!r}: {directory_value!r}")
        sources.append(DeckSource(slug, url, directory))

    if not sources:
        raise SyncError(f"No deck URLs configured in {path}")
    return sources


def fetch_deck(source: DeckSource) -> dict[str, Any]:
    query = urllib.parse.urlencode({"deck_url": source.url})
    request = urllib.request.Request(
        f"{API_URL}?{query}",
        headers={"Accept": "application/json", "User-Agent": "somebunny-deck-sync/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as error:
        try:
            detail = json.load(error).get("error", error.reason)
        except (json.JSONDecodeError, AttributeError):
            detail = error.reason
        raise SyncError(f"{source.slug}: DeckCheck returned {error.code}: {detail}") from error
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        raise SyncError(f"{source.slug}: could not fetch DeckCheck deck: {error}") from error

    if not isinstance(payload, dict):
        raise SyncError(f"{source.slug}: DeckCheck returned an invalid payload")
    if payload.get("visibility") != "public":
        raise SyncError(f"{source.slug}: deck is not public")
    if payload.get("format") != "commander":
        raise SyncError(f"{source.slug}: expected Commander, got {payload.get('format')!r}")
    return payload


def board_entries(deck: dict[str, Any], board_name: str) -> list[dict[str, Any]]:
    board = deck.get("boards", {}).get(board_name, {})
    cards = board.get("cards", {})
    if not isinstance(cards, dict):
        raise SyncError(f"{deck.get('name', 'Deck')}: invalid {board_name} board")
    entries = list(cards.values())
    entries.sort(key=lambda entry: (
        str(entry.get("card", {}).get("name", "")).casefold(),
        str(entry.get("card", {}).get("setCode", "")),
        str(entry.get("card", {}).get("collectorNumber", "")),
    ))
    return entries


def card_line(entry: dict[str, Any]) -> str:
    card = entry.get("card", {})
    quantity = entry.get("quantity")
    name = card.get("name")
    faces = card.get("cardFaces")
    if " // " in str(name) and isinstance(faces, list) and faces:
        front_name = faces[0].get("name")
        if isinstance(front_name, str) and front_name:
            name = front_name
    set_code = card.get("setCode")
    collector = card.get("collectorNumber")
    if not isinstance(quantity, int) or quantity < 1:
        raise SyncError(f"Invalid card quantity for {name!r}")
    if not all(isinstance(value, str) and value for value in (name, set_code, collector)):
        raise SyncError(f"Card is missing name, set code, or collector number: {card!r}")
    return f"{quantity} {name}|{set_code.upper()}|[{collector}]"


def render_dck(deck: dict[str, Any]) -> str:
    commanders = board_entries(deck, "commanders")
    mainboard = board_entries(deck, "mainboard")
    total = sum(entry.get("quantity", 0) for entry in commanders + mainboard)
    if not commanders:
        raise SyncError(f"{deck.get('name', 'Deck')}: no commander")
    if total != 100:
        raise SyncError(f"{deck.get('name', 'Deck')}: {total} cards, expected 100")

    lines = [
        "[metadata]",
        f"Name={deck.get('name') or 'Untitled Deck'}",
        "Deck Type=Commander",
        "[Commander]",
        *(card_line(entry) for entry in commanders),
        "[main]",
        *(card_line(entry) for entry in mainboard),
    ]
    return "\n".join(lines) + "\n"


def load_image_languages(path: Path) -> dict[str, str]:
    with path.open("rb") as config_file:
        config = tomllib.load(config_file)
    languages = config.get("image_language", {})
    if not isinstance(languages, dict):
        raise SyncError("[image_language] must be a table")
    return {str(key).casefold(): str(value).casefold() for key, value in languages.items()}


def image_sources(
    decks: dict[str, dict[str, Any]],
    languages: dict[str, str] | None = None,
) -> dict[Path, str]:
    languages = languages or {}
    sources: dict[Path, str] = {}
    for deck in decks.values():
        for board_name in ("commanders", "mainboard"):
            for entry in board_entries(deck, board_name):
                card = entry.get("card", {})
                set_code = card.get("setCode")
                collector = card.get("collectorNumber")
                image_url = card.get("imageUrl")
                if isinstance(image_url, dict):
                    image_url = image_url.get("front")
                if not all(isinstance(value, str) and value for value in (set_code, collector, image_url)):
                    raise SyncError(f"{deck.get('name', 'Deck')}: card is missing image metadata: {card.get('name')!r}")
                language = languages.get(f"{set_code}/{collector}".casefold())
                if language:
                    encoded_set = urllib.parse.quote(set_code.casefold(), safe="")
                    encoded_collector = urllib.parse.quote(collector, safe="")
                    encoded_language = urllib.parse.quote(language, safe="")
                    image_url = (
                        f"https://api.scryfall.com/cards/{encoded_set}/{encoded_collector}/"
                        f"{encoded_language}?format=image&version=large"
                    )
                if not image_url.startswith(("https://cards.scryfall.io/", "https://api.scryfall.com/")):
                    raise SyncError(f"{deck.get('name', 'Deck')}: unexpected image URL for {card.get('name')!r}")
                language_suffix = f"_{language}" if language else ""
                path = IMAGE_DIR / f"{set_code.lower()}_{collector}{language_suffix}.jpg"
                previous = sources.setdefault(path, image_url)
                if previous != image_url:
                    raise SyncError(f"Conflicting image URLs for {set_code.upper()} {collector}")
    return sources


def download_image(url: str, path: Path) -> bool:
    """Download one image atomically. Return False when already cached."""
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        url,
        headers={"Accept": "image/*", "User-Agent": "somebunny-deck-sync/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            content_type = response.headers.get_content_type()
            data = response.read()
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as error:
        raise SyncError(f"Could not download {url}: {error}") from error
    if not content_type.startswith("image/") or not data:
        raise SyncError(f"Invalid image response from {url}")

    file_descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(file_descriptor, "wb") as temporary_file:
            temporary_file.write(data)
        os.replace(temporary_name, path)
    except Exception:
        Path(temporary_name).unlink(missing_ok=True)
        raise
    return True


def write_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as temporary_file:
            temporary_file.write(content)
        os.replace(temporary_name, path)
    except Exception:
        Path(temporary_name).unlink(missing_ok=True)
        raise


def generate_artifacts(sources: list[DeckSource], *, include_mosaics: bool) -> None:
    for source in sources:
        decklist = REPO / "decks" / source.directory / "decklist.dck"
        commands = [
            [sys.executable, str(REPO / "scripts" / "dck_to_text.py"), "--write", str(decklist)],
            [sys.executable, str(REPO / "scripts" / "dck_to_moxfield.py"), "--write", "--no-scryfall", str(decklist)],
        ]
        if include_mosaics:
            commands.append([sys.executable, str(REPO / "scripts" / "generate_mosaic.py"), source.slug])
        for command in commands:
            try:
                subprocess.run(command, cwd=REPO, check=True)
            except subprocess.CalledProcessError as error:
                raise SyncError(f"Artifact generation failed for {source.slug}") from error


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--deck", metavar="SLUG", help="Sync only one configured deck")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and check without writing files")
    parser.add_argument(
        "--no-images",
        dest="images",
        action="store_false",
        help="Do not download DeckCheck's selected card images",
    )
    parser.add_argument(
        "--no-artifacts",
        dest="artifacts",
        action="store_false",
        help="Do not regenerate text exports and deck mosaics",
    )
    args = parser.parse_args(argv)

    try:
        sources = load_sources(args.config)
        if args.deck:
            sources = [source for source in sources if source.slug == args.deck]
            if not sources:
                raise SyncError(f"Unknown deck slug: {args.deck}")
        decks = {source.slug: fetch_deck(source) for source in sources}
        rendered = {key: render_dck(deck) for key, deck in decks.items()}
        languages = load_image_languages(args.config)
        images = image_sources(decks, languages) if args.images else {}
    except SyncError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2

    source_by_key = {source.slug: source for source in sources}
    for slug, content in sorted(rendered.items()):
        source = source_by_key[slug]
        output = REPO / "decks" / source.directory / "decklist.dck"
        if args.dry_run:
            print(f"Would write {output.relative_to(REPO)}")
        else:
            write_atomic(output, content)
            print(f"Wrote {output.relative_to(REPO)}")

    missing_images = [(path, url) for path, url in sorted(images.items()) if not path.exists()]
    if args.dry_run and args.images:
        print(f"Would download {len(missing_images)} images ({len(images)} selected printings)")
    elif args.images:
        downloaded = 0
        try:
            for index, (path, url) in enumerate(missing_images, start=1):
                if download_image(url, path):
                    downloaded += 1
                print(f"Downloaded image {index}/{len(missing_images)}: {path.name}")
        except SyncError as error:
            print(f"ERROR: {error}", file=sys.stderr)
            return 2
        print(f"Images: {downloaded} downloaded, {len(images) - downloaded} cached")

    if args.dry_run and args.artifacts:
        artifact_kinds = "text exports and mosaics" if args.images else "text exports"
        print(f"Would regenerate {artifact_kinds} for {len(sources)} decks")
    elif args.artifacts:
        try:
            generate_artifacts(sources, include_mosaics=args.images)
        except SyncError as error:
            print(f"ERROR: {error}", file=sys.stderr)
            return 2

    print("Sync complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())