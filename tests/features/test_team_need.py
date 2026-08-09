"""Tests for ML-7 Team Need scoring.

Team Need has no ground-truth target, so these are guards on ENGINE BEHAVIOUR
and on the rules that keep it from quietly becoming a second draft model.

  ./.venv/bin/python -m unittest discover -s tests -t .
"""

import json
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from draftlens.team_need import validation as tnv
from draftlens.team_need.dimensions import (CONFIG, DIMENSIONS, apply_reliability,
                                            combine, component_metrics,
                                            compute_dimensions, data_coverage,
                                            orient, orientation, reference_spec)
from draftlens.team_need.explanations import explain, relevant_metrics
from draftlens.team_need.profiles import (ELIGIBLE, OUT_OF_POSITION, PROFILES,
                                          UNKNOWN_POSITION, eligibility,
                                          profile_names)
from draftlens.team_need.reference import (GLOBAL_GROUP, PercentileReference,
                                           REFERENCE_METRICS)
from draftlens.team_need.scoring import (MIN_SUPPORTED_WEIGHT,
                                         SUPPORTED_DIMENSIONS, UNAVAILABLE,
                                         UnsupportedNeed, custom_fit, fit_score,
                                         profile_fit, rank_fit,
                                         validate_weights)

ROOT = Path(__file__).resolve().parents[2]
ALL_DIMENSIONS = list(DIMENSIONS)


class FakeReference:
    """Deterministic stand-in: percentile = value, clipped to 0-100.

    Lets every formula be tested exactly, without depending on the generated
    NCAA reference being present.
    """

    def has(self, season, group, metric):
        return True

    def support(self, season, group, metric):
        return 1000

    def percentile(self, values, season, group, metric):
        v = pd.to_numeric(pd.Series(values), errors="coerce").to_numpy(
            dtype="float64")
        out = np.clip(v, 0.0, 100.0)
        out[~np.isfinite(v)] = np.nan
        return out


def frame(n=4, year=2020, position="G", **overrides):
    """Prospect frame where every metric already sits on a 0-100 scale."""
    base = {m: np.linspace(10, 90, n) for m in REFERENCE_METRICS}
    base.update({
        "draft_year": year, "position_3": position,
        "three_points_attempted": 100.0, "free_throws_attempted": 100.0,
        "shot_records": 300.0,
    })
    base.update(overrides)
    return pd.DataFrame(base, index=range(n))


class TestOrientation(unittest.TestCase):
    def test_every_component_declares_an_orientation(self):
        for name, d in DIMENSIONS.items():
            for c in d["components"]:
                self.assertIn(c["orientation"],
                              ("HIGHER_IS_BETTER", "LOWER_IS_BETTER"),
                              f"{name}.{c['metric']}")

    def test_turnover_rate_is_inverted(self):
        self.assertEqual(orientation("PLAYMAKING", "tov_pct"), "LOWER_IS_BETTER")
        pct = pd.DataFrame({"ast_pct": [50.0], "tov_pct": [90.0]})
        out = orient(pct, "PLAYMAKING")
        self.assertAlmostEqual(out.tov_pct.iloc[0], 10.0)
        self.assertAlmostEqual(out.ast_pct.iloc[0], 50.0)

    def test_high_turnover_rate_lowers_playmaking(self):
        good = frame(1, **{"ast_pct": [80.0], "tov_pct": [10.0]})
        bad = frame(1, **{"ast_pct": [80.0], "tov_pct": [90.0]})
        ref = FakeReference()
        g, _ = compute_dimensions(good, ref)
        b, _ = compute_dimensions(bad, ref)
        self.assertGreater(g.PLAYMAKING.iloc[0], b.PLAYMAKING.iloc[0])

    def test_all_dimensions_are_higher_is_better(self):
        ref = FakeReference()
        for name in ALL_DIMENSIONS:
            metrics = component_metrics(name)
            lo = frame(1, **{m: [10.0] for m in metrics})
            hi = frame(1, **{m: [90.0] for m in metrics})
            for m in metrics:
                if orientation(name, m) == "LOWER_IS_BETTER":
                    lo[m], hi[m] = hi[m].copy(), lo[m].copy()
            a, _ = compute_dimensions(lo, ref)
            b, _ = compute_dimensions(hi, ref)
            self.assertGreater(b[name].iloc[0], a[name].iloc[0], name)


