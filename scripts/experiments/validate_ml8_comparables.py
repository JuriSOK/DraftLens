"""ML-8 validation — hard-fails if the comparable system stops being a
descriptive statistical comparison.

There is no ground truth, so nothing predictive can be validated. What CAN be
checked is that no forbidden input reaches the similarity vector, that raw
cross-league production is never compared directly, that the output obeys its
contract, and that every frozen upstream system is untouched.

  ./.venv/bin/python scripts/experiments/validate_ml8_comparables.py
"""

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from draftlens.comparables import validation as cv
from draftlens.comparables.reference import (MIN_GAMES, MIN_MINUTES,
                                             NCAA_REFERENCE_FILE,
                                             REFERENCE_FILE, REFERENCE_SEASONS,
                                             load_ncaa_reference, load_pool)
from draftlens.comparables.similarity import (MIN_SHARED_COVERAGE,
                                              N_COMPARABLES,
                                              build_distance_reference,
                                              find_comparables, prepare_pool,
                                              similarity_scores)
from draftlens.comparables.space import (COMMON_METRICS, DIMENSION_NAMES,
                                         DIMENSIONS, build_nba_space,
                                         build_ncaa_space)
from draftlens.data.identity.normalization import normalize_name
from draftlens.ml.board import BOARD
from draftlens.ml.datasets import load_development
from draftlens.ml.guards import (Guard, check_artifacts_untracked,
                                 check_development_population)
from draftlens.ml.stage_a import STAGE_A
from draftlens.ml.stage_b import STAGE_B
from draftlens.ml.validation import HOLDOUT_YEAR
from draftlens.paths import ROOT, interim
from draftlens.team_need.dimensions import CONFIG as TEAM_NEED_CONFIG

warnings.filterwarnings("ignore", category=RuntimeWarning)
OUT = interim("comparables")
SRC = ROOT / "src" / "draftlens" / "comparables"
AUDIT_N = 120

STAGE_A_ANCHOR = {"family": "LogisticRegression", "C": 0.25,
                  "normalization": "SEASON_RELATIVE", "calibration": "none"}
STAGE_B_ANCHOR = {"family": "Ridge", "alpha": 10.0, "target": "RAW_PICK",
                  "normalization": "STANDARD"}
BOARD_ANCHOR = {"method": "C_MULTIPLICATIVE",
                "stage_b_transform": "DRAFT_SLOT_UTILITY",
                "score_transform": "CURRENT_BOARD_PERCENTILE"}


def rule(t):
    print(f"\n{'=' * 78}\n{t}\n{'=' * 78}")


