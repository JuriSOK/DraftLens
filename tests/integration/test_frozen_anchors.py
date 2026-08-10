"""Golden anchors — the published numbers, asserted end to end.

These are the guard against a refactor, dependency bump or data refresh silently
moving the science. Every value below is quoted from a committed report and was
verified byte-identical across the R-2 repository simplification.

Tolerances are DELIBERATELY TIGHT (1e-4, i.e. the precision the reports publish).
If one of these fails, the correct response is to find out what changed — not to
loosen the tolerance.

These tests need the generated dataset/features layers present, so they skip
cleanly on a fresh clone rather than failing.

  ./.venv/bin/python -m unittest discover -s tests -t .
"""

import math
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from data.build import DATASET, FEATURES, load_development, load_draft_order
from board.probability import DRAFT_PROBABILITY, feature_set, probability_metrics, ranking_metrics
from board.probability import fit_predict_fold as probability_fold
from board.scoring import GENERAL_BOARD, build_board, graded_relevance
from board.scoring import board_binary_metrics, board_graded_metrics, board_order_metrics
from board.order import DRAFT_ORDER, draft_sizes, order_metrics
from board.order import fit_predict_fold as order_fold
from validation import folds, load_fold_config

ROOT = Path(__file__).resolve().parents[2]
TOL = 1e-4

HAVE_DATA = (FEATURES / "features_2014_2025.parquet").exists() and \
            (DATASET / "targets_2014_2025.parquet").exists()
needs_data = unittest.skipUnless(
    HAVE_DATA, "generated dataset/features layers absent — run "
               "scripts/build.py dataset then scripts/build.py features")


@needs_data
class TestPopulationAnchors(unittest.TestCase):
    """The development sampling frame."""

    def test_development_population(self):
        dev = load_development()
        self.assertEqual(len(dev), 887)
        self.assertEqual(int(dev.drafted.sum()), 431)
        self.assertEqual(int((dev.drafted == 0).sum()), 456)

    def test_unresolved_prospects_retained(self):
        """All 8 are undrafted; dropping them would selectively remove
        negatives and inflate every downstream metric."""
        dev = load_development()
        unresolved = dev[dev.hoopr_athlete_id.isna()]
        self.assertGreaterEqual(len(unresolved), 8)
        self.assertEqual(int(unresolved.drafted.sum()), 0)

    def test_draft_order_population(self):
        self.assertEqual(len(load_draft_order()), 431)

    def test_draft_order_excludes_undrafted_without_synthetic_picks(self):
        b = load_draft_order()
        self.assertTrue((b.drafted == 1).all())
        self.assertTrue(b.pick.notna().all())
        for sentinel in (0, 61, 100, 999):
            self.assertEqual(int((b.pick == sentinel).sum()), 0)

    def test_feature_layer_shape(self):
        self.assertEqual(pd.read_parquet(FEATURES / "features_2014_2025.parquet").shape,
                         (887, 81))


class TestFrozenConfiguration(unittest.TestCase):
    """The selections themselves. Changing one of these requires a
    docs/METHODOLOGY.md entry, and this test is what makes that non-optional."""

    def test_draft_probability_frozen(self):
        self.assertEqual(DRAFT_PROBABILITY, {
            "family": "LogisticRegression",
            "feature_set": "SET_2_BOX_SHOT_PROFILE",
            "normalization": "SEASON_RELATIVE",
            "missing_strategy": "B_TRAIN_MEDIAN",
            "position_handling": "ONEHOT",
            "scaling": "STANDARD",
            "class_weight": "balanced",
            "C": 0.25,
            "calibration": "none",
        })

    def test_draft_order_frozen(self):
        self.assertEqual(DRAFT_ORDER["family"], "Ridge")
        self.assertEqual(DRAFT_ORDER["alpha"], 10.0)
        self.assertEqual(DRAFT_ORDER["target"], "RAW_PICK")
        self.assertEqual(DRAFT_ORDER["feature_set"], "SET_2_BOX_SHOT_PROFILE")
        # STANDARD, not SEASON_RELATIVE — see docs/VALIDATION.md correction notice.
        self.assertEqual(DRAFT_ORDER["normalization"], "STANDARD")

    def test_folds_unchanged(self):
        self.assertEqual([(f, tr[0], tr[-1], vy) for f, tr, vy in folds()],
                         [(1, 2014, 2018, 2019), (2, 2014, 2019, 2020),
                          (3, 2014, 2020, 2021), (4, 2014, 2021, 2022),
                          (5, 2014, 2022, 2023), (6, 2014, 2023, 2024),
                          (7, 2014, 2024, 2025)])

    def test_board_frozen(self):
        self.assertEqual(GENERAL_BOARD["method"], "C_MULTIPLICATIVE")
        self.assertEqual(GENERAL_BOARD["stage_b_transform"], "DRAFT_SLOT_UTILITY")
        self.assertEqual(GENERAL_BOARD["score_transform"], "CURRENT_BOARD_PERCENTILE")
        self.assertEqual(GENERAL_BOARD["score_range"], (0, 100))
        self.assertEqual(GENERAL_BOARD["score_dtype"], "int")

    def test_draft_sizes_unchanged(self):
        s = draft_sizes()
        self.assertEqual([s[y] for y in range(2014, 2026)],
                         [60, 60, 60, 60, 60, 60, 60, 60, 58, 58, 58, 59])


