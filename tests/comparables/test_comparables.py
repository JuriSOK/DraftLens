"""Tests for ML-8 NBA statistical comparables.

There is no ground truth, so these guard ENGINE BEHAVIOUR and the rules that
keep a descriptive comparison from turning into a prediction.

  ./.venv/bin/python -m unittest discover -s tests -t .
"""

import json
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from comparables import validation as cv
from comparables.explanations import explain_pair
from comparables.nba_features import PAIRS, TOTALS, build_metrics, parse_pair
from comparables.reference import (MIN_GAMES, MIN_MINUTES,
                                             POSITION_3, REFERENCE_SEASONS,
                                             eligible_seasons,
                                             latest_season_pool,
                                             recent_multi_season_pool)
from comparables.similarity import (MIN_SHARED_COVERAGE,
                                              N_COMPARABLES, UNAVAILABLE,
                                              find_comparables,
                                              pairwise_distances, prepare_pool,
                                              similarity_scores,
                                              within_pool_percentile)
from comparables.space import (COMMON_METRICS, DIMENSION_NAMES,
                                         DIMENSIONS, league_percentiles,
                                         to_dimensions)

ROOT = Path(__file__).resolve().parents[2]
CONFIG = json.loads(
    (ROOT / "config" / "comparables.json").read_text())


def pool_frame(n=10, seed=0):
    """A synthetic NBA pool with one row per unique player."""
    rng = np.random.default_rng(seed)
    d = {m: rng.uniform(0, 100, n) for m in COMMON_METRICS}
    d.update({"athlete_id": np.arange(1, n + 1),
              "athlete_display_name": [f"Player {i}" for i in range(1, n + 1)],
              "position_3": ["G"] * n,
              "reference_seasons": [[2023, 2024, 2025]] * n,
              "minutes": np.full(n, 1500.0), "season": np.full(n, 2025)})
    return pd.DataFrame(d)


def dims_frame(rows):
    return pd.DataFrame(rows, columns=DIMENSION_NAMES)


class TestNbaSourceParsing(unittest.TestCase):
    def test_made_attempted_pairs_parse(self):
        made, att = parse_pair(pd.Series(["247-538", "2-16", "0-0", "1.2-4.6"]))
        np.testing.assert_allclose(made.to_numpy(), [247, 2, 0, 1.2])
        np.testing.assert_allclose(att.to_numpy(), [538, 16, 0, 4.6])

    def test_unparseable_pair_is_nan_not_zero(self):
        made, att = parse_pair(pd.Series(["--", ""]))
        self.assertTrue(made.isna().all())
        self.assertTrue(att.isna().all())

    def test_all_three_shooting_pairs_are_mapped(self):
        self.assertEqual(len(PAIRS), 3)
        for made, att in PAIRS.values():
            self.assertTrue(att.endswith("attempted"))

    def test_metrics_use_the_shared_formulas(self):
        """efg/ts must come from features, not a second copy."""
        src = (ROOT / "src" / "comparables"
               / "nba_features.py").read_text()
        self.assertIn("from features.basketball import", src)
        self.assertIn("from features.basketball import", src)

    def test_build_metrics_matches_hand_computation(self):
        df = pd.DataFrame({
            "points": [1000.0], "field_goals_made": [400.0],
            "field_goals_attempted": [800.0], "three_points_made": [100.0],
            "three_points_attempted": [300.0], "free_throws_made": [100.0],
            "free_throws_attempted": [120.0], "assists": [200.0],
            "turnovers": [100.0], "offensive_rebounds": [50.0],
            "defensive_rebounds": [150.0], "steals": [60.0], "blocks": [40.0],
            "minutes": [2000.0]})
        f = build_metrics(df)
        self.assertAlmostEqual(f.three_point_pct.iloc[0], 100 / 300)
        self.assertAlmostEqual(f.ft_pct.iloc[0], 100 / 120)
        self.assertAlmostEqual(f.efg_pct.iloc[0], (400 + 0.5 * 100) / 800)
        self.assertAlmostEqual(f.three_point_attempt_rate.iloc[0], 300 / 800)
        self.assertAlmostEqual(f.free_throw_rate.iloc[0], 120 / 800)
        self.assertAlmostEqual(f.assists_per_40.iloc[0], 40 * 200 / 2000)
        self.assertAlmostEqual(f.points_per_40.iloc[0], 40 * 1000 / 2000)

    def test_zero_attempts_give_null_not_zero(self):
        df = pd.DataFrame({
            "points": [0.0], "field_goals_made": [0.0],
            "field_goals_attempted": [0.0], "three_points_made": [0.0],
            "three_points_attempted": [0.0], "free_throws_made": [0.0],
            "free_throws_attempted": [0.0], "assists": [0.0],
            "turnovers": [0.0], "offensive_rebounds": [0.0],
            "defensive_rebounds": [0.0], "steals": [0.0], "blocks": [0.0],
            "minutes": [0.0]})
        f = build_metrics(df)
        self.assertTrue(np.isnan(f.three_point_pct.iloc[0]))
        self.assertTrue(np.isnan(f.points_per_40.iloc[0]))


