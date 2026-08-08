"""Tests for ML-2 basketball formulas and guards (stdlib unittest).

  ./.venv/bin/python -m unittest discover -s tests -v
"""

import math
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_ml2_features import (EXPECTED_ROWS, OUT as ML2,  # noqa: E402
                                feature_columns)
from ml2_formulas import (FT_POSSESSION_COEF, ast_pct, blk_pct,  # noqa: E402
                          efg_pct, per_100, per_40, per_game, rebound_pct,
                          safe_div, stl_pct, team_possessions, tov_pct,
                          ts_pct, usage_pct)

S = pd.Series


class TestSafeDivision(unittest.TestCase):
    """DEC-069: an undefined ratio is NULL — never 0, never inf, no epsilon."""

    def test_normal_division(self):
        self.assertAlmostEqual(safe_div(S([10.0]), S([4.0])).iloc[0], 2.5)

    def test_zero_denominator_is_null_not_zero(self):
        # 0 made from 0 attempts is UNKNOWN, not 0%.
        self.assertTrue(pd.isna(safe_div(S([0.0]), S([0.0])).iloc[0]))
        self.assertTrue(pd.isna(safe_div(S([5.0]), S([0.0])).iloc[0]))

    def test_missing_denominator_is_null(self):
        self.assertTrue(pd.isna(safe_div(S([5.0]), S([np.nan])).iloc[0]))

    def test_missing_numerator_is_null(self):
        self.assertTrue(pd.isna(safe_div(S([np.nan]), S([5.0])).iloc[0]))

    def test_negative_denominator_is_null(self):
        self.assertTrue(pd.isna(safe_div(S([5.0]), S([-2.0])).iloc[0]))

    def test_never_returns_infinity(self):
        out = safe_div(S([1.0, 2.0, 3.0]), S([0.0, np.nan, 1.0]))
        self.assertFalse(np.isinf(out.dropna()).any())

    def test_zero_numerator_over_positive_denominator_is_zero(self):
        self.assertEqual(safe_div(S([0.0]), S([10.0])).iloc[0], 0.0)


class TestShootingEfficiency(unittest.TestCase):
    def test_fg_pct(self):
        self.assertAlmostEqual(safe_div(S([5.0]), S([10.0])).iloc[0], 0.5)

    def test_two_and_three_point_pct(self):
        self.assertAlmostEqual(safe_div(S([3.0]), S([6.0])).iloc[0], 0.5)
        self.assertTrue(pd.isna(safe_div(S([0.0]), S([0.0])).iloc[0]),
                        "a player with no threes has an UNDEFINED 3P%")

    def test_efg_credits_the_extra_point(self):
        # 10 FGM of which 4 threes, 20 FGA -> (10 + 2)/20 = 0.60
        self.assertAlmostEqual(
            efg_pct(S([10.0]), S([4.0]), S([20.0])).iloc[0], 0.60)

    def test_efg_equals_fg_pct_when_no_threes(self):
        self.assertAlmostEqual(efg_pct(S([8.0]), S([0.0]), S([16.0])).iloc[0],
                               0.5)

    def test_ts_pct_uses_044_coefficient(self):
        # 20 pts, 15 FGA, 5 FTA -> 20 / (2*(15+2.2)) = 0.5814
        got = ts_pct(S([20.0]), S([15.0]), S([5.0])).iloc[0]
        self.assertAlmostEqual(got, 20 / (2 * (15 + 0.44 * 5)), places=6)
        self.assertEqual(FT_POSSESSION_COEF, 0.44)

    def test_ts_pct_undefined_with_no_attempts(self):
        self.assertTrue(pd.isna(ts_pct(S([0.0]), S([0.0]), S([0.0])).iloc[0]))


