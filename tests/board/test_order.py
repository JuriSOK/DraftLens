"""Tests for Draft Order target design and ranking (stdlib unittest).

Behavioural guards on the methodology, not on the numbers: they must keep
passing if the data is refreshed. Anything asserting a specific score belongs
in tests/integration/test_frozen_anchors.py instead.

  ./.venv/bin/python -m unittest discover -s tests -v
"""

import unittest

import numpy as np
import pandas as pd

from board.order import (DRAFT_ORDER, draft_sizes, fit_predict_fold,
                         order_metrics, strength, to_pick, to_target)
from board.probability import feature_set
from data.build import load_development, load_draft_order
from validation import DENIED, DENIED_SUBSTR, HOLDOUT_YEAR, assert_no_holdout, folds

TARGET_IDS = ("RAW_PICK", "LOG_PICK", "PICK_PERCENTILE", "DRAFT_VALUE")
FEATS = feature_set("SET_2_BOX_SHOT_PROFILE")
SIZES = draft_sizes()


def synthetic(years, n_each=30, seed=0):
    """Drafted-only frame with the columns the Draft Order pipeline touches."""
    rng = np.random.default_rng(seed)
    rows = []
    for y in years:
        size = SIZES.get(y, 60)
        picks = rng.permutation(np.arange(1, size + 1))[:n_each]
        for i, pk in enumerate(picks):
            skill = -float(pk) / size + rng.normal(scale=0.3)
            rows.append(dict(
                draft_year=y, canonical_prospect_id=f"{y}-{i}", drafted=1,
                pick=int(pk), draft_size=size,
                position_3=rng.choice(["G", "F", "C"]),
                hoopr_athlete_id=float(i),
                **{f: float(skill + rng.normal()) for f in FEATS}))
    return pd.DataFrame(rows)


class TestDraftOrderPopulation(unittest.TestCase):
    def test_population_is_drafted_only(self):
        d = load_draft_order()
        self.assertTrue((d.drafted == 1).all())
        self.assertEqual(int((d.drafted == 0).sum()), 0)

    def test_every_row_has_a_real_pick(self):
        d = load_draft_order()
        self.assertTrue(d.pick.notna().all())
        self.assertTrue((d.pick >= 1).all())

    def test_no_synthetic_sentinel_picks(self):
        d = load_draft_order()
        for sentinel in (0, 61, 100, 999, -1):
            self.assertEqual(int((d.pick == sentinel).sum()), 0,
                             f"sentinel {sentinel} present")

    def test_undrafted_prospects_are_removed_not_relabelled(self):
        """The Draft Order population must be a strict subset of the
        development one — removing undrafted rows, never assigning them a
        pick."""
        full = load_development()
        d = load_draft_order()
        self.assertLess(len(d), len(full))
        self.assertEqual(set(d.canonical_prospect_id),
                         set(full.loc[full.drafted == 1,
                                      "canonical_prospect_id"]))

    def test_holdout_year_never_loads(self):
        for rob in (False, True):
            self.assertNotIn(HOLDOUT_YEAR, set(load_draft_order(rob).draft_year))


