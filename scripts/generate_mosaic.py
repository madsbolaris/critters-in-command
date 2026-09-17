#!/usr/bin/env python3
"""
Generate mosaic images for every party (host) in the repository.

Each host lives in its own folder under ``decks/`` and carries a ``party.toml``
manifest, one Forge decklist (``decklist.dck``), and a
``theme_analysis.md``. Card membership and counts come from the decklist; the
specific printing (and the host's "highlight" flag) comes from the theme file;
all metadata used for ordering — colors, types, and border style — is
fetched live from the Scryfall API, so no card ordering is hard-coded here.

Cards are laid out in a deterministic order:
  1. The commander first.
  2. Non-land spells, grouped by color identity — white first, then green, then
     any remaining color (blue/black/red); mono colors first, then guild pairs,
     then three-color sets, …, with colorless last — and within each color by
     mana value (ascending), then by card type (creature, artifact,
     enchantment, planeswalker, instant, sorcery).
  3. Lands, sorted the same way by color identity (colorless lands last).
  4. Borderless printings first, then normal printings, then old-frame
      printings, with white-bordered printings last regardless of card type.
      The commander remains the first card.

Printings are forced to paper: if the theme file points at a digital-only
(MTGO/Arena) printing, the script substitutes a paper printing instead.

Printings have a single source of truth: the Scryfall links in
``theme_analysis.md``. The mosaic resolves those to paper printings; pass
``--sync-dck`` to write the same printings back into the ``.dck`` so Forge and the
text/Moxfield exports stay in lockstep with the mosaic. Cards absent from the
theme file (e.g. basic lands) keep whatever printing the ``.dck`` already has.

Usage:
    python scripts/generate_mosaic.py                 # every host
    python scripts/generate_mosaic.py baylen          # one host
    python scripts/generate_mosaic.py baylen --sync-dck  # + rewrite .dck printings
"""

import sys
import re
import time
import json
import math
import tomllib
import urllib.parse
import urllib.request
from pathlib import Path
from PIL import Image

REPO_DIR = Path(__file__).parent.parent
DECKS_DIR = REPO_DIR / "decks"
CACHE_DIR = REPO_DIR / "card_images"
SCRYFALL_API = "https://api.scryfall.com"

# Scryfall asks for 50-100ms between requests
DELAY_BETWEEN_REQUESTS = 0.1

CARD_WIDTH = 488   # Scryfall "normal" size
CARD_HEIGHT = 680
PREVIEW_WIDTH = 1200

USER_AGENT = "DeckMosaic/1.0 (contact: deck-builder)"


# ---------------------------------------------------------------------------
# Ordering rules
# ---------------------------------------------------------------------------

# Colors are ranked white first, then green, then any remaining color (blue,
# black, red). Mono colors come first, then guild pairs, then three-color sets,
# and so on, with colorless last. This keeps every deck's mosaic reading
# white -> green -> other (e.g. Naya = W, G, R; Bant = W, G, U).
_COLOR_ORDER = "WGUBR"


def color_rank(colors):
    """Deterministic rank for a color set: ``(num_colors, color-order bitmask)``.

    Colorless sorts after every colored card. Fewer colors sort before more,
    and within the same count colors are ordered white, green, then the rest.
    """
    key = frozenset(c for c in colors if c in _COLOR_ORDER)
    if not key:
        return (len(_COLOR_ORDER) + 1, 0)  # colorless last
    bits = sum(1 << _COLOR_ORDER.index(c) for c in key)
    return (len(key), bits)


# Within a color group, spells are ordered by type.
_TYPE_PRIORITY = ["Creature", "Artifact", "Enchantment", "Planeswalker", "Instant", "Sorcery"]


def type_rank(type_line: str) -> int:
    for i, t in enumerate(_TYPE_PRIORITY):
        if t in type_line:
            return i
    return len(_TYPE_PRIORITY)


def front_face(card):
    faces = card.get("card_faces") or []
    return faces[0] if faces else card


def card_colors(card):
    """Return colors from the card or its front face for multiface layouts."""
    colors = card.get("colors")
    if colors is None:
        colors = front_face(card).get("colors", [])
    return colors


def is_land(card) -> bool:
    return "Land" in front_face(card).get("type_line", card.get("type_line", ""))