class TestDimensionFormulas(unittest.TestCase):
    def setUp(self):
        self.ref = FakeReference()

    def test_shooting_is_the_mean_of_its_components(self):
        df = frame(1, three_point_pct=[80.0], three_point_attempt_rate=[60.0],
                   ft_pct=[70.0], efg_pct=[90.0])
        s, _ = compute_dimensions(df, self.ref)
        self.assertAlmostEqual(s.SHOOTING.iloc[0], (80 + 60 + 70 + 90) / 4)

    def test_playmaking_uses_ast_and_inverted_tov(self):
        df = frame(1, ast_pct=[80.0], tov_pct=[30.0])
        s, _ = compute_dimensions(df, self.ref)
        self.assertAlmostEqual(s.PLAYMAKING.iloc[0], (80 + 70) / 2)

    def test_defensive_production_uses_steals_and_blocks(self):
        df = frame(1, stl_pct=[60.0], blk_pct=[80.0])
        s, _ = compute_dimensions(df, self.ref)
        self.assertAlmostEqual(s.BOX_SCORE_DEFENSIVE_PRODUCTION.iloc[0], 70.0)

    def test_rebounding_uses_orb_and_drb(self):
        df = frame(1, orb_pct=[40.0], drb_pct=[80.0])
        s, _ = compute_dimensions(df, self.ref)
        self.assertAlmostEqual(s.REBOUNDING.iloc[0], 60.0)

    def test_size_uses_height_and_weight(self):
        df = frame(1, height=[90.0], weight=[70.0])
        s, _ = compute_dimensions(df, self.ref)
        self.assertAlmostEqual(s.SIZE.iloc[0], 80.0)

    def test_rim_pressure_uses_four_components(self):
        df = frame(1, rim_attempt_share=[80.0], free_throw_rate=[60.0],
                   rim_make_pct=[70.0], unassisted_made_fg_share=[50.0])
        s, _ = compute_dimensions(df, self.ref)
        self.assertAlmostEqual(s.RIM_PRESSURE.iloc[0], 65.0)

    def test_no_metric_is_shared_between_dimensions(self):
        """Cross-dimension sharing would double-count a statistic whenever a
        user weights both dimensions."""
        seen = {}
        for name in ALL_DIMENSIONS:
            for m in component_metrics(name):
                self.assertNotIn(m, seen,
                                 f"{m} appears in both {seen.get(m)} and {name}")
                seen[m] = name

    def test_reference_group_is_consistent_per_metric(self):
        reference_spec()   # raises on conflict

    def test_rejected_metrics_are_absent(self):
        used = set()
        for name in ALL_DIMENSIONS:
            used |= set(component_metrics(name))
        for banned in ("ts_pct", "trb_pct", "assist_to_turnover_ratio",
                       "layup_attempt_share", "dunk_make_pct", "tip_make_pct"):
            self.assertNotIn(banned, used,
                             f"{banned} was excluded for a documented reason")
        for m in used:
            self.assertNotIn("jump_shot", m)


class TestMissingness(unittest.TestCase):
    def setUp(self):
        self.ref = FakeReference()

    def test_missing_component_renormalises_rather_than_scoring_zero(self):
        full = frame(1, three_point_pct=[80.0], three_point_attempt_rate=[80.0],
                     ft_pct=[80.0], efg_pct=[80.0])
        part = full.copy()
        part["efg_pct"] = [np.nan]
        a, _ = compute_dimensions(full, self.ref)
        b, _ = compute_dimensions(part, self.ref)
        self.assertAlmostEqual(a.SHOOTING.iloc[0], 80.0)
        self.assertAlmostEqual(b.SHOOTING.iloc[0], 80.0)   # not 60.0

    def test_missing_is_never_treated_as_zero(self):
        df = frame(1, three_point_pct=[np.nan], three_point_attempt_rate=[90.0],
                   ft_pct=[90.0], efg_pct=[90.0])
        s, _ = compute_dimensions(df, self.ref)
        self.assertAlmostEqual(s.SHOOTING.iloc[0], 90.0)

    def test_dimension_unavailable_below_minimum_coverage(self):
        df = frame(1, ast_pct=[np.nan], tov_pct=[np.nan])
        s, cov = compute_dimensions(df, self.ref)
        self.assertTrue(np.isnan(s.PLAYMAKING.iloc[0]))
        self.assertEqual(cov.PLAYMAKING.iloc[0], 0.0)

    def test_prospect_is_never_dropped_for_a_missing_metric(self):
        df = frame(3)
        df.loc[1, "efg_pct"] = np.nan
        s, _ = compute_dimensions(df, self.ref)
        self.assertEqual(len(s), 3)

    def test_reliability_minimum_blanks_a_thin_denominator(self):
        df = frame(2, three_points_attempted=[4.0, 200.0])
        pct = pd.DataFrame({"three_point_pct": [95.0, 95.0]})
        out = apply_reliability(df, pct)
        self.assertTrue(np.isnan(out.three_point_pct.iloc[0]))
        self.assertAlmostEqual(out.three_point_pct.iloc[1], 95.0)

    def test_data_coverage_is_separate_from_score(self):
        """Coverage must never multiply, reward or penalise the score."""
        full = frame(1)
        part = full.copy()
        part["efg_pct"] = [np.nan]
        sa, ca = compute_dimensions(full, self.ref)
        sb, cb = compute_dimensions(part, self.ref)
        self.assertLess(data_coverage(cb).iloc[0], data_coverage(ca).iloc[0])
        r = profile_fit(part, "PLAYMAKER", self.ref)
        self.assertIn("data_coverage", r.columns)
        # PLAYMAKING is untouched by the missing shooting metric
        self.assertTrue(np.isfinite(r.fit_raw.iloc[0]))