class TestReferencePool(unittest.TestCase):
    def test_position_mapping_is_deterministic_and_lexical(self):
        self.assertEqual(POSITION_3["PG"], "G")
        self.assertEqual(POSITION_3["SG"], "G")
        self.assertEqual(POSITION_3["SF"], "F")
        self.assertEqual(POSITION_3["PF"], "F")
        self.assertEqual(POSITION_3["C"], "C")
        self.assertEqual(set(POSITION_3.values()), {"G", "F", "C"})

    def test_reference_window_excludes_the_holdout(self):
        self.assertNotIn(2026, REFERENCE_SEASONS)
        self.assertEqual(REFERENCE_SEASONS, [2021, 2022, 2023, 2024, 2025])

    def test_eligibility_thresholds_are_declared(self):
        self.assertEqual(MIN_MINUTES, 750)
        self.assertEqual(MIN_GAMES, 30)
        self.assertEqual(CONFIG["nba_eligibility"]["min_minutes"], MIN_MINUTES)

    def test_latest_season_pool_is_one_row_per_player(self):
        e = pd.DataFrame({
            "athlete_id": [1, 1, 2], "season": [2023, 2024, 2024],
            "athlete_display_name": ["A", "A", "B"],
            "athlete_position_abbreviation": ["G", "G", "C"],
            "position_3": ["G", "G", "C"], "team_display_name": ["X", "X", "Y"],
            "minutes": [1000.0, 2000.0, 1500.0],
            "games_played": [40.0, 70.0, 60.0],
            "points_per_40": [20.0, 30.0, 15.0]})
        p = latest_season_pool(e, ["points_per_40"])
        self.assertEqual(len(p), 2)
        self.assertTrue(p.athlete_id.is_unique)
        self.assertAlmostEqual(
            float(p.loc[p.athlete_id == 1, "points_per_40"].iloc[0]), 30.0)

    def test_multi_season_pool_is_minutes_weighted(self):
        e = pd.DataFrame({
            "athlete_id": [1, 1], "season": [2024, 2025],
            "athlete_display_name": ["A", "A"],
            "athlete_position_abbreviation": ["G", "G"],
            "position_3": ["G", "G"], "team_display_name": ["X", "X"],
            "minutes": [1000.0, 3000.0], "games_played": [40.0, 70.0],
            "points_per_40": [10.0, 30.0]})
        p = recent_multi_season_pool(e, ["points_per_40"])
        self.assertEqual(len(p), 1)
        # (10*1000 + 30*3000) / 4000 = 25
        self.assertAlmostEqual(float(p.points_per_40.iloc[0]), 25.0)
        self.assertEqual(list(p.reference_seasons.iloc[0]), [2024, 2025])

    def test_multi_season_keeps_only_the_recent_window(self):
        e = pd.DataFrame({
            "athlete_id": [1] * 5, "season": [2021, 2022, 2023, 2024, 2025],
            "athlete_display_name": ["A"] * 5,
            "athlete_position_abbreviation": ["G"] * 5,
            "position_3": ["G"] * 5, "team_display_name": ["X"] * 5,
            "minutes": [1000.0] * 5, "games_played": [40.0] * 5,
            "points_per_40": [10.0, 10.0, 20.0, 20.0, 20.0]})
        p = recent_multi_season_pool(e, ["points_per_40"], n_seasons=3)
        self.assertEqual(list(p.reference_seasons.iloc[0]), [2023, 2024, 2025])
        self.assertAlmostEqual(float(p.points_per_40.iloc[0]), 20.0)

    def test_pool_uniqueness_is_asserted(self):
        cv.check_pool_unique(pool_frame(5))
        dup = pool_frame(3)
        dup.loc[2, "athlete_id"] = 1
        with self.assertRaises(AssertionError):
            cv.check_pool_unique(dup)

    def test_eligible_seasons_refuses_the_holdout(self):
        with self.assertRaises(AssertionError):
            eligible_seasons(seasons=[2025, 2026])


