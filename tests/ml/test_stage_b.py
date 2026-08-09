"""Tests for ML-5 Stage B target design and draft ranking (stdlib unittest).

Behavioural guards on the methodology, not on the numbers: they must keep
passing if the data is refreshed. Anything asserting a specific score belongs
in scripts/experiments/validate_ml5_stage_b.py instead.

  ./.venv/bin/python -m unittest discover -s tests -v
"""

import importlib.util
import json
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "experiments"))

from draftlens.leakage import DENIED, DENIED_SUBSTR  # noqa: E402
from draftlens.ml.validation import HOLDOUT_YEAR, folds  # noqa: E402
from draftlens.ml.validation import load_fold_config as load_ml3_config  # noqa: E402
from draftlens.ml.baselines import (b5a_global_mean_pick,  # noqa: E402
                                    b5b_position_mean_pick)
from draftlens.ml.metrics import stage_b_metrics, strength, tier_metrics  # noqa: E402
from draftlens.ml.stage_b import to_pick, to_target, tier_of  # noqa: E402
from ml5_stage_b_selection import (BASELINES, CFG5, DRAFT_SIZE,  # noqa: E402
                                   SELECTED_MODEL, SELECTED_TARGET, feature_set,
                                   fit_predict, load_stage_b, make_estimator,
                                   make_pipeline)

CFG3 = load_ml3_config()
MODEL_IDS = [m["id"] for m in CFG5["models"]]
TARGET_IDS = [t["id"] for t in CFG5["targets"]]
FEATS = feature_set("SET_2_BOX_SHOT_PROFILE")


def synthetic(years, n_each=30, seed=0):
    """Drafted-only frame with the columns the Stage B pipeline touches."""
    rng = np.random.default_rng(seed)
    rows = []
    for y in years:
        size = DRAFT_SIZE.get(y, 60)
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


class TestStageBPopulation(unittest.TestCase):
    def test_population_is_drafted_only(self):
        d = load_stage_b()
        self.assertTrue((d.drafted == 1).all())
        self.assertEqual(int((d.drafted == 0).sum()), 0)

    def test_population_size_matches_config(self):
        self.assertEqual(len(load_stage_b()), CFG5["expected_rows"])

    def test_every_row_has_a_real_pick(self):
        d = load_stage_b()
        self.assertTrue(d.pick.notna().all())
        self.assertTrue((d.pick >= 1).all())

    def test_no_synthetic_sentinel_picks(self):
        d = load_stage_b()
        for sentinel in (0, 61, 100, 999, -1):
            self.assertEqual(int((d.pick == sentinel).sum()), 0,
                             f"sentinel {sentinel} present")

    def test_no_pick_exceeds_its_draft_size(self):
        d = load_stage_b()
        self.assertTrue((d.pick <= d.draft_size).all())

    def test_undrafted_prospects_are_removed_not_relabelled(self):
        """The Stage B population must be a strict subset of the Stage A one —
        removing undrafted rows, never assigning them a pick."""
        from draftlens.ml.datasets import load_development
        full = load_development()
        d = load_stage_b()
        self.assertLess(len(d), len(full))
        self.assertEqual(set(d.canonical_prospect_id),
                         set(full.loc[full.drafted == 1,
                                      "canonical_prospect_id"]))

    def test_holdout_year_never_loads(self):
        for rob in (False, True):
            self.assertNotIn(HOLDOUT_YEAR, set(load_stage_b(rob).draft_year))


class TestTargetTransforms(unittest.TestCase):
    def setUp(self):
        self.picks = np.arange(1, 61, dtype="float64")
        self.size = np.full(60, 60.0)

    def test_all_targets_are_strictly_monotonic(self):
        for t in CFG5["targets"]:
            y = to_target(self.picks, self.size, t["id"])
            d = np.diff(y)
            if t["direction"] == "LOWER_IS_BETTER":
                self.assertTrue((d > 0).all(), t["id"])
            else:
                self.assertTrue((d < 0).all(), t["id"])

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
        m = stage_b_metrics(picks, picks, np.full(30, 60.0))
        self.assertAlmostEqual(m["spearman"], 1.0, places=6)
        self.assertAlmostEqual(m["kendall_tau"], 1.0, places=6)
        self.assertAlmostEqual(m["ndcg"], 1.0, places=6)

    def test_reversed_prediction_gives_spearman_minus_one(self):
        """Guards the sign trap: a model that ranks the board backwards must
        score -1, not +1."""
        picks = np.arange(1, 31, dtype="float64")
        m = stage_b_metrics(picks, picks[::-1], np.full(30, 60.0))
        self.assertAlmostEqual(m["spearman"], -1.0, places=6)
        self.assertLess(m["ndcg"], 1.0)

    def test_ndcg_rewards_putting_early_picks_first(self):
        picks = np.array([1.0, 2.0, 3.0, 58.0, 59.0, 60.0])
        size = np.full(6, 60.0)
        good = stage_b_metrics(picks, picks, size)["ndcg"]
        bad = stage_b_metrics(picks, picks[::-1], size)["ndcg"]
        self.assertGreater(good, bad)

    def test_every_target_yields_the_same_orientation(self):
        """Whatever the target's direction, predictions are inverse-transformed
        to the pick scale first, so orientation cannot flip per target."""
        picks = np.arange(1, 21, dtype="float64")
        size = np.full(20, 60.0)
        for tid in TARGET_IDS:
            back = to_pick(to_target(picks, size, tid), size, tid)
            self.assertAlmostEqual(
                stage_b_metrics(picks, back, size)["spearman"], 1.0, places=6)