class TestCombination(unittest.TestCase):
    def test_arithmetic_mean(self):
        self.assertAlmostEqual(combine([20.0, 80.0], "ARITHMETIC_MEAN"), 50.0)

    def test_geometric_mean_is_non_compensatory(self):
        """The whole reason conjunctive archetypes use it."""
        self.assertAlmostEqual(combine([20.0, 80.0], "GEOMETRIC_MEAN"), 40.0)
        self.assertLess(combine([20.0, 80.0], "GEOMETRIC_MEAN"),
                        combine([20.0, 80.0], "ARITHMETIC_MEAN"))
        self.assertAlmostEqual(combine([50.0, 50.0], "GEOMETRIC_MEAN"), 50.0)

    def test_geometric_mean_punishes_an_unbalanced_profile(self):
        balanced = combine([60.0, 60.0], "GEOMETRIC_MEAN")
        lopsided = combine([100.0, 20.0], "GEOMETRIC_MEAN")
        self.assertGreater(balanced, lopsided)

    def test_empty_input_is_nan_not_zero(self):
        self.assertTrue(np.isnan(combine([], "ARITHMETIC_MEAN")))
        self.assertTrue(np.isnan(combine([np.nan], "GEOMETRIC_MEAN")))


class TestProfiles(unittest.TestCase):
    def setUp(self):
        self.ref = FakeReference()

    def test_six_profiles_exist(self):
        self.assertEqual(len(profile_names()), 6)
        for p in ("SHOOTER", "SLASHER", "PLAYMAKER", "THREE_AND_D",
                  "RIM_PROTECTOR", "STRETCH_BIG"):
            self.assertIn(p, profile_names())

    def test_shooter_requires_both_efficiency_and_volume(self):
        eff_only = frame(1, three_point_pct=[95.0], ft_pct=[95.0],
                         efg_pct=[95.0], three_point_attempt_rate=[5.0])
        both = frame(1, three_point_pct=[80.0], ft_pct=[80.0], efg_pct=[80.0],
                     three_point_attempt_rate=[80.0])
        a = profile_fit(eff_only, "SHOOTER", self.ref).fit_raw.iloc[0]
        b = profile_fit(both, "SHOOTER", self.ref).fit_raw.iloc[0]
        self.assertGreater(b, a)

    def test_three_and_d_is_conjunctive(self):
        shoot_only = frame(1, position="G",
                           **{m: [95.0] for m in component_metrics("SHOOTING")})
        for m in component_metrics("BOX_SCORE_DEFENSIVE_PRODUCTION"):
            shoot_only[m] = [5.0]
        balanced = frame(1, position="G")
        for m in (component_metrics("SHOOTING")
                  + component_metrics("BOX_SCORE_DEFENSIVE_PRODUCTION")):
            balanced[m] = [55.0]
        a = profile_fit(shoot_only, "THREE_AND_D", self.ref).fit_raw.iloc[0]
        b = profile_fit(balanced, "THREE_AND_D", self.ref).fit_raw.iloc[0]
        self.assertGreater(b, a, "an elite shooter who cannot defend is not 3&D")

    def test_stretch_big_rejects_a_small_shooter(self):
        small = frame(1, position="G", height=[5.0], weight=[5.0])
        for m in component_metrics("SHOOTING"):
            small[m] = [95.0]
        big = frame(1, position="C", height=[90.0], weight=[90.0])
        for m in component_metrics("SHOOTING"):
            big[m] = [70.0]
        a = profile_fit(small, "STRETCH_BIG", self.ref)
        b = profile_fit(big, "STRETCH_BIG", self.ref)
        self.assertGreater(b.fit_raw.iloc[0], a.fit_raw.iloc[0])
        self.assertEqual(a.eligibility_status.iloc[0], OUT_OF_POSITION)

    def test_rim_protector_rejects_a_small_high_steal_guard(self):
        guard = frame(1, position="G", stl_pct=[99.0], blk_pct=[20.0],
                      height=[5.0], weight=[5.0], orb_pct=[10.0],
                      drb_pct=[10.0])
        big = frame(1, position="C", stl_pct=[20.0], blk_pct=[90.0],
                    height=[95.0], weight=[95.0], orb_pct=[80.0],
                    drb_pct=[80.0])
        a = profile_fit(guard, "RIM_PROTECTOR", self.ref)
        b = profile_fit(big, "RIM_PROTECTOR", self.ref)
        self.assertGreater(b.fit_raw.iloc[0], a.fit_raw.iloc[0])
        self.assertEqual(a.eligibility_status.iloc[0], OUT_OF_POSITION)

    def test_conjunctive_profile_is_unavailable_when_a_pillar_is_missing(self):
        df = frame(1, position="F")
        for m in component_metrics("BOX_SCORE_DEFENSIVE_PRODUCTION"):
            df[m] = [np.nan]
        r = profile_fit(df, "THREE_AND_D", self.ref)
        self.assertTrue(np.isnan(r.fit_raw.iloc[0]))
        self.assertEqual(r.status.iloc[0], UNAVAILABLE)

    def test_eligibility_uses_only_position_3(self):
        df = frame(3, position="G")
        df.loc[1, "position_3"] = "C"
        df.loc[2, "position_3"] = "UNKNOWN"
        e = eligibility(df, "RIM_PROTECTOR")
        self.assertEqual(list(e), [OUT_OF_POSITION, ELIGIBLE, UNKNOWN_POSITION])

    def test_unknown_position_is_never_excluded(self):
        """Excluding UNKNOWN would penalise missing data, which historically
        correlates with going undrafted."""
        df = frame(1, position="UNKNOWN")
        r = profile_fit(df, "RIM_PROTECTOR", self.ref)
        self.assertEqual(r.eligibility_status.iloc[0], UNKNOWN_POSITION)
        ranked = rank_fit(r)
        self.assertEqual(int(ranked.fit_rank.iloc[0]), 1)

    def test_profiles_without_eligibility_accept_everyone(self):
        for p in ("SHOOTER", "SLASHER", "PLAYMAKER"):
            self.assertIsNone(PROFILES[p]["eligibility"])
            df = frame(2, position="C")
            r = profile_fit(df, p, self.ref)
            self.assertTrue((r.eligibility_status == ELIGIBLE).all())