def color_group_rank(card) -> int:
    """Color rank by the card's colors (spells) or color identity (lands)."""
    if is_land(card):
        return color_rank(card.get("color_identity", []))
    return color_rank(card_colors(card))


def style_bucket(card) -> int:
    """Sort visually borderless treatments first, old frames late, and white borders last."""
    border_color = card.get("border_color", "black")
    frame_effects = set(card.get("frame_effects") or [])
    if (border_color == "borderless" or card.get("full_art")
            or frame_effects & {"showcase", "extendedart"}):
        return 0
    if border_color == "white":
        return 3
    if card.get("frame") in {"1993", "1997"}:
        return 2
    return 1


_WUBRG = set("WUBRG")
_BASIC_TYPES = ("plains", "island", "swamp", "mountain", "forest")


def land_bucket(card) -> int:
    """Granular layout rank for a land (lower sorts earlier in the mosaic).

    Lands read from single-color to three-plus colors, and within that from the
    weakest cycle to the strongest, keeping each named cycle together:

      0  basic lands
      10 colorless utility        15 mono-color utility     20 channel lands
      -- dual cycles, weakest -> strongest --
      30 reveal    31 dual tapland   32 check     34 fast    35 slow
      36 pathway   38 untapped dual  40 pain      42 horizon 44 filter  46 shock
      -- three-plus colors --
      60 tri-color 64 rainbow (life) 66 devotion  68 rainbow (premium)
      80 fetchlands

    """
    type_line = card.get("type_line", "")
    if "Basic" in type_line:
        return 0

    oracle = (card.get("oracle_text", "") or "").lower()
    produced = [c for c in (card.get("produced_mana") or []) if c in _WUBRG]
    n = len(produced)
    layout = card.get("layout", "")

    if "search your library" in oracle and "sacrifice this land" in oracle:
        return 80  # fetchlands
    if "channel" in oracle:
        return 20  # channel lands (Boseiju, Otawara, Eiganjo, Sokenzan)
    if "devotion" in oracle:
        return 66  # devotion lands (Nykthos)
    if "any color" in oracle or n >= 5:
        # rainbow / five-color fixing
        if "1 life" in oracle or "1 damage to you" in oracle:
            return 64  # rainbow with a life cost (City of Brass, Mana Confluence)
        return 68  # premium rainbow (Command Tower, Exotic Orchard, Reflecting Pool)
    if n == 3:
        return 60  # tri-color taplands / triomes

    if n == 2:
        # dual cycles, ordered weakest -> strongest
        if "you may pay 2 life" in oracle:
            return 46  # shock lands
        if layout == "modal_dfc":
            return 36  # pathway / modal dual-faced lands
        if "sacrifice this land: draw a card" in oracle:
            return 42  # horizon lands
        if re.search(r"add \{[wubrg]\}\{[wubrg]\}", oracle):
            return 44  # filter lands
        if "1 damage to you" in oracle:
            return 40  # pain lands
        if "two or fewer other lands" in oracle:
            return 34  # fast lands
        if "two or more other lands" in oracle:
            return 35  # slow lands
        if "you may reveal a" in oracle:
            return 30  # reveal lands
        if "unless you control a" in oracle and any(b in oracle for b in _BASIC_TYPES):
            return 32  # check lands
        if "enters tapped" in oracle and "unless" not in oracle:
            return 31  # unconditional dual taplands / gainlands
        return 38  # untapped dual with no drawback

    if n == 1:
        return 15  # mono-color utility lands
    return 10  # colorless utility lands