class TestOpportunityRates(unittest.TestCase):
    def test_per_game(self):
        self.assertAlmostEqual(per_game(S([300.0]), S([30.0])).iloc[0], 10.0)

    def test_per_40(self):
        # 200 pts in 400 minutes -> 20 per 40
        self.assertAlmostEqual(per_40(S([200.0]), S([400.0])).iloc[0], 20.0)

    def test_per_40_zero_minutes_is_null(self):
        self.assertTrue(pd.isna(per_40(S([5.0]), S([0.0])).iloc[0]))

    def test_per_100(self):
        self.assertAlmostEqual(per_100(S([50.0]), S([200.0])).iloc[0], 25.0)


class TestPossessionsAndUsage(unittest.TestCase):
    def test_team_possessions_formula(self):
        # FGA 60 + 0.44*20 - ORB 10 + TOV 12 = 70.8
        got = team_possessions(S([60.0]), S([20.0]), S([10.0]), S([12.0])).iloc[0]
        self.assertAlmostEqual(got, 60 + 0.44 * 20 - 10 + 12)

    def test_usage_pct_matches_hand_calculation(self):
        # player: 200 FGA, 100 FTA, 60 TOV, 1000 MP
        # team: 1800 FGA, 700 FTA, 450 TOV, 6600 TmMP
        got = usage_pct(S([200.0]), S([100.0]), S([60.0]), S([1000.0]),
                        S([1800.0]), S([700.0]), S([450.0]), S([6600.0])).iloc[0]
        num = (200 + 0.44 * 100 + 60) * (6600 / 5)
        den = 1000 * (1800 + 0.44 * 700 + 450)
        self.assertAlmostEqual(got, 100 * num / den, places=6)

    def test_usage_undefined_with_zero_minutes(self):
        self.assertTrue(pd.isna(
            usage_pct(S([1.0]), S([1.0]), S([1.0]), S([0.0]),
                      S([1.0]), S([1.0]), S([1.0]), S([1.0])).iloc[0]))

    def test_tov_pct(self):
        got = tov_pct(S([60.0]), S([200.0]), S([100.0])).iloc[0]
        self.assertAlmostEqual(got, 100 * 60 / (200 + 0.44 * 100 + 60))

    def test_ast_pct(self):
        # MP 1000, TmMP 6600 -> share = 1000/1320
        got = ast_pct(S([150.0]), S([1000.0]), S([6600.0]), S([900.0]),
                      S([180.0])).iloc[0]
        den = (1000 / (6600 / 5)) * 900 - 180
        self.assertAlmostEqual(got, 100 * 150 / den, places=6)


class TestRebounding(unittest.TestCase):
    def test_rebound_pct_formula(self):
        got = rebound_pct(S([100.0]), S([1000.0]), S([6600.0]),
                          S([400.0]), S([600.0])).iloc[0]
        self.assertAlmostEqual(got,
                               100 * (100 * (6600 / 5)) / (1000 * (400 + 600)))

    def test_rebound_pct_undefined_without_opportunity(self):
        self.assertTrue(pd.isna(rebound_pct(S([1.0]), S([100.0]), S([1000.0]),
                                            S([0.0]), S([0.0])).iloc[0]))


class TestDefensiveProduction(unittest.TestCase):
    def test_stl_pct(self):
        got = stl_pct(S([50.0]), S([1000.0]), S([6600.0]), S([2000.0])).iloc[0]
        self.assertAlmostEqual(got, 100 * (50 * 1320) / (1000 * 2000))

    def test_blk_pct_uses_opponent_two_point_attempts(self):
        got = blk_pct(S([40.0]), S([1000.0]), S([6600.0]),
                      S([1800.0]), S([600.0])).iloc[0]
        self.assertAlmostEqual(got, 100 * (40 * 1320) / (1000 * (1800 - 600)))


class TestSharesAndCreation(unittest.TestCase):
    def test_shot_shares_sum_sensibly(self):
        layup, dunk, tip, three, total = 100.0, 30.0, 10.0, 120.0, 400.0
        shares = [safe_div(S([x]), S([total])).iloc[0]
                  for x in (layup, dunk, tip, three)]
        self.assertTrue(all(0 <= s <= 1 for s in shares))
        self.assertLessEqual(sum(shares), 1.0 + 1e-9)

    def test_assisted_and_unassisted_shares_are_complements(self):
        made = 200.0
        a = safe_div(S([120.0]), S([made])).iloc[0]
        u = safe_div(S([80.0]), S([made])).iloc[0]
        self.assertAlmostEqual(a + u, 1.0)

    def test_share_undefined_when_no_attempts(self):
        self.assertTrue(pd.isna(safe_div(S([0.0]), S([0.0])).iloc[0]))