class TestTargetTransforms(unittest.TestCase):
    def setUp(self):
        self.picks = np.arange(1, 61, dtype="float64")
        self.size = np.full(60, 60.0)

    def test_all_targets_are_strictly_monotonic(self):
        directions = {"RAW_PICK": "LOWER", "LOG_PICK": "LOWER",
                     "PICK_PERCENTILE": "LOWER", "DRAFT_VALUE": "HIGHER"}
        for tid, direction in directions.items():
            y = to_target(self.picks, self.size, tid)
            d = np.diff(y)
            if direction == "LOWER":
                self.assertTrue((d > 0).all(), tid)
            else:
                self.assertTrue((d < 0).all(), tid)

    def test_inverse_transform_recovers_the_pick(self):
        for tid in TARGET_IDS:
            y = to_target(self.picks, self.size, tid)
            np.testing.assert_allclose(to_pick(y, self.size, tid), self.picks,
                                       err_msg=tid)

    def test_transforms_preserve_ranking_order(self):
        ref = np.argsort(strength(self.picks))
        for tid in TARGET_IDS:
            back = to_pick(to_target(self.picks, self.size, tid),
                           self.size, tid)
            np.testing.assert_array_equal(np.argsort(strength(back)), ref, tid)

    def test_pick_percentile_formula(self):
        """(pick - 1) / (draft_size - 1), exactly 0 at pick 1 and 1 at the last."""
        for size in (58, 59, 60):
            s = np.full(3, float(size))
            y = to_target(np.array([1.0, 2.0, float(size)]), s,
                          "PICK_PERCENTILE")
            self.assertAlmostEqual(y[0], 0.0)
            self.assertAlmostEqual(y[1], 1.0 / (size - 1))
            self.assertAlmostEqual(y[2], 1.0)

    def test_draft_value_formula(self):
        for size in (58, 59, 60):
            s = np.full(2, float(size))
            y = to_target(np.array([1.0, float(size)]), s, "DRAFT_VALUE")
            self.assertAlmostEqual(y[0], 1.0)
            self.assertAlmostEqual(y[1], 1.0 / size)

    def test_pick_percentile_is_year_normalised(self):
        """The same pick in drafts of different size maps to different values —
        that is the entire point of the target."""
        a = to_target(np.array([30.0]), np.array([60.0]), "PICK_PERCENTILE")
        b = to_target(np.array([30.0]), np.array([58.0]), "PICK_PERCENTILE")
        self.assertNotAlmostEqual(float(a[0]), float(b[0]))

    def test_unknown_target_is_rejected(self):
        with self.assertRaises(ValueError):
            to_target(self.picks, self.size, "NOT_A_TARGET")
        with self.assertRaises(ValueError):
            to_pick(self.picks, self.size, "NOT_A_TARGET")


class TestOrientation(unittest.TestCase):
    """Lower pick = better. Higher strength = better. One convention only."""

    def test_strength_is_higher_for_earlier_picks(self):
        self.assertGreater(strength(1.0), strength(2.0))
        self.assertGreater(strength(np.array([5.0]))[0],
                           strength(np.array([50.0]))[0])

    def test_best_pick_has_maximum_strength(self):
        picks = np.array([14.0, 1.0, 60.0, 30.0])
        self.assertEqual(int(np.argmax(strength(picks))), 1)

    def test_perfect_prediction_gives_spearman_one(self):
        picks = np.arange(1, 31, dtype="float64")
        m = order_metrics(picks, picks, np.full(30, 60.0))
        self.assertAlmostEqual(m["spearman"], 1.0, places=6)
        self.assertAlmostEqual(m["kendall_tau"], 1.0, places=6)
        self.assertAlmostEqual(m["ndcg"], 1.0, places=6)

    def test_reversed_prediction_gives_spearman_minus_one(self):
        """Guards the sign trap: a model that ranks the board backwards must
        score -1, not +1."""
        picks = np.arange(1, 31, dtype="float64")
        m = order_metrics(picks, picks[::-1], np.full(30, 60.0))
        self.assertAlmostEqual(m["spearman"], -1.0, places=6)
        self.assertLess(m["ndcg"], 1.0)

    def test_ndcg_rewards_putting_early_picks_first(self):
        picks = np.array([1.0, 2.0, 3.0, 58.0, 59.0, 60.0])
        size = np.full(6, 60.0)
        good = order_metrics(picks, picks, size)["ndcg"]
        bad = order_metrics(picks, picks[::-1], size)["ndcg"]
        self.assertGreater(good, bad)

    def test_every_target_yields_the_same_orientation(self):
        """Whatever the target's direction, predictions are inverse-transformed
        to the pick scale first, so orientation cannot flip per target."""
        picks = np.arange(1, 21, dtype="float64")
        size = np.full(20, 60.0)
        for tid in TARGET_IDS:
            back = to_pick(to_target(picks, size, tid), size, tid)
            self.assertAlmostEqual(
                order_metrics(picks, back, size)["spearman"], 1.0, places=6)

    def test_constant_prediction_yields_null_rank_metrics(self):
        """A constant predictor has no ranking; reporting Spearman 1.0 for it
        would be a tie-break bug."""
        picks = np.arange(1, 21, dtype="float64")
        m = order_metrics(picks, np.full(20, 30.0), np.full(20, 60.0))
        self.assertTrue(m["constant_prediction"])
        self.assertIsNone(m["spearman"])
        self.assertIsNone(m["ndcg"])
        self.assertIsNotNone(m["mae_pick"])


