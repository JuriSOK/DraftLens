"""Tests for ML-3 temporal validation, baselines and guards (stdlib unittest).

  ./.venv/bin/python -m unittest discover -s tests -v
"""

import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "experiments"))

from draftlens.leakage import DENIED, DENIED_SUBSTR  # noqa: E402
from draftlens.ml.baselines import b0_prevalence  # noqa: E402
from draftlens.ml.datasets import resolve_features  # noqa: E402
from draftlens.ml.metrics import board_metrics, stage_a_metrics  # noqa: E402
from draftlens.ml.preprocessing import make_pipeline, position_median_impute  # noqa: E402
from draftlens.ml.validation import (HOLDOUT_YEAR, assert_no_holdout, folds,  # noqa: E402
                                     load_fold_config as load_config)

CFG = load_config()


def frame(years, drafted, n_each=10, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for y in years:
        for i in range(n_each):
            rows.append(dict(draft_year=y, drafted=drafted,
                             points_per_40=float(rng.normal(18, 4)),
                             ts_pct=float(rng.uniform(.45, .65)),
                             minutes_per_game=float(rng.uniform(15, 35)),
                             height=float(rng.normal(78, 3)),
                             position_3=rng.choice(["G", "F", "C"])))
    return pd.DataFrame(rows)


class TestFoldConstruction(unittest.TestCase):
    def test_training_years_strictly_precede_validation(self):
        for fold, tr, vy in folds(CFG):
            self.assertLess(max(tr), vy, f"fold {fold}")

    def test_expanding_window_grows(self):
        sizes = [len(tr) for _, tr, _ in folds(CFG)]
        self.assertEqual(sizes, sorted(sizes))
        self.assertTrue(all(b > a for a, b in zip(sizes, sizes[1:])))

    def test_folds_cover_expected_validation_years(self):
        self.assertEqual([vy for _, _, vy in folds(CFG)],
                         [2019, 2020, 2021, 2022, 2023, 2024, 2025])

    def test_no_fold_touches_the_holdout(self):
        for _, tr, vy in folds(CFG):
            self.assertNotIn(HOLDOUT_YEAR, tr)
            self.assertNotEqual(vy, HOLDOUT_YEAR)


class TestHoldoutGuard(unittest.TestCase):
    def test_assert_no_holdout_raises_on_2026(self):
        with self.assertRaises(AssertionError):
            assert_no_holdout(pd.DataFrame({"draft_year": [2024, 2026]}), "t")

    def test_assert_no_holdout_passes_on_development(self):
        df = pd.DataFrame({"draft_year": [2014, 2025]})
        self.assertIs(assert_no_holdout(df, "t"), df)

    def test_config_forbids_holdout(self):
        self.assertEqual(CFG["holdout_years_forbidden"], [HOLDOUT_YEAR])
        self.assertNotIn(HOLDOUT_YEAR, CFG["development_years"])


class TestPrevalenceBaseline(unittest.TestCase):
    def test_uses_training_prevalence_not_validation(self):
        train = pd.concat([frame([2018], 1, 7), frame([2018], 0, 3)])
        valid = frame([2019], 0, 50)          # validation is 0% drafted
        p = b0_prevalence(train, valid)
        self.assertAlmostEqual(float(p[0]), 0.7, places=6)
        self.assertEqual(len(set(np.round(p, 9))), 1, "must be constant")

    def test_length_matches_validation(self):
        train = pd.concat([frame([2018], 1, 5), frame([2018], 0, 5)])
        valid = frame([2019], 1, 13)
        self.assertEqual(len(b0_prevalence(train, valid)), 13)


class TestPreprocessingIsFoldLocal(unittest.TestCase):
    def test_imputer_uses_train_median_only(self):
        train = pd.concat([frame([2018], 1, 10), frame([2018], 0, 10)])
        train.loc[:, "height"] = 70.0
        valid = frame([2019], 1, 5)
        valid.loc[:, "height"] = np.nan
        feats = ["points_per_40", "ts_pct", "minutes_per_game", "height"]
        pipe = make_pipeline(feats, "B_TRAIN_MEDIAN", "NONE", "NONE", None,
                             1.0, 1)
        pipe.fit(train, train.drafted)
        out = pipe.named_steps["pre"].transform(valid)
        # every validation height was NaN -> filled with the TRAIN median 70
        self.assertTrue(np.allclose(out[:, feats.index("height")], 70.0))

    def test_position_median_impute_never_uses_validation_values(self):
        train = pd.concat([frame([2018], 1, 20), frame([2018], 0, 20)])
        train.loc[train.position_3 == "G", "points_per_40"] = 10.0
        valid = frame([2019], 1, 6)
        valid.loc[:, "points_per_40"] = np.nan
        valid.loc[:, "position_3"] = "G"
        _, va = position_median_impute(train, valid, ["points_per_40"])
        self.assertTrue((va.points_per_40 == 10.0).all())

    def test_pipeline_is_a_fresh_object_each_call(self):
        a = make_pipeline(["points_per_40"], "B_TRAIN_MEDIAN", "NONE",
                          "STANDARD", None, 1.0, 1)
        b = make_pipeline(["points_per_40"], "B_TRAIN_MEDIAN", "NONE",
                          "STANDARD", None, 1.0, 1)
        self.assertIsNot(a, b)
        self.assertIsNot(a.named_steps["clf"], b.named_steps["clf"])


class TestFeatureSafety(unittest.TestCase):
    def test_no_feature_set_contains_a_denied_column(self):
        for name, feats in CFG["feature_sets"].items():
            for c in feats:
                self.assertNotIn(c, DENIED, f"{name}: {c}")
                self.assertFalse(any(s in c.lower() for s in DENIED_SUBSTR),
                                 f"{name}: {c}")

    def test_no_feature_set_contains_a_generic_jump_shot_feature(self):
        for name, feats in CFG["feature_sets"].items():
            self.assertFalse([c for c in feats if "jump_shot" in c],
                             f"{name} contains a jump_shot feature")

    def test_conservative_exclusion_drops_sparse_ratios(self):
        train = pd.DataFrame({c: [1.0] for c in
                              CFG["feature_sets"]["SET_3_BROADER_CLEAN"]})
        keep = resolve_features(CFG, "SET_3_BROADER_CLEAN", train,
                                "A_CONSERVATIVE_EXCLUSION")
        for c in CFG["sparse_ratio_features"]:
            self.assertNotIn(c, keep)

    def test_high_coverage_strategy_uses_training_coverage(self):
        cols = CFG["feature_sets"]["SET_1_BOX_EFFICIENCY"]
        train = pd.DataFrame({c: [1.0] * 100 for c in cols})
        train.loc[:50, "ft_pct"] = np.nan          # 50% coverage
        keep = resolve_features(CFG, "SET_1_BOX_EFFICIENCY", train,
                                "C_HIGH_COVERAGE")
        self.assertNotIn("ft_pct", keep)
        self.assertIn("points_per_40", keep)


class TestMetrics(unittest.TestCase):
    def test_single_class_returns_none_for_auc_not_a_crash(self):
        m = stage_a_metrics([1, 1, 1, 1], [0.9, 0.8, 0.7, 0.6])
        self.assertIsNone(m["roc_auc"])
        self.assertIsNone(m["pr_auc"])
        self.assertIsNotNone(m["brier"])

    def test_low_negative_support_flag(self):
        m = stage_a_metrics([1] * 26 + [0, 0], [0.5] * 28, 5)
        self.assertTrue(m["low_negative_support"])
        m2 = stage_a_metrics([1] * 20 + [0] * 20, [0.5] * 40, 5)
        self.assertFalse(m2["low_negative_support"])

    def test_perfect_ranking_gives_auc_one(self):
        m = stage_a_metrics([0, 0, 1, 1], [0.1, 0.2, 0.8, 0.9])
        self.assertAlmostEqual(m["roc_auc"], 1.0)

    def test_board_metrics_tie_breaking_is_not_row_order(self):
        # Constant predictions must NOT inherit the source ordering: ML-0
        # builds the population drafted-first, which would fake a perfect board.
        y = [1] * 20 + [0] * 20
        p = [0.5] * 40
        m = board_metrics(y, p, {"drafted": 20})
        self.assertLess(m["ndcg_at_drafted"], 0.95,
                        "constant predictor must not score a near-perfect board")

    def test_board_metrics_perfect_ranking(self):
        y = [1, 1, 0, 0]
        m = board_metrics(y, [0.9, 0.8, 0.2, 0.1], {"drafted": 2})
        self.assertEqual(m["precision_at_drafted"], 1.0)
        self.assertEqual(m["recall_at_drafted"], 1.0)


class TestDeterminism(unittest.TestCase):
    def test_repeated_pipeline_fits_give_identical_predictions(self):
        train = pd.concat([frame([2018], 1, 30, seed=1),
                           frame([2018], 0, 30, seed=2)]).reset_index(drop=True)
        valid = frame([2019], 1, 20, seed=3)
        feats = ["points_per_40", "ts_pct", "minutes_per_game", "height"]
        out = []
        for _ in range(2):
            pipe = make_pipeline(feats, "B_TRAIN_MEDIAN", "ONEHOT", "STANDARD",
                                 "balanced", 1.0, CFG["seed"])
            pipe.fit(train, train.drafted)
            out.append(pipe.predict_proba(valid)[:, 1])
        np.testing.assert_allclose(out[0], out[1])

    def test_board_metrics_are_deterministic(self):
        y, p = [1, 0] * 10, [0.5] * 20
        self.assertEqual(board_metrics(y, p, {"drafted": 10}),
                         board_metrics(y, p, {"drafted": 10}))


class TestRedundancyManifest(unittest.TestCase):
    def test_every_group_names_one_representative(self):
        groups = CFG["redundancy_policy"]["groups"]
        self.assertGreaterEqual(len(groups), 10)
        for name, g in groups.items():
            self.assertIn("keep", g)
            self.assertTrue(g["drop"], f"{name} drops nothing")
            self.assertNotIn(g["keep"], g["drop"])

    def test_dropped_representations_are_absent_from_broader_set(self):
        groups = CFG["redundancy_policy"]["groups"]
        broad = set(CFG["feature_sets"]["SET_3_BROADER_CLEAN"])
        for name, g in groups.items():
            for d in g["drop"]:
                self.assertNotIn(d, broad,
                                 f"{name}: dropped {d} still in SET_3")
            self.assertIn(g["keep"], broad, f"{name}: kept {g['keep']} missing")


if __name__ == "__main__":
    unittest.main(verbosity=2)
