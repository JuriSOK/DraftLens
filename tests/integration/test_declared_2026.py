"""Tests for the 2026 ALL-DECLARED product board (`declared.py`) and the
declaration/withdrawal status resolution it depends on
(`data.population.population_status`).

Like `test_replay.py`, these guard the WORKFLOW's discipline — population
provenance, target-freedom, and that declaration/withdrawal status never
enters scoring — not the resulting ranking's numeric values (those are a
product exploration, not a frozen anchor). Tests needing acquired/generated
artifacts skip cleanly if they are absent.

  ./.venv/bin/python -m unittest discover -s tests -t .
"""

import ast
import inspect
import json
import unittest

import pandas as pd

import declared
import replay
from data.population import load_declared, load_population, population_status

HAVE_DECLARED_SNAPSHOT = (declared.OUT_DIR.parent / "raw" / "draft_population"
                          / "draft_declared_2026.csv").exists() or \
    (load_declared(2026) is not None)
needs_declared_snapshot = unittest.skipUnless(
    HAVE_DECLARED_SNAPSHOT, "declared-pool snapshot absent — run "
                           "scripts/acquire.py declared --years 2026")

HAVE_SCORED = declared.DECLARED_PREDICTIONS_PATH.exists()
needs_scored = unittest.skipUnless(
    HAVE_SCORED, "declared-pool scoring absent — run scripts/build.py "
                "declared-2026")

HAVE_FROZEN_HOLDOUT = replay.PREDICTIONS_PATH.exists()
needs_frozen_holdout = unittest.skipUnless(
    HAVE_FROZEN_HOLDOUT, "2026 holdout replay absent — run scripts/build.py "
                        "replay-2026")


def _code_only(fn):
    src = inspect.getsource(fn)
    tree = ast.parse(src)
    body = tree.body[0]
    if (body.body and isinstance(body.body[0], ast.Expr)
            and isinstance(body.body[0].value, ast.Constant)):
        body.body = body.body[1:]
    return ast.unparse(tree)


class TestDeclaredSourceIsDeterministic(unittest.TestCase):
    """The initial declared pool comes from one FIXED Wikipedia revision per
    year, not "the live article" — so acquiring it twice gives the same
    result."""

    @needs_declared_snapshot
    def test_declared_snapshot_is_a_fixed_revision(self):
        from data.wikipedia import DECLARED_SNAPSHOTS
        snap = DECLARED_SNAPSHOTS[2026]
        self.assertIn("revid", snap)
        self.assertIn("canonical_url", snap)
        self.assertIn("nba.com", snap["canonical_url"])

    @needs_declared_snapshot
    def test_loading_declared_pool_twice_gives_identical_rows(self):
        a = load_declared(2026)
        b = load_declared(2026)
        pd.testing.assert_frame_equal(a, b)

    def test_missing_year_returns_none_not_a_fabricated_pool(self):
        self.assertIsNone(load_declared(2099))


class TestPopulationStatus(unittest.TestCase):
    @needs_declared_snapshot
    def test_final_population_is_subset_of_declared(self):
        status = population_status(2026)
        self.assertIsNotNone(status)
        n_final = int((status.population_status == "FINAL_ENTRY").sum())
        self.assertEqual(n_final, len(load_population(2026)))

    @needs_declared_snapshot
    def test_status_uses_only_two_values(self):
        status = population_status(2026)
        self.assertEqual(set(status.population_status),
                         {"FINAL_ENTRY", "WITHDRAWN"})

    def test_status_is_none_when_no_snapshot_acquired(self):
        self.assertIsNone(population_status(2099))

    def test_status_resolution_never_reads_draft_targets(self):
        """Source-level guarantee: no reference to the target loader or the
        raw targets directory in the function's own code."""
        code = _code_only(population_status)
        self.assertNotIn("load_targets", code)
        self.assertNotIn("TGT_DIR", code)
        self.assertNotIn("drafted", code)
        self.assertNotIn("pick", code)