class TestCommonSpace(unittest.TestCase):
    def test_six_dimensions_with_declared_kinds(self):
        self.assertEqual(len(DIMENSION_NAMES), 6)
        kinds = {d["kind"] for d in DIMENSIONS.values()}
        self.assertTrue(kinds <= {"QUALITY", "ROLE", "STYLE"})
        cv.check_dimensions_declared()

    def test_space_is_not_all_higher_is_better(self):
        """If every axis were quality, similarity would collapse into a
        goodness ranking."""
        kinds = [d["kind"] for d in DIMENSIONS.values()]
        self.assertIn("STYLE", kinds)
        self.assertIn("ROLE", kinds)
        self.assertEqual(kinds.count("QUALITY"), 1)

    def test_no_metric_is_shared_between_dimensions(self):
        seen = {}
        for name, spec in DIMENSIONS.items():
            for m in spec["metrics"]:
                self.assertNotIn(m, seen, f"{m} in both {seen.get(m)} and {name}")
                seen[m] = name

    def test_percentiles_are_league_relative(self):
        ref = pd.DataFrame({"points_per_40": np.arange(0, 100, dtype=float)})
        df = pd.DataFrame({"points_per_40": [0.0, 50.0, 99.0]})
        p = league_percentiles(df, ref, metrics=["points_per_40"])
        self.assertLess(p.points_per_40.iloc[0], 5)
        self.assertGreater(p.points_per_40.iloc[2], 95)
        self.assertTrue(0 <= p.points_per_40.iloc[1] <= 100)

    def test_identical_relative_position_maps_to_the_same_percentile(self):
        """The core cross-league claim: different raw scales, same percentile."""
        ncaa_ref = pd.DataFrame({"points_per_40": np.arange(0, 100.0)})
        nba_ref = pd.DataFrame({"points_per_40": np.arange(0, 100.0) * 0.5})
        a = league_percentiles(pd.DataFrame({"points_per_40": [80.0]}),
                               ncaa_ref, metrics=["points_per_40"])
        b = league_percentiles(pd.DataFrame({"points_per_40": [40.0]}),
                               nba_ref, metrics=["points_per_40"])
        self.assertAlmostEqual(float(a.points_per_40.iloc[0]),
                               float(b.points_per_40.iloc[0]), places=6)

    def test_missing_metric_gives_nan_not_zero(self):
        ref = pd.DataFrame({"points_per_40": np.arange(0, 100.0)})
        p = league_percentiles(pd.DataFrame({"points_per_40": [np.nan]}), ref,
                               metrics=["points_per_40"])
        self.assertTrue(np.isnan(p.points_per_40.iloc[0]))

    def test_inverted_metric_flips_the_dimension(self):
        hi_ft = pd.DataFrame({"three_point_attempt_rate": [50.0],
                              "free_throw_rate": [90.0]})
        lo_ft = pd.DataFrame({"three_point_attempt_rate": [50.0],
                              "free_throw_rate": [10.0]})
        a = to_dimensions(hi_ft).PERIMETER_ORIENTATION.iloc[0]
        b = to_dimensions(lo_ft).PERIMETER_ORIENTATION.iloc[0]
        self.assertLess(a, b, "high free-throw rate must read as interior")

    def test_equal_weight_per_dimension_not_per_metric(self):
        """Shooting has 3 metrics and creation 1; neither may outvote by count."""
        pct = pd.DataFrame({m: [60.0] for m in COMMON_METRICS})
        d = to_dimensions(pct)
        self.assertEqual(len(d.columns), 6)
        self.assertAlmostEqual(d.SHOOTING_EFFICIENCY.iloc[0], 60.0)
        self.assertAlmostEqual(d.CREATION.iloc[0], 60.0)

    def test_dimension_is_nan_when_no_metric_available(self):
        pct = pd.DataFrame({m: [np.nan] for m in COMMON_METRICS})
        d = to_dimensions(pct)
        self.assertTrue(d.isna().all().all())


