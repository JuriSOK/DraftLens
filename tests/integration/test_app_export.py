"""Tests for the public application data export (`app_export.py`).

This module performs no analytical computation — these tests guard that it
faithfully and deterministically exposes the already-frozen 2026 replay
artifacts, and nothing else. Skips cleanly if the replay hasn't been run.

  ./.venv/bin/python -m unittest discover -s tests -t .
"""

import copy
import json
import unittest

import app_export

HAVE_REPLAY = (app_export.ROOT / "data" / "processed" / "2026"
              / "draftlens_2026_predictions.parquet").exists()
needs_replay = unittest.skipUnless(
    HAVE_REPLAY, "2026 replay artifacts absent — run scripts/build.py "
                "replay-2026 then replay-2026-eval")


@needs_replay
class TestExportContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = app_export.build_payload()

    def test_exactly_26_prospects(self):
        self.assertEqual(self.payload["prospectCount"], 26)
        self.assertEqual(len(self.payload["prospects"]), 26)

    def test_ranks_are_unique_1_through_26(self):
        ranks = sorted(p["board"]["rank"] for p in self.payload["prospects"])
        self.assertEqual(ranks, list(range(1, 27)))

    def test_overall_score_is_monotonic_with_rank(self):
        by_rank = sorted(self.payload["prospects"], key=lambda p: p["board"]["rank"])
        scores = [p["board"]["overallScore"] for p in by_rank]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_exactly_three_comparables_where_available(self):
        for p in self.payload["prospects"]:
            if p["comparables"]:
                self.assertEqual(len(p["comparables"]), 3, p["id"])
                names = {c["nbaPlayerName"] for c in p["comparables"]}
                self.assertEqual(len(names), 3, p["id"])

    def test_team_need_profile_values_match_frozen_artifact(self):
        import pandas as pd
        df = pd.read_parquet(app_export.ROOT / "data" / "processed" / "2026"
                            / "draftlens_2026_predictions.parquet")
        df = df.set_index("canonical_prospect_id")
        for p in self.payload["prospects"]:
            row = df.loc[p["id"]]
            for src_key, out_key in app_export.PROFILE_KEYS.items():
                frozen = row[f"team_need_{src_key.lower()}_fit_score"]
                exported = p["profiles"][out_key]["fitScore"]
                if pd.isna(frozen):
                    self.assertIsNone(exported)
                else:
                    self.assertEqual(exported, round(float(frozen)))

    def test_custom_dimensions_match_frozen_dimension_scores(self):
        import pandas as pd
        df = pd.read_parquet(app_export.ROOT / "data" / "processed" / "2026"
                            / "draftlens_2026_predictions.parquet")
        df = df.set_index("canonical_prospect_id")
        mapping = dict(shooting="dimension_shooting",
                      playmaking="dimension_playmaking",
                      defensiveProduction="dimension_box_score_defensive_production",
                      rebounding="dimension_rebounding", size="dimension_size")
        for p in self.payload["prospects"]:
            row = df.loc[p["id"]]
            for out_key, src_col in mapping.items():
                self.assertAlmostEqual(p["dimensions"][out_key],
                                       round(float(row[src_col]), 1), places=1)

    def test_custom_dimensions_exclude_athleticism_and_rim_pressure(self):
        self.assertNotIn("athleticism", self.payload["customDimensions"])
        self.assertNotIn("rimPressure", self.payload["customDimensions"])
        self.assertEqual(self.payload["customDimensions"],
                         ["shooting", "playmaking", "defensiveProduction",
                          "rebounding", "size"])

    def test_rim_pressure_still_present_for_display_even_though_not_custom(self):
        for p in self.payload["prospects"]:
            self.assertIn("rimPressure", p["dimensions"])


@needs_replay
class TestDeterminism(unittest.TestCase):
    def test_export_is_deterministic_apart_from_the_timestamp(self):
        a = app_export.build_payload()
        b = app_export.build_payload()
        a.pop("generatedAt"), b.pop("generatedAt")
        self.assertEqual(json.dumps(a, sort_keys=True),
                         json.dumps(b, sort_keys=True))

    def test_prospects_are_sorted_by_board_rank(self):
        payload = app_export.build_payload()
        ranks = [p["board"]["rank"] for p in payload["prospects"]]
        self.assertEqual(ranks, sorted(ranks))

    def test_comparables_are_sorted_by_similarity_rank(self):
        payload = app_export.build_payload()
        for p in payload["prospects"]:
            ranks = [c["rank"] for c in p["comparables"]]
            self.assertEqual(ranks, sorted(ranks))


class TestNoTargetLeakage(unittest.TestCase):
    def test_prohibited_fields_are_rejected(self):
        for bad_key in ("drafted", "pick", "actualPick", "actual_pick",
                       "draftTeam", "draft_team", "actualRound"):
            payload = {"prospects": [{"id": "x", bad_key: 1}]}
            with self.assertRaises(AssertionError, msg=bad_key):
                app_export.assert_no_leakage(payload)

    def test_internal_only_signal_is_rejected(self):
        payload = {"prospects": [{
            "id": "x", "_draft_order_raw_pick_signal_INTERNAL_ONLY": 12.0}]}
        with self.assertRaises(AssertionError):
            app_export.assert_no_leakage(payload)

    def test_clean_payload_passes(self):
        app_export.assert_no_leakage({"prospects": [{"id": "x", "board":
                                                       {"rank": 1}}]})

    @needs_replay
    def test_real_export_has_no_prohibited_field_anywhere(self):
        payload = app_export.build_payload()
        app_export.assert_no_leakage(payload)  # must not raise

    @needs_replay
    def test_written_json_file_has_no_prohibited_substring(self):
        path, _, _ = app_export.write_payload()
        text = path.read_text().lower()
        for bad in ("actual_pick", "actualpick", "draft_team", "draftteam",
                   "actual_round", "\"drafted\":", "\"pick\":"):
            self.assertNotIn(bad, text, bad)


if __name__ == "__main__":
    unittest.main()
