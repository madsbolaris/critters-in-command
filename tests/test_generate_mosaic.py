import importlib.util
import sys
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "generate_mosaic.py"
SPEC = importlib.util.spec_from_file_location("generate_mosaic", SCRIPT)
generate_mosaic = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = generate_mosaic
SPEC.loader.exec_module(generate_mosaic)


def entry(name, *, border="black", frame="2015", frame_effects=None,
          full_art=False, colors=None, type_line="Artifact", commander=False):
    return {
        "name": name,
        "count": 1,
        "has_bunny": False,
        "is_commander": commander,
        "card": {
            "name": name,
            "border_color": border,
            "frame": frame,
            "frame_effects": frame_effects,
            "full_art": full_art,
            "colors": colors or [],
            "color_identity": colors or [],
            "cmc": 1,
            "type_line": type_line,
        },
    }


class MosaicSortTests(unittest.TestCase):
    def test_language_override_uses_distinct_cache_file(self):
        card = {"set": "lci", "collector_number": "324"}
        languages = {"lci/324": "ja"}
        self.assertEqual(
            generate_mosaic.image_cache_path(card, languages).name,
            "lci_324_ja.jpg",
        )
        self.assertIn("/lci/324/ja?", generate_mosaic.image_url_for(card, languages))

    def test_transform_card_uses_front_face_colors(self):
        card = {
            "name": "Etali, Primal Conqueror // Etali, Primal Sickness",
            "card_faces": [
                {"name": "Etali, Primal Conqueror", "colors": ["R"]},
                {"name": "Etali, Primal Sickness", "colors": ["B", "G", "R"]},
            ],
        }
        self.assertEqual(generate_mosaic.card_colors(card), ["R"])

    def test_borderless_first_and_any_white_border_last(self):
        entries = [
            entry("Commander", commander=True),
            entry("Normal Creature", colors=["R"], type_line="Creature"),
            entry("White Artifact", border="white"),
            entry("Old Sorcery", frame="1993", colors=["U"], type_line="Sorcery"),
            entry("Old Land", frame="1997", type_line="Land"),
            entry("Borderless Land", border="borderless", type_line="Land"),
            entry("Showcase Creature", frame_effects=["showcase"], colors=["G"], type_line="Creature"),
            entry("Extended Art", frame_effects=["extendedart"]),
            entry("Full Art Land", full_art=True, type_line="Land"),
            entry("Old White Sorcery", border="white", frame="1993", colors=["R"], type_line="Sorcery"),
            entry("Borderless Creature", border="borderless", colors=["G"], type_line="Creature"),
        ]
        entries.sort(key=generate_mosaic.make_sort_key([], []))
        self.assertEqual(
            [item["name"] for item in entries],
            [
                "Commander",
                "Borderless Creature",
                "Showcase Creature",
                "Extended Art",
                "Borderless Land",
                "Full Art Land",
                "Normal Creature",
                "Old Sorcery",
                "Old Land",
                "Old White Sorcery",
                "White Artifact",
            ],
        )

    def test_pinned_order_must_cover_every_first_bucket_card(self):
        entries = [
            entry("Commander", commander=True),
            entry("Featured One", border="borderless"),
            entry("Featured Two", frame_effects=["showcase"]),
            entry("Normal"),
        ]
        generate_mosaic.validate_pinned(
            entries, ["Featured Two", "Featured One"], "test"
        )
        with self.assertRaisesRegex(ValueError, "unconfigured first-bucket"):
            generate_mosaic.validate_pinned(entries, ["Featured One"], "test")


if __name__ == "__main__":
    unittest.main()