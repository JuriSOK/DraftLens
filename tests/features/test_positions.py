"""Tests for leakage-safe position handling and the deny list.

  ./.venv/bin/python -m unittest discover -s tests -v
"""

import unittest

import pandas as pd

from paths import interim
from validation import DENY_EXACT

DATASET = interim("dataset")
from features.basketball import UNKNOWN, to_position_3  # noqa: E402


class TestCoarsePosition(unittest.TestCase):
    """position_3 from hoopR — the only leakage-safe source."""

    def test_guard_labels(self):
        for lab in ("G", "PG", "SG", "g", " sg "):
            self.assertEqual(to_position_3(lab), "G", lab)

    def test_forward_labels(self):
        for lab in ("F", "SF", "PF"):
            self.assertEqual(to_position_3(lab), "F", lab)

    def test_center(self):
        self.assertEqual(to_position_3("C"), "C")

    def test_unresolvable_labels_are_unknown_not_guessed(self):
        for lab in ("ATH", "NA", "", None, "QQ"):
            self.assertEqual(to_position_3(lab), UNKNOWN, repr(lab))


class TestLeakageDenyList(unittest.TestCase):
    def test_contaminated_population_metadata_is_denied(self):
        # Measured: position_from_population resolves for 100% of drafted vs
        # 7.7% of undrafted prospects.
        for c in ("position_from_population", "class_from_population",
                  "match_method", "match_confidence"):
            self.assertIn(c, DENY_EXACT, f"{c} must be denied as a feature")

    def test_hoopr_position_remains_allowed(self):
        self.assertNotIn("hoopr_position", DENY_EXACT)


@unittest.skipUnless((DATASET / "features_2014_2025.parquet").exists(),
                     "dataset outputs not built")
class TestBuiltFeatureFiles(unittest.TestCase):
    def test_no_contaminated_column_survives_in_any_partition(self):
        for lab in ("2011_2013", "2014_2025", "2026"):
            cols = {c.lower()
                    for c in pd.read_parquet(DATASET / f"features_{lab}.parquet").columns}
            self.assertFalse(cols & DENY_EXACT,
                             f"{lab} carries prohibited columns: {cols & DENY_EXACT}")

    def test_hoopr_position_still_available_for_canonical_mapping(self):
        f = pd.read_parquet(DATASET / "features_2014_2025.parquet")
        self.assertIn("hoopr_position", f.columns)
        p3 = f.hoopr_position.map(to_position_3)
        self.assertGreater((p3 != UNKNOWN).mean(), 0.95,
                           "coarse position coverage should exceed 95%")


if __name__ == "__main__":
    unittest.main(verbosity=2)