def main():
    rule("ML-8 VALIDATION")
    for f in (REFERENCE_FILE, NCAA_REFERENCE_FILE):
        if not f.exists():
            print(f"  FAIL  {f.name} missing — run "
                  f"scripts/build_comparable_references.py")
            return 1

    g = Guard()
    dev = load_development()
    pool = prepare_pool(load_pool())
    ncaa_ref = load_ncaa_reference()
    nba_dims, _ = build_nba_space(pool)
    ncaa_dims, _ = build_ncaa_space(dev, ncaa_ref)

    # --------------------------------------- 1. frozen upstream untouched
    for k, want in STAGE_A_ANCHOR.items():
        g.check(STAGE_A[k] == want, f"Stage A {k} changed: {STAGE_A[k]}")
    for k, want in STAGE_B_ANCHOR.items():
        g.check(STAGE_B[k] == want, f"Stage B {k} changed: {STAGE_B[k]}")
    for k, want in BOARD_ANCHOR.items():
        g.check(BOARD[k] == want, f"Board {k} changed: {BOARD[k]}")
    g.check(TEAM_NEED_CONFIG["athleticism"]["status"] == "UNAVAILABLE",
            "Team Need athleticism status changed")
    g.check(len(TEAM_NEED_CONFIG["dimensions"]) == 6,
            "Team Need dimensions changed")
    print("  1. frozen upstream: Stage A, Stage B, Board and Team Need "
          "unchanged")

    # ------------------------------------------ 2. no prohibited inputs
    cv.check_no_prohibited_inputs()
    cv.check_no_raw_per_game_inputs()
    cv.check_dimensions_declared()
    for banned in ("drafted", "pick", "stage_a_probability", "stage_b_signal",
                   "overall_score", "final_board_signal", "fit_score", "age",
                   "date_of_birth", "position_from_population"):
        g.check(banned not in COMMON_METRICS,
                f"prohibited input {banned} is a similarity dimension")
    for banned in ("all_star", "mvp", "award", "bpm", "raptor", "vorp",
                   "career"):
        g.check(not [m for m in COMMON_METRICS if banned in m.lower()],
                f"an NBA career-success input matching '{banned}' is present")
    g.check(not [m for m in COMMON_METRICS if "jump_shot" in m],
            "a rejected jump-shot metric entered the space (DEC-068)")
    g.check(not [m for m in COMMON_METRICS
                 if m in ("height", "weight", "athleticism")],
            "a fabricated size or athleticism input is present")
    print(f"  2. inputs: {len(COMMON_METRICS)} metrics across "
          f"{len(DIMENSION_NAMES)} dimensions, none prohibited")

    # ----------------------------- 3. no raw cross-league production
    for m in COMMON_METRICS:
        g.check(not m.endswith("_per_game"),
                f"{m} is raw per-game production — not cross-league comparable")
    for mod in ("space", "similarity"):
        src = (SRC / f"{mod}.py").read_text()
        g.check("percentile" in src.lower(),
                f"{mod}.py does not normalise before comparing")
    print("  3. cross-league: only league-relative percentiles are compared")

    # ------------------------------- 4. no scoring-system contamination
    for mod in ("nba_features", "reference", "space", "similarity",
                "explanations", "validation"):
        src = (SRC / f"{mod}.py").read_text()
        for banned in ("from draftlens.ml.board", "from draftlens.ml.stage_a",
                       "from draftlens.ml.stage_b", "team_need.dimensions",
                       "team_need.profiles", "team_need.scoring"):
            g.check(banned not in src, f"comparables/{mod}.py imports {banned}")
    # a board column on the frame must not change a comparable
    d2 = dev.copy()
    d2["overall_score"] = np.linspace(0, 100, len(d2))
    d2["stage_a_probability"] = np.linspace(0, 1, len(d2))
    alt_dims, _ = build_ncaa_space(d2, ncaa_ref)
    g.check(np.allclose(ncaa_dims.fillna(-1).to_numpy(),
                        alt_dims.fillna(-1).to_numpy()),
            "a General Board column changed the common-space vector")
    print("  4. independence: no board / Team Need score can reach similarity")

    # --------------------------------------------- 5. pool integrity
    cv.check_pool_unique(pool)
    g.check(pool.athlete_id.is_unique, "the NBA pool holds a duplicate player")
    names = pool.groupby("athlete_id").athlete_display_name.nunique()
    g.check(int((names > 1).sum()) == 0,
            "an athlete_id carries more than one name")
    g.check(set(pool.reference_seasons.explode().dropna().astype(int))
            <= set(REFERENCE_SEASONS),
            "the pool references a season outside the frozen window")
    print(f"  5. pool: {len(pool)} unique NBA players, "
          f"{REFERENCE_SEASONS[0]}-{REFERENCE_SEASONS[-1]}, ids stable")

    # ------------------------------------------------ 6. holdout firewall
    g.check(HOLDOUT_YEAR not in set(dev.draft_year), "2026 in the population")
    g.check(HOLDOUT_YEAR not in set(REFERENCE_SEASONS),
            "2026 in the NBA reference window")
    g.check(HOLDOUT_YEAR not in set(pd.to_numeric(ncaa_ref.season,
                                                  errors="coerce").dropna()),
            "2026 in the NCAA peer reference")
    for mod in ("nba_features", "reference", "space", "similarity",
                "explanations", "validation"):
        s = (SRC / f"{mod}.py").read_text()
        for banned in ("targets_2026", "features_2026"):
            g.check(banned not in s, f"comparables/{mod}.py references {banned}")
    for p in sorted(OUT.glob("*.csv")):
        df = pd.read_csv(p)
        for col in df.columns:
            if "season" in str(col).lower() or "year" in str(col).lower():
                vals = pd.to_numeric(df[col], errors="coerce").dropna()
                g.check(HOLDOUT_YEAR not in set(vals),
                        f"{p.name}: {HOLDOUT_YEAR} in {col}")
    print("  6. holdout firewall: 2026 absent from every population, "
          "reference and artifact")

    check_development_population(g, dev)

    # ------------------------------------- 7. output contract on real data
    dist_ref = build_distance_reference(ncaa_dims, nba_dims, max_prospects=200)
    rng = np.random.default_rng(20260808)
    need = int(np.ceil(MIN_SHARED_COVERAGE * len(DIMENSION_NAMES)))
    scorable = [i for i in dev.index
                if np.isfinite(ncaa_dims.loc[i].to_numpy(dtype="float64")).sum()
                >= need]
    sample = rng.choice(scorable, size=min(AUDIT_N, len(scorable)),
                        replace=False)
    unavailable = 0
    for i in sample:
        name = dev.loc[i, "player_name"]
        r = find_comparables(ncaa_dims.loc[i], pool, nba_dims,
                             prospect_name=name, distance_reference=dist_ref)
        if r["status"] != "OK":
            unavailable += 1
            g.check(not r["comparables"],
                    "an UNAVAILABLE result still returned names")
            continue
        try:
            cv.check_result(r)
            cv.check_no_self_match(r, name)
        except AssertionError as e:
            g.check(False, f"{name}: {e}")
    print(f"  7. output contract: {len(sample)} prospects, exactly "
          f"{N_COMPARABLES} unique players each, {unavailable} unavailable")

    # ------------------------------------------ 8. coverage guard bites
    thin = ncaa_dims.loc[sample[0]].copy()
    thin[DIMENSION_NAMES[0]] = np.nan
    thin[DIMENSION_NAMES[1]] = np.nan
    thin[DIMENSION_NAMES[2]] = np.nan
    r = find_comparables(thin, pool, nba_dims, distance_reference=dist_ref)
    g.check(r["status"] != "OK",
            "a prospect below the shared-coverage minimum still got comparables")
    g.check(not r["comparables"], "an UNAVAILABLE result returned names")
    print(f"  8. coverage guard: below {MIN_SHARED_COVERAGE:.0%} shared "
          f"dimensions returns UNAVAILABLE, not manufactured names")

    # ------------------------------------------- 9. self-match on real data
    pool_keys = set(pool["_name_key"])
    in_pool = [i for i in scorable
               if normalize_name(dev.loc[i, "player_name"]) in pool_keys]
    violations = 0
    for i in in_pool[:200]:
        name = dev.loc[i, "player_name"]
        r = find_comparables(ncaa_dims.loc[i], pool, nba_dims,
                             prospect_name=name, distance_reference=dist_ref)
        if r["status"] != "OK":
            continue
        try:
            cv.check_no_self_match(r, name)
        except AssertionError:
            violations += 1
    g.check(violations == 0,
            f"{violations} prospects matched themselves")
    print(f"  9. self-match: {len(in_pool)} prospects also appear in the NBA "
          f"pool, {violations} matched themselves")

    # --------------------------------------- 10. similarity score bounds
    s = similarity_scores(np.array([0.0, 5.0, 20.0, 100.0]), dist_ref)
    g.check(bool(np.all((s >= 0) & (s <= 100))),
            "similarity score outside 0-100")
    g.check(bool(np.all(np.diff(s) <= 0)),
            "similarity score is not decreasing in distance")
    print("  10. similarity score: within 0-100 and monotone in distance")

    # ---------------------------------------- 11. artifacts stay ignored
    check_artifacts_untracked(g, "data/interim/comparables")
    print("  11. generated comparable artifacts remain untracked")

    return g.report()


if __name__ == "__main__":
    sys.exit(main())
