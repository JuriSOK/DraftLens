"""Tests for the 2027 PROJECTED WATCHLIST (`watchlist2027.py`).

These guard the workflow's discipline: the consensus population is built
from recorded public sources (never a mock draft used as a feature), no
Draft Probability / Draft Order / General Board is ever computed for this
population, incoming freshmen without NCAA data are never scored, and the
watchlist can never be mistaken for an official declaration. Tests needing
acquired/built artifacts skip cleanly if absent.

  ./.venv/bin/python -m unittest discover -s tests -t .
"""

import ast
import inspect
import json
import unittest

import pandas as pd

import watchlist2027

HAVE_SOURCES = watchlist2027.SOURCES_PATH.exists()
needs_sources = unittest.skipUnless(
    HAVE_SOURCES, "2027 watchlist sources not acquired — see "
                 "data/raw/draft_watchlist/draft_watchlist_sources_2027.csv")

HAVE_BUILT = watchlist2027.PROVENANCE_PATH.exists()
needs_built = unittest.skipUnless(
    HAVE_BUILT, "2027 watchlist not built — run scripts/build.py watchlist-2027")


def _code_only(fn):
    src = inspect.getsource(fn)
    tree = ast.parse(src)
    body = tree.body[0]
    if (body.body and isinstance(body.body[0], ast.Expr)
            and isinstance(body.body[0].value, ast.Constant)):
        body.body = body.body[1:]
    return ast.unparse(tree)


def _module_code_only(module):
    """Every function/class definition's code, docstrings stripped —
    excludes the module's own top-level docstring (which explains in prose
    what this module deliberately does NOT call)."""
    tree = ast.parse(inspect.getsource(module))
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                            ast.ClassDef)):
            if (node.body and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)):
                node.body = node.body[1:] or [ast.Pass()]
    return ast.unparse(tree)


class TestNoDraftModelForWatchlist(unittest.TestCase):
    """Source-level guarantee: this module's code never references the
    frozen Draft Probability / Draft Order / General Board functions."""

    def test_module_never_calls_draft_probability(self):
        code = _module_code_only(watchlist2027)
        self.assertNotIn("fit_draft_probability_2026", code)

    def test_module_never_calls_draft_order(self):
        code = _module_code_only(watchlist2027)
        self.assertNotIn("fit_draft_order_2026", code)

    def test_module_never_calls_build_2026_board(self):
        code = _module_code_only(watchlist2027)
        self.assertNotIn("build_2026_board", code)

    def test_score_returning_only_calls_team_need_and_comparables(self):
        src = inspect.getsource(watchlist2027.score_returning)
        self.assertIn("build_2026_team_need", src)
        self.assertIn("build_2026_comparables", src)


class TestConsensusRuleIsReproducible(unittest.TestCase):
    def test_missing_sources_returns_none(self):
        # build_consensus reads the module-level SOURCES_PATH; when absent
        # it must return None rather than fabricate a population.
        if HAVE_SOURCES:
            self.skipTest("sources present in this environment")
        self.assertIsNone(watchlist2027.build_consensus())

    @needs_sources
    def test_consensus_is_deterministic(self):
        a = watchlist2027.build_consensus()
        b = watchlist2027.build_consensus()
        pd.testing.assert_frame_equal(a, b)

    @needs_sources
    def test_consensus_requires_at_least_two_sources(self):
        pop = watchlist2027.build_consensus()
        self.assertTrue((pop.n_sources >= watchlist2027.MIN_SOURCES).all())

    @needs_sources
    def test_consensus_excludes_international_only_players(self):
        df = watchlist2027.load_sources()
        international_names = set(
            df[df.is_ncaa.astype(str) == "False"].player_name)
        pop = watchlist2027.build_consensus()
        self.assertFalse(set(pop.player_name) & international_names)

    @needs_sources
    def test_source_rank_is_never_used_as_a_feature(self):
        """rank exists only in the raw source table for membership
        determination — build_consensus's own code never reads it."""
        code = _code_only(watchlist2027.build_consensus)
        self.assertNotIn("rank", code)


class TestReturningVsIncoming(unittest.TestCase):
    def test_build_watchlist_frame_never_calls_load_targets(self):
        code = _code_only(watchlist2027.build_watchlist_frame)
        self.assertNotIn("load_targets", code)

    @needs_sources
    def test_incoming_players_have_no_engineered_features(self):
        matched, feats_returning, incoming = watchlist2027.build_watchlist_frame()
        returning_ids = set(feats_returning.canonical_prospect_id)
        incoming_ids = {r["canonical_prospect_id"] for r in incoming}
        self.assertFalse(returning_ids & incoming_ids)

    @needs_sources
    def test_matching_uses_most_recent_completed_season(self):
        src = inspect.getsource(watchlist2027.build_watchlist_frame)
        self.assertIn("STATS_SEASON", src)
        self.assertEqual(watchlist2027.STATS_SEASON, 2026)


class TestWatchlistArtifacts(unittest.TestCase):
    @needs_built
    def test_provenance_label_does_not_claim_official_declaration(self):
        provenance = json.loads(watchlist2027.PROVENANCE_PATH.read_text())
        label = provenance["label"].lower()
        self.assertNotIn("declared", label)
        self.assertNotIn("official", label)
        self.assertIn("projected", label + provenance["label"])

    @needs_built
    def test_returning_predictions_are_target_free(self):
        import replay
        if not watchlist2027.RETURNING_PREDICTIONS_PATH.exists():
            self.skipTest("no returning players this build")
        df = pd.read_parquet(watchlist2027.RETURNING_PREDICTIONS_PATH)
        replay.assert_target_free(df, "test")

    @needs_built
    def test_returning_predictions_carry_no_board_columns(self):
        if not watchlist2027.RETURNING_PREDICTIONS_PATH.exists():
            self.skipTest("no returning players this build")
        df = pd.read_parquet(watchlist2027.RETURNING_PREDICTIONS_PATH)
        for banned in ("board_rank", "overall_score", "final_board_signal",
                      "stage_a_probability", "stage_b_quality"):
            self.assertNotIn(banned, df.columns)


class TestAppExportWatchlist(unittest.TestCase):
    @needs_built
    def test_incoming_prospects_have_no_fabricated_stats(self):
        import app_export
        payload = app_export.build_payload()
        y2027 = payload["years"]["2027"]
        if y2027["status"] != "watchlist":
            self.skipTest("2027 not built in this environment")
        for p in y2027["prospects"]:
            if not p["hasStats"]:
                self.assertIsNone(p["stats"])
                self.assertIsNone(p["dimensions"])
                self.assertIsNone(p["profiles"])
                self.assertEqual(p["comparables"], [])

    @needs_built
    def test_no_board_or_draft_probability_fields_for_2027(self):
        import app_export
        payload = app_export.build_payload()
        y2027 = payload["years"]["2027"]
        if y2027["status"] != "watchlist":
            self.skipTest("2027 not built in this environment")
        blob = json.dumps(y2027).lower()
        for banned in ("boardrank", "overallscore", "draftprobability",
                      "draftordersignal", "\"board\":"):
            self.assertNotIn(banned, blob.replace(" ", ""), banned)

    @needs_built
    def test_2026_final_entrants_unaffected_by_2027_or_scope_changes(self):
        """Regression guard for this phase: the frozen 26-player holdout
        artifact is untouched by any APP-1.2 work."""
        import replay
        provenance, live_hash = replay._require_frozen_predictions()
        self.assertEqual(provenance["prediction_artifact"]["sha256"], live_hash)


if __name__ == "__main__":
    unittest.main()
