"""Tests for the public application data export (`app_export.py`).

This module performs no analytical computation — these tests guard that it
faithfully and deterministically exposes the already-frozen 2026 replay and
all-declared artifacts, and nothing else. Skips cleanly if the replay hasn't
been run.

  ./.venv/bin/python -m unittest discover -s tests -t .
"""

import json
import unittest

import app_export

HAVE_REPLAY = (app_export.ROOT / "data" / "processed" / "2026"
              / "draftlens_2026_predictions.parquet").exists()
HAVE_DECLARED = (app_export.ROOT / "data" / "processed" / "2026"
                 / "draftlens_2026_declared_predictions.parquet").exists()
needs_replay = unittest.skipUnless(
    HAVE_REPLAY, "2026 replay artifacts absent — run scripts/build.py "
                "replay-2026 then replay-2026-eval")
needs_declared = unittest.skipUnless(
    HAVE_DECLARED, "2026 declared-pool artifacts absent — run "
                  "scripts/acquire.py declared --years 2026 then "
                  "scripts/build.py declared-2026")


@needs_replay
class TestExportContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = app_export.build_payload()
        cls.y2026 = cls.payload["years"]["2026"]

    def test_year_2026_available(self):
        self.assertEqual(self.y2026["status"], "available")

    def test_final_entrants_count_is_exactly_26(self):
        self.assertEqual(self.y2026["finalEntrantsCount"], 26)
        final_entrants = [p for p in self.y2026["prospects"]
                          if p["finalEntrantsBoard"] is not None]
        self.assertEqual(len(final_entrants), 26)

    def test_final_entrant_ranks_are_unique_1_through_26(self):
        ranks = sorted(p["finalEntrantsBoard"]["rank"]
                       for p in self.y2026["prospects"]
                       if p["finalEntrantsBoard"] is not None)
        self.assertEqual(ranks, list(range(1, 27)))

    def test_final_entrants_overall_score_monotonic_with_rank(self):
        final_entrants = [p for p in self.y2026["prospects"]
                          if p["finalEntrantsBoard"] is not None]
        by_rank = sorted(final_entrants, key=lambda p: p["finalEntrantsBoard"]["rank"])
        scores = [p["finalEntrantsBoard"]["overallScore"] for p in by_rank]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_exactly_three_comparables_where_available(self):
        for p in self.y2026["prospects"]:
            if p["comparables"]:
                self.assertEqual(len(p["comparables"]), 3, p["id"])
                names = {c["nbaPlayerName"] for c in p["comparables"]}
                self.assertEqual(len(names), 3, p["id"])

    def test_team_need_profile_values_match_frozen_artifact(self):
        import pandas as pd
        df = pd.read_parquet(app_export.ROOT / "data" / "processed" / "2026"
                            / "draftlens_2026_predictions.parquet")
        df = df.set_index("canonical_prospect_id")
        for p in self.y2026["prospects"]:
            if p["id"] not in df.index:
                continue
            row = df.loc[p["id"]]
            for src_key, out_key in app_export.PROFILE_KEYS.items():
                frozen = row[f"team_need_{src_key.lower()}_fit_score"]
                exported = p["profiles"][out_key]["fitScore"]
                if pd.isna(frozen):
                    self.assertIsNone(exported)
                else:
                    self.assertEqual(exported, round(float(frozen)))

    def test_custom_dimensions_exclude_athleticism_and_rim_pressure(self):
        self.assertNotIn("athleticism", self.payload["customDimensions"])
        self.assertNotIn("rimPressure", self.payload["customDimensions"])
        self.assertEqual(self.payload["customDimensions"],
                         ["shooting", "playmaking", "defensiveProduction",
                          "rebounding", "size"])

    def test_no_athleticism_anywhere_in_payload(self):
        text = json.dumps(self.payload).lower()
        self.assertNotIn("athletic", text)

    def test_rim_pressure_still_present_for_display_even_though_not_custom(self):
        for p in self.y2026["prospects"]:
            self.assertIn("rimPressure", p["dimensions"])

    def test_profile_stats_expose_height_stl_blk_tov(self):
        found_height = False
        for p in self.y2026["prospects"]:
            self.assertIn("heightInches", p["stats"])
            self.assertIn("stealsPer40", p["stats"])
            self.assertIn("blocksPer40", p["stats"])
            self.assertIn("turnoversPer40", p["stats"])
            if p["stats"]["heightInches"] is not None:
                found_height = True
                self.assertGreater(p["stats"]["heightInches"], 60)
                self.assertLess(p["stats"]["heightInches"], 96)
        self.assertTrue(found_height, "no prospect had a height value at all")

    def test_2027_is_unavailable_and_carries_no_prospect_data(self):
        y2027 = self.payload["years"]["2027"]
        self.assertEqual(y2027["status"], "unavailable")
        self.assertNotIn("prospects", y2027)
        self.assertIn("reason", y2027)


@needs_declared
class TestAllDeclared(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = app_export.build_payload()
        cls.y2026 = cls.payload["years"]["2026"]

    def test_declared_pool_includes_withdrawn_prospects(self):
        statuses = {p["populationStatus"] for p in self.y2026["prospects"]}
        self.assertIn("WITHDRAWN", statuses)
        self.assertIn("FINAL_ENTRY", statuses)

    def test_withdrawn_prospects_have_no_final_entrants_board(self):
        for p in self.y2026["prospects"]:
            if p["populationStatus"] == "WITHDRAWN":
                self.assertIsNone(p["finalEntrantsBoard"], p["id"])

    def test_final_entry_prospects_have_both_boards_when_scoreable(self):
        for p in self.y2026["prospects"]:
            if p["populationStatus"] == "FINAL_ENTRY" and p["declaredBoard"] is not None:
                self.assertIsNotNone(p["finalEntrantsBoard"], p["id"])

    def test_declared_board_ranks_are_dense_and_unique(self):
        ranks = sorted(p["declaredBoard"]["rank"] for p in self.y2026["prospects"]
                       if p["declaredBoard"] is not None)
        self.assertEqual(ranks, list(range(1, len(ranks) + 1)))

    def test_official_source_is_recorded(self):
        src = self.y2026["officialSource"]
        self.assertIn("nba.com", src["url"])
        self.assertIn("announcementDate", src)

    def test_no_draft_outcome_fields_in_audit_or_source(self):
        blob = json.dumps(self.y2026["audit"]) + json.dumps(self.y2026["officialSource"])
        for bad in ("drafted", "pick", "actual_pick", "draft_team"):
            self.assertNotIn(bad, blob.lower())


@needs_replay
class TestDeterminism(unittest.TestCase):
    def test_export_is_deterministic_apart_from_the_timestamp(self):
        a = app_export.build_payload()
        b = app_export.build_payload()
        a.pop("generatedAt"), b.pop("generatedAt")
        self.assertEqual(json.dumps(a, sort_keys=True),
                         json.dumps(b, sort_keys=True))

    def test_comparables_are_sorted_by_similarity_rank(self):
        payload = app_export.build_payload()
        for p in payload["years"]["2026"]["prospects"]:
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
