"""Tests for DraftLens Dataset Format v1 (`dataset_format.py`).

The format is a contract with a user's spreadsheet. These tests guard the
parts of it that would be silently wrong if they drifted: that the required
fields really are the ones the frozen pipeline needs, that units are stated
and unambiguous, that outcome columns are refused, and that the mapping into
the engineered layer is a rename and nothing more.

  ./.venv/bin/python -m unittest discover -s tests -t .
"""

import unittest

import numpy as np
import pandas as pd

import dataset_format as fmt


class TestSchemaShape(unittest.TestCase):
    def test_every_field_declares_type_unit_and_description(self):
        for field in fmt.METADATA_FIELDS + fmt.PROSPECT_FIELDS:
            self.assertTrue(field["name"])
            self.assertIn(field["type"],
                          {"string", "number", "integer", "enum"})
            self.assertTrue(field["unit"], field["name"])
            self.assertTrue(field["description"], field["name"])

    def test_field_names_are_unique(self):
        names = [f["name"] for f in fmt.PROSPECT_FIELDS]
        self.assertEqual(len(names), len(set(names)))

    def test_no_rate_column_is_an_input(self):
        """COUNTS, NEVER RATES. If a percentage were ever accepted as input,
        the 0.412-versus-41.2 ambiguity would come straight back."""
        for field in fmt.PROSPECT_FIELDS:
            self.assertNotIn(field["name"], fmt.DERIVED_RATE_FIELDS)
            self.assertFalse(field["name"].endswith("_pct"), field["name"])
            self.assertFalse(field["name"].endswith("_per_game"), field["name"])

    def test_prohibited_fields_are_not_also_accepted_fields(self):
        accepted = {f["name"] for f in fmt.PROSPECT_FIELDS}
        self.assertEqual(accepted & set(fmt.PROHIBITED_FIELDS), set())

    def test_outcome_vocabulary_is_covered(self):
        for word in ("drafted", "pick", "actual_pick", "draft_team",
                     "actual_round"):
            self.assertIn(word, fmt.PROHIBITED_FIELDS)

    def test_counts_are_integers_with_a_floor_of_zero(self):
        for field in fmt.BOX_FIELDS:
            self.assertTrue(field["integer"], field["name"])
            self.assertEqual(field["min"], 0, field["name"])
            self.assertIsNotNone(field["max"], field["name"])

    def test_height_and_weight_state_their_units(self):
        by_name = {f["name"]: f for f in fmt.PROSPECT_FIELDS}
        self.assertEqual(by_name["height_inches"]["unit"], "inches")
        self.assertEqual(by_name["weight_lbs"]["unit"], "pounds")

    def test_minutes_are_documented_as_a_season_total(self):
        by_name = {f["name"]: f for f in fmt.PROSPECT_FIELDS}
        self.assertIn("TOTAL", by_name["minutes"]["description"])

    def test_position_vocabulary_is_the_leakage_safe_one(self):
        self.assertEqual(fmt.POSITIONS, ["G", "F", "C", "UNKNOWN"])

    def test_full_board_population_is_a_declared_population_type(self):
        self.assertIn(fmt.FULL_BOARD_POPULATION, fmt.POPULATION_TYPES)

    def test_limits_are_a_draft_class_not_a_warehouse(self):
        self.assertLessEqual(fmt.LIMITS["maxRows"], 10000)
        self.assertGreaterEqual(fmt.LIMITS["minRows"], 2)
        self.assertLessEqual(fmt.LIMITS["maxFileBytes"], 64 * 1024 * 1024)


class TestRequiredFieldsSupportTheFrozenPipeline(unittest.TestCase):
    """The required set must be enough to build the frozen model features
    that do not depend on an optional group."""

    def test_required_fields_cover_the_core_box_score(self):
        required = set(fmt.required_prospect_fields())
        for name in ("games_played", "minutes", "points",
                     "field_goals_made", "field_goals_attempted",
                     "three_points_made", "three_points_attempted",
                     "free_throws_made", "free_throws_attempted",
                     "offensive_rebounds", "defensive_rebounds",
                     "total_rebounds", "assists", "turnovers", "steals",
                     "blocks", "personal_fouls", "prospect_id", "name",
                     "position"):
            self.assertIn(name, required, name)

    def test_optional_groups_are_the_two_documented_ones(self):
        optional_groups = {f["group"] for f in fmt.PROSPECT_FIELDS
                           if not f["required"]}
        self.assertTrue({"team_context", "shot_profile"} <= optional_groups)

    def test_every_group_is_described(self):
        groups = {f["group"] for f in fmt.PROSPECT_FIELDS}
        self.assertEqual(groups - set(fmt.GROUPS), set())


