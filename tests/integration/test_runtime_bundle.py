"""Tests for the browser inference bundle (`runtime_bundle.py`).

The bundle is the only copy of the frozen models that leaves Python, so these
tests guard three things: that it carries the frozen configuration and not
some other one, that the compression it uses is lossless where a lossy step
would change an answer, and that it never contains a draft outcome.

They skip cleanly when the bundle has not been built.

  ./.venv/bin/python -m unittest discover -s tests -t .
"""

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

import dataset_format
import runtime_bundle

CORE = runtime_bundle.CORE_PATH
HAVE_BUNDLE = CORE.exists()
needs_bundle = unittest.skipUnless(
    HAVE_BUNDLE, "runtime bundle absent — run scripts/build.py app-runtime")


@needs_bundle
class TestBundleContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.core = json.loads(CORE.read_text())

    def test_frozen_draft_probability_configuration_is_the_selected_one(self):
        from board.probability import DRAFT_PROBABILITY
        self.assertEqual(self.core["frozen"]["draftProbability"],
                         DRAFT_PROBABILITY)

    def test_frozen_draft_order_configuration_is_the_selected_one(self):
        from board.order import DRAFT_ORDER
        self.assertEqual(self.core["frozen"]["draftOrder"], DRAFT_ORDER)

    def test_general_board_method_is_multiplicative(self):
        from board.scoring import GENERAL_BOARD
        self.assertEqual(self.core["frozen"]["generalBoard"]["method"],
                         GENERAL_BOARD["method"])

    def test_feature_order_matches_the_frozen_feature_set(self):
        from board.probability import DRAFT_PROBABILITY, feature_set
        self.assertEqual(self.core["draftProbability"]["featureOrder"],
                         feature_set(DRAFT_PROBABILITY["feature_set"]))

    def test_coefficient_vector_covers_every_feature_and_position(self):
        for key in ("draftProbability", "draftOrder"):
            model = self.core[key]
            n = len(model["featureOrder"])
            self.assertEqual(len(model["coefNumeric"]), n, key)
            self.assertEqual(len(model["imputerMedians"]), n, key)
            self.assertEqual(len(model["scalerMean"]), n, key)
            self.assertEqual(len(model["scalerScale"]), n, key)
            self.assertEqual(len(model["coefPosition"]),
                             len(model["positionCategories"]), key)

    def test_scaler_scale_is_never_zero(self):
        """A zero scale would divide by zero in the browser."""
        for key in ("draftProbability", "draftOrder"):
            for value in self.core[key]["scalerScale"]:
                self.assertIsNotNone(value, key)
                self.assertGreater(value, 0.0, key)

    def test_nba_pool_carries_no_outcome_fields(self):
        for player in self.core["comparables"]["nbaPool"]:
            self.assertEqual(
                set(player) & {"drafted", "pick", "career", "outcome"}, set())

    def test_bundle_has_no_prohibited_tokens(self):
        runtime_bundle.assert_no_outcomes(self.core, "core bundle under test")

    def test_supported_seasons_have_a_season_file(self):
        for season in self.core["supportedSeasons"]:
            path = runtime_bundle.RUNTIME_DIR / f"season-{season}.json"
            self.assertTrue(path.exists(), f"missing bundle for {season}")

    def test_dataset_format_is_embedded_and_current(self):
        self.assertEqual(self.core["datasetFormat"], dataset_format.schema())


@needs_bundle
class TestLosslessPacking(unittest.TestCase):
    """The comparables percentile is a mid-rank, so a value EQUAL to a
    reference entry scores differently from one just above it. The packed
    peer distributions must therefore round-trip exactly, not approximately."""

    def test_pack_round_trips_bit_for_bit(self):
        rng = np.random.default_rng(20260810)
        values = rng.normal(12.0, 5.0, size=4000)
        packed = runtime_bundle._pack_sorted(values)
        restored = runtime_bundle._unpack_sorted(packed)
        expected = np.sort(values)
        self.assertEqual(len(restored), len(expected))
        # bit-for-bit, not np.allclose
        self.assertTrue(np.array_equal(restored, expected))

    def test_packed_season_reference_matches_the_source_distribution(self):
        season = 2026
        path = runtime_bundle.RUNTIME_DIR / f"season-{season}.json"
        if not path.exists():
            self.skipTest(f"no bundle for {season}")
        payload = json.loads(path.read_text())
        reference = runtime_bundle._comparable_reference()
        reference = reference[reference.season == season]

        import pandas as pd
        for metric, packed in payload["comparableReference"].items():
            source = pd.to_numeric(reference[metric], errors="coerce")
            source = np.sort(source[np.isfinite(source)].to_numpy(dtype="float64"))
            restored = runtime_bundle._unpack_sorted(packed)
            self.assertTrue(np.array_equal(restored, source), metric)