class TestDistances(unittest.TestCase):
    def test_identical_profiles_have_zero_distance(self):
        v = np.full(6, 50.0)
        d, n = pairwise_distances(v, v[None, :])
        self.assertAlmostEqual(float(d[0]), 0.0)
        self.assertEqual(int(n[0]), 6)

    def test_euclidean_increases_with_divergence(self):
        p = np.full(6, 50.0)
        M = np.vstack([np.full(6, 55.0), np.full(6, 80.0)])
        d, _ = pairwise_distances(p, M)
        self.assertLess(d[0], d[1])

    def test_distance_is_coverage_normalised(self):
        """A prospect missing dimensions must not be mechanically closer."""
        full = np.full(6, 50.0)
        part = np.array([50.0, 50.0, 50.0, np.nan, np.nan, np.nan])
        M = np.vstack([np.full(6, 60.0)])
        d_full, n_full = pairwise_distances(full, M)
        d_part, n_part = pairwise_distances(part, M)
        self.assertEqual(int(n_full[0]), 6)
        self.assertEqual(int(n_part[0]), 3)
        self.assertAlmostEqual(float(d_full[0]), float(d_part[0]), places=6)

    def test_all_three_metrics_are_available(self):
        p = np.array([20.0, 40.0, 60.0, 80.0, 30.0, 70.0])
        M = np.vstack([np.array([25.0, 45.0, 55.0, 75.0, 35.0, 65.0])])
        for m in ("EUCLIDEAN", "COSINE", "MANHATTAN"):
            d, _ = pairwise_distances(p, M, m)
            self.assertTrue(np.isfinite(d[0]), m)

    def test_cosine_is_undefined_for_an_exactly_average_profile(self):
        """A real property of the CENTRED cosine, and part of why it was not
        selected: a prospect at exactly the 50th percentile on every dimension
        has a zero-length centred vector, so the angle does not exist.
        Euclidean handles that prospect fine."""
        p = np.full(6, 50.0)
        M = np.vstack([np.full(6, 70.0)])
        d_cos, _ = pairwise_distances(p, M, "COSINE")
        d_euc, _ = pairwise_distances(p, M, "EUCLIDEAN")
        self.assertTrue(np.isnan(d_cos[0]))
        self.assertTrue(np.isfinite(d_euc[0]))

    def test_cosine_is_centred_before_use(self):
        """Uncentred cosine on all-positive percentiles calls everything
        similar; centring on 50 makes the angle meaningful."""
        src = (ROOT / "src" / "comparables"
               / "similarity.py").read_text()
        self.assertIn("- 50.0", src)

    def test_unknown_metric_is_rejected(self):
        with self.assertRaises(ValueError):
            pairwise_distances(np.full(6, 50.0), np.full((1, 6), 50.0), "NOPE")


