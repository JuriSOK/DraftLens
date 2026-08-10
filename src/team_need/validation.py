"""Guards for Team Need configuration and scores.

Team Need has no ground-truth target, so ordinary predictive validation does not
apply. What CAN be checked is that the engine never reads something it must not,
and never emits a score that misrepresents the evidence.
"""

import numpy as np
import pandas as pd

from team_need.dimensions import (CONFIG, DIMENSIONS,
                                            component_metrics, reference_spec)
from team_need.profiles import PROFILES

# Anything that would turn Team Need into a second draft model, or reintroduce
# a leakage channel closed in an earlier phase.
PROHIBITED_INPUTS = {
    "drafted", "pick", "round", "drafting_team",
    "stage_a_probability", "stage_b_signal", "stage_b_raw_pick",
    "stage_b_quality", "overall_score", "final_board_signal", "board_rank",
    "age", "current_age", "date_of_birth", "dob",
    "position_from_population", "class_from_population",
    "match_method", "match_confidence", "early_entrant", "population_source",
}
PROHIBITED_SUBSTRINGS = ("jump_shot", "nba_", "mock", "consensus", "analyst")


def all_component_metrics():
    out = []
    for name in DIMENSIONS:
        out += component_metrics(name)
    for spec in PROFILES.values():
        for p in spec.get("pillars", []):
            out += list(p.get("metrics", []))
    return sorted(set(out))


def check_no_prohibited_inputs():
    """No dimension or profile may be built from a prohibited metric."""
    bad = [m for m in all_component_metrics()
           if m in PROHIBITED_INPUTS
           or any(s in m.lower() for s in PROHIBITED_SUBSTRINGS)]
    if bad:
        raise AssertionError(f"prohibited metric in a Team Need formula: {bad}")
    return True


def check_athleticism_not_scored():
    """Athleticism must remain unavailable until a real measurement exists."""
    a = CONFIG["athleticism"]
    if a["status"] != "UNAVAILABLE" or a["scored"]:
        raise AssertionError("Athleticism is being scored without a data source")
    proxies = set(a["explicitly_prohibited_proxies"])
    for name, d in DIMENSIONS.items():
        if "ATHLETIC" in name.upper():
            raise AssertionError(f"an athleticism dimension exists: {name}")
    # a prohibited proxy may legitimately appear elsewhere (dunk share is part
    # of rim pressure); what is forbidden is calling any of it athleticism
    return bool(proxies)


def check_orientation_declared():
    for name, d in DIMENSIONS.items():
        for c in d["components"]:
            if c["orientation"] not in ("HIGHER_IS_BETTER", "LOWER_IS_BETTER"):
                raise AssertionError(
                    f"{name}.{c['metric']} has no valid orientation")
    return True


def check_reference_consistency():
    """A metric must resolve to one reference group across all dimensions."""
    reference_spec()
    return True


def check_scores_valid(scored, score_col="fit_score", raw_col="fit_raw"):
    """Scores are within 0-100, integral, and consistent with the raw signal."""
    s = pd.to_numeric(scored[score_col], errors="coerce")
    ok = s.notna()
    if ok.any():
        v = s[ok]
        if float(v.min()) < 0 or float(v.max()) > 100:
            raise AssertionError(f"fit score outside 0-100: "
                                 f"[{v.min()}, {v.max()}]")
        if not np.allclose(v.to_numpy(), np.rint(v.to_numpy())):
            raise AssertionError("fit score is not integral")
    if raw_col in scored.columns:
        r = pd.to_numeric(scored[raw_col], errors="coerce")
        if (r.notna() != s.notna()).any():
            raise AssertionError(
                "fit_score and fit_raw disagree about availability")
    return True


def check_monotone_with_raw(scored, score_col="fit_score", raw_col="fit_raw"):
    """A higher raw fit must never produce a lower integer score."""
    d = scored[[raw_col, score_col]].dropna().sort_values(
        raw_col, ascending=False, kind="stable")
    if not d[score_col].is_monotonic_decreasing:
        raise AssertionError("fit_score order disagrees with fit_raw")
    return True


def check_population_preserved(scored, expected):
    """No prospect may vanish because one metric was missing."""
    if len(scored) != expected:
        raise AssertionError(
            f"Team Need returned {len(scored)} rows for {expected} prospects "
            f"— a prospect was dropped")
    return True


def run_all(scored=None, expected=None):
    checks = {"no_prohibited_inputs": check_no_prohibited_inputs(),
              "athleticism_unavailable": check_athleticism_not_scored(),
              "orientation_declared": check_orientation_declared(),
              "reference_consistent": check_reference_consistency()}
    if scored is not None:
        checks["scores_valid"] = check_scores_valid(scored)
        checks["score_monotone"] = check_monotone_with_raw(scored)
        if expected is not None:
            checks["population_preserved"] = check_population_preserved(
                scored, expected)
    return checks


def validate():
    """Score every predefined profile for the full development population and
    check the contract holds. Team Need has no ground truth, so what CAN be
    checked is that the engine never reads something it must not, and never
    emits a score that misrepresents the evidence.

      ./.venv/bin/python scripts/validate.py
    """
    from board.probability import DRAFT_PROBABILITY
    from board.order import DRAFT_ORDER
    from board.scoring import GENERAL_BOARD
    from data.build import load_development
    from team_need.profiles import profile_names, score_all_profiles
    from team_need.reference import PercentileReference
    from validation import Guard, HOLDOUT_YEAR

    g = Guard()
    dev = load_development()

    g.check(DRAFT_PROBABILITY["family"] == "LogisticRegression" and DRAFT_PROBABILITY["C"] == 0.25,
            "Draft Probability changed")
    g.check(DRAFT_ORDER["family"] == "Ridge" and DRAFT_ORDER["alpha"] == 10.0,
            "Draft Order changed")
    g.check(GENERAL_BOARD["method"] == "C_MULTIPLICATIVE", "General Board changed")
    print("  1. frozen upstream: Draft Probability, Draft Order and General "
          "Board unchanged")

    for k, v in run_all().items():
        g.check(bool(v), f"static guard failed: {k}")
    print("  2. static guards: no prohibited input, athleticism unavailable, "
          "orientation declared, reference consistent")

    g.check(HOLDOUT_YEAR not in set(dev.draft_year), "2026 in development")
    print("  3. holdout firewall: 2026 absent from development")

    reference = PercentileReference()
    scored = score_all_profiles(dev, reference)
    for profile in profile_names():
        v = pd.to_numeric(scored[profile], errors="coerce").dropna()
        g.check(bool(((v >= 0) & (v <= 100)).all()),
                f"{profile}: score outside 0-100")
    g.check(len(scored) == len(dev),
            f"score_all_profiles returned {len(scored)} rows for "
            f"{len(dev)} prospects — a prospect was dropped")
    print(f"  4. output contract: {len(profile_names())} profiles scored for "
          f"all {len(dev)} development prospects, 0-100 or missing, never "
          f"dropped")

    return g.report()
