"""Tests for the General Draft Board and Overall Score.

Behavioural guards on the methodology, not on the numbers. The published board
metrics are pinned separately in tests/integration/test_frozen_anchors.py.

  ./.venv/bin/python -m unittest discover -s tests -t .
"""

import importlib.util
import inspect
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from board.order import DRAFT_ORDER
from board.probability import DRAFT_PROBABILITY
from board.scoring import (GENERAL_BOARD, NEUTRAL_QUALITY,
                           board_binary_metrics, board_graded_metrics,
                           board_order_metrics, build_board,
                           combine_board_signals, draft_slot_utility,
                           graded_relevance, historical_empirical_percentile,
                           load_config, overall_score, rank_board,
                           stage_b_orientation, transform_stage_b_signal,
                           within_board_percentile)
from validation import HOLDOUT_YEAR, folds

ROOT = Path(__file__).resolve().parents[2]

CFG = load_config()
TRANSFORMS = ["WITHIN_BOARD_PERCENTILE", "DRAFT_SLOT_UTILITY",
             "HISTORICAL_EMPIRICAL_PERCENTILE"]
METHODS = ["A_STAGE_A_ONLY", "B_STAGE_B_ONLY", "C_MULTIPLICATIVE",
          "D_RANK_FUSION", "E_LEXICOGRAPHIC", "F_EQUAL_WEIGHT_SUM"]


class TestFrozenStagesUnchanged(unittest.TestCase):
    """The board may combine Draft Probability and Draft Order. It may not
    change them."""

    def test_draft_probability_anchor(self):
        self.assertEqual(DRAFT_PROBABILITY["family"], "LogisticRegression")
        self.assertEqual(DRAFT_PROBABILITY["feature_set"], "SET_2_BOX_SHOT_PROFILE")
        self.assertEqual(DRAFT_PROBABILITY["normalization"], "SEASON_RELATIVE")
        self.assertEqual(DRAFT_PROBABILITY["class_weight"], "balanced")
        self.assertEqual(DRAFT_PROBABILITY["C"], 0.25)
        self.assertEqual(DRAFT_PROBABILITY["calibration"], "none")

    def test_draft_order_anchor(self):
        self.assertEqual(DRAFT_ORDER["family"], "Ridge")
        self.assertEqual(DRAFT_ORDER["alpha"], 10.0)
        self.assertEqual(DRAFT_ORDER["target"], "RAW_PICK")

    def test_draft_order_is_standard_not_season_relative(self):
        """The measured +0.0031 macro Spearman from switching is not
        sufficient to reopen Draft Order — see docs/VALIDATION.md."""
        self.assertEqual(DRAFT_ORDER["normalization"], "STANDARD")


class TestOrientation(unittest.TestCase):
    """Lower predicted pick = better. Higher signal = better. One convention."""

    def test_stage_b_orientation_prefers_earlier_picks(self):
        self.assertGreater(stage_b_orientation(1.0), stage_b_orientation(2.0))
        v = stage_b_orientation(np.array([30.0, 1.0, 60.0]))
        self.assertEqual(int(np.argmax(v)), 1)

    def test_within_board_percentile_is_increasing(self):
        p = within_board_percentile([1.0, 2.0, 3.0, 4.0])
        self.assertTrue(np.all(np.diff(p) > 0))
        self.assertTrue(np.all((p > 0) & (p < 1)))

    def test_within_board_percentile_never_hits_zero_or_one(self):
        """A multiplicative board must not zero out a prospect for being last
        on one axis."""
        for n in (2, 5, 50):
            p = within_board_percentile(np.arange(n, dtype=float))
            self.assertGreater(p.min(), 0.0)
            self.assertLess(p.max(), 1.0)

    def test_within_board_percentile_ties_share_a_value(self):
        p = within_board_percentile([5.0, 5.0, 1.0])
        self.assertAlmostEqual(p[0], p[1])

    def test_draft_slot_utility_decreases_with_pick(self):
        size = np.full(4, 60.0)
        u = draft_slot_utility([1.0, 10.0, 30.0, 60.0], size)
        self.assertTrue(np.all(np.diff(u) < 0))
        self.assertAlmostEqual(u[0], 1.0)
        self.assertAlmostEqual(u[-1], 1.0 / 60.0)

    def test_draft_slot_utility_clips_illegal_predictions(self):
        """Clipping is predeclared to the basketball-valid slot range."""
        size = np.full(3, 60.0)
        u = draft_slot_utility([-5.0, 1.0, 999.0], size)
        self.assertAlmostEqual(u[0], u[1])           # -5 clips to pick 1
        self.assertAlmostEqual(u[2], 1.0 / 60.0)     # 999 clips to last slot
        self.assertTrue(np.all((u > 0) & (u <= 1)))

    def test_every_transform_is_higher_is_better(self):
        size = np.full(5, 60.0)
        ref = np.linspace(5, 55, 40)
        for t in TRANSFORMS:
            q = transform_stage_b_signal(np.array([5., 15., 25., 35., 45.]),
                                         size, t, ref)
            self.assertTrue(np.all(np.diff(q) < 0),
                            f"{t} is not decreasing in predicted pick")