class TestDeclaredFrameIsTargetFree(unittest.TestCase):
    def test_build_declared_frame_never_calls_load_targets(self):
        code = _code_only(declared.build_declared_frame)
        self.assertNotIn("load_targets", code)

    def test_score_declared_never_passes_status_into_scoring_calls(self):
        """population_status's output must never be an argument to any
        model-fitting or board-building call — it is joined onto the
        finished predictions afterward, as display metadata only."""
        src = inspect.getsource(declared.score_declared)
        for call in ("fit_draft_probability_2026(", "fit_draft_order_2026(",
                    "build_2026_board(", "build_2026_team_need(",
                    "build_2026_comparables("):
            start = src.index(call) + len(call)
            end = src.index(")", start)
            args = src[start:end]
            self.assertNotIn("status", args, call)

    @needs_declared_snapshot
    def test_declared_population_frame_is_target_free(self):
        matched, feats, audit = declared.build_declared_frame()
        replay.assert_target_free(matched, "test")
        replay.assert_target_free(feats, "test")
        self.assertNotIn("population_status", feats.columns)
        self.assertNotIn("early_entrant", feats.columns)


class TestScoredDeclaredPool(unittest.TestCase):
    @needs_scored
    def test_predictions_are_target_free(self):
        df = pd.read_parquet(declared.DECLARED_PREDICTIONS_PATH)
        replay.assert_target_free(df, "test")

    @needs_scored
    def test_includes_withdrawn_prospects_where_data_exists(self):
        df = pd.read_parquet(declared.DECLARED_PREDICTIONS_PATH)
        self.assertIn("WITHDRAWN", set(df.population_status))
        self.assertIn("FINAL_ENTRY", set(df.population_status))

    @needs_scored
    def test_ranking_is_deterministic_within_a_run(self):
        matched, feats, audit = declared.build_declared_frame()
        feats = feats.sort_values("canonical_prospect_id").reset_index(drop=True)
        p1 = replay.fit_draft_probability_2026(feats)
        p2 = replay.fit_draft_probability_2026(feats)
        import numpy as np
        self.assertTrue(np.allclose(p1, p2))
        board1, _ = replay.build_2026_board(feats, p1, np.zeros(len(feats)))
        board2, _ = replay.build_2026_board(feats, p2, np.zeros(len(feats)))
        self.assertEqual(list(board1.sort_values("canonical_prospect_id").board_rank),
                         list(board2.sort_values("canonical_prospect_id").board_rank))

    @needs_scored
    def test_overall_score_is_class_relative_to_the_declared_pool(self):
        """A prospect's Overall Score depends on the population it is ranked
        within — declared-pool scores are computed fresh, not copied from the
        26-only frozen board."""
        df = pd.read_parquet(declared.DECLARED_PREDICTIONS_PATH)
        self.assertEqual(sorted(df.board_rank), list(range(1, len(df) + 1)))
        ordered = df.sort_values("final_board_signal", ascending=False)
        self.assertTrue(ordered.overall_score.is_monotonic_decreasing)


@needs_scored
@needs_frozen_holdout
class TestFinalEntrantsUnchangedByDeclaredWork(unittest.TestCase):
    """The regression guard: none of this phase's new code may alter the
    frozen 26-prospect holdout artifact. `replay.evaluate()`'s own hash guard
    is the authority; this test additionally cross-checks values."""

    def test_frozen_artifact_hash_still_matches_its_provenance_record(self):
        provenance, live_hash = replay._require_frozen_predictions()
        self.assertEqual(provenance["prediction_artifact"]["sha256"], live_hash)
        self.assertEqual(provenance["prediction_artifact"]["rows"], 26)

    def test_app_export_final_entrants_board_matches_frozen_file_exactly(self):
        import app_export
        frozen = pd.read_parquet(replay.PREDICTIONS_PATH).set_index(
            "canonical_prospect_id")
        payload = app_export.build_payload()
        checked = 0
        for p in payload["years"]["2026"]["prospects"]:
            if p["finalEntrantsBoard"] is None:
                continue
            row = frozen.loc[p["id"]]
            self.assertEqual(p["finalEntrantsBoard"]["rank"], int(row.board_rank))
            self.assertEqual(p["finalEntrantsBoard"]["overallScore"],
                             int(row.overall_score))
            self.assertAlmostEqual(p["finalEntrantsBoard"]["draftProbability"],
                                   round(float(row.stage_a_probability), 3))
            checked += 1
        self.assertEqual(checked, 26)


if __name__ == "__main__":
    unittest.main()
