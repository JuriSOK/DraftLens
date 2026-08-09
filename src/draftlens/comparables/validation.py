"""Guards for the NBA comparable system.

There is no ground truth, so nothing predictive can be validated. What CAN be
checked is that no forbidden input reaches the similarity vector, that the
output obeys its own contract, and that raw cross-league production is never
compared directly.
"""

import numpy as np
import pandas as pd

from draftlens.comparables.similarity import (MIN_SHARED_COVERAGE,
                                              N_COMPARABLES, UNAVAILABLE)
from draftlens.comparables.space import COMMON_METRICS, DIMENSIONS

# Anything that would turn a descriptive comparison into a prediction, or
# reintroduce a leakage channel closed in an earlier phase.
PROHIBITED_INPUTS = {
    "drafted", "pick", "round", "drafting_team",
    "stage_a_probability", "stage_b_signal", "stage_b_raw_pick",
    "stage_b_quality", "overall_score", "final_board_signal", "board_rank",
    "fit_score", "fit_raw",
    "age", "current_age", "date_of_birth", "dob",
    "position_from_population", "class_from_population",
    "all_star", "mvp", "awards", "career_win_shares", "bpm", "raptor", "vorp",
}
PROHIBITED_SUBSTRINGS = ("jump_shot", "mock", "consensus", "analyst",
                         "award", "all_star", "career_")

# Raw per-game production must never be a similarity input: 19 NCAA PPG and
# 19 NBA PPG are not the same event.
RAW_PER_GAME = {"points_per_game", "rebounds_per_game", "assists_per_game",
                "steals_per_game", "blocks_per_game", "turnovers_per_game",
                "avgPoints", "avgRebounds", "avgAssists"}


def check_no_prohibited_inputs():
    bad = [m for m in COMMON_METRICS
           if m in PROHIBITED_INPUTS
           or any(s in m.lower() for s in PROHIBITED_SUBSTRINGS)]
    if bad:
        raise AssertionError(f"prohibited input in the common space: {bad}")
    return True


def check_no_raw_per_game_inputs():
    bad = [m for m in COMMON_METRICS if m in RAW_PER_GAME]
    if bad:
        raise AssertionError(
            f"raw per-game production used as a cross-league input: {bad} — "
            f"leagues differ in pace, role and competition")
    return True


def check_dimensions_declared():
    for name, spec in DIMENSIONS.items():
        if spec["kind"] not in ("QUALITY", "ROLE", "STYLE"):
            raise AssertionError(f"{name} has no valid kind")
        if not spec["metrics"]:
            raise AssertionError(f"{name} has no metrics")
        for m in spec["invert"]:
            if m not in spec["metrics"]:
                raise AssertionError(f"{name} inverts a metric it does not use")
    return True


def check_pool_unique(pool):
    if not pool.athlete_id.is_unique:
        raise AssertionError("the NBA reference pool contains a duplicate player")
    return True


def check_result(result, n=N_COMPARABLES):
    """The output contract: exactly n unique players, scores in range."""
    if result.get("status") != "OK":
        if result.get("comparables"):
            raise AssertionError("an UNAVAILABLE result still returned names")
        return True
    comps = result["comparables"]
    if len(comps) != n:
        raise AssertionError(f"{len(comps)} comparables returned, expected {n}")
    ids = [c["nba_player_id"] for c in comps]
    if len(set(ids)) != n:
        raise AssertionError(f"duplicate NBA players in the top {n}: {ids}")
    for c in comps:
        s = c["similarity_score"]
        if not (0 <= s <= 100):
            raise AssertionError(f"similarity score outside 0-100: {s}")
        if c["comparison_coverage"] < MIN_SHARED_COVERAGE:
            raise AssertionError(
                f"a comparable was accepted below the shared-coverage minimum: "
                f"{c['comparison_coverage']}")
    dists = [c["raw_distance"] for c in comps]
    if dists != sorted(dists):
        raise AssertionError("comparables are not ordered closest-first")
    return True


def check_no_self_match(result, prospect_name):
    from draftlens.data.identity.normalization import normalize_name
    if result.get("status") != "OK" or not prospect_name:
        return True
    key = normalize_name(prospect_name)
    for c in result["comparables"]:
        if normalize_name(c["nba_player_name"]) == key:
            raise AssertionError(
                f"{prospect_name} was returned as his own NBA comparable")
    return True


def run_all(pool=None, result=None, prospect_name=None):
    checks = {"no_prohibited_inputs": check_no_prohibited_inputs(),
              "no_raw_per_game": check_no_raw_per_game_inputs(),
              "dimensions_declared": check_dimensions_declared()}
    if pool is not None:
        checks["pool_unique"] = check_pool_unique(pool)
    if result is not None:
        checks["result_contract"] = check_result(result)
        checks["no_self_match"] = check_no_self_match(result, prospect_name)
    return checks
