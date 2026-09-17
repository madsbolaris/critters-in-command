#!/usr/bin/env python3
"""
Build a cross-deck **shopping list** (``SHOPPING_LIST.md``) for every card in the
three decks.

What it does:

1. **Dedupe printings across decks.** Cards are grouped by *(name, set,
   collector)*. If the same printing is used in more than one deck, it becomes a
   single line with the copies summed. It also reports how many times each card
   appears across all three decks.
2. **Warn on split printings.** If a card is used with *different* printings in
   different decks (some of these are deliberate), it's listed in a "mismatch"
   section for review.
3. **Cheapest same-art price.** For the printing you picked, it finds every other
   printing of that card that shows the **same artwork**, then takes the cheapest
   USD price among them. "Same artwork" is decided by Scryfall's
   ``illustration_id`` and *verified with a dHash perceptual visual diff on the
   art crop* — the art crop excludes the set symbol, collector number, artist
   line, and other bottom badges/text, so only the picture is compared.
4. **Sorted high -> low by line cost** and written to Markdown.

Usage:
    python scripts/shopping_list.py            # writes SHOPPING_LIST.md
    python scripts/shopping_list.py --stdout   # print to stdout instead
"""

import argparse
import json
import re
import shutil
import sys
import time
import tomllib
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

from PIL import Image

REPO = Path(__file__).parent.parent
DECKS = ["baylen", "bumbleflower", "finneas"]
with (REPO / "deckcheck.toml").open("rb") as config_file:
    DECKCHECK = tomllib.load(config_file)
DECK_PATHS = DECKCHECK.get("paths", {})
MOSAIC_ORDER = DECKCHECK.get("mosaic_order", {})
API = "https://api.scryfall.com"
UA = "SomebunnyShoppingList/1.0 (personal deck tooling)"
HEADERS = {"User-Agent": UA, "Accept": "application/json"}
ARTCACHE = REPO / "card_images" / "_artcrop_cache"
CACHE_DIR = REPO / "scripts" / ".cache"
BULK_FILE = CACHE_DIR / "scryfall_default_cards.json"
BULK_MAX_AGE = 24 * 3600  # refresh bulk data if older than a day
DELAY = 0.15  # be polite to Scryfall
BASICS = {"forest", "plains", "island", "swamp", "mountain", "wastes"}
DHASH_THRESHOLD = 14  # max Hamming distance to still count as "same picture"
# Printings that share the artwork but aren't real, buyable, playable cards:
# World Championship gold-border decks, Collectors'/International Edition, 30th
# Anniversary Edition, etc. (all Scryfall set_type "memorabilia"), plus oversized.
EXCLUDE_SET_TYPES = {"memorabilia"}
# Buy/proxy policy (based on the cheapest same-art unit price):
#   unit <= PROXY_THRESHOLD    -> buy every copy for real
#   unit  > PROXY_THRESHOLD    -> buy one real, proxy the rest
#   unit  > STORAGE_THRESHOLD  -> buy one real for storage, proxy EVERY deck copy
PROXY_THRESHOLD = 10.0
STORAGE_THRESHOLD = 100.0


# ---------------------------------------------------------------------------
# Deck parsing
# ---------------------------------------------------------------------------
def parse_deck(host):
    """Return [(name, set, collector, qty), ...] for commander+main."""
    path = REPO / "decks" / DECK_PATHS[host] / "decklist.dck"
    section = None
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        head = re.match(r"^\[([^\]]+)\]", line)
        if head:
            section = head.group(1).lower()
            continue
        if section not in ("commander", "main"):
            continue
        m = re.match(r"^(\d+)\s+(.+)$", line.rstrip("\n"))
        if not m:
            continue
        qty = int(m.group(1))
        parts = m.group(2).split("|")
        name = parts[0].strip()
        setc = parts[1].strip().lower() if len(parts) > 1 and parts[1].strip() else None
        col = parts[2].strip("[]").strip() if len(parts) > 2 and parts[2].strip() else None
        rows.append((name, setc, col, qty))
    return rows