def make_sort_key(end_of_color_names, pinned_names=()):
    """Build a deterministic layout-order key bound to a host's config.

    Cards named in ``pinned_names`` are placed immediately after the commander,
    in the exact order they appear in that list.
    """
    end_of_color_names = {n.lower() for n in end_of_color_names}
    pin_index = {n.lower(): i for i, n in enumerate(pinned_names)}

    def sort_key(entry):
        card = entry["card"]
        if entry["is_commander"]:
            return (0,)

        border_bucket = style_bucket(card)

        name = card["name"].lower()
        # Match pins on either the resolved card name or the decklist name, so
        # double-faced cards (e.g. "Search for Azcanta") can be pinned by their
        # front-face name rather than the full "Front // Back" name.
        entry_name = entry["name"].lower()
        if name in pin_index or entry_name in pin_index:
            # Pinned cards sit right after the commander, in listed order.
            return (border_bucket, 0, pin_index.get(name, pin_index.get(entry_name)))

        if entry.get("is_attraction"):
            # The Attraction deck forms a trailing band at the very end.
            return (border_bucket, 4, name)

        highlight = 0 if entry["has_bunny"] else 1

        if is_land(card):
            # Lands: single -> triple colors, then weakest -> strongest cycle,
            # each named cycle kept together (see land_bucket). Colour rank
            # keeps each cycle ordered white -> green -> other.
                return (border_bucket, 2, land_bucket(card),
                    color_rank(card.get("color_identity", [])), highlight, name)

        # Non-land spells: by color, then mana value (ascending), then type.
        # Cards named in the host's `end_of_color` list sit at the end of their
        # color section instead of curving in with the rest (e.g. Baylen's
        # Hare Apparents).
        end_of_color = 1 if name in end_of_color_names else 0
        face = front_face(card)
        return (border_bucket, 1, color_rank(card_colors(card)), end_of_color,
            card.get("cmc", 0), type_rank(face.get("type_line", card["type_line"])),
                highlight, name)

    return sort_key


# ---------------------------------------------------------------------------
# Scryfall access
# ---------------------------------------------------------------------------

_json_cache: dict = {}


def _get_json(url: str):
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req) as resp:
        data = json.load(resp)
    time.sleep(DELAY_BETWEEN_REQUESTS)
    return data


def fetch_printing(set_code: str, collector: str):
    key = f"{set_code}/{collector}"
    if key not in _json_cache:
        s = urllib.parse.quote(str(set_code), safe="")
        c = urllib.parse.quote(str(collector), safe="")
        _json_cache[key] = _get_json(f"{SCRYFALL_API}/cards/{s}/{c}")
    return _json_cache[key]


def fetch_named(name: str):
    key = f"named:{name.lower()}"
    if key not in _json_cache:
        q = urllib.parse.urlencode({"exact": name})
        _json_cache[key] = _get_json(f"{SCRYFALL_API}/cards/named?{q}")
    return _json_cache[key]


def is_paper(card) -> bool:
    return "paper" in card.get("games", []) and not card.get("digital")


def ensure_paper(card):
    """If `card` is a digital-only printing, swap to a paper printing."""
    if is_paper(card):
        return card
    alt = fetch_named(card["name"])
    if is_paper(alt):
        print(f"    NOTE: {card['name']}: digital printing "
              f"{card['set']}/{card['collector_number']} -> paper "
              f"{alt['set']}/{alt['collector_number']}")
        return alt
    print(f"    WARNING: {card['name']}: no paper printing found "
          f"(keeping {card['set']}/{card['collector_number']})")
    return card


def image_language(card, languages: dict[str, str]) -> str | None:
    key = f"{card['set']}/{card['collector_number']}".casefold()
    return languages.get(key)


def image_cache_path(card, languages: dict[str, str]) -> Path:
    language = image_language(card, languages)
    suffix = f"_{language}" if language else ""
    return CACHE_DIR / f"{card['set']}_{card['collector_number']}{suffix}.jpg"


def image_url_for(card, languages: dict[str, str] | None = None) -> str:
    languages = languages or {}
    s = urllib.parse.quote(str(card["set"]), safe="")
    c = urllib.parse.quote(str(card["collector_number"]), safe="")
    language = image_language(card, languages)
    if language:
        lang = urllib.parse.quote(language, safe="")
        return f"{SCRYFALL_API}/cards/{s}/{c}/{lang}?format=image&version=large"
    return f"{SCRYFALL_API}/cards/{s}/{c}?format=image&version=normal"


def download_image(url: str, cache_path: Path) -> Path:
    """Download an image, using cache to avoid re-downloads."""
    if cache_path.exists():
        return cache_path
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "image/*",
    })
    with urllib.request.urlopen(req) as resp:
        data = resp.read()
    cache_path.write_bytes(data)
    time.sleep(DELAY_BETWEEN_REQUESTS)
    return cache_path


# ---------------------------------------------------------------------------
# Deck + theme parsing
# ---------------------------------------------------------------------------

def _norm(name: str) -> str:
    return name.strip().lower()


