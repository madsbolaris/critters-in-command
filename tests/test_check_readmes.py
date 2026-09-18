import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "check_readmes.py"
SPEC = importlib.util.spec_from_file_location("check_readmes", SCRIPT)
check_readmes = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = check_readmes
SPEC.loader.exec_module(check_readmes)


DCK_TEXT = """[metadata]
Name=Test Deck
[Commander]
1 Test Commander|TST|[1]
[main]
1 Caretaker's Talent|BLB|[6]
1 The Great Henge|LTC|[348]
1 Forest|TRK|[325]
"""


def write_dck(directory: Path) -> Path:
    path = directory / "decklist.dck"
    path.write_text(DCK_TEXT, encoding="utf-8")
    return path


VALID_LAYOUT_README = (
    "# Test Commander\n"
    "\n"
    "| | |\n"
    "|---|---|\n"
    "| **Commander** | [Test Commander](https://scryfall.com/card/tst/1) |\n"
    "| **Colors** | Selesnya (White / Green) |\n"
    "| **Archetype** | Testing |\n"
    "| **Good against** | Nothing |\n"
    "| **Struggles against** | Everything |\n"
    "\n"
    "## Test Deck\n"
    "\n"
    "[Caretaker's Talent](https://scryfall.com/card/blb/6/caretakers-talent) is great.\n"
    "\n"
    "## The Deck\n"
    "\n"
    "![Deck mosaic](deck_mosaic_preview.jpg)\n"
    "\n"
    "## Deck Resources\n"
    "\n"
    "[Forge decklist](decklist.dck)\n"
)


class NormalizeNameTests(unittest.TestCase):
    def test_smart_quotes_fold_to_straight_quotes(self):
        self.assertEqual(
            check_readmes.normalize_name("Caretaker\u2019s Talent"),
            check_readmes.normalize_name("Caretaker's Talent"),
        )

    def test_whitespace_and_case_are_normalized(self):
        self.assertEqual(check_readmes.normalize_name("  Sol   Ring "), "sol ring")


class IsShortenedNameMatchTests(unittest.TestCase):
    def test_trailing_word_matches(self):
        self.assertTrue(check_readmes.is_shortened_name_match("Tutelage", "Teferi's Tutelage"))

    def test_leading_word_does_not_match(self):
        self.assertFalse(check_readmes.is_shortened_name_match("Teferi's", "Teferi's Tutelage"))

    def test_unrelated_word_does_not_match(self):
        self.assertFalse(check_readmes.is_shortened_name_match("Sphinx", "Teferi's Tutelage"))

    def test_full_name_matches(self):
        self.assertTrue(check_readmes.is_shortened_name_match("Teferi's Tutelage", "Teferi's Tutelage"))


class CharacterNameTests(unittest.TestCase):
    def test_splits_off_comma_epithet(self):
        self.assertEqual(check_readmes.character_name("Teferi, Time Raveler"), "Teferi")

    def test_no_comma_returns_full_name(self):
        self.assertEqual(check_readmes.character_name("Sol Ring"), "Sol Ring")


class IsCharacterNameMatchTests(unittest.TestCase):
    def test_leading_character_name_matches(self):
        self.assertTrue(check_readmes.is_character_name_match("Teferi", "Teferi, Time Raveler"))

    def test_trailing_epithet_does_not_match(self):
        self.assertFalse(check_readmes.is_character_name_match("Time Raveler", "Teferi, Time Raveler"))

    def test_names_without_a_comma_never_match(self):
        self.assertFalse(check_readmes.is_character_name_match("Sol", "Sol Ring"))


