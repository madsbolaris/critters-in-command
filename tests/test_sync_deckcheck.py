import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "sync_deckcheck.py"
SPEC = importlib.util.spec_from_file_location("sync_deckcheck", SCRIPT)
sync_deckcheck = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = sync_deckcheck
SPEC.loader.exec_module(sync_deckcheck)


def entry(name, set_code, collector, scryfall_id, quantity=1, image_url=None):
    return {
        "quantity": quantity,
        "card": {
            "name": name,
            "setCode": set_code,
            "collectorNumber": collector,
            "scryfallId": scryfall_id,
            "imageUrl": image_url or f"https://cards.scryfall.io/large/front/{scryfall_id}.jpg",
        },
    }


def deck(name="Test Deck", forest_set="FDN", forest_collector="281", forest_id="forest-a"):
    return {
        "name": name,
        "format": "commander",
        "visibility": "public",
        "boards": {
            "commanders": {"cards": {"commander": entry("Test Commander", "TST", "1", "cmdr")}},
            "mainboard": {"cards": {"forest": entry("Forest", forest_set, forest_collector, forest_id, 99)}},
        },
    }


class SyncDeckcheckTests(unittest.TestCase):
    def test_manifest_maps_decks_to_grouped_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "deckcheck.toml"
            config.write_text(
                '[paths]\nbaylen = "Parties/Baylen - Warren"\ndumpster-dig = "Diving/Bello - Dig"\n'
                '[folders.b3]\nbaylen = "https://deckcheck.co/app/decklist/b3-id"\n'
                'dumpster-dig = "https://deckcheck.co/app/decklist/dig-id"\n',
                encoding="utf-8",
            )
            sources = sync_deckcheck.load_sources(config)
        self.assertEqual(
            [(source.bracket, source.slug, str(source.directory)) for source in sources],
            [
                ("b3", "baylen", "Parties/Baylen - Warren"),
                ("b3", "dumpster-dig", "Diving/Bello - Dig"),
            ],
        )

    def test_manifest_rejects_path_outside_decks(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "deckcheck.toml"
            config.write_text(
                '[paths]\nbaylen = "../outside"\n'
                '[folders.b3]\nbaylen = "https://deckcheck.co/app/decklist/b3-id"\n',
                encoding="utf-8",
            )
            with self.assertRaises(sync_deckcheck.SyncError):
                sync_deckcheck.load_sources(config)

    def test_render_dck_preserves_printing_and_quantity(self):
        output = sync_deckcheck.render_dck(deck())
        self.assertIn("1 Test Commander|TST|[1]", output)
        self.assertIn("99 Forest|FDN|[281]", output)

    def test_render_dck_uses_multiface_front_name_for_forge(self):
        payload = deck()
        card = payload["boards"]["mainboard"]["cards"]["forest"]["card"]
        card["name"] = "Front Room // Back Room"
        card["cardFaces"] = [{"name": "Front Room"}, {"name": "Back Room"}]
        output = sync_deckcheck.render_dck(payload)
        self.assertIn("99 Front Room|FDN|[281]", output)
        self.assertNotIn("Front Room // Back Room", output)

    def test_image_sources_deduplicate_shared_printings(self):
        decks = {("b3", "one"): deck(), ("b3", "two"): deck("Other Deck")}
        sources = sync_deckcheck.image_sources(decks)
        self.assertEqual(len(sources), 2)
        self.assertIn(sync_deckcheck.IMAGE_DIR / "fdn_281.jpg", sources)
        self.assertIn(sync_deckcheck.IMAGE_DIR / "tst_1.jpg", sources)

    def test_image_sources_use_front_face_for_double_faced_card(self):
        payload = deck()
        card = payload["boards"]["mainboard"]["cards"]["forest"]["card"]
        card["imageUrl"] = {
            "front": "https://cards.scryfall.io/large/front/forest.jpg",
            "back": "https://cards.scryfall.io/large/back/forest.jpg",
        }
        sources = sync_deckcheck.image_sources({("b3", "test"): payload})
        self.assertEqual(
            sources[sync_deckcheck.IMAGE_DIR / "fdn_281.jpg"],
            "https://cards.scryfall.io/large/front/forest.jpg",
        )

    def test_image_sources_use_language_specific_cache_and_url(self):
        sources = sync_deckcheck.image_sources(
            {("b3", "test"): deck()}, {"fdn/281": "ja"}
        )
        path = sync_deckcheck.IMAGE_DIR / "fdn_281_ja.jpg"
        self.assertIn(path, sources)
        self.assertEqual(
            sources[path],
            "https://api.scryfall.com/cards/fdn/281/ja?format=image&version=large",
        )

if __name__ == "__main__":
    unittest.main()