# ---------------------------------------------------------------------------
# Scryfall access — bulk data (no per-card rate limiting) + cached art crops
# ---------------------------------------------------------------------------
def _http(url, headers=None, timeout=60):
    req = urllib.request.Request(url, headers=headers or HEADERS)
    backoff = 1.0
    for attempt in range(6):
        try:
            return urllib.request.urlopen(req, timeout=timeout)
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and attempt < 5:
                time.sleep(backoff)
                backoff = min(backoff * 2, 16)
                continue
            raise


def load_bulk_cards():
    """Download (cached) Scryfall's `default_cards` bulk file and return all printings."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    fresh = BULK_FILE.exists() and (time.time() - BULK_FILE.stat().st_mtime) < BULK_MAX_AGE
    if not fresh:
        with _http(f"{API}/bulk-data") as resp:
            meta = json.load(resp)
        uri = next(b["download_uri"] for b in meta["data"] if b["type"] == "default_cards")
        print("Downloading Scryfall bulk `default_cards` (~150 MB, cached for 24h)...", file=sys.stderr)
        tmp = BULK_FILE.with_suffix(".tmp")
        with _http(uri, headers={"User-Agent": UA}, timeout=600) as resp, open(tmp, "wb") as f:
            shutil.copyfileobj(resp, f)
        tmp.replace(BULK_FILE)
    with open(BULK_FILE, encoding="utf-8") as f:
        return json.load(f)


# built by build_indexes()
BY_SETCOL = {}
BY_ORACLE = {}
BY_NAME = {}


def build_indexes(cards):
    for c in cards:
        setc = (c.get("set") or "").lower()
        col = str(c.get("collector_number") or "").lower()
        BY_SETCOL[(setc, col)] = c
        oid = c.get("oracle_id")
        if oid:
            BY_ORACLE.setdefault(oid, []).append(c)
        BY_NAME.setdefault((c.get("name") or "").lower(), c)


def fetch_printing(setc, col, name):
    """Resolve the exact printing the deck picked from bulk data, with fallbacks."""
    if setc and col:
        c = BY_SETCOL.get((setc.lower(), col.lower()))
        if c:
            return c
    c = BY_NAME.get((name or "").lower())
    if c:
        return c
    # split/adventure/DFC front-face name fallback
    key = (name or "").split(" //")[0].strip().lower()
    return BY_NAME.get(key)


def all_prints(card):
    oid = card.get("oracle_id")
    if oid and oid in BY_ORACLE:
        return BY_ORACLE[oid]
    return [card]


# ---------------------------------------------------------------------------
# Same-art detection: illustration_id + dHash visual diff on the art crop
# ---------------------------------------------------------------------------
def face_illustration(card):
    if card.get("illustration_id"):
        return card["illustration_id"]
    for f in card.get("card_faces", []) or []:
        if f.get("illustration_id"):
            return f["illustration_id"]
    return None


def art_crop_uri(card):
    iu = card.get("image_uris") or {}
    if iu.get("art_crop"):
        return iu["art_crop"]
    for f in card.get("card_faces", []) or []:
        fiu = f.get("image_uris") or {}
        if fiu.get("art_crop"):
            return fiu["art_crop"]
    return None


def _dhash(img, size=8):
    """64-bit difference hash of a (grayscale) image."""
    img = img.convert("L").resize((size + 1, size), Image.LANCZOS)
    px = list(img.getdata())
    w = size + 1
    bits = 0
    for row in range(size):
        for col in range(size):
            left = px[row * w + col]
            right = px[row * w + col + 1]
            bits = (bits << 1) | (1 if left > right else 0)
    return bits


def hamming(a, b):
    return bin(a ^ b).count("1")


def art_dhash(card):
    """Download (cached) the art crop and return its dHash, or None."""
    uri = art_crop_uri(card)
    if not uri:
        return None
    ARTCACHE.mkdir(parents=True, exist_ok=True)
    key = f"{card.get('set')}_{card.get('collector_number')}".replace("/", "_").replace("*", "")
    fp = ARTCACHE / f"{key}.jpg"
    if not fp.exists():
        try:
            with _http(uri, headers={"User-Agent": UA, "Accept": "image/*"}) as r:
                fp.write_bytes(r.read())
            time.sleep(DELAY)
        except Exception:
            return None
    try:
        with Image.open(fp) as img:
            return _dhash(img)
    except Exception:
        return None


def print_price(p):
    """Cheapest available (price, finish) for a single printing, or None."""
    prices = p.get("prices") or {}
    cands = []
    for key, finish in (("usd", "nonfoil"), ("usd_foil", "foil"), ("usd_etched", "etched")):
        v = prices.get(key)
        if v is not None:
            try:
                cands.append((float(v), finish))
            except ValueError:
                pass
    return min(cands) if cands else None


def finish_price(p, mode):
    """(price, finish) for a printing restricted to a finish preference, or None.

    mode="nonfoil" -> only the non-foil price.
    mode="foil"    -> foil (or etched) price only.
    """
    prices = p.get("prices") or {}

    def val(key):
        v = prices.get(key)
        try:
            return float(v) if v is not None else None
        except ValueError:
            return None

    if mode == "nonfoil":
        v = val("usd")
        return (v, "nonfoil") if v is not None else None
    # foil-preferred (for the commander + pinned foils)
    for key, finish in (("usd_foil", "foil"), ("usd_etched", "etched")):
        v = val(key)
        if v is not None:
            return (v, finish)
    return None


def cheapest_same_art(chosen, mode="nonfoil"):
    """
    Cheapest printing that shows the same artwork as `chosen`, verified by a
    perceptual visual diff on the art crop. `mode` picks the preferred finish
    ("nonfoil" for most cards, "foil" for the commander + pinned foils). If no
    printing of the same art exists in the preferred finish, falls back to the
    cheapest of any finish and sets `fallback=True`.
    """
    ill = face_illustration(chosen)
    base_hash = art_dhash(chosen)
    prints = all_prints(chosen)

    group = []
    for p in prints:
        if p.get("digital") or "paper" not in (p.get("games") or []):
            continue
        if p.get("set_type") in EXCLUDE_SET_TYPES or p.get("oversized"):
            continue
        if ill and face_illustration(p) != ill:
            continue
        # visual-diff verification (art crop -> excludes badges/bottom text)
        if base_hash is not None:
            h = art_dhash(p)
            if h is not None and hamming(base_hash, h) > DHASH_THRESHOLD:
                continue
        group.append(p)
    if not group:
        group = [chosen]

    def pick(price_fn):
        best = None
        for p in group:
            pp = price_fn(p)
            if pp is None:
                continue
            price, finish = pp
            if best is None or price < best["price"]:
                best = {
                    "price": price,
                    "finish": finish,
                    "set": p.get("set", "").upper(),
                    "collector": p.get("collector_number", ""),
                    "n_same_art": len(group),
                }
        return best

    best = pick(lambda p: finish_price(p, mode))
    fallback = False
    if best is None:
        best = pick(print_price)  # nothing in the preferred finish -> any finish
        fallback = True
    if best is not None:
        best["fallback"] = fallback
    return best


def load_exempt():
    """Per-deck cards kept as foil: the commander + the pinned trio (from party.toml)."""
    exempt = {}
    for host in DECKS:
        names = set()
        try:
            manifest = REPO / "decks" / DECK_PATHS[host] / "party.toml"
            data = tomllib.loads(manifest.read_text(encoding="utf-8"))
            if data.get("commander"):
                names.add(data["commander"])
            names.update(MOSAIC_ORDER.get(host, []))
            names.update(data.get("extra_foils", []))
        except Exception as exc:
            print(f"  warning: could not read {host} party.toml: {exc}", file=sys.stderr)
        exempt[host] = names
    return exempt


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def money(x):
    return f"${x:,.2f}" if x is not None else "—"


def allocate(unit, deck_qtys):
    """
    Decide how many real cards to buy vs. proxy, given the cheapest unit price and
    how many copies each deck needs. Returns
    (real_count, proxy_count, home, per_deck_real, per_deck_proxy) where `home` is
    None (all real), a deck name (the single real lives there), or "storage".
    """
    copies = sum(deck_qtys.values())
    per_real = {d: 0 for d in deck_qtys}
    per_proxy = {d: 0 for d in deck_qtys}

    if unit <= PROXY_THRESHOLD:
        # cheap enough to own every copy for real, homed in its own deck(s)
        for d, q in deck_qtys.items():
            per_real[d] = q
        return copies, 0, None, per_real, per_proxy

    if unit <= STORAGE_THRESHOLD:
        # one real card, homed in the first deck (by priority) that uses it
        home = next(d for d in DECKS if d in deck_qtys)
        for d, q in deck_qtys.items():
            if d == home:
                per_real[d] = 1
                per_proxy[d] = q - 1
            else:
                per_proxy[d] = q
        return 1, copies - 1, home, per_real, per_proxy

    # too expensive to play: one real for storage, proxy every deck copy
    for d, q in deck_qtys.items():
        per_proxy[d] = q
    return 1, copies, "storage", per_real, per_proxy


def main():
    ap = argparse.ArgumentParser(description="Cross-deck shopping list.")
    ap.add_argument("--stdout", action="store_true", help="Print instead of writing the file.")
    args = ap.parse_args()

    build_indexes(load_bulk_cards())

    # collect deck usage: name -> {(set,col): {qty, decks:{deck:qty}}}
    cards = {}
    for host in DECKS:
        for name, setc, col, qty in parse_deck(host):
            if name.lower() in BASICS:
                continue
            entry = cards.setdefault(name, {})
            key = (setc, col)
            slot = entry.setdefault(key, {"qty": 0, "decks": {}})
            slot["qty"] += qty
            slot["decks"][host] = slot["decks"].get(host, 0) + qty

    print(f"Pricing {len(cards)} unique cards from Scryfall...", file=sys.stderr)

    exempt_by_deck = load_exempt()  # cards kept foil per deck (commander + pinned)

    lines = []          # priced shopping lines
    unpriced = []       # (name, set, col, qty)
    mismatches = []     # (name, {deck:(set,col)})

    deck_real = {d: 0 for d in DECKS}    # real cards homed in each deck
    deck_proxy = {d: 0 for d in DECKS}   # proxies each deck needs
    storage_reals = 0                    # >$100 reals kept in storage (proxied in decks)

    for i, (name, printings) in enumerate(sorted(cards.items()), 1):
        # split-printing warning
        if len(printings) > 1:
            per_deck = {}
            for (setc, col), slot in printings.items():
                for dk in slot["decks"]:
                    per_deck[dk] = f"{(setc or '?').upper()} {col or '?'}"
            mismatches.append((name, per_deck))

        for (setc, col), slot in printings.items():
            print(f"  [{i}/{len(cards)}] {name} ({(setc or '?').upper()} {col or '?'})", file=sys.stderr)
            try:
                chosen = fetch_printing(setc, col, name) if setc and col else fetch_printing(None, None, name)
            except Exception as exc:
                print(f"    lookup failed: {exc}", file=sys.stderr)
                chosen = None
            if not chosen:
                print(f"    not found on Scryfall", file=sys.stderr)
                unpriced.append((name, setc, col, slot["qty"]))
                continue
            # keep foil for the commander + pinned trio of any deck that runs this card
            exempt = any(name in exempt_by_deck.get(d, set()) for d in slot["decks"])
            cheap = cheapest_same_art(chosen, mode="foil" if exempt else "nonfoil")
            picked_set = (chosen.get("set") or setc or "?").upper()
            picked_col = chosen.get("collector_number") or col or "?"
            if cheap is None:
                unpriced.append((name, picked_set, picked_col, slot["qty"]))
                continue

            unit = cheap["price"]
            deck_qtys = dict(slot["decks"])
            real_count, proxy_count, home, per_real, per_proxy = allocate(unit, deck_qtys)
            for d in DECKS:
                deck_real[d] += per_real.get(d, 0)
                deck_proxy[d] += per_proxy.get(d, 0)
            if home == "storage":
                storage_reals += 1

            decks_str = ", ".join(f"{d}×{q}" if q > 1 else d for d, q in sorted(slot["decks"].items()))
            lines.append({
                "name": name,
                "picked_set": picked_set,
                "picked_col": picked_col,
                "qty": slot["qty"],
                "decks": decks_str,
                "cheap": cheap,
                "unit": unit,
                "real_count": real_count,
                "proxy_count": proxy_count,
                "home": home,
                "line": unit * real_count,
                "exempt": exempt,
                "nonfoil_missing": (not exempt) and cheap.get("fallback", False),
            })

    lines.sort(key=lambda r: (r["line"], r["unit"]), reverse=True)

    grand_spend = sum(r["line"] for r in lines)
    total_proxies = sum(deck_proxy.values())
    total_reals = sum(deck_real.values()) + storage_reals
    total_copies_all = sum(sum(s["qty"] for s in p.values()) for p in cards.values())
    no_nonfoil = [r for r in lines if r["nonfoil_missing"]]
    foil_exempt = [r for r in lines if r["exempt"]]

    def deck_label(h):
        if h is None:
            return "—"
        if h == "storage":
            return "📦 storage"
        return h.capitalize()

    # ---- render markdown ----
    out = []
    out.append("# 🛒 Shopping List — Somebunny Is Having a Party\n")
    out.append(
        f"_Generated {date.today().isoformat()} · prices: [Scryfall](https://scryfall.com) USD, "
        f"cheapest **real, buyable** printing whose **artwork matches** the one picked in each deck "
        f"(Scryfall `illustration_id` verified with a dHash visual diff on the art crop, which excludes "
        f"set symbols, collector numbers, and bottom text; World Championship / Collectors' Edition / "
        f"30th Anniversary memorabilia are excluded)._\n"
    )
    out.append(
        "**Buy/proxy rules:** cards **≤ $10** → buy every copy for real; cards **> $10** → buy **one** "
        "real and proxy the rest; cards **> $100** → buy one real for **storage** and proxy **every** deck "
        f"copy. Between $10–$100 the single real card is homed in the first deck that uses it "
        f"(priority: {' → '.join(d.capitalize() for d in DECKS)}).\n"
    )
    out.append(
        f"**Totals:** buy **{total_reals} real cards** for **{money(grand_spend)}**, print "
        f"**{total_proxies} proxies** · {total_copies_all} total copies across all decks · "
        f"{len(lines)} priced buy-lines.\n"
    )
    out.append(
        "**Finish:** everything is bought **nonfoil** except each deck's **commander**, its **3 "
        "pinned foils**, and any **extra cards marked foil** (all shown with 📌), which stay foil. A ⚠️ "
        "marks a non-exempt card that has **no nonfoil printing of the picked artwork**, so it stays "
        "foil unless you change its art.\n"
    )

    out.append("## 🖨️ Real vs. proxy per deck\n")
    out.append("| Deck | Real cards | Proxies |")
    out.append("|------|-----------:|--------:|")
    for d in DECKS:
        out.append(f"| {d.capitalize()} | {deck_real[d]} | **{deck_proxy[d]}** |")
    out.append(f"| 📦 Storage (not played) | {storage_reals} | — |")
    out.append(f"| **All decks** | **{total_reals}** | **{total_proxies}** |")
    out.append("")

    if mismatches:
        out.append("## ⚠️ Different printings across decks (confirm intentional)\n")
        out.append("| Card | Baylen | Bumbleflower | Finneas |")
        out.append("|------|--------|--------------|---------|")
        for name, per_deck in sorted(mismatches):
            row = " | ".join(per_deck.get(d, "—") for d in DECKS)
            out.append(f"| {name} | {row} |")
        out.append("")

    out.append("## List (highest cost first)\n")
    out.append("| # | Card | Copies | Real | Proxies | Unit | Real cost | Real home | Buy — cheapest same-art | In decks |")
    out.append("|--:|------|-------:|-----:|--------:|-----:|----------:|-----------|-------------------------|----------|")
    for n, r in enumerate(lines, 1):
        c = r["cheap"]
        finish = c["finish"]
        if r["exempt"]:
            finish += ", 📌"
        elif r["nonfoil_missing"]:
            finish += ", ⚠️ no nonfoil"
        buy = f"{c['set']} {c['collector']} ({finish})"
        if (c["set"], str(c["collector"])) == (r["picked_set"], str(r["picked_col"])):
            buy += " *(as picked)*"
        elif c["n_same_art"] > 1:
            buy += f" *(of {c['n_same_art']})*"
        proxies = f"**{r['proxy_count']}**" if r["proxy_count"] else "0"
        out.append(
            f"| {n} | {r['name']} | {r['qty']} | {r['real_count']} | {proxies} | "
            f"{money(r['unit'])} | {money(r['line'])} | {deck_label(r['home'])} | {buy} | {r['decks']} |"
        )
    out.append("")

    # ---- proxy print list (only cards that need proxies) ----
    proxy_lines = [r for r in lines if r["proxy_count"] > 0]
    total_proxy_units = sum(r["proxy_count"] for r in proxy_lines)
    out.append("## 🖨️ Proxy print list (cards needing proxies)\n")
    out.append(
        f"_{len(proxy_lines)} cards · {total_proxy_units} proxies to print._\n"
    )
    out.append("| # | Card | Proxies | Print (art to use) | Unit | In decks |")
    out.append("|--:|------|--------:|--------------------|-----:|----------|")
    for n, r in enumerate(sorted(proxy_lines, key=lambda x: x["proxy_count"], reverse=True), 1):
        c = r["cheap"]
        art = f"{r['picked_set']} {r['picked_col']}"
        out.append(
            f"| {n} | {r['name']} | **{r['proxy_count']}** | {art} | "
            f"{money(r['unit'])} | {r['decks']} |"
        )
    out.append("")

    if no_nonfoil:
        out.append("## ⚠️ No nonfoil for the picked art (stays foil)\n")
        out.append(
            "_These non-exempt cards have no nonfoil printing that shares the picked artwork, so they "
            "remain foil. Pick a different printing/art if you want them nonfoil._\n"
        )
        out.append("| Card | Foil print | Unit | In decks |")
        out.append("|------|------------|-----:|----------|")
        for r in sorted(no_nonfoil, key=lambda x: x["unit"], reverse=True):
            c = r["cheap"]
            out.append(f"| {r['name']} | {c['set']} {c['collector']} | {money(r['unit'])} | {r['decks']} |")
        out.append("")

    if foil_exempt:
        out.append("## 📌 Foils kept (commander + pinned trio)\n")
        out.append("| Card | Foil print | Unit | In decks |")
        out.append("|------|------------|-----:|----------|")
        for r in sorted(foil_exempt, key=lambda x: x["unit"], reverse=True):
            c = r["cheap"]
            out.append(f"| {r['name']} | {c['set']} {c['collector']} | {money(r['unit'])} | {r['decks']} |")
        out.append("")

    if unpriced:
        out.append("## No price found (check manually)\n")
        for name, setc, col, qty in sorted(unpriced):
            out.append(f"- {name} ({(setc or '?')} {col or '?'}) ×{qty}")
        out.append("")

    text = "\n".join(out) + "\n"
    if args.stdout:
        sys.stdout.write(text)
    else:
        dest = REPO / "SHOPPING_LIST.md"
        dest.write_text(text, encoding="utf-8")
        print(f"Wrote {dest}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