def parse_deck(dck_path: Path):
    """Return (commander_entry, main, attractions).

    Entries are ``(name, count, set_code, collector)`` tuples.
    The Attraction deck is a separate zone (not part of the 100), rendered last.
    """
    commander = None
    main = []
    attractions = []
    section = None
    for raw in dck_path.read_text().splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("["):
            section = line.strip("[]").lower()
            continue
        m = re.match(r"(\d+)\s+(.*)", line)
        if not m:
            continue
        count = int(m.group(1))
        fields = m.group(2).split("|")
        name = fields[0].strip()
        set_code = fields[1].strip().lower() if len(fields) > 1 else None
        collector = fields[2].strip().strip("[]") if len(fields) > 2 else None
        entry = (name, count, set_code, collector)
        if section == "commander":
            commander = entry
        elif section == "main":
            main.append(entry)
        elif section == "attractions":
            attractions.append(entry)
    return commander, main, attractions


def _split_row(line: str):
    """Split a Markdown table row into stripped cell values."""
    return [c.strip() for c in line.strip().strip("|").split("|")]


_SCRYFALL_LINK = re.compile(r"\[🔗\]\((https://scryfall\.com/card/[^)]+)\)")


def parse_theme(theme_file: Path, highlight_columns):
    """Map normalized card name -> (scryfall_page_url, is_highlighted).

    The theme file holds one or more Markdown tables. Columns are matched by
    header name, so different hosts can use different schemas as long as each
    table has a card-name column (first column), a column with a Scryfall
    ``[🔗](…)`` link, and (optionally) the highlight columns named in the host
    manifest. A card is highlighted when any highlight column holds a ✅.
    """
    content = theme_file.read_text()
    idx = content.find("## Sideboard")
    if idx != -1:
        content = content[:idx]

    highlight_set = {h.lower() for h in highlight_columns}
    info = {}
    header = None  # lowercased column names for the current table

    for raw in content.splitlines():
        line = raw.strip()
        if not line.startswith("|"):
            header = None
            continue
        cells = _split_row(line)
        if all(set(c) <= set("-: ") for c in cells):
            continue  # separator row (|---|---|)
        if header is None:
            header = [c.lower() for c in cells]
            continue
        row = dict(zip(header, cells))
        link = None
        for cell in cells:
            m = _SCRYFALL_LINK.search(cell)
            if m:
                link = m.group(1)
                break
        if not link:
            continue
        name = _norm(cells[0].split(" ×")[0])
        highlighted = any("✅" in row.get(col, "") for col in highlight_set)
        info[name] = (link, highlighted)
    return info


def _url_to_set_collector(url: str):
    parts = url.rstrip("/").split("/card/")[1].split("/")
    return parts[0], parts[1]


def resolve_card(name: str, set_code: str | None, collector: str | None, theme: dict):
    """Resolve a deck card to a paper Scryfall printing and its bunny flag."""
    key = _norm(name)
    has_bunny = theme.get(key, (None, False))[1]
    if set_code and collector:
        card = fetch_printing(set_code, collector)
    elif key in theme:
        url, _has_bunny = theme[key]
        set_code, collector = _url_to_set_collector(url)
        card = fetch_printing(set_code, collector)
    else:
        print(f"    WARNING: '{name}' not in theme analysis; using default printing")
        card = fetch_named(name)
    return ensure_paper(card), has_bunny


def build_entries(host_dir: Path, theme: dict, sort_key):
    """Build the ordered list of card entries for one host."""
    dck_path = host_dir / "decklist.dck"
    commander, main, attractions = parse_deck(dck_path)

    entries = []

    if commander:
        name, count, set_code, collector = commander
        card, has_bunny = resolve_card(name, set_code, collector, theme)
        entries.append({"name": name, "count": count, "card": card,
                        "has_bunny": has_bunny, "is_commander": True})

    for name, count, set_code, collector in main:
        card, has_bunny = resolve_card(name, set_code, collector, theme)
        entries.append({"name": name, "count": count, "card": card,
                        "has_bunny": has_bunny, "is_commander": False})

    for name, count, set_code, collector in attractions:
        card, has_bunny = resolve_card(name, set_code, collector, theme)
        entries.append({"name": name, "count": count, "card": card,
                        "has_bunny": has_bunny, "is_commander": False,
                        "is_attraction": True})

    entries.sort(key=sort_key)
    return entries


