"""Guards that the frozen `config/team_need.json` profile definitions still
match the exact structure the Methodology page's hardcoded archetype
explanations (app/src/pages/AboutPage.tsx) describe.

This does not read the frontend file (Python can't import TSX) — it pins the
CONFIG structure itself, so any change to a profile's combination method,
pillars, or eligibility rule fails this test as a signal that
AboutPage.tsx's ArchetypeBlock content needs a matching update.

  ./.venv/bin/python -m unittest discover -s tests -t .
"""

import unittest

from team_need.dimensions import CONFIG


class TestArchetypeStructureMatchesMethodologyPage(unittest.TestCase):
    def setUp(self):
        self.profiles = CONFIG["profiles"]

    def test_shooter_is_geometric_mean_of_efficiency_and_volume(self):
        p = self.profiles["SHOOTER"]
        self.assertEqual(p["combination"], "GEOMETRIC_MEAN")
        pillar_ids = {pl["id"] for pl in p["pillars"]}
        self.assertEqual(pillar_ids, {"efficiency", "volume"})
        self.assertIsNone(p["eligibility"])

    def test_slasher_is_the_rim_pressure_dimension_directly(self):
        p = self.profiles["SLASHER"]
        self.assertEqual(p["combination"], "DIMENSION")
        self.assertEqual(p["dimension"], "RIM_PRESSURE")

    def test_playmaker_is_the_playmaking_dimension_directly(self):
        p = self.profiles["PLAYMAKER"]
        self.assertEqual(p["combination"], "DIMENSION")
        self.assertEqual(p["dimension"], "PLAYMAKING")

    def test_three_and_d_is_geometric_mean_shooting_and_defense_gf_only(self):
        p = self.profiles["THREE_AND_D"]
        self.assertEqual(p["combination"], "GEOMETRIC_MEAN")
        dims = {pl["dimension"] for pl in p["pillars"] if pl["source"] == "DIMENSION"}
        self.assertEqual(dims, {"SHOOTING", "BOX_SCORE_DEFENSIVE_PRODUCTION"})
        self.assertEqual(set(p["eligibility"]["position_3_in"]), {"G", "F"})

    def test_rim_protector_is_geometric_mean_blocking_rebounding_size_fc_only(self):
        p = self.profiles["RIM_PROTECTOR"]
        self.assertEqual(p["combination"], "GEOMETRIC_MEAN")
        pillar_ids = {pl["id"] for pl in p["pillars"]}
        self.assertEqual(pillar_ids, {"shot_blocking", "rebounding", "size"})
        blocking = next(pl for pl in p["pillars"] if pl["id"] == "shot_blocking")
        self.assertEqual(blocking["reference_group"], "GLOBAL")
        self.assertEqual(set(p["eligibility"]["position_3_in"]), {"F", "C"})

    def test_stretch_big_is_geometric_mean_shooting_and_size_fc_only(self):
        p = self.profiles["STRETCH_BIG"]
        self.assertEqual(p["combination"], "GEOMETRIC_MEAN")
        dims = {pl["dimension"] for pl in p["pillars"] if pl["source"] == "DIMENSION"}
        self.assertEqual(dims, {"SHOOTING", "SIZE"})
        self.assertEqual(set(p["eligibility"]["position_3_in"]), {"F", "C"})

    def test_custom_mode_dimensions_match_methodology_page(self):
        custom = CONFIG["custom_mode"]
        self.assertEqual(set(custom["supported_dimensions"]),
                         {"SHOOTING", "PLAYMAKING",
                          "BOX_SCORE_DEFENSIVE_PRODUCTION", "REBOUNDING", "SIZE"})
        self.assertEqual(custom["optional_dimension"], "RIM_PRESSURE")
        self.assertEqual(custom["unavailable_dimensions"], ["ATHLETICISM"])
        self.assertIn("sum(w_i * d_i)", custom["formula"])

    def test_general_board_formula_matches_methodology_page(self):
        from paths import CONFIG as CONFIG_DIR
        import json
        board_cfg = json.loads((CONFIG_DIR / "board.json").read_text())
        formula = board_cfg["general_board_frozen"]["formula"]
        self.assertIn("draft_probability", formula)
        self.assertIn("draft_slot_utility", formula)
        self.assertIn("percentile_rank", formula)


if __name__ == "__main__":
    unittest.main()
