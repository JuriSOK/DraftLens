"""Tests for ML-0 deterministic logic (stdlib unittest — pytest is not installed).

  ./.venv/bin/python -m unittest discover -s tests -v

Fixtures are synthetic; these tests do not read acquired data except for the
two population-count gates, which are the point of the ML-0 build.
"""

import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "experiments"))

from draftlens.leakage import (DENY_EXACT, DENY_SUBSTRING,  # noqa: E402
                               SUSPICIOUS, SUSPICIOUS_ALLOWED)
from draftlens.data.population import EXPECTED  # noqa: E402
from draftlens.data.identity.matching import to_int_id  # noqa: E402
from draftlens.data.identity.normalization import match_key, norm_school  # noqa: E402
from draftlens.features.boxscore import aggregate_box_frame  # noqa: E402
from draftlens.features.shot_profile import aggregate_shots_frame  # noqa: E402
from draftlens.paths import interim  # noqa: E402

OUT = interim("ml0")


def box_row(athlete_id, game_id, team_id, **kw):
    """Minimal player_box row with the columns the aggregator touches."""
    row = dict(athlete_id=athlete_id, game_id=game_id, team_id=team_id,
               team_location="Somewhere", game_date="2020-01-01",
               did_not_play=False, starter=False, minutes=10.0, points=5.0,
               field_goals_made=2.0, field_goals_attempted=4.0,
               three_point_field_goals_made=1.0,
               three_point_field_goals_attempted=2.0,
               free_throws_made=0.0, free_throws_attempted=0.0,
               offensive_rebounds=1.0, defensive_rebounds=2.0, rebounds=3.0,
               assists=1.0, turnovers=1.0, steals=0.0, blocks=0.0, fouls=1.0)
    row.update(kw)
    return row


def shot_row(shooter, type_text, made, score_value, assister=None):
    return dict(athlete_id_1=shooter, athlete_id_2=assister, type_text=type_text,
                scoring_play=made, score_value=score_value)


class TestNameNormalisation(unittest.TestCase):
    def test_collapses_spaced_initials(self):
        # Wikipedia writes "T. J. Warren"; ESPN writes "TJ Warren".
        self.assertEqual(match_key("T. J. Warren"), match_key("TJ Warren"))
        self.assertEqual(match_key("G. G. Jackson"), "gg jackson")

    def test_suffix_stripped_only_at_end(self):
        # A leading "V." must NOT be eaten as the Roman numeral suffix V.
        self.assertEqual(match_key("V. J. Edgecombe"), "vj edgecombe")
        self.assertEqual(match_key("D. J. Stewart Jr."), "dj stewart")
        self.assertEqual(match_key("Gary Payton II"), "gary payton")

    def test_transliterates_undecomposable_letters(self):
        # NFKD does not decompose 'ø'; without transliteration it becomes a gap.
        self.assertEqual(match_key("Asbjørn Midtgaard"), "asbjorn midtgaard")

    def test_accents_and_punctuation(self):
        self.assertEqual(match_key("Alperen Şengün"), "alperen sengun")
        self.assertEqual(match_key("De'Andre O'Neal"), "deandre oneal")

    def test_distinct_players_stay_distinct(self):
        self.assertNotEqual(match_key("Chris Johnson"), match_key("Chris Jones"))


class TestSchoolNormalisation(unittest.TestCase):
    def test_equivalences(self):
        # Spelling/spacing/case variants of one school must normalise together.
        self.assertEqual(norm_school("Texas A&M"), norm_school("texas a & m "))
        self.assertEqual(norm_school("Texas A&M"), norm_school("Texas A and M"))
        self.assertEqual(norm_school("Saint Joseph's"), "saint josephs")

    def test_strips_program_suffix(self):
        self.assertEqual(norm_school("Duke Blue Devils men's basketball"),
                         "duke blue devils")


class TestIdNormalisation(unittest.TestCase):
    def test_float_and_int_ids_compare_equal(self):
        # player_core is int64; player_box/shots are float64. Naive string
        # casting produced a false 0% overlap in the DATA.md §22.7 audit.
        core = to_int_id(pd.Series([5142718, 5041935], dtype="int64"))
        box = to_int_id(pd.Series([5142718.0, 5041935.0], dtype="float64"))
        self.assertEqual(set(core.dropna()), set(box.dropna()))

    def test_nan_becomes_na_not_zero(self):
        out = to_int_id(pd.Series([1.0, None]))
        self.assertTrue(pd.isna(out.iloc[1]))
        self.assertEqual(out.iloc[0], 1)