class TestGradedRelevance(unittest.TestCase):
    """An EVALUATION quantity only — never a target, never a synthetic pick."""

    def test_undrafted_relevance_is_zero(self):
        r = graded_relevance([0, 0], [np.nan, np.nan], np.full(2, 60.0))
        self.assertTrue(np.all(r == 0.0))

    def test_drafted_relevance_increases_for_better_picks(self):
        r = graded_relevance([1, 1, 1], [1.0, 30.0, 60.0], np.full(3, 60.0))
        self.assertTrue(np.all(np.diff(r) < 0))
        self.assertAlmostEqual(r[0], 1.0)

    def test_worst_drafted_outranks_every_undrafted(self):
        r = graded_relevance([1, 0], [60.0, np.nan], np.full(2, 60.0))
        self.assertGreater(r[0], r[1])
        self.assertGreater(r[0], 0.0)

    def test_normalised_by_that_years_draft_size(self):
        """Equivalent RELATIVE draft positions score alike across draft sizes,
        so a mid-second-round pick is not penalised for landing in a shorter
        draft. Pick 1 is worth 1.0 in every year."""
        half_58 = graded_relevance([1], [29.0], np.array([58.0]))[0]
        half_60 = graded_relevance([1], [30.0], np.array([60.0]))[0]
        self.assertAlmostEqual(float(half_58), float(half_60), places=2)
        for size in (58.0, 59.0, 60.0):
            self.assertAlmostEqual(
                float(graded_relevance([1], [1.0], np.array([size]))[0]), 1.0)

    def test_relevance_is_bounded(self):
        r = graded_relevance([1, 1, 0], [1.0, 60.0, np.nan], np.full(3, 60.0))
        self.assertTrue(np.all((r >= 0) & (r <= 1)))

    def test_undrafted_never_receives_a_pick_value(self):
        """The relevance of an undrafted prospect must not depend on any pick
        number — it is identically zero."""
        for fake in (61.0, 100.0, 999.0, np.nan):
            r = graded_relevance([0], [fake], np.array([60.0]))
            self.assertEqual(float(r[0]), 0.0)

    def test_never_imported_by_the_scoring_path(self):
        self.assertNotIn("graded_relevance", inspect.getsource(build_board))


class TestCombination(unittest.TestCase):
    def test_stage_a_only_ignores_stage_b(self):
        p = np.array([0.2, 0.8])
        a = combine_board_signals(p, np.array([0.1, 0.9]), "A_STAGE_A_ONLY")
        b = combine_board_signals(p, np.array([0.9, 0.1]), "A_STAGE_A_ONLY")
        np.testing.assert_array_equal(a, b)

    def test_multiplicative_is_the_literal_product(self):
        p = np.array([0.5, 0.8, 1.0])
        q = np.array([0.4, 0.5, 0.25])
        np.testing.assert_allclose(
            combine_board_signals(p, q, "C_MULTIPLICATIVE"), p * q)

    def test_multiplicative_is_monotone_in_each_input(self):
        q = np.full(3, 0.5)
        s = combine_board_signals(np.array([0.1, 0.5, 0.9]), q,
                                  "C_MULTIPLICATIVE")
        self.assertTrue(np.all(np.diff(s) > 0))
        p = np.full(3, 0.5)
        s = combine_board_signals(p, np.array([0.1, 0.5, 0.9]),
                                  "C_MULTIPLICATIVE")
        self.assertTrue(np.all(np.diff(s) > 0))

    def test_rank_fusion_is_the_geometric_mean_of_percentiles(self):
        p = np.array([0.1, 0.5, 0.9])
        q = np.array([0.9, 0.5, 0.1])
        got = combine_board_signals(p, q, "D_RANK_FUSION")
        want = np.sqrt(within_board_percentile(p) * within_board_percentile(q))
        np.testing.assert_allclose(got, want)

    def test_rank_fusion_is_deterministic(self):
        rng = np.random.default_rng(0)
        p, q = rng.uniform(size=40), rng.uniform(size=40)
        np.testing.assert_array_equal(
            combine_board_signals(p, q, "D_RANK_FUSION"),
            combine_board_signals(p, q, "D_RANK_FUSION"))

    def test_lexicographic_lets_stage_a_dominate(self):
        """A prospect a whole band higher on Draft Probability outranks any
        Draft Order edge."""
        p = np.array([0.05, 0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.95])
        q_best_for_worst = np.zeros(10)
        q_best_for_worst[0] = 1.0
        s = combine_board_signals(p, q_best_for_worst, "E_LEXICOGRAPHIC")
        self.assertEqual(int(np.argmax(s)), 9)

    def test_no_method_carries_a_fitted_weight(self):
        """No blend-weight search anywhere: the only numeric weights in the
        method set are the single equal-weight 0.5/0.5 reference point."""
        src = (ROOT / "src" / "board" / "scoring.py").read_text()
        for banned in ("0.3 *", "0.7 *", "0.4 *", "0.6 *", "0.2 *", "0.8 *"):
            self.assertNotIn(banned, src)

    def test_unknown_method_is_rejected(self):
        with self.assertRaises(ValueError):
            combine_board_signals(np.array([0.5]), np.array([0.5]), "NOPE")