@needs_data
class TestDraftProbabilityAnchors(unittest.TestCase):
    """docs/VALIDATION.md — the selected configuration's published metrics."""

    @classmethod
    def setUpClass(cls):
        cfg = load_fold_config()
        dev = load_development()
        feats = feature_set(DRAFT_PROBABILITY["feature_set"], cfg)
        low = cfg["low_negative_support_threshold"]
        rows, oof = [], []
        for _, tr_years, vy in folds(cfg):
            train = dev[dev.draft_year.isin(tr_years)].reset_index(drop=True)
            valid = dev[dev.draft_year == vy].reset_index(drop=True)
            p, _ = probability_fold(train, valid, feats)
            m = probability_metrics(valid.drafted, p, low)
            m.update(ranking_metrics(valid.drafted, p,
                                     {"drafted": int(valid.drafted.sum()),
                                      "top25": math.ceil(0.25 * len(valid))}))
            rows.append(dict(validate_year=vy, **m))
            oof.append(pd.DataFrame({"y": valid.drafted.values, "p": p}))
        cls.fold_df = pd.DataFrame(rows)
        cls.oof = pd.concat(oof, ignore_index=True)
        cls.low = low

    def test_macro_roc_auc(self):
        self.assertAlmostEqual(self.fold_df.roc_auc.mean(), 0.6986, delta=TOL)

    def test_pooled_roc_auc(self):
        pooled = probability_metrics(self.oof.y, self.oof.p, self.low)["roc_auc"]
        self.assertAlmostEqual(pooled, 0.6953, delta=TOL)

    def test_macro_brier(self):
        self.assertAlmostEqual(self.fold_df.brier.mean(), 0.2238, delta=TOL)

    def test_macro_ndcg(self):
        self.assertAlmostEqual(self.fold_df.ndcg_at_drafted.mean(), 0.7061,
                               delta=TOL)

    def test_fold_sd_and_worst_year(self):
        scored = self.fold_df[self.fold_df.roc_auc.notna()]
        self.assertAlmostEqual(scored.roc_auc.std(), 0.0281, delta=TOL)
        self.assertAlmostEqual(scored.roc_auc.min(), 0.6742, delta=TOL)

    def test_expected_calibration_error(self):
        from board.probability import expected_calibration_error
        self.assertAlmostEqual(expected_calibration_error(self.oof.y, self.oof.p),
                               0.0590, delta=TOL)

    def test_low_support_year_flagged(self):
        flagged = self.fold_df[self.fold_df.low_negative_support].validate_year
        self.assertEqual(list(flagged), [2025])


@needs_data
class TestDraftOrderAnchors(unittest.TestCase):
    """docs/VALIDATION.md — the selected configuration's published metrics."""

    @classmethod
    def setUpClass(cls):
        cfg = load_fold_config()
        dev = load_draft_order()
        dev["draft_size"] = dev.draft_year.map(draft_sizes())
        feats = feature_set(DRAFT_ORDER["feature_set"], cfg)
        rows = []
        for _, tr_years, vy in folds(cfg):
            train = dev[dev.draft_year.isin(tr_years)].reset_index(drop=True)
            valid = dev[dev.draft_year == vy].reset_index(drop=True)
            pred, _ = order_fold(train, valid, feats,
                                 family=DRAFT_ORDER["family"],
                                 params={"alpha": DRAFT_ORDER["alpha"]},
                                 target=DRAFT_ORDER["target"])
            rows.append(dict(validate_year=vy,
                             **order_metrics(valid.pick, pred, valid.draft_size)))
        cls.fold_df = pd.DataFrame(rows)

    def test_macro_spearman(self):
        self.assertAlmostEqual(self.fold_df.spearman.mean(), 0.2968, delta=TOL)

    def test_macro_kendall(self):
        self.assertAlmostEqual(self.fold_df.kendall_tau.mean(), 0.2089, delta=TOL)

    def test_macro_ndcg(self):
        self.assertAlmostEqual(self.fold_df.ndcg.mean(), 0.9043, delta=TOL)

    def test_macro_ndcg_at_14(self):
        self.assertAlmostEqual(self.fold_df.ndcg_at_14.mean(), 0.7555, delta=TOL)

    def test_macro_mae_and_rmse(self):
        self.assertAlmostEqual(self.fold_df.mae_pick.mean(), 13.2141, delta=TOL)
        self.assertAlmostEqual(self.fold_df.rmse_pick.mean(), 15.5641, delta=TOL)

    def test_fold_sd_and_worst_year(self):
        self.assertAlmostEqual(self.fold_df.spearman.std(), 0.1242, delta=TOL)
        self.assertAlmostEqual(self.fold_df.spearman.min(), 0.1381, delta=TOL)

    def test_spearman_positive_every_fold(self):
        """The model never ranks a draft class backwards."""
        self.assertTrue((self.fold_df.spearman > 0).all())


