"""Guards for the NBA comparable system.

There is no ground truth, so nothing predictive can be validated. What CAN be
checked is that no forbidden input reaches the similarity vector, that the
output obeys its own contract, and that raw cross-league production is never
compared directly.
"""

import numpy as np
import pandas as pd

from comparables.similarity import (MIN_SHARED_COVERAGE,
                                              N_COMPARABLES, UNAVAILABLE)
from comparables.space import COMMON_METRICS, DIMENSIONS

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
    from data.matching import normalize_name
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


def validate():
    """Recompute comparables for a real sample end to end and check the
    contract holds. No ground truth exists, so what CAN be checked is that no
    forbidden input reaches the similarity vector — comparables never imports
    a scoring system, so upstream anchors are not re-checked here; that is
    `board.scoring.validate`'s job — and that the output obeys its contract.

      ./.venv/bin/python scripts/validate.py
    """
    import numpy as np
    import pandas as pd

    from comparables.reference import load_ncaa_reference, load_pool
    from comparables.similarity import build_distance_reference, find_comparables, prepare_pool
    from comparables.space import build_ncaa_space, build_nba_space
    from data.build import load_development
    from data.matching import normalize_name
    from validation import Guard, HOLDOUT_YEAR

    g = Guard()
    dev = load_development()
    pool = prepare_pool(load_pool())
    ncaa_ref = load_ncaa_reference()
    nba_dims, _ = build_nba_space(pool)
    ncaa_dims, _ = build_ncaa_space(dev, ncaa_ref)

    for k, v in run_all(pool=pool).items():
        g.check(bool(v), f"static guard failed: {k}")
    print("  1. static guards: no prohibited input, no raw per-game "
          "production, dimensions declared")

    g.check(HOLDOUT_YEAR not in set(dev.draft_year), "2026 in development")
    g.check(HOLDOUT_YEAR not in set(pool.reference_seasons.explode().dropna().astype(int)),
            "2026 in the NBA reference window")
    print("  2. holdout firewall: 2026 absent from population and reference")

    dist_ref = build_distance_reference(ncaa_dims, nba_dims, max_prospects=150)
    rng = np.random.default_rng(20260809)
    need = int(np.ceil(0.75 * len(nba_dims.columns)))
    scorable = [i for i in dev.index
                if np.isfinite(ncaa_dims.loc[i].to_numpy(dtype="float64")).sum() >= need]
    sample = rng.choice(scorable, size=min(60, len(scorable)), replace=False)
    unavailable = 0
    for i in sample:
        name = dev.loc[i, "player_name"]
        r = find_comparables(ncaa_dims.loc[i], pool, nba_dims,
                             prospect_name=name, distance_reference=dist_ref,
                             prospect_height=dev.loc[i, "height"])
        if r["status"] != "OK":
            unavailable += 1
            continue
        try:
            check_result(r)
            check_no_self_match(r, name)
        except AssertionError as e:
            g.check(False, f"{name}: {e}")
    print(f"  3. output contract: {len(sample)} prospects sampled, "
          f"{unavailable} unavailable, all others exactly 3 unique players")

    return g.report()