class TestBoxAggregation(unittest.TestCase):
    def test_transfer_aggregates_across_teams_into_one_row(self):
        box = pd.DataFrame([
            box_row(1, 100, team_id=10, points=10.0),
            box_row(1, 101, team_id=10, points=5.0),
            box_row(1, 200, team_id=20, points=7.0),   # transferred mid-season
        ])
        agg, dupes, _ = aggregate_box_frame(box, 2020)
        self.assertEqual(len(agg), 1, "transfer must not duplicate the prospect")
        self.assertEqual(agg.iloc[0].points, 22.0, "totals span all teams")
        self.assertEqual(agg.iloc[0].n_teams, 2)
        self.assertEqual(agg.iloc[0].games_played, 3)
        self.assertEqual(dupes, 0)

    def test_duplicate_game_rows_are_not_double_counted(self):
        box = pd.DataFrame([
            box_row(1, 100, team_id=10, points=10.0),
            box_row(1, 100, team_id=10, points=10.0),   # exact duplicate
            box_row(1, 101, team_id=10, points=4.0),
        ])
        agg, dupes, before = aggregate_box_frame(box, 2020)
        self.assertEqual(dupes, 1)
        self.assertEqual(before, 3)
        self.assertEqual(agg.iloc[0].points, 14.0)
        self.assertEqual(agg.iloc[0].games_played, 2)

    def test_did_not_play_rows_excluded_from_games_and_totals(self):
        box = pd.DataFrame([
            box_row(1, 100, team_id=10, points=8.0),
            box_row(1, 101, team_id=10, points=0.0, did_not_play=True, minutes=0.0),
        ])
        agg, _, _ = aggregate_box_frame(box, 2020)
        self.assertEqual(agg.iloc[0].games_played, 1)

    def test_games_started_counted_from_starter_flag(self):
        box = pd.DataFrame([
            box_row(1, 100, team_id=10, starter=True),
            box_row(1, 101, team_id=10, starter=False),
        ])
        agg, _, _ = aggregate_box_frame(box, 2020)
        self.assertEqual(agg.iloc[0].games_started, 1)
        self.assertLessEqual(agg.iloc[0].games_started, agg.iloc[0].games_played)

    def test_season_label_equals_requested_draft_year(self):
        agg, _, _ = aggregate_box_frame(pd.DataFrame([box_row(1, 1, 10)]), 2019)
        self.assertEqual(agg.iloc[0].ncaa_season, 2019)


class TestTwoPointArithmetic(unittest.TestCase):
    def test_two_point_primitives_are_identity_preserving(self):
        box = pd.DataFrame([box_row(1, 100, 10, field_goals_made=7.0,
                                    field_goals_attempted=15.0,
                                    three_point_field_goals_made=3.0,
                                    three_point_field_goals_attempted=8.0)])
        agg, _, _ = aggregate_box_frame(box, 2020)
        r = agg.iloc[0]
        two_made = r.field_goals_made - r.three_points_made
        two_att = r.field_goals_attempted - r.three_points_attempted
        self.assertEqual(two_made, 4.0)
        self.assertEqual(two_att, 7.0)
        self.assertLessEqual(two_made, two_att)
        self.assertGreaterEqual(two_made, 0)