class TestTiers(unittest.TestCase):
    def test_tier_boundaries_match_the_config(self):
        b = CFG5["tier_target"]["boundaries"]
        self.assertEqual(tier_of(np.array([1]))[0], 0)
        self.assertEqual(tier_of(np.array([b["1_lottery"][1]]))[0], 0)
        self.assertEqual(tier_of(np.array([b["1_lottery"][1] + 1]))[0], 1)
        self.assertEqual(tier_of(np.array([b["2_rest_of_r1"][1]]))[0], 1)
        self.assertEqual(tier_of(np.array([b["2_rest_of_r1"][1] + 1]))[0], 2)
        self.assertEqual(tier_of(np.array([60]))[0], 2)

    def test_tier_index_is_ordered_worse_with_later_picks(self):
        t = tier_of(np.array([1, 14, 15, 30, 31, 60]))
        self.assertTrue((np.diff(t) >= 0).all())

    def test_adopted_scheme_has_better_support_than_traditional(self):
        """ML_SPEC 6.3 requires boundaries to be justified against density, not
        tradition."""
        d = load_stage_b()
        trad = np.select([d.pick <= 14, d.pick <= 30, d.pick <= 45],
                         [0, 1, 2], 3)
        ct4 = pd.crosstab(d.draft_year, trad)
        ct3 = pd.crosstab(d.draft_year, tier_of(d.pick.to_numpy()))
        self.assertGreater(int((ct4 < 5).sum().sum()),
                           int((ct3 < 5).sum().sum()))

    def test_tier_metrics_respect_order(self):
        a = np.array([0, 0, 1, 2])
        self.assertEqual(tier_metrics(a, a)["exact_tier_accuracy"], 1.0)
        self.assertEqual(tier_metrics(a, a)["ordered_distance_error"], 0.0)
        far = tier_metrics(np.array([0]), np.array([2]))
        near = tier_metrics(np.array([0]), np.array([1]))
        self.assertGreater(far["ordered_distance_error"],
                           near["ordered_distance_error"])
        self.assertEqual(near["adjacent_tier_accuracy"], 1.0)
        self.assertEqual(far["adjacent_tier_accuracy"], 0.0)

    def test_ordinal_limitation_is_documented(self):
        self.assertIn("ordinal", CFG5["tier_target"]["limitation"].lower())


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

    def test_fitted_model_never_sees_pick(self):
        df = synthetic([2014, 2015])
        pipe = make_pipeline(CFG5["models"][0], FEATS)
        pipe.fit(df, to_target(df.pick, df.draft_size, "RAW_PICK"))
        names = list(pipe.named_steps["pre"].get_feature_names_out())
        for banned in ("pick", "round", "drafted", "draft_size"):
            self.assertFalse([n for n in names
                              if n.split("__", 1)[-1] == banned])

    def test_position_source_is_the_leakage_safe_one(self):
        pipe = make_pipeline(CFG5["models"][0], FEATS)
        self.assertEqual(pipe.named_steps["pre"].transformers[1][2],
                         ["position_3"])

    def test_stage_b_representation_matches_what_was_validated(self):
        """ML-5 declared it would inherit Stage A's SEASON_RELATIVE
        representation but never called `season_relative`, so every published
        Stage B number was measured on STANDARD. The config records STANDARD
        because that is what the evidence supports; adopting SEASON_RELATIVE
        would move macro Spearman 0.2968 -> 0.2999 and needs its own phase.
        See docs/experiments/ML5_STAGE_B.md, correction notice."""
        from draftlens.ml.stage_b import STAGE_B
        fa = CFG5["frozen_stage_a_representation"]
        self.assertEqual(fa["feature_set"], "SET_2_BOX_SHOT_PROFILE")
        self.assertEqual(fa["normalization"], "STANDARD")
        self.assertEqual(STAGE_B["normalization"], "STANDARD")
        self.assertEqual(fa["missing_strategy"], "B_TRAIN_MEDIAN")
        self.assertEqual(fa["position_handling"], "ONEHOT")