class TestCustomMode(unittest.TestCase):
    def setUp(self):
        self.ref = FakeReference()

    def test_weighted_mean_formula(self):
        df = frame(1)
        for m in component_metrics("SHOOTING"):
            df[m] = [80.0]
        for m in component_metrics("REBOUNDING"):
            df[m] = [40.0]
        r = custom_fit(df, {"SHOOTING": 3.0, "REBOUNDING": 1.0}, self.ref)
        self.assertAlmostEqual(r.fit_raw.iloc[0], (3 * 80 + 1 * 40) / 4)

    def test_weights_need_not_sum_to_one(self):
        df = frame(1)
        a = custom_fit(df, {"SHOOTING": 1.0, "SIZE": 1.0}, self.ref)
        b = custom_fit(df, {"SHOOTING": 50.0, "SIZE": 50.0}, self.ref)
        self.assertAlmostEqual(a.fit_raw.iloc[0], b.fit_raw.iloc[0])

    def test_negative_weight_is_rejected(self):
        with self.assertRaises(UnsupportedNeed):
            validate_weights({"SHOOTING": -0.5})

    def test_all_zero_weights_are_rejected(self):
        with self.assertRaises(UnsupportedNeed):
            validate_weights({"SHOOTING": 0.0, "SIZE": 0.0})

    def test_unknown_dimension_is_rejected(self):
        with self.assertRaises(UnsupportedNeed):
            validate_weights({"CLUTCH_GENE": 1.0})

    def test_empty_request_is_rejected(self):
        with self.assertRaises(UnsupportedNeed):
            validate_weights({})

    def test_supported_dimensions_match_the_product_list(self):
        self.assertEqual(set(SUPPORTED_DIMENSIONS),
                         {"SHOOTING", "PLAYMAKING",
                          "BOX_SCORE_DEFENSIVE_PRODUCTION", "REBOUNDING",
                          "SIZE"})

    def test_unavailable_dimension_returns_no_manufactured_score(self):
        df = frame(1)
        for m in component_metrics("REBOUNDING"):
            df[m] = [np.nan]
        r = custom_fit(df, {"REBOUNDING": 0.9, "SHOOTING": 0.1}, self.ref)
        self.assertTrue(np.isnan(r.fit_raw.iloc[0]))
        self.assertEqual(r.status.iloc[0], UNAVAILABLE)
        self.assertLess(r.supported_weight_fraction.iloc[0],
                        MIN_SUPPORTED_WEIGHT)

    def test_partially_supported_request_still_scores_above_threshold(self):
        df = frame(1)
        for m in component_metrics("REBOUNDING"):
            df[m] = [np.nan]
        r = custom_fit(df, {"REBOUNDING": 0.2, "SHOOTING": 0.8}, self.ref)
        self.assertTrue(np.isfinite(r.fit_raw.iloc[0]))
        self.assertAlmostEqual(r.supported_weight_fraction.iloc[0], 0.8)


