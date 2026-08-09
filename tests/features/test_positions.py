"""Tests for ML-1 position handling and holdout guards.

  ./.venv/bin/python -m unittest discover -s tests -v
"""

import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "experiments"))

from draftlens.leakage import DENY_EXACT  # noqa: E402
from draftlens.paths import interim  # noqa: E402

ML0 = interim("ml0")
from draftlens.features.positions import (UNKNOWN, load_map, normalize_label,  # noqa: E402
                       parse_five_position, to_position_3)


class TestCoarsePosition(unittest.TestCase):
    """position_3 from hoopR — the only leakage-safe source (DEC-065)."""

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


class TestFivePositionParser(unittest.TestCase):
    """Retained parser; deliberately NOT applied to any contaminated field."""

    def test_direct_labels_map_to_themselves(self):
        for lab in ("PG", "SG", "SF", "PF", "C"):
            self.assertEqual(parse_five_position(lab), lab)

    def test_composite_takes_first_listed_position(self):
        self.assertEqual(parse_five_position("PG/SG"), "PG")
        self.assertEqual(parse_five_position("SG/PG"), "SG")
        self.assertEqual(parse_five_position("PF/C"), "PF")
        self.assertEqual(parse_five_position("C/PF"), "C")

    def test_broad_labels_are_unknown_never_guessed(self):
        # Resolving PG vs SG, or SF vs PF, would require inference.
        for lab in ("G", "F", "G/F", "F/C"):
            self.assertEqual(parse_five_position(lab), UNKNOWN, lab)

    def test_missing_and_unrecognised(self):
        for lab in (None, "", "nan", "ATH", "Guard"):
            self.assertEqual(parse_five_position(lab), UNKNOWN, repr(lab))

    def test_separator_and_case_variants(self):
        self.assertEqual(parse_five_position("pg-sg"), "PG")
        self.assertEqual(parse_five_position(" SF / PF "), "SF")

    def test_normalize_label(self):
        self.assertEqual(normalize_label(" pg/sg "), "PG/SG")
        self.assertEqual(normalize_label(None), "")

    def test_config_is_the_source_of_truth(self):
        m = load_map()
        self.assertIn("PG/SG", m)
        self.assertEqual(m["G"][0], UNKNOWN, "broad G must not resolve")
        self.assertEqual(m["G"][1], "G")


class TestLeakageDenyList(unittest.TestCase):
    def test_contaminated_population_metadata_is_denied(self):
        # ML-1 measured position_from_population as resolvable for 100% of
        # drafted vs 7.7% of undrafted prospects.
        for c in ("position_from_population", "class_from_population",
                  "match_method", "match_confidence"):
            self.assertIn(c, DENY_EXACT, f"{c} must be denied as a feature")

    def test_hoopr_position_remains_allowed(self):
        self.assertNotIn("hoopr_position", DENY_EXACT)


@unittest.skipUnless((ML0 / "features_2014_2025.parquet").exists(),
                     "ML-0 outputs not built")
class TestBuiltFeatureFiles(unittest.TestCase):
    def test_no_contaminated_column_survives_in_any_partition(self):
        for lab in ("2011_2013", "2014_2025", "2026"):
            cols = {c.lower()
                    for c in pd.read_parquet(ML0 / f"features_{lab}.parquet").columns}
            self.assertFalse(cols & DENY_EXACT,
                             f"{lab} carries prohibited columns: {cols & DENY_EXACT}")

    def test_hoopr_position_still_available_for_canonical_mapping(self):
        f = pd.read_parquet(ML0 / "features_2014_2025.parquet")
        self.assertIn("hoopr_position", f.columns)
        p3 = f.hoopr_position.map(to_position_3)
        self.assertGreater((p3 != UNKNOWN).mean(), 0.95,
                           "coarse position coverage should exceed 95%")


class TestHoldoutGuard(unittest.TestCase):
    def test_dev_only_rejects_2026(self):
        import ml1_eda as eda
        with self.assertRaises(AssertionError):
            eda.dev_only(pd.DataFrame({"draft_year": [2024, 2026]}))

    def test_dev_only_accepts_development_years(self):
        import ml1_eda as eda
        df = pd.DataFrame({"draft_year": [2014, 2025]})
        self.assertIs(eda.dev_only(df), df)

    def test_loading_the_2026_target_file_is_refused(self):
        import ml1_eda as eda
        with self.assertRaises(AssertionError):
            eda.load_target("2026")


if __name__ == "__main__":
    unittest.main(verbosity=2)