class TestStageBMissingPolicy(unittest.TestCase):
    """A prospect Draft Probability can score must never be dropped for Draft
    Order's sake."""

    def test_missing_stage_b_gets_neutral_not_penalised(self):
        size = np.full(4, 60.0)
        raw = np.array([10.0, 20.0, np.nan, 50.0])
        for t in TRANSFORMS:
            q = transform_stage_b_signal(raw, size, t, np.linspace(5, 55, 40))
            self.assertTrue(np.isfinite(q).all(), t)
            self.assertGreater(q[2], q[3],
                               f"{t}: missing was penalised below a late pick")

    def test_missing_stage_b_still_yields_a_board_signal(self):
        b = build_board(np.array([0.9, 0.4]), np.array([np.nan, 20.0]),
                        np.full(2, 60.0))
        self.assertTrue(np.isfinite(b.final_board_signal).all())
        self.assertEqual(len(b), 2)

    def test_draft_probability_still_orders_two_prospects_both_missing_order(self):
        b = build_board(np.array([0.9, 0.4]), np.array([np.nan, np.nan]),
                        np.full(2, 60.0))
        self.assertGreater(b.final_board_signal.iloc[0],
                           b.final_board_signal.iloc[1])


class TestOverallScore(unittest.TestCase):
    def test_range_is_0_to_100(self):
        rng = np.random.default_rng(1)
        s = overall_score(rng.uniform(size=200))
        self.assertGreaterEqual(s.min(), 0)
        self.assertLessEqual(s.max(), 100)

    def test_scores_are_integers(self):
        s = overall_score(np.linspace(0, 1, 50))
        self.assertTrue(np.issubdtype(s.dtype, np.integer))

    def test_monotonic_with_the_board_signal(self):
        """HARD REQUIREMENT: score order can never disagree with board order."""
        rng = np.random.default_rng(2)
        sig = rng.uniform(size=300)
        sc = overall_score(sig)
        order = np.argsort(-sig)
        self.assertTrue(np.all(np.diff(sc[order]) <= 0))

    def test_monotonic_for_the_historical_transform_too(self):
        rng = np.random.default_rng(3)
        ref = rng.uniform(size=500)
        sig = rng.uniform(size=100)
        sc = overall_score(sig, "HISTORICAL_EMPIRICAL_PERCENTILE", ref)
        order = np.argsort(-sig)
        self.assertTrue(np.all(np.diff(sc[order]) <= 0))

    def test_equal_signals_receive_equal_scores(self):
        s = overall_score(np.array([0.5, 0.5, 0.9, 0.1]))
        self.assertEqual(s[0], s[1])

    def test_tie_handling_uses_no_forbidden_information(self):
        """Ties must never be broken by name, outcome or NBA data — the score
        depends on the signal alone."""
        sig = np.array([0.5, 0.5])
        np.testing.assert_array_equal(overall_score(sig),
                                      overall_score(sig[::-1])[::-1])

    def test_historical_transform_requires_a_reference(self):
        with self.assertRaises(ValueError):
            overall_score(np.array([0.5]), "HISTORICAL_EMPIRICAL_PERCENTILE")

    def test_rank_board_orders_by_continuous_signal(self):
        df = pd.DataFrame({"final_board_signal": [0.1, 0.9, 0.5]})
        df["overall_score"] = overall_score(df.final_board_signal)
        b = rank_board(df)
        self.assertEqual(list(b.board_rank), [1, 2, 3])
        self.assertTrue(b.final_board_signal.is_monotonic_decreasing)


