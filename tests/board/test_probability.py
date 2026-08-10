"""Tests for Draft Probability feature safety and representation (stdlib
unittest).

Behavioural guards on the methodology, not on the numbers: they must keep
passing if the data is refreshed. Anything asserting a specific score belongs
in tests/integration/test_frozen_anchors.py instead.

  ./.venv/bin/python -m unittest discover -s tests -v
"""

import importlib.util
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from board.preprocessing import SEASON_RELATIVE_METRICS, season_relative
from board.probability import (DRAFT_PROBABILITY, calibration_bins,
                               expected_calibration_error, feature_set,
                               fit_predict_fold)
from validation import (DENIED, DENIED_SUBSTR, HOLDOUT_YEAR,
                        LOW_SUPPORT_YEAR, assert_no_holdout, folds)

ROOT = Path(__file__).resolve().parents[2]


def synthetic(years, n_each=40, seed=0):
    """A frame with the columns the pipeline touches. Signal is deliberate so
    that a fitted model is non-degenerate."""
    rng = np.random.default_rng(seed)
    rows = []
    for y in years:
        for i in range(n_each):
            skill = rng.normal()
            rows.append(dict(
                draft_year=y, canonical_prospect_id=f"{y}-{i}",
                drafted=int(skill + rng.normal(scale=0.5) > 0),
                position_3=rng.choice(["G", "F", "C"]),
                hoopr_athlete_id=float(i),
                **{f: float(skill + rng.normal())
                   for f in feature_set("SET_2_BOX_SHOT_PROFILE")}))
    return pd.DataFrame(rows)


class TestFoldDesign(unittest.TestCase):
    def test_outer_folds_are_the_frozen_folds(self):
        self.assertEqual([vy for _, _, vy in folds()],
                         [2019, 2020, 2021, 2022, 2023, 2024, 2025])

    def test_training_years_strictly_precede_validation(self):
        for fold, tr, vy in folds():
            self.assertLess(max(tr), vy, f"fold {fold}")

    def test_no_fold_touches_the_holdout(self):
        for _, tr, vy in folds():
            self.assertNotIn(HOLDOUT_YEAR, tr)
            self.assertNotEqual(vy, HOLDOUT_YEAR)

    def test_window_is_expanding_not_sliding(self):
        sizes = [len(tr) for _, tr, _ in folds()]
        self.assertEqual(sizes, sorted(sizes))
        self.assertLess(sizes[0], sizes[-1])


class TestFeatureSafety(unittest.TestCase):
    def test_no_denied_feature_in_either_set(self):
        for name in ("SET_2_BOX_SHOT_PROFILE", "SET_2R_REDUCED"):
            for c in feature_set(name):
                self.assertNotIn(c, DENIED, f"{c} in {name}")
                for s in DENIED_SUBSTR:
                    self.assertNotIn(s, c.lower(), f"{c} in {name}")

    def test_reduced_set_is_a_strict_subset(self):
        full = set(feature_set("SET_2_BOX_SHOT_PROFILE"))
        red = set(feature_set("SET_2R_REDUCED"))
        self.assertTrue(red < full)

    def test_position_source_is_the_leakage_safe_one(self):
        from board.probability import build_pipeline
        pipe = build_pipeline(feature_set("SET_2_BOX_SHOT_PROFILE"))
        cols = pipe.named_steps["pre"].transformers[1][2]
        self.assertEqual(cols, ["position_3"])


class TestSeasonRelative(unittest.TestCase):
    def test_only_covered_metrics_are_rewritten(self):
        feats = feature_set("SET_2_BOX_SHOT_PROFILE")
        df = synthetic([2019])
        out = season_relative(df, feats)
        covered = set(SEASON_RELATIVE_METRICS) & set(feats)
        for c in feats:
            if c in covered:
                continue
            pd.testing.assert_series_equal(df[c], out[c], check_names=False)

    def test_reference_is_same_season_only(self):
        """Season Y must be normalised against season Y — never a later one."""
        ref = pd.read_parquet(ROOT / "data" / "interim" / "features" /
                              "ncaa_reference_distributions.parquet")
        feats = feature_set("SET_2_BOX_SHOT_PROFILE")
        a = season_relative(synthetic([2019], seed=1), feats)
        b = season_relative(synthetic([2019], seed=1), feats)
        pd.testing.assert_frame_equal(a, b)
        self.assertIn(2019, set(ref.season))

    def test_row_count_and_ids_are_preserved(self):
        df = synthetic([2019, 2020])
        out = season_relative(df, feature_set("SET_2_BOX_SHOT_PROFILE"))
        self.assertEqual(len(out), len(df))
        self.assertEqual(list(out.canonical_prospect_id),
                         list(df.canonical_prospect_id))