class TestSimilarityScore(unittest.TestCase):
    def test_score_is_within_0_100(self):
        ref = np.linspace(0, 50, 1000)
        s = similarity_scores(np.array([0.0, 25.0, 50.0, 99.0]), ref)
        self.assertTrue(np.all((s >= 0) & (s <= 100)))

    def test_closer_pairings_score_higher(self):
        ref = np.linspace(0, 50, 1000)
        s = similarity_scores(np.array([5.0, 25.0, 45.0]), ref)
        self.assertTrue(np.all(np.diff(s) < 0))

    def test_within_pool_variant_is_degenerate_for_the_top3(self):
        """Documented reason it was rejected: identical for every prospect."""
        a = within_pool_percentile(np.array([1.0, 2.0, 3.0] + [50.0] * 539))
        b = within_pool_percentile(np.array([10.0, 20.0, 30.0] + [50.0] * 539))
        top_a = np.sort(a)[::-1][:3]
        top_b = np.sort(b)[::-1][:3]
        np.testing.assert_allclose(top_a, top_b)

    def test_score_is_not_a_linear_rescale_of_distance(self):
        """Scan the CODE, not the docstrings — they legitimately name the
        arbitrary rescale as the thing being avoided."""
        import ast
        import inspect
        from comparables import similarity as sim
        tree = ast.parse(inspect.getsource(sim))
        for node in ast.walk(tree):
            if isinstance(node, ast.Expr) and isinstance(node.value,
                                                         ast.Constant):
                node.value = ast.Constant(value="")
        code = ast.unparse(tree)
        self.assertNotIn("100 - 10 *", code)

    def test_empty_reference_gives_nan(self):
        s = similarity_scores(np.array([1.0]), np.array([]))
        self.assertTrue(np.isnan(s[0]))


class TestExactlyThree(unittest.TestCase):
    def setUp(self):
        self.pool = prepare_pool(pool_frame(20, seed=1))
        rng = np.random.default_rng(2)
        self.dims = dims_frame(rng.uniform(0, 100, (20, 6)))

    def test_returns_exactly_three_unique_players(self):
        p = pd.Series(np.full(6, 50.0), index=DIMENSION_NAMES)
        r = find_comparables(p, self.pool, self.dims)
        self.assertEqual(r["status"], "OK")
        self.assertEqual(len(r["comparables"]), N_COMPARABLES)
        ids = [c["nba_player_id"] for c in r["comparables"]]
        self.assertEqual(len(set(ids)), N_COMPARABLES)
        cv.check_result(r)

    def test_ordered_closest_first(self):
        p = pd.Series(np.full(6, 50.0), index=DIMENSION_NAMES)
        r = find_comparables(p, self.pool, self.dims)
        d = [c["raw_distance"] for c in r["comparables"]]
        self.assertEqual(d, sorted(d))

    def test_ranks_are_1_2_3(self):
        p = pd.Series(np.full(6, 50.0), index=DIMENSION_NAMES)
        r = find_comparables(p, self.pool, self.dims)
        self.assertEqual([c["rank"] for c in r["comparables"]], [1, 2, 3])

    def test_ties_break_deterministically_on_athlete_id(self):
        pool = prepare_pool(pool_frame(5, seed=3))
        dims = dims_frame(np.full((5, 6), 50.0))     # every distance identical
        p = pd.Series(np.full(6, 50.0), index=DIMENSION_NAMES)
        a = find_comparables(p, pool, dims)
        b = find_comparables(p, pool, dims)
        ids = [c["nba_player_id"] for c in a["comparables"]]
        self.assertEqual(ids, [c["nba_player_id"] for c in b["comparables"]])
        self.assertEqual(ids, sorted(ids))

    def test_too_small_a_pool_returns_unavailable(self):
        pool = prepare_pool(pool_frame(2, seed=4))
        dims = dims_frame(np.full((2, 6), 50.0))
        p = pd.Series(np.full(6, 50.0), index=DIMENSION_NAMES)
        r = find_comparables(p, pool, dims)
        self.assertEqual(r["status"], UNAVAILABLE)
        self.assertEqual(r["comparables"], [])

    def test_guards_are_never_relaxed_to_force_three_names(self):
        pool = prepare_pool(pool_frame(2, seed=5))
        dims = dims_frame(np.full((2, 6), 50.0))
        p = pd.Series(np.full(6, 50.0), index=DIMENSION_NAMES)
        cv.check_result(find_comparables(p, pool, dims))