class TestInternalMapping(unittest.TestCase):
    def test_mapping_is_a_rename_only(self):
        """Every mapped source name is a real import column, and every target
        is a primitive the frozen feature builder reads."""
        names = {f["name"] for f in fmt.PROSPECT_FIELDS}
        for source in fmt.TO_PRIMITIVE:
            self.assertIn(source, names, source)

    def test_frame_carries_every_primitive_build_features_reads(self):
        rows = [dict(fmt.EXAMPLE_ROW)]
        frame = fmt.to_internal_frame(rows, 2026)
        for column in fmt.REQUIRED_PRIMITIVES:
            self.assertIn(column, frame.columns, column)

    def test_absent_optional_columns_become_missing_not_zero(self):
        """A gap must reach the pipeline as NaN. Zero would be a measurement,
        and a fabricated one."""
        frame = fmt.to_internal_frame([dict(fmt.EXAMPLE_ROW)], 2026)
        for column in ("layup_attempts", "fg_attempts_shotfile",
                       "shot_records"):
            self.assertTrue(bool(pd.isna(frame[column].iloc[0])), column)

    def test_two_point_identities_are_derived(self):
        frame = fmt.to_internal_frame([dict(fmt.EXAMPLE_ROW)], 2026)
        row = fmt.EXAMPLE_ROW
        self.assertEqual(frame.two_points_made.iloc[0],
                         row["field_goals_made"] - row["three_points_made"])
        self.assertEqual(frame.two_points_attempted.iloc[0],
                         row["field_goals_attempted"]
                         - row["three_points_attempted"])

    def test_position_flows_through_the_frozen_mapping(self):
        """`build_features` derives position_3 from `hoopr_position`; an
        imported position that did not reach that column would silently make
        every player UNKNOWN."""
        from features.basketball import build_features

        rows = [dict(fmt.EXAMPLE_ROW, prospect_id="A", position="C")]
        frame = fmt.to_internal_frame(rows, 2026)
        self.assertEqual(build_features(frame).position_3.iloc[0], "C")

    def test_unknown_position_stays_unknown(self):
        from features.basketball import build_features

        rows = [dict(fmt.EXAMPLE_ROW, position="UNKNOWN")]
        frame = fmt.to_internal_frame(rows, 2026)
        self.assertEqual(build_features(frame).position_3.iloc[0], "UNKNOWN")


class TestFeatureConstruction(unittest.TestCase):
    """An imported row must reach the same engineered values the frozen
    formulas produce — this is what the browser then reproduces."""

    def setUp(self):
        from features.basketball import build_features
        self.features = build_features(
            fmt.to_internal_frame([dict(fmt.EXAMPLE_ROW)], 2026)).iloc[0]

    def test_rates_are_derived_from_counts(self):
        row = fmt.EXAMPLE_ROW
        self.assertAlmostEqual(
            self.features.three_point_pct,
            row["three_points_made"] / row["three_points_attempted"])
        self.assertAlmostEqual(
            self.features.points_per_40,
            40.0 * row["points"] / row["minutes"])

    def test_team_dependent_rates_are_missing_without_team_context(self):
        for metric in ("usage_pct", "ast_pct", "orb_pct", "stl_pct"):
            self.assertTrue(bool(np.isnan(self.features[metric])), metric)


class TestTemplateContent(unittest.TestCase):
    def test_metadata_rows_declare_every_required_metadata_field(self):
        keys = {row[0] for row in fmt.metadata_rows()}
        for field in fmt.METADATA_FIELDS:
            if field["required"]:
                self.assertIn(field["name"], keys, field["name"])

    def test_prospect_header_lists_every_column_in_schema_order(self):
        header = fmt.prospect_rows()[0]
        self.assertEqual(header, [f["name"] for f in fmt.PROSPECT_FIELDS])

    def test_example_row_respects_declared_ranges(self):
        by_name = {f["name"]: f for f in fmt.PROSPECT_FIELDS}
        for name, value in fmt.EXAMPLE_ROW.items():
            field = by_name[name]
            if field["type"] in ("string", "enum"):
                continue
            if field["min"] is not None:
                self.assertGreaterEqual(value, field["min"], name)
            if field["max"] is not None:
                self.assertLessEqual(value, field["max"], name)

    def test_example_row_is_internally_consistent(self):
        row = fmt.EXAMPLE_ROW
        self.assertLessEqual(row["field_goals_made"], row["field_goals_attempted"])
        self.assertLessEqual(row["three_points_made"], row["three_points_attempted"])
        self.assertLessEqual(row["free_throws_made"], row["free_throws_attempted"])
        self.assertLessEqual(row["three_points_attempted"],
                             row["field_goals_attempted"])
        self.assertEqual(row["offensive_rebounds"] + row["defensive_rebounds"],
                         row["total_rebounds"])
        self.assertLessEqual(row["games_started"], row["games_played"])


if __name__ == "__main__":
    unittest.main()
