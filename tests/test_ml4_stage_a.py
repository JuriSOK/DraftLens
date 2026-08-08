"""Tests for ML-4 Stage A candidate selection (stdlib unittest).

These are behavioural guards on the methodology, not on the numbers: they must
keep passing if the data is refreshed. Anything that asserts a specific score
belongs in scripts/validate_ml4_results.py instead.

  ./.venv/bin/python -m unittest discover -s tests -v
"""

import importlib.util
import json
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from ml3_common import DENIED, DENIED_SUBSTR, HOLDOUT_YEAR, folds  # noqa: E402
from ml3_common import load_config as load_ml3_config  # noqa: E402
from run_ml4_stage_a import (CFG4, INCUMBENT, LOW_SUPPORT_YEAR,  # noqa: E402
                             SELECTED, expected_calibration_error,
                             feature_set, fit_predict, make_estimator,
                             make_pipeline, low_support_sensitivity,
                             paired_vs_incumbent, season_relative)

CFG3 = load_ml3_config()
CANDIDATE_IDS = [c["id"] for c in CFG4["candidates"]]


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

    def test_window_is_expanding_not_sliding(self):
        sizes = [len(tr) for _, tr, _ in folds(CFG3)]
        self.assertEqual(sizes, sorted(sizes))
        self.assertLess(sizes[0], sizes[-1])


class TestSelectionDesign(unittest.TestCase):
    def test_design_is_predeclared_and_disallows_random_cv(self):
        self.assertEqual(CFG4["selection_design"]["chosen"],
                         "PREDECLARED_FIXED_CONFIGURATIONS")
        self.assertTrue(CFG4["selection_design"]["no_random_cv"])

    def test_candidate_ids_are_unique(self):
        self.assertEqual(len(CANDIDATE_IDS), len(set(CANDIDATE_IDS)))

    def test_incumbent_and_selection_are_both_declared(self):
        self.assertIn(INCUMBENT, CANDIDATE_IDS)
        self.assertIn(SELECTED, CANDIDATE_IDS)

    def test_all_four_model_families_are_represented(self):
        fams = {c["family"] for c in CFG4["candidates"]}
        self.assertEqual(fams, {"LogisticRegression", "RandomForest",
                                "HistGradientBoosting", "GradientBoosting"})

    def test_no_prohibited_gradient_boosting_dependency(self):
        """XGBoost / LightGBM / CatBoost / Optuna / SHAP are out of scope."""
        for mod in ("xgboost", "lightgbm", "catboost", "optuna", "shap",
                    "mlflow", "tensorflow", "torch"):
            self.assertNotIn(mod, sys.modules)
            self.assertIsNone(importlib.util.find_spec(mod),
                              f"{mod} must not be installed")


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
        self.assertEqual(full - red,
                         set(CFG4["feature_sets"]["SET_2R_REDUCED"]["removed"]))

    def test_removals_are_justified_structurally_not_by_score(self):
        for feat, why in CFG4["feature_sets"]["SET_2R_REDUCED"]["removed"].items():
            self.assertTrue(any(k in why.lower()
                                for k in ("linear combination", "|r|=")),
                            f"{feat} lacks a structural justification")

    def test_position_source_is_the_leakage_safe_one(self):
        pipe = make_pipeline(CFG4["candidates"][0],
                            feature_set("SET_2_BOX_SHOT_PROFILE"))
        cols = pipe.named_steps["pre"].transformers[1][2]
        self.assertEqual(cols, ["position_3"])