def validate_pinned(entries: list, pinned_names: list[str], slug: str) -> None:
    """Require an explicit order for every non-commander first-bucket card."""
    configured = [name.casefold() for name in pinned_names]
    if len(configured) != len(set(configured)):
        raise ValueError(f"{slug}: duplicate name in mosaic_order")

    actual = {
        entry["name"].casefold(): entry["name"]
        for entry in entries
        if not entry["is_commander"] and style_bucket(entry["card"]) == 0
    }
    missing = [actual[name] for name in actual.keys() - set(configured)]
    unknown = [name for name in pinned_names if name.casefold() not in actual]
    if missing or unknown:
        details = []
        if missing:
            details.append(f"unconfigured first-bucket cards: {sorted(missing)}")
        if unknown:
            details.append(f"configured cards not in first bucket: {unknown}")
        raise ValueError(f"{slug}: {'; '.join(details)}")


# ---------------------------------------------------------------------------
# Mosaic rendering
# ---------------------------------------------------------------------------

def create_mosaic(image_paths: list[Path], output: Path, cols: int = 10):
    """Combine card images into a grid mosaic."""
    images = []
    for p in image_paths:
        img = Image.open(p)
        # Resize to standard dimensions if needed
        if img.size != (CARD_WIDTH, CARD_HEIGHT):
            img = img.resize((CARD_WIDTH, CARD_HEIGHT), Image.LANCZOS)
        images.append(img)

    rows = math.ceil(len(images) / cols)
    mosaic_w = cols * CARD_WIDTH
    mosaic_h = rows * CARD_HEIGHT

    mosaic = Image.new("RGB", (mosaic_w, mosaic_h), (30, 30, 30))

    for i, img in enumerate(images):
        row = i // cols
        col = i % cols
        mosaic.paste(img, (col * CARD_WIDTH, row * CARD_HEIGHT))

    mosaic.save(output, "PNG", optimize=True)
    return mosaic_w, mosaic_h, rows, cols


def create_preview(mosaic_path: Path, preview_path: Path):
    """Create a web-friendly preview image from the full-resolution mosaic."""
    with Image.open(mosaic_path) as mosaic:
        preview_height = round(mosaic.height * (PREVIEW_WIDTH / mosaic.width))
        preview = mosaic.resize((PREVIEW_WIDTH, preview_height), Image.LANCZOS)
        preview.save(preview_path, "JPEG", quality=88, optimize=True)


def sync_dck_printings(host_dir: Path, entries: list, theme: dict) -> None:
    """Rewrite the ``.dck``'s ``|SET|[collector]`` to match the mosaic's resolved
    printings, keeping the decklist in lockstep with ``theme_analysis.md`` (the
    single source of truth for printings). Cards absent from the theme file
    (e.g. basic lands) keep their existing ``.dck`` printing.
    """
    dck_path = host_dir / "decklist.dck"
    resolved = {}
    for e in entries:
        if _norm(e["name"]) in theme:
            card = e["card"]
            resolved[_norm(e["name"])] = (str(card["set"]).upper(),
                                          str(card["collector_number"]))

    out = []
    section = None
    changes = 0
    for raw in dck_path.read_text().splitlines():
        stripped = raw.strip()
        if stripped.startswith("["):
            section = stripped.strip("[]").lower()
            out.append(raw)
            continue
        m = re.match(r"(\d+)\s+(.*)", stripped)
        if not m or section not in ("commander", "main", "attractions"):
            out.append(raw)
            continue
        count, rest = m.group(1), m.group(2)
        name = rest.split("|")[0].strip()
        hit = resolved.get(_norm(name))
        if not hit:
            out.append(raw)
            continue
        new_line = f"{count} {name}|{hit[0]}|[{hit[1]}]"
        if new_line != stripped:
            changes += 1
        out.append(new_line)

    dck_path.write_text("\n".join(out) + "\n")
    print(f"  Synced {dck_path.name}: {changes} printing(s) updated from theme_analysis.md")