class TestCoverageGuard(unittest.TestCase):
    def setUp(self):
        self.pool = prepare_pool(pool_frame(20, seed=6))
        rng = np.random.default_rng(7)
        self.dims = dims_frame(rng.uniform(0, 100, (20, 6)))

    def test_min_shared_coverage_is_declared(self):
        self.assertEqual(MIN_SHARED_COVERAGE, 0.75)
        self.assertEqual(CONFIG["similarity"]["min_shared_coverage"],
                         MIN_SHARED_COVERAGE)

    def test_below_minimum_coverage_returns_unavailable(self):
        p = pd.Series([50.0, 50.0, np.nan, np.nan, np.nan, np.nan],
                      index=DIMENSION_NAMES)
        r = find_comparables(p, self.pool, self.dims)
        self.assertEqual(r["status"], UNAVAILABLE)
        self.assertIn("below", r["reason"])

    def test_at_minimum_coverage_still_scores(self):
        p = pd.Series([50.0] * 5 + [np.nan], index=DIMENSION_NAMES)
        r = find_comparables(p, self.pool, self.dims)
        self.assertEqual(r["status"], "OK")

    def test_missing_dimension_is_dropped_not_filled(self):
        src = (ROOT / "src" / "comparables"
               / "similarity.py").read_text()
        self.assertNotIn("fillna(50", src)
        self.assertNotIn("fillna(0", src)


class TestSelfMatchGuard(unittest.TestCase):
    def test_prospect_never_matches_himself(self):
        pool = pool_frame(10, seed=8)
        pool.loc[0, "athlete_display_name"] = "Trae Young"
        pool = prepare_pool(pool)
        dims = dims_frame(np.full((10, 6), 50.0))
        dims.iloc[0] = 50.0
        p = pd.Series(np.full(6, 50.0), index=DIMENSION_NAMES)
        r = find_comparables(p, pool, dims, prospect_name="Trae Young")
        names = [c["nba_player_name"] for c in r["comparables"]]
        self.assertNotIn("Trae Young", names)
        cv.check_no_self_match(r, "Trae Young")

    def test_self_match_uses_normalised_name(self):
        pool = pool_frame(10, seed=9)
        pool.loc[0, "athlete_display_name"] = "R.J. Barrett"
        pool = prepare_pool(pool)
        dims = dims_frame(np.full((10, 6), 50.0))
        p = pd.Series(np.full(6, 50.0), index=DIMENSION_NAMES)
        r = find_comparables(p, pool, dims, prospect_name="RJ Barrett")
        self.assertNotIn("R.J. Barrett",
                         [c["nba_player_name"] for c in r["comparables"]])

    def test_guard_can_be_disabled_for_production_use(self):
        pool = prepare_pool(pool_frame(10, seed=10))
        dims = dims_frame(np.full((10, 6), 50.0))
        p = pd.Series(np.full(6, 50.0), index=DIMENSION_NAMES)
        r = find_comparables(p, pool, dims, prospect_name="Player 1",
                             exclude_self=False)
        self.assertEqual(r["status"], "OK")

    def test_validator_detects_a_self_match(self):
        bad = {"status": "OK", "comparables": [
            {"nba_player_name": "Trae Young", "nba_player_id": 1,
             "similarity_score": 99, "raw_distance": 0.0,
             "comparison_coverage": 1.0}]}
        with self.assertRaises(AssertionError):
            cv.check_no_self_match(bad, "Trae Young")