@unittest.skipUnless((ML2 / "features_2014_2025.parquet").exists(),
                     "ML-2 outputs not built")
class TestBuiltFeatureLayer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dev = pd.read_parquet(ML2 / "features_2014_2025.parquet")
        cls.hold = pd.read_parquet(ML2 / "features_2026.parquet")

    def test_population_preserved(self):
        self.assertEqual(len(self.dev), EXPECTED_ROWS["2014_2025"])
        self.assertEqual(len(self.hold), EXPECTED_ROWS["2026"])

    def test_unresolved_prospects_retained_not_dropped(self):
        # All 8 are undrafted; dropping them would remove only negatives.
        self.assertGreaterEqual(int(self.dev.hoopr_athlete_id.isna().sum()), 8)

    def test_no_target_or_denied_metadata_column(self):
        cols = {c.lower() for c in self.dev.columns}
        for bad in ("drafted", "pick", "round", "position_from_population",
                    "class_from_population", "match_method", "age",
                    "date_of_birth"):
            self.assertNotIn(bad, cols)

    def test_no_generic_jump_shot_feature(self):
        # DEC-068: the source category changes at 2020/21.
        self.assertFalse([c for c in self.dev.columns if "jump_shot" in c.lower()])

    def test_no_infinities(self):
        for c in feature_columns(self.dev):
            v = self.dev[c].dropna()
            self.assertFalse(np.isinf(v).any(), f"{c} contains infinity")

    def test_undefined_ratios_are_null_not_zero(self):
        # A player with zero three-point attempts must have NULL 3P%, not 0.
        z = self.dev[self.dev.three_points_attempted == 0]
        if len(z):
            self.assertTrue(z.three_point_pct.isna().all())

    def test_percentages_in_range(self):
        for c in ("fg_pct", "ts_pct", "efg_pct", "ft_pct"):
            v = self.dev[c].dropna()
            self.assertTrue(((v >= 0) & (v <= 1)).all(), c)
        for c in ("usage_pct", "orb_pct", "drb_pct", "blk_pct"):
            v = self.dev[c].dropna()
            self.assertTrue(((v >= 0) & (v <= 100)).all(), c)

    def test_position_is_coarse_only(self):
        self.assertTrue(set(self.dev.position_3.unique())
                        <= {"G", "F", "C", "UNKNOWN"})

    def test_holdout_uses_identical_schema(self):
        self.assertEqual(set(self.dev.columns), set(self.hold.columns))

    def test_holdout_disjoint_from_development(self):
        self.assertFalse(set(self.dev.canonical_prospect_id)
                         & set(self.hold.canonical_prospect_id))


class TestHoldoutTargetGuard(unittest.TestCase):
    def test_feature_builder_never_reads_a_targets_file(self):
        """No read_parquet call in the feature path may name a targets file."""
        src = (ROOT / "scripts" / "build_ml2_features.py").read_text()
        reads = [ln.strip() for ln in src.splitlines() if "read_parquet" in ln]
        self.assertTrue(reads, "expected the builder to read something")
        offenders = [ln for ln in reads if "target" in ln.lower()]
        self.assertFalse(offenders,
                         f"feature path reads target data: {offenders}")

    def test_feature_builder_reads_only_ml0_features_and_raw_box(self):
        src = (ROOT / "scripts" / "build_ml2_features.py").read_text()
        self.assertIn("features_{label}", src)
        self.assertNotIn("targets_{label}", src)

    def test_validator_refuses_the_2026_target_file(self):
        import validate_ml2_features as v
        with self.assertRaises(AssertionError):
            v.load_targets_guarded("2026")


if __name__ == "__main__":
    unittest.main(verbosity=2)