class TestNoDroppedProspects(unittest.TestCase):
    def test_every_validation_row_receives_a_prediction(self):
        df = synthetic([2014, 2015, 2016])
        train, valid = df[df.draft_year < 2016], df[df.draft_year == 2016]
        p, _ = fit_predict_fold(train, valid)
        self.assertEqual(len(p), len(valid))
        self.assertTrue(np.isfinite(p).all())

    def test_rows_with_missing_features_are_imputed_not_dropped(self):
        feats = feature_set("SET_2_BOX_SHOT_PROFILE")
        df = synthetic([2014, 2015, 2016])
        df.loc[df.index[:20], feats[0]] = np.nan
        train, valid = df[df.draft_year < 2016], df[df.draft_year == 2016]
        p, _ = fit_predict_fold(train, valid, feats)
        self.assertEqual(len(p), len(valid))
        self.assertFalse(np.isnan(p).any())

    def test_no_missing_indicator_columns_are_added(self):
        from board.probability import build_pipeline
        feats = feature_set("SET_2_BOX_SHOT_PROFILE")
        df = synthetic([2014, 2015])
        pipe = build_pipeline(feats)
        pipe.fit(df, df.drafted)
        names = list(pipe.named_steps["pre"].get_feature_names_out())
        self.assertFalse([n for n in names if "missing" in n.lower()])
        self.assertEqual(len([n for n in names if n.startswith("num__")]),
                         len(feats))


class TestDeterminism(unittest.TestCase):
    def test_same_seed_gives_identical_predictions(self):
        df = synthetic([2014, 2015, 2016])
        train, valid = df[df.draft_year < 2016], df[df.draft_year == 2016]
        a, _ = fit_predict_fold(train, valid)
        b, _ = fit_predict_fold(train, valid)
        np.testing.assert_allclose(a, b)


class TestLowSupportHandling(unittest.TestCase):
    def test_low_support_year_is_2025(self):
        self.assertEqual(LOW_SUPPORT_YEAR, 2025)


class TestMetrics(unittest.TestCase):
    def test_ece_is_support_weighted_and_bounded(self):
        y = np.array([0, 1] * 50)
        perfect = np.where(y == 1, 0.99, 0.01)
        self.assertLess(expected_calibration_error(y, perfect), 0.05)
        inverted = np.where(y == 1, 0.01, 0.99)
        self.assertGreater(expected_calibration_error(inverted, inverted), 0.0)

    def test_ece_and_max_gap_can_disagree(self):
        """The reason ECE is reported: one sparse decile can dominate the max
        gap while the model is well behaved across its support."""
        rng = np.random.default_rng(0)
        p = np.clip(rng.uniform(0, 1, 400), 0.01, 0.99)
        y = (rng.uniform(size=400) < p).astype(int)
        self.assertLessEqual(expected_calibration_error(y, p), 1.0)

    def test_single_class_returns_none_for_auc_not_a_crash(self):
        from board.probability import probability_metrics
        m = probability_metrics([1, 1, 1, 1], [0.9, 0.8, 0.7, 0.6])
        self.assertIsNone(m["roc_auc"])
        self.assertIsNone(m["pr_auc"])
        self.assertIsNotNone(m["brier"])

    def test_low_negative_support_flag(self):
        from board.probability import probability_metrics
        m = probability_metrics([1] * 26 + [0, 0], [0.5] * 28, 5)
        self.assertTrue(m["low_negative_support"])
        m2 = probability_metrics([1] * 20 + [0] * 20, [0.5] * 40, 5)
        self.assertFalse(m2["low_negative_support"])

    def test_perfect_ranking_gives_auc_one(self):
        from board.probability import probability_metrics
        m = probability_metrics([0, 0, 1, 1], [0.1, 0.2, 0.8, 0.9])
        self.assertAlmostEqual(m["roc_auc"], 1.0)

    def test_ranking_metrics_tie_breaking_is_not_row_order(self):
        # Constant predictions must NOT inherit the source ordering: the
        # population is built drafted-first, which would fake a perfect board.
        from board.probability import ranking_metrics
        y = [1] * 20 + [0] * 20
        p = [0.5] * 40
        m = ranking_metrics(y, p, {"drafted": 20})
        self.assertLess(m["ndcg_at_drafted"], 0.95,
                        "constant predictor must not score a near-perfect board")

    def test_ranking_metrics_perfect_ranking(self):
        from board.probability import ranking_metrics
        y = [1, 1, 0, 0]
        m = ranking_metrics(y, [0.9, 0.8, 0.2, 0.1], {"drafted": 2})
        self.assertEqual(m["precision_at_drafted"], 1.0)
        self.assertEqual(m["recall_at_drafted"], 1.0)

    def test_ranking_metrics_are_deterministic(self):
        from board.probability import ranking_metrics
        y, p = [1, 0] * 10, [0.5] * 20
        self.assertEqual(ranking_metrics(y, p, {"drafted": 10}),
                         ranking_metrics(y, p, {"drafted": 10}))


class TestHoldoutFirewall(unittest.TestCase):
    def test_development_loader_refuses_the_holdout_year(self):
        with self.assertRaises(AssertionError):
            assert_no_holdout(pd.DataFrame({"draft_year": [2025, 2026]}), "test")


if __name__ == "__main__":
    unittest.main()