class TestExplanations(unittest.TestCase):
    def test_deltas_cover_every_shared_dimension(self):
        a = pd.Series(np.full(6, 60.0), index=DIMENSION_NAMES)
        b = pd.Series(np.full(6, 50.0), index=DIMENSION_NAMES)
        e = explain_pair(a, b)
        self.assertEqual(len(e["dimension_delta"]), 6)
        for d in e["dimension_delta"]:
            self.assertAlmostEqual(d["delta"], 10.0)

    def test_closest_dimensions_are_the_smallest_gaps(self):
        a = pd.Series([50, 50, 50, 50, 50, 50.0], index=DIMENSION_NAMES)
        b = pd.Series([51, 90, 52, 95, 53, 99.0], index=DIMENSION_NAMES)
        e = explain_pair(a, b)
        close = [d["dimension"] for d in e["closest_dimensions"]]
        self.assertIn(DIMENSION_NAMES[0], close)
        self.assertNotIn(DIMENSION_NAMES[5], close)

    def test_largest_differences_are_the_biggest_gaps(self):
        a = pd.Series([50.0] * 6, index=DIMENSION_NAMES)
        b = pd.Series([51, 52, 53, 54, 55, 99.0], index=DIMENSION_NAMES)
        e = explain_pair(a, b)
        self.assertEqual(e["largest_differences"][0]["dimension"],
                         DIMENSION_NAMES[5])

    def test_unavailable_dimension_is_not_a_difference(self):
        a = pd.Series([50.0] * 5 + [np.nan], index=DIMENSION_NAMES)
        b = pd.Series([50.0] * 6, index=DIMENSION_NAMES)
        e = explain_pair(a, b)
        self.assertEqual(len(e["unavailable_dimensions"]), 1)
        self.assertNotIn(DIMENSION_NAMES[5],
                         [d["dimension"] for d in e["largest_differences"]])

    def test_explanations_are_deterministic(self):
        a = pd.Series(np.linspace(10, 90, 6), index=DIMENSION_NAMES)
        b = pd.Series(np.linspace(20, 80, 6), index=DIMENSION_NAMES)
        self.assertEqual(explain_pair(a, b), explain_pair(a, b))


class TestNoProhibitedInputs(unittest.TestCase):
    def test_no_outcome_or_board_signal_in_the_space(self):
        cv.check_no_prohibited_inputs()
        for banned in ("drafted", "pick", "stage_a_probability",
                       "stage_b_signal", "overall_score", "fit_score"):
            self.assertNotIn(banned, COMMON_METRICS)

    def test_no_nba_career_success_input(self):
        for banned in ("all_star", "mvp", "awards", "bpm", "raptor", "vorp"):
            self.assertNotIn(banned, COMMON_METRICS)

    def test_no_raw_per_game_production(self):
        """19 NCAA PPG and 19 NBA PPG are not the same event."""
        cv.check_no_raw_per_game_inputs()
        for banned in ("points_per_game", "rebounds_per_game",
                       "assists_per_game"):
            self.assertNotIn(banned, COMMON_METRICS)

    def test_no_age_or_contaminated_position(self):
        for banned in ("age", "date_of_birth", "position_from_population"):
            self.assertNotIn(banned, COMMON_METRICS)

    def test_no_rejected_jump_shot_metric(self):
        for m in COMMON_METRICS:
            self.assertNotIn("jump_shot", m)

    def test_no_fabricated_athleticism_or_size(self):
        for banned in ("athleticism", "vertical", "wingspan", "height",
                       "weight"):
            self.assertNotIn(banned, COMMON_METRICS)

    def test_comparables_never_import_a_scoring_system(self):
        """The board, the stages and Team Need SCORES must be unreachable.

        `team_need.reference._season_frame` is a deliberate exception: it is the
        NCAA season-population builder, shared so the peer group is produced by
        the same code on both sides. It carries no Team Need score.
        """
        for mod in ("nba_features", "reference", "space", "similarity",
                    "explanations", "validation"):
            src = (ROOT / "src" / "comparables"
                   / f"{mod}.py").read_text()
            self.assertNotIn("from board.scoring", src)
            self.assertNotIn("from board.probability", src)
            self.assertNotIn("from board.order", src)
            for banned in ("team_need.dimensions", "team_need.profiles",
                           "team_need.scoring"):
                self.assertNotIn(banned, src)

    def test_the_only_team_need_import_is_the_shared_population_builder(self):
        src = (ROOT / "src" / "comparables"
               / "reference.py").read_text()
        for line in src.splitlines():
            if "team_need" in line:
                self.assertIn("_season_frame", line)