class TestFolds(unittest.TestCase):
    def test_outer_folds_are_the_ml3_folds(self):
        self.assertEqual([vy for _, _, vy in folds(CFG3)],
                         [2019, 2020, 2021, 2022, 2023, 2024, 2025])

    def test_training_years_strictly_precede_validation(self):
        for fold, tr, vy in folds(CFG3):
            self.assertLess(max(tr), vy, f"fold {fold}")

    def test_no_fold_touches_the_holdout(self):
        for _, tr, vy in folds(CFG3):
            self.assertNotIn(HOLDOUT_YEAR, tr)
            self.assertNotEqual(vy, HOLDOUT_YEAR)

    def test_robustness_years_are_disjoint_from_folds(self):
        val = {vy for _, _, vy in folds(CFG3)}
        train = {y for _, tr, _ in folds(CFG3) for y in tr}
        self.assertFalse(set(CFG5["robustness_years"]) & (val | train))


class TestNoDroppedProspects(unittest.TestCase):
    def test_every_validation_row_gets_a_prediction(self):
        df = synthetic([2014, 2015, 2016])
        tr, va = df[df.draft_year < 2016], df[df.draft_year == 2016]
        p, _ = fit_predict(CFG5["models"][0], "RAW_PICK", tr, va, FEATS)
        self.assertEqual(len(p), len(va))
        self.assertTrue(np.isfinite(p).all())

    def test_missing_features_are_imputed_not_dropped(self):
        df = synthetic([2014, 2015, 2016])
        df.loc[df.index[:15], FEATS[0]] = np.nan
        tr, va = df[df.draft_year < 2016], df[df.draft_year == 2016]
        p, _ = fit_predict(CFG5["models"][0], "RAW_PICK", tr, va, FEATS)
        self.assertEqual(len(p), len(va))
        self.assertFalse(np.isnan(p).any())

    def test_no_missing_indicator_columns_are_added(self):
        df = synthetic([2014, 2015])
        pipe = make_pipeline(CFG5["models"][0], FEATS)
        pipe.fit(df, to_target(df.pick, df.draft_size, "RAW_PICK"))
        names = list(pipe.named_steps["pre"].get_feature_names_out())
        self.assertFalse([n for n in names if "missing" in n.lower()])
        self.assertEqual(len([n for n in names if n.startswith("num__")]),
                         len(FEATS))


class TestBaselines(unittest.TestCase):
    def test_global_mean_baseline_is_constant(self):
        df = synthetic([2014, 2015])
        tr, va = df[df.draft_year == 2014], df[df.draft_year == 2015]
        p = b5a_global_mean_pick(tr, va)
        self.assertEqual(len(np.unique(p)), 1)

    def test_constant_prediction_yields_null_rank_metrics(self):
        """A constant predictor has no ranking; reporting Spearman 1.0 for it
        would be the ML-3 NDCG tie-break bug all over again."""
        picks = np.arange(1, 21, dtype="float64")
        m = stage_b_metrics(picks, np.full(20, 30.0), np.full(20, 60.0))
        self.assertTrue(m["constant_prediction"])
        self.assertIsNone(m["spearman"])
        self.assertIsNone(m["ndcg"])
        self.assertIsNotNone(m["mae_pick"])

    def test_position_baseline_uses_training_history_only(self):
        df = synthetic([2014, 2015])
        tr, va = df[df.draft_year == 2014], df[df.draft_year == 2015]
        p = b5b_position_mean_pick(tr, va)
        self.assertEqual(len(p), len(va))
        self.assertTrue(set(np.unique(p)) <=
                        set(tr.groupby("position_3").pick.mean()) |
                        {float(tr.pick.mean())})

    def test_all_three_baselines_declared(self):
        self.assertEqual({b["id"] for b in CFG5["baselines"]},
                         set(BASELINES))