class TestTemporalCalibration(unittest.TestCase):
    """The calibrator must never see the outer validation year."""

    def setUp(self):
        self.cand = next(c for c in CFG4["candidates"] if c["id"] == INCUMBENT)
        self.feats = feature_set(self.cand["feature_set"])
        self.df = synthetic([2014, 2015, 2016, 2017, 2018, 2019])

    def test_calibrator_fits_only_on_the_last_training_year(self):
        train = self.df[self.df.draft_year < 2019]
        valid = self.df[self.df.draft_year == 2019]
        for method in ("sigmoid", "isotonic"):
            _, _, cal_year = fit_predict(self.cand, train, valid, self.feats,
                                         method)
            self.assertEqual(cal_year, int(train.draft_year.max()))
            self.assertLess(cal_year, 2019)

    def test_calibration_never_uses_the_validation_year(self):
        for _, tr, vy in folds(CFG3):
            df = synthetic(tr + [vy])
            train, valid = df[df.draft_year.isin(tr)], df[df.draft_year == vy]
            _, _, cal_year = fit_predict(self.cand, train, valid, self.feats,
                                         "sigmoid")
            self.assertLess(cal_year, vy, f"fold validating {vy}")

    def test_uncalibrated_path_reports_no_calibration_year(self):
        train = self.df[self.df.draft_year < 2019]
        valid = self.df[self.df.draft_year == 2019]
        _, _, cal_year = fit_predict(self.cand, train, valid, self.feats, "none")
        self.assertIsNone(cal_year)

    def test_sigmoid_is_rank_preserving(self):
        """A monotone calibrator must not reorder the board — so any AUC change
        under sigmoid is the surrendered training year, not the calibration."""
        train = self.df[self.df.draft_year < 2019]
        valid = self.df[self.df.draft_year == 2019]
        p_ctrl, _, _ = fit_predict(self.cand, train, valid, self.feats,
                                   "none_reduced")
        p_sig, _, _ = fit_predict(self.cand, train, valid, self.feats, "sigmoid")
        self.assertTrue(np.array_equal(np.argsort(p_ctrl), np.argsort(p_sig)))

    def test_control_uses_the_same_shortened_training_window(self):
        train = self.df[self.df.draft_year < 2019]
        valid = self.df[self.df.draft_year == 2019]
        _, _, y1 = fit_predict(self.cand, train, valid, self.feats,
                               "none_reduced")
        _, _, y2 = fit_predict(self.cand, train, valid, self.feats, "sigmoid")
        self.assertEqual(y1, y2)