class TestSemanticsAndHoldout(unittest.TestCase):
    def test_config_forbids_career_prediction_language(self):
        banned = CONFIG["semantics"]["prohibited_language"]
        for phrase in ("ceiling", "floor", "will become", "expected career"):
            self.assertTrue(any(phrase in b for b in banned), phrase)

    def test_config_declares_there_is_no_target(self):
        self.assertIn("no ground-truth", CONFIG["semantics"]["no_target"])

    def test_no_source_file_scores_the_holdout(self):
        for mod in ("nba_features", "reference", "space", "similarity",
                    "explanations", "validation"):
            src = (ROOT / "src" / "comparables"
                   / f"{mod}.py").read_text()
            self.assertNotIn("targets_2026", src)
            self.assertNotIn("features_2026", src)

    def test_cli_refuses_the_holdout_year(self):
        src = (ROOT / "scripts" / "demo.py").read_text()
        self.assertIn("HOLDOUT_YEAR = 2026", src)
        self.assertIn("REFUSED", src)

    def test_reference_builder_refuses_the_holdout(self):
        src = (ROOT / "scripts" / "build.py").read_text()
        self.assertIn("REFUSED", src)

    def test_config_excludes_2026_from_the_nba_window(self):
        self.assertEqual(CONFIG["reference_window"]["excludes"], 2026)
        self.assertNotIn(2026, CONFIG["reference_window"]["nba_seasons"])


class TestValidationGuards(unittest.TestCase):
    def test_all_static_guards_pass(self):
        self.assertTrue(all(cv.run_all().values()))

    def test_duplicate_players_are_rejected(self):
        bad = {"status": "OK", "comparables": [
            {"nba_player_id": 1, "nba_player_name": "A", "similarity_score": 90,
             "raw_distance": 1.0, "comparison_coverage": 1.0},
            {"nba_player_id": 1, "nba_player_name": "A", "similarity_score": 89,
             "raw_distance": 2.0, "comparison_coverage": 1.0},
            {"nba_player_id": 2, "nba_player_name": "B", "similarity_score": 88,
             "raw_distance": 3.0, "comparison_coverage": 1.0}]}
        with self.assertRaises(AssertionError):
            cv.check_result(bad)

    def test_out_of_range_score_is_rejected(self):
        bad = {"status": "OK", "comparables": [
            {"nba_player_id": i, "nba_player_name": str(i),
             "similarity_score": 150, "raw_distance": float(i),
             "comparison_coverage": 1.0} for i in range(3)]}
        with self.assertRaises(AssertionError):
            cv.check_result(bad)

    def test_unordered_comparables_are_rejected(self):
        bad = {"status": "OK", "comparables": [
            {"nba_player_id": i, "nba_player_name": str(i),
             "similarity_score": 90, "raw_distance": d,
             "comparison_coverage": 1.0}
            for i, d in enumerate([3.0, 1.0, 2.0])]}
        with self.assertRaises(AssertionError):
            cv.check_result(bad)

    def test_unavailable_result_must_not_carry_names(self):
        bad = {"status": UNAVAILABLE, "comparables": [
            {"nba_player_id": 1, "nba_player_name": "A"}]}
        with self.assertRaises(AssertionError):
            cv.check_result(bad)

    def test_below_coverage_comparable_is_rejected(self):
        bad = {"status": "OK", "comparables": [
            {"nba_player_id": i, "nba_player_name": str(i),
             "similarity_score": 90, "raw_distance": float(i),
             "comparison_coverage": 0.3} for i in range(3)]}
        with self.assertRaises(AssertionError):
            cv.check_result(bad)


if __name__ == "__main__":
    unittest.main()