@needs_data
class TestHoldoutFirewall(unittest.TestCase):
    """2026 must be unreachable from any modelling path."""

    def test_development_excludes_holdout(self):
        self.assertNotIn(2026, set(load_development().draft_year))

    def test_draft_order_excludes_holdout(self):
        self.assertNotIn(2026, set(load_draft_order().draft_year))

    def test_no_fold_touches_holdout(self):
        for _, tr, vy in folds():
            self.assertNotIn(2026, tr)
            self.assertNotEqual(vy, 2026)

    def test_board_never_reaches_the_holdout(self):
        from board import scoring
        src = (ROOT / "src" / "board" / "scoring.py").read_text()
        for banned in ("targets_2026", "features_2026", "predictions_2026"):
            self.assertNotIn(banned, src)
        self.assertTrue(hasattr(scoring, "build_board"))


@needs_data
class TestBoardAnchors(unittest.TestCase):
    """docs/VALIDATION.md — the selected board's published metrics."""

    @classmethod
    def setUpClass(cls):
        cfg = load_fold_config()
        dev = load_development()
        dev["draft_size"] = dev.draft_year.map(draft_sizes())
        feats = feature_set(DRAFT_PROBABILITY["feature_set"], cfg)
        rows = []
        for _, tr_years, vy in folds(cfg):
            tr_all = dev[dev.draft_year.isin(tr_years)].reset_index(drop=True)
            va = dev[dev.draft_year == vy].reset_index(drop=True)
            tr_dr = tr_all[tr_all.drafted == 1].reset_index(drop=True)
            p_a, _ = probability_fold(tr_all, va, feats)
            p_b, _ = order_fold(tr_dr, va, feats, family=DRAFT_ORDER["family"],
                                params={"alpha": DRAFT_ORDER["alpha"]},
                                target=DRAFT_ORDER["target"])
            b = build_board(p_a, p_b, va.draft_size)
            sig = b.final_board_signal.to_numpy()
            rel = graded_relevance(va.drafted, va.pick, va.draft_size)
            m = dict(validate_year=vy)
            m.update(board_binary_metrics(va.drafted, sig,
                                          {"drafted": int(va.drafted.sum())}))
            m.update(board_graded_metrics(rel, sig))
            d = (va.drafted == 1).to_numpy()
            m.update(board_order_metrics(va.pick[d], sig[d]))
            m["overall_score"] = b.overall_score.to_numpy()
            m["signal"] = sig
            rows.append(m)
        cls.fold_df = pd.DataFrame(rows)

    def test_binary_macro_auc(self):
        sc = self.fold_df[self.fold_df.roc_auc.notna()]
        self.assertAlmostEqual(sc.roc_auc.mean(), 0.7123, delta=TOL)

    def test_macro_average_precision(self):
        sc = self.fold_df[self.fold_df.average_precision.notna()]
        self.assertAlmostEqual(sc.average_precision.mean(), 0.7237, delta=TOL)

    def test_graded_ndcg(self):
        self.assertAlmostEqual(self.fold_df.graded_ndcg.mean(), 0.8283,
                               delta=TOL)

    def test_drafted_order_metrics(self):
        self.assertAlmostEqual(self.fold_df.drafted_spearman.mean(), 0.2781,
                               delta=TOL)
        self.assertAlmostEqual(self.fold_df.drafted_kendall.mean(), 0.1973,
                               delta=TOL)

    def test_stability(self):
        self.assertAlmostEqual(self.fold_df.graded_ndcg.std(), 0.0594, delta=TOL)
        self.assertAlmostEqual(self.fold_df.graded_ndcg.min(), 0.7281, delta=TOL)

    def test_beats_draft_probability_only_on_every_headline_metric(self):
        """The reason Draft Order is in the board at all. Draft-Probability-only
        reference: AUC 0.6986, graded NDCG 0.8159, drafted Spearman 0.2461."""
        sc = self.fold_df[self.fold_df.roc_auc.notna()]
        self.assertGreater(sc.roc_auc.mean(), 0.6986)
        self.assertGreater(self.fold_df.graded_ndcg.mean(), 0.8159)
        self.assertGreater(self.fold_df.drafted_spearman.mean(), 0.2461)
        self.assertGreater(self.fold_df.graded_ndcg.min(), 0.6590)

    def test_scores_are_valid_and_monotone_every_class(self):
        for _, r in self.fold_df.iterrows():
            s, sig = r["overall_score"], r["signal"]
            self.assertTrue(((s >= 0) & (s <= 100)).all())
            order = np.argsort(-sig)
            self.assertTrue(np.all(np.diff(s[order]) <= 0),
                            f"{r['validate_year']}: score order broken")


if __name__ == "__main__":
    unittest.main()