class TestAthleticismGuard(unittest.TestCase):
    def test_athleticism_weight_is_rejected_not_ignored(self):
        with self.assertRaises(UnsupportedNeed) as ctx:
            validate_weights({"SHOOTING": 0.5, "ATHLETICISM": 0.5})
        self.assertIn("UNAVAILABLE", str(ctx.exception))

    def test_zero_athleticism_weight_is_permitted(self):
        self.assertEqual(validate_weights({"SHOOTING": 1.0,
                                           "ATHLETICISM": 0.0}),
                         {"SHOOTING": 1.0})

    def test_athleticism_is_not_a_dimension(self):
        self.assertNotIn("ATHLETICISM", DIMENSIONS)
        for name in DIMENSIONS:
            self.assertNotIn("ATHLETIC", name.upper())

    def test_config_declares_it_unavailable_and_unscored(self):
        a = CONFIG["athleticism"]
        self.assertEqual(a["status"], "UNAVAILABLE")
        self.assertFalse(a["scored"])
        self.assertIn("dunk_attempt_share", a["explicitly_prohibited_proxies"])

    def test_no_dimension_is_named_after_a_prohibited_proxy(self):
        tnv.check_athleticism_not_scored()


class TestScoreScale(unittest.TestCase):
    def test_score_is_integer_within_0_100(self):
        s = fit_score(np.array([0.0, 12.4, 55.5, 99.9, 100.0]))
        self.assertTrue(np.all((s >= 0) & (s <= 100)))
        self.assertTrue(np.allclose(s, np.rint(s)))

    def test_unavailable_score_stays_nan(self):
        s = fit_score(np.array([np.nan, 50.0]))
        self.assertTrue(np.isnan(s[0]))
        self.assertEqual(s[1], 50.0)

    def test_score_is_monotone_in_the_raw_fit(self):
        raw = np.linspace(0, 100, 200)
        s = fit_score(raw)
        self.assertTrue(np.all(np.diff(s) >= 0))

    def test_score_is_not_a_within_class_percentile(self):
        """Fit Score keeps absolute trait meaning; re-ranking within a class
        would destroy it. Two identical prospects must both score the same
        absolute value, not 100 and 0."""
        df = frame(2)
        for m in component_metrics("SHOOTING"):
            df[m] = [70.0, 70.0]
        r = custom_fit(df, {"SHOOTING": 1.0}, FakeReference())
        self.assertAlmostEqual(r.fit_score.iloc[0], r.fit_score.iloc[1])
        self.assertAlmostEqual(r.fit_raw.iloc[0], 70.0)

    def test_score_semantics_forbid_probability_language(self):
        must_not = CONFIG["score"]["must_not_be_labelled"]
        self.assertIn("probability of fit", must_not)
        self.assertEqual(CONFIG["score"]["dtype"], "integer")