class TestFeatureAndTargetSeparation(unittest.TestCase):
    def test_target_fields_are_not_features(self):
        for name in ("SET_2_BOX_SHOT_PROFILE", "SET_2R_REDUCED"):
            for c in feature_set(name):
                self.assertNotIn(c, {"pick", "round", "drafted",
                                     "drafting_team", "draft_size"},
                                 f"{c} in {name}")

    def test_no_denied_feature_in_either_set(self):
        for name in ("SET_2_BOX_SHOT_PROFILE", "SET_2R_REDUCED"):
            for c in feature_set(name):
                self.assertNotIn(c, DENIED)
                for s in DENIED_SUBSTR:
                    self.assertNotIn(s, c.lower())


class TestFolds(unittest.TestCase):
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


class TestNoDroppedProspects(unittest.TestCase):
    def test_every_validation_row_gets_a_prediction(self):
        df = synthetic([2014, 2015, 2016])
        tr, va = df[df.draft_year < 2016], df[df.draft_year == 2016]
        p, _ = fit_predict_fold(tr, va, FEATS)
        self.assertEqual(len(p), len(va))
        self.assertTrue(np.isfinite(p).all())

    def test_missing_features_are_imputed_not_dropped(self):
        df = synthetic([2014, 2015, 2016])
        df.loc[df.index[:15], FEATS[0]] = np.nan
        tr, va = df[df.draft_year < 2016], df[df.draft_year == 2016]
        p, _ = fit_predict_fold(tr, va, FEATS)
        self.assertEqual(len(p), len(va))
        self.assertFalse(np.isnan(p).any())


class TestDeterminism(unittest.TestCase):
    def test_same_inputs_give_identical_predictions(self):
        df = synthetic([2014, 2015, 2016])
        tr, va = df[df.draft_year < 2016], df[df.draft_year == 2016]
        a, _ = fit_predict_fold(tr, va, FEATS, family=DRAFT_ORDER["family"],
                                params={"alpha": DRAFT_ORDER["alpha"]})
        b, _ = fit_predict_fold(tr, va, FEATS, family=DRAFT_ORDER["family"],
                                params={"alpha": DRAFT_ORDER["alpha"]})
        np.testing.assert_allclose(a, b)


class TestDraftSizes(unittest.TestCase):
    def test_every_year_has_a_declared_draft_size(self):
        d = load_draft_order()
        self.assertTrue(d.draft_size.notna().all()
                        if "draft_size" in d else True)
        for y in d.draft_year.unique():
            self.assertIn(int(y), SIZES)

    def test_declared_sizes_bound_observed_picks(self):
        for rob in (False, True):
            d = load_draft_order(rob)
            sizes = d.draft_year.map(SIZES)
            self.assertTrue((d.pick <= sizes).all())

    def test_holdout_year_absent_from_draft_sizes(self):
        self.assertNotIn(HOLDOUT_YEAR, SIZES)

    def test_sizes_are_plausible_draft_lengths(self):
        for y, s in SIZES.items():
            self.assertTrue(55 <= s <= 60, f"{y}: {s}")


class TestHoldoutFirewall(unittest.TestCase):
    def test_order_loader_refuses_the_holdout(self):
        with self.assertRaises(AssertionError):
            assert_no_holdout(pd.DataFrame({"draft_year": [2025, 2026]}), "t")


if __name__ == "__main__":
    unittest.main()
