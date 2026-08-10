"""Tests for the NCAA population parser (ML-0.1 corrective fix).

Guards against the classification defect found in ML-0: foreign professional
clubs were counted as NCAA because their Wikipedia article titles contain
"men's basketball", while several genuine NCAA programs were dropped because
their canonical titles omit "men's".

  ./.venv/bin/python -m unittest discover -s tests -v
"""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

from data.wikipedia import (collect_school_candidates,  # noqa: E402
                                      find_school, is_ncaa_program,
                                      parse_early_entrants)


class TestNcaaProgramClassification(unittest.TestCase):
    def test_accepts_canonical_mens_basketball_programs(self):
        for t in ("Duke Blue Devils men's basketball",
                  "Kentucky Wildcats men's basketball",
                  "LSU Tigers men's basketball"):
            self.assertTrue(is_ncaa_program(t), t)

    def test_accepts_programs_without_the_mens_infix(self):
        # Wikipedia is inconsistent: these canonical titles omit "men's".
        # The ML-0 rule required "men's basketball" and wrongly dropped them.
        for t in ("Georgia Bulldogs basketball", "Tennessee Volunteers basketball",
                  "Texas Tech Red Raiders basketball",
                  "UNLV Runnin' Rebels basketball", "Penn State Nittany Lions basketball"):
            self.assertTrue(is_ncaa_program(t), t)

    def test_rejects_foreign_clubs_with_mens_basketball_in_the_title(self):
        # The exact defect ML-0.1 corrects.
        for t in ("Beşiktaş J.K. (men's basketball)",
                  "CSM Constanța (men's basketball)",
                  "Galatasaray S.K. (men's basketball)"):
            self.assertFalse(is_ncaa_program(t), t)

    def test_rejects_league_articles(self):
        self.assertFalse(is_ncaa_program("Liga Națională (men's basketball)"))

    def test_rejects_player_disambiguation_articles(self):
        # Player links must never be mistaken for a school.
        for t in ("Anthony Edwards (basketball)", "AJ Griffin (basketball)",
                  "A. J. Green (basketball)"):
            self.assertFalse(is_ncaa_program(t), t)

    def test_rejects_non_basketball_athletics_pages(self):
        self.assertFalse(is_ncaa_program("UT Permian Basin Falcons"))
        self.assertFalse(is_ncaa_program("Real Madrid Baloncesto"))


class TestFindSchool(unittest.TestCase):
    def test_picks_the_ncaa_link_and_strips_label_markup(self):
        line = ("* {{flagicon|USA}} [[Some Player]] – G, "
                "[[Hawaii Rainbow Warriors basketball|Hawai{{okina}}i]] (junior)")
        ncaa = {"Hawaii Rainbow Warriors basketball"}
        college, is_ncaa = find_school(line, ncaa)
        self.assertTrue(is_ncaa)
        self.assertEqual(college, "Hawaii", "template markup must be stripped")

    def test_returns_not_ncaa_when_only_a_club_is_linked(self):
        line = ("* {{flagicon|TUR}} [[Alperen Şengün]] – C, "
                "[[Beşiktaş J.K. (men's basketball)|Beşiktaş]] ([[Turkey]])")
        college, is_ncaa = find_school(line, ncaa_targets=set())
        self.assertFalse(is_ncaa)
        self.assertIsNone(college)


class TestEarlyEntrantParsing(unittest.TestCase):
    NCAA = {"Duke Blue Devils men's basketball",
            "Hawaii Rainbow Warriors basketball"}

    def test_bullet_with_player_article(self):
        sec = ("===Early entrants===\n"
               "* {{flagicon|USA}} [[Cameron Boozer]] – F, "
               "[[Duke Blue Devils men's basketball|Duke]] (freshman)\n")
        out = parse_early_entrants(sec, self.NCAA)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["player_name"], "Cameron Boozer")
        self.assertEqual(out[0]["college"], "Duke")
        self.assertTrue(out[0]["is_ncaa"])

    def test_prospect_without_a_wikipedia_article_is_not_named_after_school(self):
        # Regression: links[0] was the SCHOOL, so the prospect was named
        # "Hawai{{okina}}i" instead of "Casdon Jardine".
        sec = ("===Early entrants===\n"
               "*{{flagicon|USA}} Casdon Jardine – G/F, "
               "[[Hawaii Rainbow Warriors basketball|Hawai{{okina}}i]]\n")
        out = parse_early_entrants(sec, self.NCAA)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["player_name"], "Casdon Jardine")
        self.assertEqual(out[0]["college"], "Hawaii")
        self.assertEqual(out[0]["wikipedia_title"], "")

    def test_table_markup_variant_still_supported(self):
        sec = ("===Early entrants===\n"
               "{|class=\"wikitable\"\n|-\n"
               "| {{sortname|Jabari|Parker}} || "
               "[[Duke Blue Devils men's basketball|Duke]] || [[Freshman]]\n|}\n")
        out = parse_early_entrants(sec, self.NCAA)
        self.assertTrue(any(o["player_name"] == "Jabari Parker" for o in out))

    def test_club_entrant_is_flagged_non_ncaa(self):
        sec = ("===Early entrants===\n"
               "* {{flagicon|TUR}} [[Alperen Şengün]] – C, "
               "[[Beşiktaş J.K. (men's basketball)|Beşiktaş]]\n")
        out = parse_early_entrants(sec, self.NCAA)
        self.assertEqual(len(out), 1)
        self.assertFalse(out[0]["is_ncaa"], "foreign club must not count as NCAA")


class TestCandidateCollection(unittest.TestCase):
    def test_collects_only_basketball_links(self):
        text = ("[[Duke Blue Devils men's basketball|Duke]] [[Washington Wizards]] "
                "[[Beşiktaş J.K. (men's basketball)|B]]")
        got = collect_school_candidates(text)
        self.assertIn("Duke Blue Devils men's basketball", got)
        self.assertIn("Beşiktaş J.K. (men's basketball)", got)
        self.assertNotIn("Washington Wizards", got)


if __name__ == "__main__":
    unittest.main(verbosity=2)