@needs_bundle
class TestSimilarityThresholds(unittest.TestCase):
    """The 101 distance cut-points must reproduce the frozen similarity
    score exactly — that is the whole justification for shipping them
    instead of the full ~160,000-value reference distribution."""

    def test_thresholds_reproduce_similarity_scores(self):
        from comparables.similarity import similarity_scores

        rng = np.random.default_rng(20260810)
        reference = np.abs(rng.normal(14.0, 5.0, size=50000))
        thresholds = runtime_bundle.similarity_thresholds(reference)

        queries = np.abs(rng.normal(14.0, 6.0, size=3000))
        expected = similarity_scores(queries, reference)
        for query, want in zip(queries, expected):
            got = runtime_bundle.score_from_thresholds(query, thresholds)
            self.assertEqual(got, int(round(float(want))), query)


class TestNoOutcomeGuard(unittest.TestCase):
    def test_guard_rejects_an_outcome_field(self):
        with self.assertRaises(AssertionError):
            runtime_bundle.assert_no_outcomes(
                {"players": [{"name": "x", "actual_pick": 3}]}, "test payload")

    def test_guard_allows_the_schema_naming_what_it_refuses(self):
        """The import schema lists the outcome columns it rejects. That list
        is the specification of what is banned, not an instance of it."""
        runtime_bundle.assert_no_outcomes(
            {"datasetFormat": dataset_format.schema()}, "schema only")

    def test_guard_still_scans_the_rest_of_a_payload_with_a_schema(self):
        with self.assertRaises(AssertionError):
            runtime_bundle.assert_no_outcomes(
                {"datasetFormat": dataset_format.schema(),
                 "players": [{"actual_pick": 1}]}, "schema plus data")


@needs_bundle
class TestParityFixture(unittest.TestCase):
    """The fixture the browser runtime is held to must be a real
    DraftLens-format file, and must carry no outcome."""

    @classmethod
    def setUpClass(cls):
        base = runtime_bundle.PARITY_DIR
        if not (base / "dataset_2026.json").exists():
            raise unittest.SkipTest("parity fixture absent")
        cls.dataset = json.loads((base / "dataset_2026.json").read_text())
        cls.expected = json.loads((base / "expected_2026.json").read_text())

    def test_dataset_declares_the_current_schema_version(self):
        self.assertEqual(self.dataset["schemaVersion"],
                         dataset_format.SCHEMA_VERSION)

    def test_every_required_field_is_present_on_every_row(self):
        required = dataset_format.required_prospect_fields()
        for row in self.dataset["prospects"]:
            for field in required:
                self.assertIn(field, row)
                self.assertIsNotNone(row[field], (row["prospect_id"], field))

    def test_prospect_ids_are_unique(self):
        ids = [r["prospect_id"] for r in self.dataset["prospects"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_fixture_carries_no_outcome(self):
        runtime_bundle.assert_no_outcomes(self.dataset, "parity dataset")
        runtime_bundle.assert_no_outcomes(self.expected, "parity expectation")

    def test_expected_answers_cover_every_prospect(self):
        self.assertEqual(len(self.expected["prospects"]),
                         len(self.dataset["prospects"]))

    def test_expected_board_ranks_are_a_permutation(self):
        ranks = sorted(p["boardRank"] for p in self.expected["prospects"])
        self.assertEqual(ranks, list(range(1, len(ranks) + 1)))


class TestTemplates(unittest.TestCase):
    def test_json_template_validates_against_its_own_required_fields(self):
        template = dataset_format.json_template()
        self.assertEqual(template["schemaVersion"],
                         dataset_format.SCHEMA_VERSION)
        row = template["prospects"][0]
        for field in dataset_format.required_prospect_fields():
            self.assertIn(field, row, field)

    def test_excel_template_is_a_readable_workbook(self):
        import zipfile

        with tempfile.TemporaryDirectory() as tmp:
            json_path, xlsx_path = dataset_format.write_templates(
                Path(tmp), log=lambda *a: None)
            self.assertTrue(json_path.exists())
            with zipfile.ZipFile(xlsx_path) as z:
                self.assertIsNone(z.testzip())
                names = set(z.namelist())
                self.assertIn("xl/workbook.xml", names)
                self.assertIn("xl/worksheets/sheet1.xml", names)
                self.assertIn("xl/worksheets/sheet2.xml", names)
                header = z.read("xl/worksheets/sheet2.xml").decode()
        # every documented column appears in the prospects header row
        for field in dataset_format.PROSPECT_FIELDS:
            self.assertIn(field["name"], header, field["name"])


if __name__ == "__main__":
    unittest.main()
