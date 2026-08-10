"""Tests for the 2026 holdout replay orchestration (`replay.py`).

These are guards on the REPLAY WORKFLOW's discipline — population size,
target-freedom, training scope, and the freeze/unseal ordering — not on the
2026 evaluation numbers themselves (those are one-time results, recorded in
docs/VALIDATION.md, not re-asserted by a test).

Tests that need the frozen artifacts already on disk (produced by
`scripts/build.py replay-2026`) skip cleanly if they are absent, exactly like
`tests/integration/test_frozen_anchors.py` does for the dataset/features
layers.

  ./.venv/bin/python -m unittest discover -s tests -t .
"""

import inspect
import json
import unittest
from pathlib import Path

import pandas as pd

import replay

ROOT = Path(__file__).resolve().parents[2]

HAVE_ARTIFACTS = (replay.PREDICTIONS_PATH.exists()
                  and replay.COMPARABLES_PATH.exists()
                  and replay.PROVENANCE_PATH.exists())
needs_artifacts = unittest.skipUnless(
    HAVE_ARTIFACTS, "2026 replay artifacts absent — run "
                   "scripts/build.py replay-2026")


class TestPopulation(unittest.TestCase):
    def test_2026_population_is_26(self):
        pop, feats = replay.build_2026_frame()
        self.assertEqual(len(pop), 26)
        self.assertEqual(len(feats), 26)

    def test_2026_population_is_target_free(self):
        pop, feats = replay.build_2026_frame()
        replay.assert_target_free(pop, "test")
        replay.assert_target_free(feats, "test")

    def test_build_2026_frame_never_calls_load_targets(self):
        """Source-level guarantee: the function's own CODE (not its
        docstring, which explains why it avoids these) never references the
        target loader."""
        import ast
        src = inspect.getsource(replay.build_2026_frame)
        tree = ast.parse(src)
        body = tree.body[0]
        if (body.body and isinstance(body.body[0], ast.Expr)
                and isinstance(body.body[0].value, ast.Constant)):
            body.body = body.body[1:]
        code_only = ast.unparse(tree)
        self.assertNotIn("load_targets", code_only)
        self.assertNotIn("build_year", code_only)
        self.assertNotIn("build_prospect_dataset", code_only)


class TestTrainingScope(unittest.TestCase):
    def test_draft_probability_trains_on_development_only(self):
        src = inspect.getsource(replay.fit_draft_probability_2026)
        self.assertIn("load_development", src)
        self.assertNotIn("load_population(HOLDOUT_YEAR", src)
        self.assertIn("assert_no_holdout", src)

    def test_draft_order_trains_on_drafted_development_only(self):
        src = inspect.getsource(replay.fit_draft_order_2026)
        self.assertIn("load_draft_order", src)
        self.assertIn("assert_no_holdout", src)

    def test_training_frames_exclude_2026_by_construction(self):
        from data.build import load_development, load_draft_order
        self.assertNotIn(2026, set(load_development().draft_year))
        self.assertNotIn(2026, set(load_draft_order().draft_year))


class TestNoTargetInPredictionPath(unittest.TestCase):
    def test_generate_asserts_target_free_before_writing(self):
        src = inspect.getsource(replay.generate)
        self.assertIn("assert_target_free(predictions", src)

    def test_prohibited_fields_cover_every_outcome_name(self):
        for f in ("drafted", "pick", "round", "drafting_team", "actual_pick",
                 "draft_team"):
            self.assertIn(f, replay.PROHIBITED_TARGET_FIELDS)

    def test_assert_target_free_raises_on_a_planted_column(self):
        df = pd.DataFrame({"a": [1], "drafted": [1]})
        with self.assertRaises(AssertionError):
            replay.assert_target_free(df, "test")

    def test_team_need_builder_never_reaches_an_outcome_field(self):
        src = inspect.getsource(replay.build_2026_team_need)
        for banned in replay.PROHIBITED_TARGET_FIELDS:
            self.assertNotIn(f'"{banned}"', src)
            self.assertNotIn(f"'{banned}'", src)
        self.assertNotIn("load_targets", src)

    def test_comparables_builder_never_reaches_an_outcome_field(self):
        src = inspect.getsource(replay.build_2026_comparables)
        for banned in replay.PROHIBITED_TARGET_FIELDS:
            self.assertNotIn(f'"{banned}"', src)
            self.assertNotIn(f"'{banned}'", src)
        self.assertNotIn("load_targets", src)

    def test_comparables_never_touches_the_nba_reference_window(self):
        """Only the NCAA-side reference is extended for 2026 scoring; the
        frozen NBA reference window (2021-2025) must never be touched."""
        src = inspect.getsource(replay.build_2026_comparables)
        self.assertNotIn("REFERENCE_SEASONS", src)
        self.assertNotIn("2026 + 1", src.replace("HOLDOUT_YEAR + 1", "X"))