class TestBoardMetrics(unittest.TestCase):
    def test_perfect_board_scores_one(self):
        drafted = np.array([1, 1, 1, 0, 0])
        pick = np.array([1.0, 5.0, 20.0, np.nan, np.nan])
        size = np.full(5, 60.0)
        rel = graded_relevance(drafted, pick, size)
        self.assertEqual(board_graded_metrics(rel, rel)["graded_ndcg"], 1.0)
        self.assertEqual(
            board_binary_metrics(drafted, rel, {"d": 3})["roc_auc"], 1.0)

    def test_reversed_board_scores_badly(self):
        drafted = np.array([1, 1, 0, 0])
        sig = np.array([0.1, 0.2, 0.9, 0.8])
        self.assertLess(board_binary_metrics(drafted, sig, {"d": 2})["roc_auc"],
                        0.5)

    def test_no_brier_is_reported_for_a_rank_score(self):
        """The board signal is a ranking score; scoring it as a probability
        would be exactly the false precision the product avoids elsewhere."""
        m = board_binary_metrics(np.array([1, 0, 1]), np.array([.9, .2, .7]),
                                 {"d": 2})
        self.assertNotIn("brier", m)
        self.assertNotIn("log_loss", m)

    def test_order_metrics_use_drafted_only(self):
        m = board_order_metrics(np.array([1.0, 10.0, 30.0]),
                                np.array([0.9, 0.5, 0.1]))
        self.assertEqual(m["drafted_n"], 3)
        self.assertAlmostEqual(m["drafted_spearman"], 1.0)

    def test_low_support_year_is_flagged(self):
        m = board_binary_metrics(np.array([1] * 26 + [0, 0]),
                                 np.arange(28, dtype=float), {"d": 26})
        self.assertTrue(m["low_negative_support"])


class TestHistoricalEmpiricalTransform(unittest.TestCase):
    def test_uses_training_reference_only(self):
        ref = np.linspace(10, 50, 100)
        q = historical_empirical_percentile(np.array([10.0, 30.0, 50.0]), ref)
        self.assertTrue(np.all(np.diff(q) < 0))
        self.assertTrue(np.all((q > 0) & (q < 1)))

    def test_transform_rejects_a_missing_reference(self):
        with self.assertRaises(ValueError):
            transform_stage_b_signal(np.array([20.0]), np.array([60.0]),
                                     "HISTORICAL_EMPIRICAL_PERCENTILE")


class TestNoTargetLeakage(unittest.TestCase):
    """Production board scoring must need only pre-draft inputs."""

    def test_build_board_takes_no_target_argument(self):
        params = set(inspect.signature(build_board).parameters)
        for banned in ("drafted", "pick", "actual_pick", "actual_drafted",
                       "relevance", "y"):
            self.assertNotIn(banned, params)

    def test_build_board_output_has_no_target_column(self):
        b = build_board(np.array([0.5, 0.9]), np.array([30.0, 5.0]),
                        np.full(2, 60.0))
        for banned in ("drafted", "pick", "actual_drafted", "actual_pick"):
            self.assertNotIn(banned, b.columns)


class TestHoldoutFirewall(unittest.TestCase):
    def test_board_module_never_loads_the_holdout(self):
        """The module may CHECK 2026 is absent (its own validate() does); it
        must never load a 2026 file by name."""
        src = (ROOT / "src" / "board" / "scoring.py").read_text()
        for banned in ("targets_2026", "features_2026", "predictions_2026"):
            self.assertNotIn(banned, src)

    def test_demo_never_loads_the_holdout(self):
        src = (ROOT / "scripts" / "demo.py").read_text()
        for banned in ("targets_2026", "features_2026"):
            self.assertNotIn(banned, src)

    def test_folds_exclude_the_holdout(self):
        for _, tr, vy in folds():
            self.assertNotIn(HOLDOUT_YEAR, tr)
            self.assertNotEqual(vy, HOLDOUT_YEAR)


class TestSelectionDiscipline(unittest.TestCase):
    def test_stage_a_only_remains_a_declared_candidate(self):
        """Draft-Probability-only must always stay on the table — it is a
        valid outcome."""
        self.assertIn("A_STAGE_A_ONLY", METHODS)

    def test_selected_method_is_predeclared(self):
        self.assertIn(GENERAL_BOARD["method"], METHODS)
        self.assertIn(GENERAL_BOARD["stage_b_transform"], TRANSFORMS)

    def test_no_new_dependencies(self):
        for mod in ("xgboost", "lightgbm", "catboost", "optuna", "shap",
                    "mlflow", "torch", "tensorflow"):
            self.assertIsNone(importlib.util.find_spec(mod))


if __name__ == "__main__":
    unittest.main()