class TestShotAggregation(unittest.TestCase):
    def test_free_throws_excluded_entirely(self):
        # shots holds only MADE free throws, so FT must never come from here.
        sh = pd.DataFrame([
            shot_row(1, "MadeFreeThrow", True, 1),
            shot_row(1, "JumpShot", True, 2),
        ])
        out = aggregate_shots_frame(sh)
        self.assertEqual(out.iloc[0].fg_attempts_shotfile, 1)

    def test_three_pointers_identified_by_score_value_not_coordinates(self):
        sh = pd.DataFrame([
            shot_row(1, "JumpShot", True, 3),
            shot_row(1, "JumpShot", False, 3),
            shot_row(1, "JumpShot", True, 2),
        ])
        out = aggregate_shots_frame(sh)
        self.assertEqual(out.iloc[0].three_point_shot_attempts, 2)
        self.assertEqual(out.iloc[0].three_point_shot_makes, 1)

    def test_assist_linkage_splits_made_field_goals(self):
        sh = pd.DataFrame([
            shot_row(1, "LayUpShot", True, 2, assister=99),
            shot_row(1, "LayUpShot", True, 2, assister=None),
            shot_row(1, "DunkShot", True, 2, assister=99),
            shot_row(1, "LayUpShot", False, 2, assister=None),
        ])
        out = aggregate_shots_frame(sh).iloc[0]
        self.assertEqual(out.assisted_made_field_goals, 2)
        self.assertEqual(out.unassisted_made_field_goals, 1)
        self.assertEqual(out.assisted_layup_makes, 1)
        self.assertEqual(out.unassisted_layup_makes, 1)
        self.assertEqual(out.assisted_dunk_makes, 1)

    def test_makes_never_exceed_attempts(self):
        sh = pd.DataFrame([shot_row(1, "DunkShot", True, 2),
                           shot_row(1, "DunkShot", False, 2)])
        out = aggregate_shots_frame(sh).iloc[0]
        self.assertEqual(out.dunk_attempts, 2)
        self.assertEqual(out.dunk_makes, 1)
        self.assertLessEqual(out.dunk_makes, out.dunk_attempts)


class TestLeakageDenyList(unittest.TestCase):
    def test_outcome_and_age_columns_are_denied(self):
        for c in ("drafted", "pick", "round", "drafting_team", "early_entrant",
                  "population_source", "date_of_birth", "age"):
            self.assertIn(c, DENY_EXACT, f"{c} must be on the deny list")

    def test_nba_and_analyst_concepts_denied_by_substring(self):
        for c in ("nba_career_points", "mock_rank", "consensus_rank",
                  "analyst_rank", "post_draft_value"):
            self.assertTrue(any(s in c for s in DENY_SUBSTRING),
                            f"{c} should trip a deny substring")

    def test_legitimate_primitives_not_denied(self):
        for c in ("points", "assists", "three_points_made", "games_played",
                  "height", "weight", "draft_year"):
            self.assertNotIn(c, DENY_EXACT)
            self.assertFalse(any(s in c for s in DENY_SUBSTRING))


@unittest.skipUnless((OUT / "features_2014_2025.parquet").exists(),
                     "ML-0 outputs not built")
class TestBuiltDataset(unittest.TestCase):
    """Gates on the actual build — these are the point of ML-0."""

    @classmethod
    def setUpClass(cls):
        cls.f = pd.read_parquet(OUT / "features_2014_2025.parquet")
        cls.t = pd.read_parquet(OUT / "targets_2014_2025.parquet")
        cls.h = pd.read_parquet(OUT / "features_2026.parquet")

    def test_development_population_counts(self):
        exp_n, exp_d, exp_u = EXPECTED["2014_2025"]
        self.assertEqual(len(self.f), exp_n)
        self.assertEqual(int(self.t.drafted.sum()), exp_d)
        self.assertEqual(int((self.t.drafted == 0).sum()), exp_u)

    def test_holdout_population_count(self):
        self.assertEqual(len(self.h), EXPECTED["2026"][0])

    def test_feature_file_carries_no_outcome_column(self):
        cols = {c.lower() for c in self.f.columns}
        self.assertFalse(cols & DENY_EXACT,
                         f"prohibited columns present: {cols & DENY_EXACT}")

    def test_features_and_targets_are_separate_files(self):
        self.assertNotIn("drafted", self.f.columns)
        self.assertNotIn("points", self.t.columns)

    def test_feature_target_keys_align_exactly(self):
        self.assertEqual(set(self.f.canonical_prospect_id),
                         set(self.t.canonical_prospect_id))

    def test_no_future_season_used(self):
        s = self.f.dropna(subset=["ncaa_season"])
        self.assertTrue((s.ncaa_season == s.draft_year).all())

    def test_holdout_is_disjoint_from_development(self):
        self.assertFalse(set(self.f.canonical_prospect_id)
                         & set(self.h.canonical_prospect_id))

    def test_no_duplicate_prospects(self):
        self.assertFalse(self.f.canonical_prospect_id.duplicated().any())


if __name__ == "__main__":
    unittest.main(verbosity=2)
