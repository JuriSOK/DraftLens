"""Golden anchors — the published numbers, asserted end to end.

These are the guard against a refactor, dependency bump or data refresh silently
moving the science. Every value below is quoted from a committed report and was
verified byte-identical across the R-1 refactor.

Tolerances are DELIBERATELY TIGHT (1e-4, i.e. the precision the reports publish).
If one of these fails, the correct response is to find out what changed — not to
loosen the tolerance.

These tests need the generated ML-0/ML-2 layers present, so they skip cleanly on
a fresh clone rather than failing.

  ./.venv/bin/python -m unittest discover -s tests -t .
"""

import math
import unittest

import pandas as pd

from draftlens.ml.datasets import ML0, ML2, load_development, load_stage_b
from draftlens.ml.metrics import (board_metrics, expected_calibration_error,
                                  stage_a_metrics, stage_b_metrics)
from draftlens.ml.stage_a import STAGE_A, feature_set
from draftlens.ml.stage_a import fit_predict_fold as stage_a_fold
from draftlens.ml.stage_b import STAGE_B, draft_sizes
from draftlens.ml.stage_b import fit_predict_fold as stage_b_fold
from draftlens.ml.validation import folds, load_fold_config

TOL = 1e-4

HAVE_DATA = (ML2 / "features_2014_2025.parquet").exists() and \
            (ML0 / "targets_2014_2025.parquet").exists()
needs_data = unittest.skipUnless(
    HAVE_DATA, "generated ML-0/ML-2 layers absent — run scripts/build_dataset.py "
               "then scripts/build_features.py")


@needs_data
class TestPopulationAnchors(unittest.TestCase):
    """ML0_DATASET.md, corrected in ML-0.1."""

    def test_development_population(self):
        dev = load_development()
        self.assertEqual(len(dev), 887)
        self.assertEqual(int(dev.drafted.sum()), 431)
        self.assertEqual(int((dev.drafted == 0).sum()), 456)

    def test_unresolved_prospects_retained(self):
        """All 8 are undrafted (DEC-071); dropping them would selectively
        remove negatives and inflate every downstream metric."""
        dev = load_development()
        unresolved = dev[dev.hoopr_athlete_id.isna()]
        self.assertGreaterEqual(len(unresolved), 8)
        self.assertEqual(int(unresolved.drafted.sum()), 0)

    def test_stage_b_population(self):
        self.assertEqual(len(load_stage_b()), 431)

    def test_stage_b_excludes_undrafted_without_synthetic_picks(self):
        b = load_stage_b()
        self.assertTrue((b.drafted == 1).all())
        self.assertTrue(b.pick.notna().all())
        for sentinel in (0, 61, 100, 999):
            self.assertEqual(int((b.pick == sentinel).sum()), 0)

    def test_feature_layer_shape(self):
        self.assertEqual(pd.read_parquet(ML2 / "features_2014_2025.parquet").shape,
                         (887, 81))


class TestFrozenConfiguration(unittest.TestCase):
    """The selections themselves. Changing one of these requires a DECISIONS
    entry, and this test is what makes that non-optional."""

    def test_stage_a_frozen(self):
        self.assertEqual(STAGE_A, {
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

    def test_stage_b_frozen(self):
        self.assertEqual(STAGE_B["family"], "Ridge")
        self.assertEqual(STAGE_B["alpha"], 10.0)
        self.assertEqual(STAGE_B["target"], "RAW_PICK")
        self.assertEqual(STAGE_B["feature_set"], "SET_2_BOX_SHOT_PROFILE")
        # STANDARD, not SEASON_RELATIVE — see ML5_STAGE_B.md correction notice.
        self.assertEqual(STAGE_B["normalization"], "STANDARD")

    def test_folds_unchanged(self):
        self.assertEqual([(f, tr[0], tr[-1], vy) for f, tr, vy in folds()],
                         [(1, 2014, 2018, 2019), (2, 2014, 2019, 2020),
                          (3, 2014, 2020, 2021), (4, 2014, 2021, 2022),
                          (5, 2014, 2022, 2023), (6, 2014, 2023, 2024),
                          (7, 2014, 2024, 2025)])

    def test_draft_sizes_unchanged(self):
        s = draft_sizes()
        self.assertEqual([s[y] for y in range(2014, 2026)],
                         [60, 60, 60, 60, 60, 60, 60, 60, 58, 58, 58, 59])


@needs_data
class TestStageAAnchors(unittest.TestCase):
    """ML4_STAGE_A.md §8 — the selected configuration's published metrics."""

    @classmethod
    def setUpClass(cls):
        cfg = load_fold_config()
        dev = load_development()
        feats = feature_set(STAGE_A["feature_set"], cfg)
        low = cfg["low_negative_support_threshold"]
        rows, oof = [], []
        for _, tr_years, vy in folds(cfg):
            train = dev[dev.draft_year.isin(tr_years)].reset_index(drop=True)
            valid = dev[dev.draft_year == vy].reset_index(drop=True)
            p, _ = stage_a_fold(train, valid, feats)
            m = stage_a_metrics(valid.drafted, p, low)
            m.update(board_metrics(valid.drafted, p,
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
        pooled = stage_a_metrics(self.oof.y, self.oof.p, self.low)["roc_auc"]
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
        self.assertAlmostEqual(expected_calibration_error(self.oof.y, self.oof.p),
                               0.0590, delta=TOL)

    def test_low_support_year_flagged(self):
        flagged = self.fold_df[self.fold_df.low_negative_support].validate_year
        self.assertEqual(list(flagged), [2025])


@needs_data
class TestStageBAnchors(unittest.TestCase):
    """ML5_STAGE_B.md §11 — the selected configuration's published metrics."""

    @classmethod
    def setUpClass(cls):
        cfg = load_fold_config()
        dev = load_stage_b()
        dev["draft_size"] = dev.draft_year.map(draft_sizes())
        feats = feature_set(STAGE_B["feature_set"], cfg)
        rows = []
        for _, tr_years, vy in folds(cfg):
            train = dev[dev.draft_year.isin(tr_years)].reset_index(drop=True)
            valid = dev[dev.draft_year == vy].reset_index(drop=True)
            pred, _ = stage_b_fold(train, valid, feats,
                                   family=STAGE_B["family"],
                                   params={"alpha": STAGE_B["alpha"]},
                                   target=STAGE_B["target"])
            rows.append(dict(validate_year=vy,
                             **stage_b_metrics(valid.pick, pred, valid.draft_size)))
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

    def test_stage_b_excludes_holdout(self):
        self.assertNotIn(2026, set(load_stage_b().draft_year))

    def test_no_fold_touches_holdout(self):
        for _, tr, vy in folds():
            self.assertNotIn(2026, tr)
            self.assertNotEqual(vy, 2026)

    def test_board_module_is_not_implemented(self):
        """ML-6 has not run; board.py must expose no prediction API yet."""
        from draftlens.ml import board
        public = [n for n in dir(board) if not n.startswith("_")]
        self.assertEqual(public, [], f"board.py already exposes {public}")


if __name__ == "__main__":
    unittest.main()