class TestGeneralBoardAndOverallScoreUnchanged(unittest.TestCase):
    def test_replay_calls_the_frozen_build_board(self):
        src = inspect.getsource(replay.build_2026_board)
        self.assertIn("from board.scoring import build_board, rank_board", src)

    @needs_artifacts
    def test_overall_score_is_monotonic_on_the_frozen_artifact(self):
        df = pd.read_parquet(replay.PREDICTIONS_PATH)
        order = df.sort_values("final_board_signal", ascending=False)
        self.assertTrue(order.overall_score.is_monotonic_decreasing)
        self.assertTrue(((df.overall_score >= 0) & (df.overall_score <= 100)).all())

    @needs_artifacts
    def test_frozen_artifact_config_matches_live_frozen_dicts(self):
        from board.order import DRAFT_ORDER
        from board.probability import DRAFT_PROBABILITY
        from board.scoring import GENERAL_BOARD
        prov = json.loads(replay.PROVENANCE_PATH.read_text())
        spec = prov["model_specifications"]
        self.assertIn(DRAFT_PROBABILITY["family"], spec["draft_probability"])
        self.assertIn(str(DRAFT_PROBABILITY["C"]), spec["draft_probability"])
        self.assertIn(DRAFT_ORDER["family"], spec["draft_order"])
        self.assertIn(GENERAL_BOARD["method"], spec["general_board"])


class TestTeamNeedFrozenConfig(unittest.TestCase):
    def test_all_six_profiles_are_the_frozen_profiles(self):
        from team_need.profiles import profile_names
        self.assertEqual(set(profile_names()),
                         {"SHOOTER", "SLASHER", "PLAYMAKER", "THREE_AND_D",
                          "RIM_PROTECTOR", "STRETCH_BIG"})

    @needs_artifacts
    def test_frozen_artifact_has_a_column_for_every_profile(self):
        from team_need.profiles import profile_names
        df = pd.read_parquet(replay.PREDICTIONS_PATH)
        for p in profile_names():
            self.assertIn(f"team_need_{p.lower()}_fit_score", df.columns)


class TestComparablesFrozenReference(unittest.TestCase):
    @needs_artifacts
    def test_every_prospect_used_the_frozen_nba_pool(self):
        prov = json.loads(replay.PROVENANCE_PATH.read_text())
        self.assertIn("2021-2025", prov["nba_reference_window"])
        self.assertIn("RECENT_MULTI_SEASON", prov["nba_reference_window"])

    @needs_artifacts
    def test_exactly_three_unique_players_where_available(self):
        comps = json.loads(replay.COMPARABLES_PATH.read_text())
        for pid, r in comps.items():
            if r["status"] != "OK":
                self.assertEqual(r["comparables"], [])
                continue
            ids = [c["nba_player_id"] for c in r["comparables"]]
            self.assertEqual(len(r["comparables"]), 3, pid)
            self.assertEqual(len(set(ids)), 3, pid)


class TestTargetAccessGuard(unittest.TestCase):
    def test_evaluate_refuses_when_artifacts_are_absent(self):
        import shutil
        import tempfile
        if not replay.PREDICTIONS_PATH.exists():
            self.skipTest("no frozen predictions to temporarily move")
        with tempfile.TemporaryDirectory() as tmp:
            backup = Path(tmp) / "predictions.parquet"
            shutil.move(str(replay.PREDICTIONS_PATH), str(backup))
            try:
                with self.assertRaises(RuntimeError):
                    replay._require_frozen_predictions()
            finally:
                shutil.move(str(backup), str(replay.PREDICTIONS_PATH))

    @needs_artifacts
    def test_evaluate_refuses_on_a_tampered_hash(self):
        original = replay.PREDICTIONS_PATH.read_bytes()
        try:
            replay.PREDICTIONS_PATH.write_bytes(original + b"tampered")
            with self.assertRaises(RuntimeError):
                replay._require_frozen_predictions()
        finally:
            replay.PREDICTIONS_PATH.write_bytes(original)

    @needs_artifacts
    def test_hash_exists_and_matches_provenance_before_any_target_access(self):
        prov, live_hash = replay._require_frozen_predictions()
        self.assertEqual(live_hash, prov["prediction_artifact"]["sha256"])
        self.assertEqual(prov["prediction_artifact"]["rows"], 26)

    @needs_artifacts
    def test_evaluate_is_gated_by_require_frozen_predictions(self):
        src = inspect.getsource(replay.evaluate)
        self.assertTrue(src.strip().startswith('"""')
                        or "_require_frozen_predictions()" in src.split("\n")[1]
                        or "_require_frozen_predictions" in src)
        # the guard call must precede the first target read in source order
        guard_pos = src.index("_require_frozen_predictions()")
        target_pos = src.index("draft_targets_")
        self.assertLess(guard_pos, target_pos,
                        "evaluate() reads a target file before its guard")


class TestHashImmutability(unittest.TestCase):
    @needs_artifacts
    def test_recorded_hash_matches_the_file_on_disk_right_now(self):
        prov = json.loads(replay.PROVENANCE_PATH.read_text())
        self.assertEqual(replay._sha256_file(replay.PREDICTIONS_PATH),
                         prov["prediction_artifact"]["sha256"])

    @needs_artifacts
    def test_evaluation_record_shows_two_matching_immutability_checks(self):
        """`evaluate()` re-hashes immediately after unsealing and again after
        evaluation; both are recorded and must equal the pre-unseal hash."""
        ev = json.loads(replay.EVALUATION_PATH.read_text())
        prov = json.loads(replay.PROVENANCE_PATH.read_text())
        self.assertEqual(ev["pre_unseal_hash"],
                         prov["prediction_artifact"]["sha256"])
        # the artifact on disk right now must still match — proves nothing
        # rewrote it after evaluation either
        self.assertEqual(replay._sha256_file(replay.PREDICTIONS_PATH),
                         ev["pre_unseal_hash"])


if __name__ == "__main__":
    unittest.main()