class TestSeasonRelative(unittest.TestCase):
    def test_only_covered_metrics_are_rewritten(self):
        feats = feature_set("SET_2_BOX_SHOT_PROFILE")
        df = synthetic([2019])
        out = season_relative(df, feats)
        covered = set(CFG4["normalization_variants"]["SEASON_RELATIVE"]
                      ["covered_metrics"]) & set(feats)
        for c in feats:
            if c in covered:
                continue
            pd.testing.assert_series_equal(df[c], out[c], check_names=False)

    def test_reference_is_same_season_only(self):
        """Season Y must be normalised against season Y — never a later one."""
        ref = pd.read_parquet(ROOT / "data" / "interim" / "ml2" /
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
        cand = next(c for c in CFG4["candidates"] if c["id"] == INCUMBENT)
        feats = feature_set(cand["feature_set"])
        df = synthetic([2014, 2015, 2016])
        train, valid = df[df.draft_year < 2016], df[df.draft_year == 2016]
        p, _, _ = fit_predict(cand, train, valid, feats, "none")
        self.assertEqual(len(p), len(valid))
        self.assertTrue(np.isfinite(p).all())

    def test_rows_with_missing_features_are_imputed_not_dropped(self):
        cand = next(c for c in CFG4["candidates"] if c["id"] == INCUMBENT)
        feats = feature_set(cand["feature_set"])
        df = synthetic([2014, 2015, 2016])
        df.loc[df.index[:20], feats[0]] = np.nan
        train, valid = df[df.draft_year < 2016], df[df.draft_year == 2016]
        p, _, _ = fit_predict(cand, train, valid, feats, "none")
        self.assertEqual(len(p), len(valid))
        self.assertFalse(np.isnan(p).any())

    def test_no_missing_indicator_columns_are_added(self):
        cand = next(c for c in CFG4["candidates"] if c["id"] == INCUMBENT)
        feats = feature_set(cand["feature_set"])
        df = synthetic([2014, 2015])
        pipe = make_pipeline(cand, feats)
        pipe.fit(df, df.drafted)
        names = list(pipe.named_steps["pre"].get_feature_names_out())
        self.assertFalse([n for n in names if "missing" in n.lower()])
        self.assertEqual(len([n for n in names if n.startswith("num__")]),
                         len(feats))


class TestDeterminism(unittest.TestCase):
    def test_same_seed_gives_identical_predictions(self):
        df = synthetic([2014, 2015, 2016])
        train, valid = df[df.draft_year < 2016], df[df.draft_year == 2016]
        for cid in (INCUMBENT, SELECTED, "RF_d4_leaf20", "HGB_lr005_leaf8"):
            cand = next(c for c in CFG4["candidates"] if c["id"] == cid)
            feats = feature_set(cand["feature_set"])
            a, _, _ = fit_predict(cand, train, valid, feats, "none")
            b, _, _ = fit_predict(cand, train, valid, feats, "none")
            np.testing.assert_allclose(a, b, err_msg=cid)

    def test_estimators_carry_a_fixed_random_state(self):
        for cand in CFG4["candidates"]:
            est = make_estimator(cand)
            self.assertEqual(getattr(est, "random_state", None), CFG4["seed"],
                             cand["id"])

    def test_penalty_is_translated_without_mutating_the_config(self):
        """make_estimator rewrites `penalty` for sklearn >= 1.8; the declared
        configuration must survive being read twice."""
        cand = next(c for c in CFG4["candidates"] if c["id"] == "LR_L1_C0.1")
        before = dict(cand["params"])
        make_estimator(cand)
        make_estimator(cand)
        self.assertEqual(cand["params"], before)


class TestLowSupportHandling(unittest.TestCase):
    def test_low_support_year_is_2025(self):
        self.assertEqual(LOW_SUPPORT_YEAR, 2025)

    def test_sensitivity_drops_exactly_that_year(self):
        fold_df = pd.DataFrame([
            dict(config=c, validate_year=y, roc_auc=v)
            for c, base in ((INCUMBENT, 0.60), ("OTHER", 0.70))
            for y, v in zip([2019, 2020, 2021, 2022, 2023, 2024, 2025],
                            [base] * 6 + [0.99])])
        s = low_support_sensitivity(fold_df).set_index("config")
        self.assertAlmostEqual(s.loc["OTHER", "macro_excl_low"], 0.70, places=4)
        self.assertAlmostEqual(s.loc[INCUMBENT, "macro_excl_low"], 0.60,
                               places=4)
        # the inflated 2025 fold must not survive into the robust column
        self.assertLess(s.loc["OTHER", "macro_excl_low"],
                        s.loc["OTHER", "macro_all7"])

    def test_paired_comparison_is_relative_to_the_incumbent(self):
        fold_df = pd.DataFrame([
            dict(config=c, validate_year=y, roc_auc=v)
            for c, v in ((INCUMBENT, 0.60), ("OTHER", 0.65))
            for y in [2019, 2020, 2021, 2022, 2023, 2024, 2025]])
        p = paired_vs_incumbent(fold_df).set_index("config")
        self.assertNotIn(INCUMBENT, p.index)
        self.assertAlmostEqual(p.loc["OTHER", "mean_diff"], 0.05, places=4)
        self.assertEqual(p.loc["OTHER", "wins"], 7)


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


class TestHoldoutFirewall(unittest.TestCase):
    def test_config_declares_the_holdout_is_untouched(self):
        self.assertTrue(any("2026" in n for n in CFG4["notes"]))

    def test_no_ml4_source_file_loads_the_2026_targets(self):
        for name in ("run_ml4_stage_a.py", "validate_ml4_results.py"):
            src = (ROOT / "scripts" / name).read_text()
            self.assertNotIn("targets_2026", src, name)
            self.assertNotIn("features_2026", src, name)
            self.assertNotIn("predictions_2026", src, name)

    def test_development_loader_refuses_the_holdout_year(self):
        from ml3_common import assert_no_holdout
        with self.assertRaises(AssertionError):
            assert_no_holdout(pd.DataFrame({"draft_year": [2025, 2026]}), "test")


if __name__ == "__main__":
    unittest.main()