class TestDeterminism(unittest.TestCase):
    def test_same_inputs_give_identical_predictions(self):
        df = synthetic([2014, 2015, 2016])
        tr, va = df[df.draft_year < 2016], df[df.draft_year == 2016]
        for mid in ("RIDGE_a10", "RF_d4_leaf20", "HGB_lr005_leaf8"):
            m = next(x for x in CFG5["models"] if x["id"] == mid)
            a, _ = fit_predict(m, "RAW_PICK", tr, va, FEATS)
            b, _ = fit_predict(m, "RAW_PICK", tr, va, FEATS)
            np.testing.assert_allclose(a, b, err_msg=mid)

    def test_stochastic_estimators_carry_a_fixed_seed(self):
        for m in CFG5["models"]:
            if m["family"] == "Ridge":
                continue          # deterministic solver, no seed needed
            self.assertEqual(getattr(make_estimator(m), "random_state", None),
                             CFG5["seed"], m["id"])

    def test_target_z_scoring_is_rank_preserving(self):
        """The train-fold z-score is a numerical conditioning step; it must not
        change anything the report depends on."""
        y = np.array([1.0, 5.0, 10.0, 40.0, 60.0])
        z = (y - y.mean()) / y.std()
        np.testing.assert_array_equal(np.argsort(y), np.argsort(z))


class TestSelectionDesign(unittest.TestCase):
    def test_no_random_cv(self):
        self.assertTrue(CFG5["design"]["no_random_cv"])

    def test_selection_is_predeclared(self):
        self.assertIn(SELECTED_MODEL, MODEL_IDS)
        self.assertIn(SELECTED_TARGET, TARGET_IDS)

    def test_all_four_ml_spec_target_designs_are_covered(self):
        self.assertIn("RAW_PICK", TARGET_IDS)
        self.assertTrue(any(t in TARGET_IDS
                            for t in ("LOG_PICK", "DRAFT_VALUE")))
        self.assertEqual(CFG5["tier_target"]["id"], "TIER_3")
        self.assertEqual(CFG5["direct_ranking"]["evaluated"],
                         "AS EVALUATION OBJECTIVE ONLY")

    def test_no_ranking_library_was_installed(self):
        for mod in ("xgboost", "lightgbm", "catboost", "optuna", "shap",
                    "mlflow", "tensorflow", "torch", "lightning",
                    "allrank", "pyltr"):
            self.assertIsNone(importlib.util.find_spec(mod),
                              f"{mod} must not be installed")

    def test_ranking_metrics_outrank_numeric_in_the_selection_priority(self):
        pri = CFG5["metrics"]["selection_priority"]
        self.assertIn("Spearman", pri[0])
        self.assertIn("NDCG", pri[1])
        self.assertTrue(any("MAE" in p for p in pri[4:]))


class TestDraftSizes(unittest.TestCase):
    def test_every_year_has_a_declared_draft_size(self):
        d = load_stage_b()
        self.assertTrue(d.draft_size.notna().all())
        for y in d.draft_year.unique():
            self.assertIn(int(y), DRAFT_SIZE)

    def test_declared_sizes_bound_observed_picks(self):
        for rob in (False, True):
            d = load_stage_b(rob)
            self.assertTrue((d.pick <= d.draft_size).all())

    def test_holdout_year_absent_from_draft_sizes(self):
        self.assertNotIn(HOLDOUT_YEAR, DRAFT_SIZE)

    def test_sizes_are_plausible_draft_lengths(self):
        for y, s in DRAFT_SIZE.items():
            self.assertTrue(55 <= s <= 60, f"{y}: {s}")


class TestHoldoutFirewall(unittest.TestCase):
    def test_run_script_never_loads_holdout_targets(self):
        """Only the run script is scanned: the validator contains
        these strings precisely because it is the code that forbids them."""
        src = (ROOT / "scripts" / "experiments" / "ml5_stage_b_selection.py").read_text()
        for banned in ("targets_2026", "features_2026", "predictions_2026"):
            self.assertNotIn(banned, src)

    def test_validator_enforces_the_holdout_ban(self):
        src = (ROOT / "scripts" / "experiments" / "validate_ml5_stage_b.py").read_text()
        self.assertIn("targets_2026", src)
        self.assertIn("HOLDOUT_YEAR", src)

    def test_config_declares_the_holdout_is_untouched(self):
        self.assertTrue(any("2026" in n for n in CFG5["notes"]))

    def test_stage_b_loader_refuses_the_holdout(self):
        from draftlens.ml.validation import assert_no_holdout
        with self.assertRaises(AssertionError):
            assert_no_holdout(pd.DataFrame({"draft_year": [2025, 2026]}), "t")


if __name__ == "__main__":
    unittest.main()