class TestRanking(unittest.TestCase):
    def setUp(self):
        self.ref = FakeReference()

    def test_ranking_is_deterministic(self):
        df = frame(6)
        r = profile_fit(df, "PLAYMAKER", self.ref)
        a = list(rank_fit(r).index)
        b = list(rank_fit(r).index)
        self.assertEqual(a, b)

    def test_best_fit_ranks_first(self):
        df = frame(3, ast_pct=[10.0, 90.0, 50.0], tov_pct=[50.0, 10.0, 50.0])
        r = profile_fit(df, "PLAYMAKER", self.ref)
        self.assertEqual(int(rank_fit(r).index[0]), 1)

    def test_ties_are_ordered_by_the_continuous_signal(self):
        r = pd.DataFrame({"fit_raw": [70.4, 70.6], "fit_score": [70.0, 71.0],
                          "eligibility_status": [ELIGIBLE, ELIGIBLE]})
        ranked = rank_fit(r)
        self.assertEqual(list(ranked.index), [1, 0])

    def test_unavailable_scores_rank_last(self):
        r = pd.DataFrame({"fit_raw": [np.nan, 20.0],
                          "fit_score": [np.nan, 20.0],
                          "eligibility_status": [ELIGIBLE, ELIGIBLE]})
        self.assertEqual(list(rank_fit(r).index), [1, 0])

    def test_out_of_position_ranks_behind_eligible(self):
        r = pd.DataFrame({"fit_raw": [90.0, 40.0],
                          "fit_score": [90.0, 40.0],
                          "eligibility_status": [OUT_OF_POSITION, ELIGIBLE]})
        self.assertEqual(list(rank_fit(r).index), [1, 0])

    def test_ranking_never_reads_an_outcome(self):
        """Scan the CODE, not the docstring — the docstring legitimately names
        the things the function promises not to use."""
        import ast
        import inspect
        tree = ast.parse(inspect.getsource(rank_fit).lstrip())
        fn = tree.body[0]
        if (fn.body and isinstance(fn.body[0], ast.Expr)
                and isinstance(fn.body[0].value, ast.Constant)):
            fn.body = fn.body[1:]
        code = ast.unparse(fn).lower()
        for banned in ("drafted", "pick", "overall_score", "nba"):
            self.assertNotIn(banned, code)


class TestExplanations(unittest.TestCase):
    def setUp(self):
        self.ref = FakeReference()

    def test_strengths_are_ordered_best_first(self):
        comp = pd.DataFrame({"ast_pct": [90.0], "tov_pct": [70.0]})
        raw = pd.DataFrame({"ast_pct": [90.0], "tov_pct": [30.0]})
        e = explain(comp, raw, {"PLAYMAKING": 1.0})
        s = e.strengths.iloc[0]
        self.assertEqual(s[0]["metric"], "ast_pct")
        self.assertGreaterEqual(s[0]["oriented_percentile"],
                                s[-1]["oriented_percentile"])

    def test_inverted_metric_is_quoted_in_its_natural_direction(self):
        comp = pd.DataFrame({"ast_pct": [50.0], "tov_pct": [95.0]})
        raw = pd.DataFrame({"ast_pct": [50.0], "tov_pct": [5.0]})
        e = explain(comp, raw, {"PLAYMAKING": 1.0})
        tov = [c for c in e.strengths.iloc[0] if c["metric"] == "tov_pct"][0]
        self.assertEqual(tov["percentile"], 5.0)
        self.assertTrue(tov["lower_is_better"])

    def test_missing_component_is_not_called_a_weakness(self):
        comp = pd.DataFrame({"ast_pct": [np.nan], "tov_pct": [80.0]})
        raw = comp.copy()
        e = explain(comp, raw, {"PLAYMAKING": 1.0})
        self.assertEqual(len(e.missing_components.iloc[0]), 1)
        limiters = [c["metric"] for c in e.limiting_components.iloc[0]]
        self.assertNotIn("ast_pct", limiters)

    def test_only_requested_dimensions_appear(self):
        metrics, dims = relevant_metrics({"SIZE": 1.0})
        self.assertEqual(set(metrics), {"height", "weight"})
        self.assertEqual(dims, ["SIZE"])

    def test_explanation_is_deterministic(self):
        comp = pd.DataFrame({"ast_pct": [90.0], "tov_pct": [70.0]})
        raw = comp.copy()
        a = explain(comp, raw, {"PLAYMAKING": 1.0}).strengths.iloc[0]
        b = explain(comp, raw, {"PLAYMAKING": 1.0}).strengths.iloc[0]
        self.assertEqual(a, b)