class IsFlavorNameMatchTests(unittest.TestCase):
    def test_known_flavor_name_matches(self):
        self.assertTrue(check_readmes.is_flavor_name_match("Cordyceps Rat King", "sld", "2205"))

    def test_case_and_set_code_are_case_insensitive(self):
        self.assertTrue(check_readmes.is_flavor_name_match("cordyceps rat king", "SLD", "2205"))

    def test_unknown_printing_does_not_match(self):
        self.assertFalse(check_readmes.is_flavor_name_match("Cordyceps Rat King", "blb", "348"))

    def test_oracle_name_is_not_a_flavor_name_match(self):
        self.assertFalse(check_readmes.is_flavor_name_match("Mycoloth", "sld", "2205"))


class ScryfallCardPrintingTests(unittest.TestCase):
    def test_parses_set_and_collector_number(self):
        self.assertEqual(
            check_readmes.scryfall_card_printing("https://scryfall.com/card/sld/2205/mycoloth"),
            ("sld", "2205"),
        )

    def test_non_card_path_returns_none(self):
        self.assertIsNone(check_readmes.scryfall_card_printing("https://scryfall.com/search?q=foo"))

    def test_non_scryfall_domain_returns_none(self):
        self.assertIsNone(check_readmes.scryfall_card_printing("https://example.com/card/sld/2205"))