def generate_variant(host: dict, sync_dck: bool = False):
    """Generate a mosaic for a single host."""
    host_dir = host["dir"]
    mosaic_cfg = host["config"].get("mosaic", {})
    highlight_columns = mosaic_cfg.get("highlight_columns", [])
    end_of_color = mosaic_cfg.get("end_of_color", [])
    pinned = mosaic_cfg.get("pinned", [])
    image_languages = host["config"].get("image_language", {})

    output_file = host_dir / "deck_mosaic.png"
    preview_file = host_dir / "deck_mosaic_preview.jpg"

    label = host["slug"]
    print(f"\n{'='*60}")
    print(f"Generating {label} mosaic...")
    print(f"{'='*60}")

    theme_file = host_theme_file(host)
    if theme_file is None:
        print(f"  WARNING: no theme_analysis.md in {host_dir}; "
              "using default printings")
        theme = {}
    else:
        theme = parse_theme(theme_file, highlight_columns)

    sort_key = make_sort_key(end_of_color, pinned)

    print("Resolving cards from decklist + theme analysis (via Scryfall)...")
    entries = build_entries(host_dir, theme, sort_key)
    validate_pinned(entries, pinned, host["slug"])
    total = sum(e["count"] for e in entries)
    bunny_count = sum(e["count"] for e in entries if e["has_bunny"])
    print(f"Found {total} cards ({bunny_count} highlighted)")

    CACHE_DIR.mkdir(exist_ok=True)

    image_paths: list[Path] = []
    for i, e in enumerate(entries):
        card = e["card"]
        cache_path = image_cache_path(card, image_languages)
        status = "cached" if cache_path.exists() else "downloading"
        bunny_marker = " 🐰" if e["has_bunny"] else ""
        copies = f" ×{e['count']}" if e["count"] > 1 else ""
        print(f"  [{i+1}/{len(entries)}] {e['name']}{copies} ({status}){bunny_marker}")
        try:
            download_image(image_url_for(card, image_languages), cache_path)
        except Exception as exc:
            print(f"    ERROR: {exc}")
            continue
        image_paths.extend([cache_path] * e["count"])

    print(f"\nAssembling mosaic from {len(image_paths)} images...")
    w, h, rows, cols = create_mosaic(image_paths, output_file, cols=10)
    create_preview(output_file, preview_file)
    print(f"Done! {label} mosaic: {w}x{h} ({cols} cols × {rows} rows)")
    print(f"Saved to: {output_file}")
    print(f"Saved preview to: {preview_file}")

    if sync_dck:
        sync_dck_printings(host_dir, entries, theme)


def load_hosts() -> dict:
    """Load every deck directory configured in ``deckcheck.toml``."""
    hosts = {}
    with (REPO_DIR / "deckcheck.toml").open("rb") as config_file:
        deckcheck = tomllib.load(config_file)
    mosaic_order = deckcheck.get("mosaic_order", {})
    image_languages = deckcheck.get("image_language", {})
    for slug, relative_path in sorted(deckcheck.get("paths", {}).items()):
        host_dir = DECKS_DIR / relative_path
        manifest = host_dir / "party.toml"
        if manifest.exists():
            with manifest.open("rb") as manifest_file:
                config = tomllib.load(manifest_file)
        else:
            config = {}
        config.setdefault("mosaic", {})["pinned"] = list(mosaic_order.get(slug, []))
        config["image_language"] = image_languages
        hosts[slug] = {"slug": slug, "dir": host_dir, "config": config}
    return hosts


def host_theme_file(host: dict):
    for name in ("theme_analysis.md", "THEME_ANALYSIS.md"):
        candidate = host["dir"] / name
        if candidate.exists():
            return candidate
    return None


def main():
    hosts = load_hosts()
    if not hosts:
        print(f"No deck paths configured in {REPO_DIR / 'deckcheck.toml'}.")
        sys.exit(1)

    args = sys.argv[1:]
    sync_dck = "--sync-dck" in args
    args = [a for a in args if not a.startswith("--")]
    host_arg = args[0].lower() if len(args) >= 1 else None

    if host_arg and host_arg not in hosts:
        print(f"Unknown host '{host_arg}'. Available: {', '.join(sorted(hosts))}.")
        sys.exit(1)

    selected = [hosts[host_arg]] if host_arg else [hosts[h] for h in sorted(hosts)]

    for host in selected:
        generate_variant(host, sync_dck=sync_dck)


if __name__ == "__main__":
    main()
