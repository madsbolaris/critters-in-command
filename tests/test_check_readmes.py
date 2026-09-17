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


class NormalizeNameTests(unittest.TestCase):
    def test_smart_quotes_fold_to_straight_quotes(self):
        self.assertEqual(
            check_readmes.normalize_name("Caretaker\u2019s Talent"),
            check_readmes.normalize_name("Caretaker's Talent"),
        )

    def test_whitespace_and_case_are_normalized(self):
        self.assertEqual(check_readmes.normalize_name("  Sol   Ring "), "sol ring")


class ParseDecklistTests(unittest.TestCase):
    def test_parses_names_and_printings(self):
        with tempfile.TemporaryDirectory() as directory:
            cards = check_readmes.parse_decklist(write_dck(Path(directory)))
        self.assertIn(check_readmes.normalize_name("Caretaker's Talent"), cards.by_name)
        self.assertEqual(cards.by_printing[("blb", "6")][0], "Caretaker's Talent")
        self.assertEqual(cards.by_printing[("ltc", "348")][0], "The Great Henge")

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
        uncovered = check_readmes.find_uncovered_cards(text, self.cards)
        self.assertNotIn("Caretaker's Talent", uncovered)

    def test_unmentioned_nonland_cards_are_reported(self):
        uncovered = check_readmes.find_uncovered_cards("No links here.", self.cards)
        self.assertIn("The Great Henge", uncovered)
        self.assertIn("Caretaker's Talent", uncovered)

    def test_basic_lands_are_excluded(self):
        uncovered = check_readmes.find_uncovered_cards("No links here.", self.cards)
        self.assertNotIn("Forest", uncovered)

    def test_smart_quote_mentions_still_count_as_covered(self):
        text = "[Caretaker\u2019s Talent](https://scryfall.com/card/blb/6/caretakers-talent) keeps everyone fed."
        uncovered = check_readmes.find_uncovered_cards(text, self.cards)
        self.assertNotIn("Caretaker's Talent", uncovered)


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

    def test_search_link_requires_query(self):
        issues = self._check("Faith's Reward", "https://scryfall.com/search")
        self.assertTrue(any("Malformed scryfall search link" in i.message for i in issues))

    def test_unrecognized_scryfall_path_is_an_error(self):
        issues = self._check("Sol Ring", "https://scryfall.com/sets/blb")
        self.assertTrue(any("Unrecognized scryfall.com link shape" in i.message for i in issues))


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
        issues = self._run(
            "[Caretaker's Talent](https://scryfall.com/card/blb/6/caretakers-talent) is great.\n"
            "[Forge decklist](decklist.dck)\n"
        )
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


if __name__ == "__main__":
    unittest.main()