class ParseDecklistTests(unittest.TestCase):
    def test_parses_names_and_printings(self):
        with tempfile.TemporaryDirectory() as directory:
            cards = check_readmes.parse_decklist(write_dck(Path(directory)))
        self.assertIn(check_readmes.normalize_name("Caretaker's Talent"), cards.by_name)
        self.assertEqual(cards.by_printing[("blb", "6")][0], "Caretaker's Talent")
        self.assertEqual(cards.by_printing[("ltc", "348")][0], "The Great Henge")

    def test_tracks_character_names_shared_across_cards(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "decklist.dck"
            path.write_text(
                "[metadata]\nName=Test Deck\n[main]\n"
                "1 Teferi, Time Raveler|WAR|[221]\n"
                "1 Teferi, Who Slows the Sunset|WOE|[400]\n",
                encoding="utf-8",
            )
            cards = check_readmes.parse_decklist(path)
        sharers = cards.character_names[check_readmes.normalize_name("Teferi")]
        self.assertEqual(sorted(sharers), ["Teferi, Time Raveler", "Teferi, Who Slows the Sunset"])

    def test_ignores_sections_outside_the_known_boards(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "decklist.dck"
            path.write_text("[metadata]\nName=Test Deck\n1 Ignored Line\n", encoding="utf-8")
            cards = check_readmes.parse_decklist(path)
        self.assertEqual(cards.by_name, {})


class FindUncoveredCardsTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.cards = check_readmes.parse_decklist(write_dck(Path(self._tmpdir.name)))

    def test_mentioned_cards_are_not_reported(self):
        text = "[Caretaker's Talent](https://scryfall.com/card/blb/6/caretakers-talent) keeps everyone fed."
        names = [name for name, _count in check_readmes.find_uncovered_cards(text, self.cards)]
        self.assertNotIn("Caretaker's Talent", names)

    def test_flavor_name_link_covers_the_underlying_card(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "decklist.dck"
            path.write_text("[metadata]\nName=Test Deck\n[main]\n1 Mycoloth|SLD|[2205]\n", encoding="utf-8")
            cards = check_readmes.parse_decklist(path)
        text = "The [Cordyceps Rat King](https://scryfall.com/card/sld/2205) arrives.\n"
        names = [name for name, _count in check_readmes.find_uncovered_cards(text, cards)]
        self.assertNotIn("Mycoloth", names)

    def test_unmentioned_nonland_cards_are_reported(self):
        names = [name for name, _count in check_readmes.find_uncovered_cards("No links here.", self.cards)]
        self.assertIn("The Great Henge", names)
        self.assertIn("Caretaker's Talent", names)

    def test_basic_lands_are_excluded(self):
        names = [name for name, _count in check_readmes.find_uncovered_cards("No links here.", self.cards)]
        self.assertNotIn("Forest", names)

    def test_smart_quote_mentions_still_count_as_covered(self):
        text = "[Caretaker\u2019s Talent](https://scryfall.com/card/blb/6/caretakers-talent) keeps everyone fed."
        names = [name for name, _count in check_readmes.find_uncovered_cards(text, self.cards)]
        self.assertNotIn("Caretaker's Talent", names)

    def test_defaults_to_zero_other_decks_without_global_counts(self):
        uncovered = dict(check_readmes.find_uncovered_cards("No links here.", self.cards))
        self.assertEqual(uncovered["The Great Henge"], 0)

    def test_sorted_fewest_other_decks_first(self):
        global_counts = {
            check_readmes.normalize_name("Caretaker's Talent"): 4,  # in 3 other decks
            check_readmes.normalize_name("The Great Henge"): 1,     # deck-unique
            check_readmes.normalize_name("Test Commander"): 4,      # in 3 other decks
        }
        uncovered = dict(check_readmes.find_uncovered_cards("No links here.", self.cards, global_counts))
        self.assertEqual(uncovered["The Great Henge"], 0)
        self.assertEqual(uncovered["Caretaker's Talent"], 3)
        names_in_order = [name for name, _count in
                           check_readmes.find_uncovered_cards("No links here.", self.cards, global_counts)]
        self.assertEqual(names_in_order[0], "The Great Henge")


class BuildGlobalCardCountsTests(unittest.TestCase):
    def test_counts_decks_not_copies(self):
        with tempfile.TemporaryDirectory() as directory:
            deck_a = Path(directory) / "a"
            deck_b = Path(directory) / "b"
            deck_a.mkdir()
            deck_b.mkdir()
            write_dck(deck_a)
            write_dck(deck_b)
            counts = check_readmes.build_global_card_counts([deck_a, deck_b])
        self.assertEqual(counts[check_readmes.normalize_name("Caretaker's Talent")], 2)


class RequireInDeckTests(unittest.TestCase):
    def test_full_name_is_allowed(self):
        with tempfile.TemporaryDirectory() as directory:
            cards = check_readmes.parse_decklist(write_dck(Path(directory)))
        issues = []
        check_readmes.require_in_deck("Caretaker's Talent", cards, issues)
        self.assertEqual(issues, [])

    def test_unambiguous_character_name_is_allowed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "decklist.dck"
            path.write_text(
                "[metadata]\nName=Test Deck\n[main]\n1 Teferi, Time Raveler|WAR|[221]\n",
                encoding="utf-8",
            )
            cards = check_readmes.parse_decklist(path)
        issues = []
        check_readmes.require_in_deck("Teferi", cards, issues)
        self.assertEqual(issues, [])

    def test_ambiguous_character_name_is_an_error(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "decklist.dck"
            path.write_text(
                "[metadata]\nName=Test Deck\n[main]\n"
                "1 Teferi, Time Raveler|WAR|[221]\n"
                "1 Teferi, Who Slows the Sunset|WOE|[400]\n",
                encoding="utf-8",
            )
            cards = check_readmes.parse_decklist(path)
        issues = []
        check_readmes.require_in_deck("Teferi", cards, issues)
        errors = [i for i in issues if i.level == "ERROR"]
        self.assertTrue(any("Ambiguous character name" in i.message for i in errors))


class CheckFeaturedCardsAreBoldTests(unittest.TestCase):
    def test_bolded_featured_link_has_no_issues(self):
        text = "The **[Wedding Ring](https://scryfall.com/card/who/1059)** gleams.\n"
        issues = check_readmes.check_featured_cards_are_bold(text, ["Wedding Ring"])
        self.assertEqual(issues, [])

    def test_unbolded_featured_link_is_an_error(self):
        text = "The [Wedding Ring](https://scryfall.com/card/who/1059) gleams.\n"
        issues = check_readmes.check_featured_cards_are_bold(text, ["Wedding Ring"])
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].level, "ERROR")
        self.assertIn("wrap it in bold", issues[0].message)

    def test_shortened_link_text_to_a_featured_card_must_also_be_bold(self):
        text = "He hides under his [Tutelage](https://scryfall.com/card/m21/78).\n"
        issues = check_readmes.check_featured_cards_are_bold(text, ["Teferi's Tutelage"])
        self.assertEqual(len(issues), 1)

    def test_non_featured_links_are_unaffected(self):
        text = "A plain [Sol Ring](https://scryfall.com/card/lea/162) sits there.\n"
        issues = check_readmes.check_featured_cards_are_bold(text, ["Wedding Ring"])
        self.assertEqual(issues, [])

    def _mycoloth_cards(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "decklist.dck"
            path.write_text("[metadata]\nName=Test Deck\n[main]\n1 Mycoloth|SLD|[2205]\n", encoding="utf-8")
            return check_readmes.parse_decklist(path)

    def test_unbolded_flavor_name_link_to_featured_card_is_an_error(self):
        cards = self._mycoloth_cards()
        text = "The [Cordyceps Rat King](https://scryfall.com/card/sld/2205) arrives.\n"
        issues = check_readmes.check_featured_cards_are_bold(text, ["Mycoloth"], cards)
        self.assertEqual(len(issues), 1)

    def test_bolded_flavor_name_link_to_featured_card_has_no_issues(self):
        cards = self._mycoloth_cards()
        text = "The **[Cordyceps Rat King](https://scryfall.com/card/sld/2205)** arrives.\n"
        issues = check_readmes.check_featured_cards_are_bold(text, ["Mycoloth"], cards)
        self.assertEqual(issues, [])


class LoadMosaicOrderTests(unittest.TestCase):
    def test_bumbleflower_featured_cards_are_configured(self):
        mosaic_order = check_readmes.load_mosaic_order()
        deck_dir = check_readmes.DECKS_DIR / "Somebunny Is Having a Party" / "Ms. Bumbleflower – Somebunny Said I Do"
        self.assertEqual(
            mosaic_order.get(deck_dir),
            ["Wedding Ring", "Savor the Moment", "Smothering Tithe"],
        )


class ClassifyCardTypeTests(unittest.TestCase):
    def test_land_takes_priority_over_creature(self):
        self.assertEqual(check_readmes.classify_card_type("Land Creature — Tree"), "Land")

    def test_creature_takes_priority_over_artifact(self):
        self.assertEqual(check_readmes.classify_card_type("Artifact Creature — Golem"), "Creature")

    def test_plain_types(self):
        self.assertEqual(check_readmes.classify_card_type("Sorcery"), "Sorcery")
        self.assertEqual(check_readmes.classify_card_type("Instant"), "Instant")
        self.assertEqual(check_readmes.classify_card_type("Enchantment"), "Enchantment")
        self.assertEqual(check_readmes.classify_card_type("Artifact"), "Artifact")

    def test_unrecognized_type_is_other(self):
        self.assertEqual(check_readmes.classify_card_type("Planeswalker — Jace"), "Other")


class GroupUncoveredByTypeTests(unittest.TestCase):
    def test_returns_none_without_a_type_index(self):
        self.assertIsNone(check_readmes.group_uncovered_by_type([("Sol Ring", 0)], None))

    def test_groups_in_display_order_and_flags_unknowns(self):
        uncovered = [
            ("Sol Ring", 9), ("Command Tower", 8), ("Sylvan Library", 3),
            ("Fascination", 0), ("Mystery Card", 0),
        ]
        type_index = {
            check_readmes.normalize_name("Sol Ring"): "Artifact",
            check_readmes.normalize_name("Command Tower"): "Land",
            check_readmes.normalize_name("Sylvan Library"): "Enchantment",
            check_readmes.normalize_name("Fascination"): "Sorcery",
            # "Mystery Card" deliberately left out of the index.
        }
        grouped = check_readmes.group_uncovered_by_type(uncovered, type_index)
        group_names = [group for group, _cards in grouped]
        self.assertEqual(group_names, ["Sorcery", "Artifact", "Enchantment", "Land", "Unknown"])
        self.assertEqual(dict(grouped)["Unknown"], [("Mystery Card", 0)])


class CheckScryfallLinkTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.cards = check_readmes.parse_decklist(write_dck(Path(self._tmpdir.name)))

    def _check(self, text, url):
        import urllib.parse
        return check_readmes.check_scryfall_link(text, url, urllib.parse.urlparse(url), self.cards)

    def test_matching_printing_has_no_errors(self):
        issues = self._check("Caretaker's Talent", "https://scryfall.com/card/blb/6/caretakers-talent")
        self.assertEqual(issues, [])

    def test_printing_collision_is_an_error(self):
        issues = self._check("The Party Tree", "https://scryfall.com/card/ltc/348")
        errors = [i for i in issues if i.level == "ERROR"]
        self.assertTrue(any("Printing collision" in i.message for i in errors))

    def test_card_not_in_deck_is_an_error(self):
        issues = self._check("Smothering Tithe", "https://scryfall.com/card/2x2/1/smothering-tithe")
        errors = [i for i in issues if i.level == "ERROR"]
        self.assertEqual(len(errors), 1)
        self.assertIn("is not in the decklist", errors[0].message)

    def test_malformed_card_link_missing_number(self):
        issues = self._check("Sol Ring", "https://scryfall.com/card/blb")
        self.assertTrue(any("missing set/number" in i.message for i in issues))

    def test_search_link_is_an_error(self):
        issues = self._check("Faith's Reward", "https://scryfall.com/search?q=%21%22Faith%27s+Reward%22")
        self.assertTrue(any("Scryfall search link not allowed" in i.message for i in issues))

    def test_unrecognized_scryfall_path_is_an_error(self):
        issues = self._check("Sol Ring", "https://scryfall.com/sets/blb")
        self.assertTrue(any("Unrecognized scryfall.com link shape" in i.message for i in issues))

    def test_shortened_trailing_word_link_text_is_allowed(self):
        issues = self._check("Talent", "https://scryfall.com/card/blb/6/caretakers-talent")
        self.assertEqual(issues, [])

    def test_shortened_link_text_still_requires_trailing_words(self):
        issues = self._check("Caretaker's", "https://scryfall.com/card/blb/6/caretakers-talent")
        errors = [i for i in issues if i.level == "ERROR"]
        self.assertTrue(any("Printing collision" in i.message for i in errors))


class CheckScryfallLinkFlavorNameTests(unittest.TestCase):
    def _check(self, text, url, cards):
        import urllib.parse
        return check_readmes.check_scryfall_link(text, url, urllib.parse.urlparse(url), cards)

    def test_flavor_name_link_text_is_allowed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "decklist.dck"
            path.write_text("[metadata]\nName=Test Deck\n[main]\n1 Mycoloth|SLD|[2205]\n", encoding="utf-8")
            cards = check_readmes.parse_decklist(path)
        issues = self._check("Cordyceps Rat King", "https://scryfall.com/card/sld/2205", cards)
        self.assertEqual(issues, [])

    def test_flavor_name_does_not_apply_to_a_different_printing(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "decklist.dck"
            path.write_text("[metadata]\nName=Test Deck\n[main]\n1 Sol Ring|LEA|[2205]\n", encoding="utf-8")
            cards = check_readmes.parse_decklist(path)
        issues = self._check("Cordyceps Rat King", "https://scryfall.com/card/lea/2205", cards)
        errors = [i for i in issues if i.level == "ERROR"]
        self.assertTrue(any("Printing collision" in i.message for i in errors))


class CheckScryfallLinkCharacterNameTests(unittest.TestCase):
    def _check(self, text, url, cards):
        import urllib.parse
        return check_readmes.check_scryfall_link(text, url, urllib.parse.urlparse(url), cards)

    def test_unambiguous_character_name_is_allowed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "decklist.dck"
            path.write_text(
                "[metadata]\nName=Test Deck\n[main]\n1 Teferi, Time Raveler|WAR|[221]\n",
                encoding="utf-8",
            )
            cards = check_readmes.parse_decklist(path)
        issues = self._check("Teferi", "https://scryfall.com/card/war/221", cards)
        self.assertEqual(issues, [])

    def test_ambiguous_character_name_is_an_error(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "decklist.dck"
            path.write_text(
                "[metadata]\nName=Test Deck\n[main]\n"
                "1 Teferi, Time Raveler|WAR|[221]\n"
                "1 Teferi, Who Slows the Sunset|WOE|[400]\n",
                encoding="utf-8",
            )
            cards = check_readmes.parse_decklist(path)
        issues = self._check("Teferi", "https://scryfall.com/card/war/221", cards)
        errors = [i for i in issues if i.level == "ERROR"]
        self.assertTrue(any("Ambiguous character name" in i.message for i in errors))


class CheckLinkTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.deck_dir = Path(self._tmpdir.name)
        write_dck(self.deck_dir)
        self.cards = check_readmes.parse_decklist(self.deck_dir / "decklist.dck")

    def test_existing_relative_file_is_fine(self):
        issues = check_readmes.check_link("Forge decklist", "decklist.dck", self.deck_dir, self.cards)
        self.assertEqual(issues, [])

    def test_missing_relative_file_is_an_error(self):
        issues = check_readmes.check_link("Theme analysis", "theme_analysis.md", self.deck_dir, self.cards)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].level, "ERROR")

    def test_deckcheck_link_is_allowed(self):
        issues = check_readmes.check_link(
            "DeckCheck", "https://deckcheck.co/app/decklist/abc123", self.deck_dir, self.cards
        )
        self.assertEqual(issues, [])

    def test_unexpected_domain_is_a_warning(self):
        issues = check_readmes.check_link(
            "EDHREC", "https://edhrec.com/commanders/test", self.deck_dir, self.cards
        )
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].level, "WARNING")


class CheckReadmeTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.deck_dir = Path(self._tmpdir.name)
        write_dck(self.deck_dir)
        self.cards = check_readmes.parse_decklist(self.deck_dir / "decklist.dck")

    def _run(self, readme_text):
        readme = self.deck_dir / "README.md"
        readme.write_text(readme_text, encoding="utf-8")
        return check_readmes.check_readme(readme, self.deck_dir, self.cards)

    def test_clean_readme_has_no_issues(self):
        (self.deck_dir / "deck_mosaic_preview.jpg").write_bytes(b"")
        issues = self._run(VALID_LAYOUT_README)
        self.assertEqual(issues, [])

    def test_bare_url_is_an_error(self):
        issues = self._run("Check out https://scryfall.com/card/blb/6 sometime.\n")
        self.assertTrue(any("Unlinked or malformed URL" in i.message for i in issues))

    def test_broken_link_syntax_leaves_stray_bracket(self):
        # A stray space between "]" and "(" breaks the markdown link.
        issues = self._run("[Caretaker's Talent] (https://scryfall.com/card/blb/6)\n")
        self.assertTrue(any("Stray" in i.message for i in issues))

    def test_card_not_in_deck_fails_the_readme(self):
        issues = self._run(
            "[Smothering Tithe](https://scryfall.com/card/2x2/1/smothering-tithe) shows up.\n"
        )
        errors = [i for i in issues if i.level == "ERROR"]
        self.assertTrue(any("is not in the decklist" in i.message for i in errors))


class DeckFlavorNameTests(unittest.TestCase):
    def test_splits_on_en_dash(self):
        self.assertEqual(
            check_readmes.deck_flavor_name(Path("Ms. Bumbleflower \u2013 Somebunny Said I Do")),
            "Somebunny Said I Do",
        )

    def test_returns_none_without_a_dash(self):
        self.assertIsNone(check_readmes.deck_flavor_name(Path("NoDashHere")))


class CheckReadmeLayoutTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.deck_dir = Path(self._tmpdir.name) / "Test Commander \u2013 Test Deck"
        self.deck_dir.mkdir()
        write_dck(self.deck_dir)
        self.cards = check_readmes.parse_decklist(self.deck_dir / "decklist.dck")

    def _layout_issues(self, text):
        return check_readmes.check_readme_layout(text, self.deck_dir, self.cards)

    def test_valid_layout_has_no_errors(self):
        self.assertEqual(self._layout_issues(VALID_LAYOUT_README), [])

    def test_title_with_flavor_subtitle_is_an_error(self):
        text = VALID_LAYOUT_README.replace("# Test Commander\n", "# Test Commander \u2014 Test Deck\n", 1)
        issues = self._layout_issues(text)
        self.assertTrue(any("should be just the commander's plain name" in i.message for i in issues))

    def test_missing_metadata_table_is_an_error(self):
        text = (
            "# Test Commander\n"
            "\n"
            "## Test Deck\n"
            "\n"
            "Some story.\n"
            "\n"
            "## The Deck\n"
            "\n"
            "![Deck mosaic](deck_mosaic_preview.jpg)\n"
            "\n"
            "## Deck Resources\n"
            "\n"
            "[Forge decklist](decklist.dck)\n"
        )
        issues = self._layout_issues(text)
        self.assertTrue(any("Missing metadata table" in i.message for i in issues))
        self.assertTrue(any("missing row(s)" in i.message for i in issues))

    def test_metadata_table_wrong_order_is_an_error(self):
        text = VALID_LAYOUT_README.replace(
            "| **Commander** | [Test Commander](https://scryfall.com/card/tst/1) |\n"
            "| **Colors** | Selesnya (White / Green) |\n",
            "| **Colors** | Selesnya (White / Green) |\n"
            "| **Commander** | [Test Commander](https://scryfall.com/card/tst/1) |\n",
        )
        issues = self._layout_issues(text)
        self.assertTrue(any("out of order" in i.message for i in issues))

    def test_narrative_header_mismatch_is_an_error(self):
        text = VALID_LAYOUT_README.replace("## Test Deck\n", "## Wrong Name\n", 1)
        issues = self._layout_issues(text)
        self.assertTrue(any("should match the deck's name" in i.message for i in issues))

    def test_missing_the_deck_section_is_an_error(self):
        text = VALID_LAYOUT_README.replace(
            "## The Deck\n\n![Deck mosaic](deck_mosaic_preview.jpg)\n\n", ""
        )
        issues = self._layout_issues(text)
        self.assertTrue(any("Missing '## The Deck' section" in i.message for i in issues))

    def test_mosaic_image_outside_the_deck_section_is_an_error(self):
        text = VALID_LAYOUT_README + "\n![Deck mosaic](deck_mosaic_preview.jpg)\n"
        issues = self._layout_issues(text)
        self.assertTrue(any("found outside the '## The Deck' section" in i.message for i in issues))

    def test_the_deck_after_deck_resources_is_an_error(self):
        text = (
            "# Test Commander\n"
            "\n"
            "| | |\n"
            "|---|---|\n"
            "| **Commander** | [Test Commander](https://scryfall.com/card/tst/1) |\n"
            "| **Colors** | Selesnya (White / Green) |\n"
            "| **Archetype** | Testing |\n"
            "| **Good against** | Nothing |\n"
            "| **Struggles against** | Everything |\n"
            "\n"
            "## Test Deck\n"
            "\n"
            "Some story.\n"
            "\n"
            "## Deck Resources\n"
            "\n"
            "[Forge decklist](decklist.dck)\n"
            "\n"
            "## The Deck\n"
            "\n"
            "![Deck mosaic](deck_mosaic_preview.jpg)\n"
        )
        issues = self._layout_issues(text)
        self.assertTrue(any("must come before" in i.message for i in issues))


if __name__ == "__main__":
    unittest.main()