class TestNoOutcomeOrBoardContamination(unittest.TestCase):
    def test_no_prohibited_metric_in_any_formula(self):
        tnv.check_no_prohibited_inputs()

    def test_no_board_signal_is_a_component(self):
        used = set(tnv.all_component_metrics())
        for banned in ("stage_a_probability", "stage_b_signal", "overall_score",
                       "final_board_signal", "drafted", "pick"):
            self.assertNotIn(banned, used)

    def test_no_age_or_contaminated_position(self):
        used = set(tnv.all_component_metrics())
        for banned in ("age", "date_of_birth", "position_from_population",
                       "class_from_population"):
            self.assertNotIn(banned, used)

    def test_scoring_modules_never_import_the_board(self):
        for mod in ("dimensions", "profiles", "scoring", "explanations"):
            src = (ROOT / "src" / "draftlens" / "team_need"
                   / f"{mod}.py").read_text()
            self.assertNotIn("from draftlens.ml.board", src)
            self.assertNotIn("from draftlens.ml.stage_a", src)
            self.assertNotIn("from draftlens.ml.stage_b", src)

    def test_fit_score_ignores_a_board_column_if_present(self):
        """Even if a caller joins board output onto the frame, it must not
        change a Fit Score."""
        df = frame(2)
        a = custom_fit(df, {"SHOOTING": 1.0}, FakeReference())
        df2 = df.copy()
        df2["overall_score"] = [99, 1]
        df2["stage_a_probability"] = [0.99, 0.01]
        b = custom_fit(df2, {"SHOOTING": 1.0}, FakeReference())
        np.testing.assert_allclose(a.fit_raw.to_numpy(), b.fit_raw.to_numpy())


class TestReferenceAndHoldout(unittest.TestCase):
    def test_reference_metrics_cover_every_component(self):
        for m in tnv.all_component_metrics():
            self.assertIn(m, REFERENCE_METRICS, f"{m} has no reference")

    def test_config_declares_the_reference_reads_no_outcome(self):
        self.assertFalse(CONFIG["reference"]["reads_draft_outcome"])

    def test_reference_position_source_is_leakage_safe(self):
        self.assertIn("position_3", CONFIG["reference"]["position_source"])
        self.assertIn("PROHIBITED", CONFIG["reference"]["position_source"])

    def test_no_team_need_source_scores_the_holdout(self):
        for mod in ("dimensions", "profiles", "scoring", "explanations",
                    "reference", "validation"):
            src = (ROOT / "src" / "draftlens" / "team_need"
                   / f"{mod}.py").read_text()
            self.assertNotIn("targets_2026", src)
            self.assertNotIn("features_2026", src)

    def test_cli_refuses_the_holdout_year(self):
        src = (ROOT / "scripts" / "run_team_need.py").read_text()
        self.assertIn("HOLDOUT_YEAR = 2026", src)
        self.assertIn("REFUSED", src)

    def test_reference_builder_refuses_the_holdout(self):
        src = (ROOT / "scripts" / "build_team_need_reference.py").read_text()
        self.assertIn("REFUSED", src)


class TestValidationGuards(unittest.TestCase):
    def test_all_static_guards_pass(self):
        checks = tnv.run_all()
        self.assertTrue(all(checks.values()), checks)

    def test_score_validity_guard_catches_out_of_range(self):
        bad = pd.DataFrame({"fit_score": [150.0], "fit_raw": [150.0]})
        with self.assertRaises(AssertionError):
            tnv.check_scores_valid(bad)

    def test_monotonicity_guard_catches_inversion(self):
        bad = pd.DataFrame({"fit_raw": [10.0, 90.0], "fit_score": [90.0, 10.0]})
        with self.assertRaises(AssertionError):
            tnv.check_monotone_with_raw(bad)

    def test_population_guard_catches_a_dropped_prospect(self):
        with self.assertRaises(AssertionError):
            tnv.check_population_preserved(pd.DataFrame({"a": [1, 2]}), 3)


if __name__ == "__main__":
    unittest.main()
