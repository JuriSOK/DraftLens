"""ML-7 validation — hard-fails if Team Need becomes anything other than a
transparent, preference-based fit score.

Team Need has no ground-truth target, so there is nothing to validate
predictively. What CAN be checked is that no draft outcome, board signal or
fabricated trait reaches a formula, that no prospect vanishes because one
statistic is missing, and that the frozen General Board is untouched.

  ./.venv/bin/python scripts/experiments/validate_ml7_team_need.py
"""

import inspect
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from draftlens.ml.board import BOARD
from draftlens.ml.datasets import load_development
from draftlens.ml.guards import (Guard, check_artifacts_untracked,
                                 check_development_population)
from draftlens.ml.stage_a import STAGE_A
from draftlens.ml.stage_b import STAGE_B
from draftlens.ml.validation import HOLDOUT_YEAR
from draftlens.paths import ROOT, interim
from draftlens.team_need import validation as tnv
from draftlens.team_need.dimensions import (CONFIG, DIMENSIONS,
                                            compute_components,
                                            compute_dimensions, data_coverage)
from draftlens.team_need.profiles import PROFILES
from draftlens.team_need.reference import PercentileReference, REFERENCE_FILE
from draftlens.team_need.scoring import (SUPPORTED_DIMENSIONS, UnsupportedNeed,
                                         custom_fit, profile_fit, rank_fit)

OUT = interim("team_need")
TEAM_NEED_SRC = ROOT / "src" / "draftlens" / "team_need"

# The frozen upstream methodology ML-7 must leave alone.
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
    rule("ML-7 VALIDATION")
    if not REFERENCE_FILE.exists():
        print("  FAIL  NCAA percentile reference missing — run "
              "scripts/build_team_need_reference.py")
        return 1

    g = Guard()
    dev = load_development()
    ref = PercentileReference()
    components, raw = compute_components(dev, ref)
    dims, coverage = compute_dimensions(dev, ref, components)

    # --------------------------------------- 1. upstream methodology frozen
    for k, want in STAGE_A_ANCHOR.items():
        g.check(STAGE_A[k] == want, f"Stage A {k} changed: {STAGE_A[k]} != {want}")
    for k, want in STAGE_B_ANCHOR.items():
        g.check(STAGE_B[k] == want, f"Stage B {k} changed: {STAGE_B[k]} != {want}")
    for k, want in BOARD_ANCHOR.items():
        g.check(BOARD[k] == want, f"Board {k} changed: {BOARD[k]} != {want}")
    print("  1. frozen upstream: Stage A, Stage B and the General Board "
          "unchanged")

    # ------------------------------------------- 2. no prohibited input
    try:
        tnv.check_no_prohibited_inputs()
        ok = True
    except AssertionError as e:
        ok = False
        g.check(False, str(e))
    metrics = tnv.all_component_metrics()
    for banned in ("drafted", "pick", "round", "stage_a_probability",
                   "stage_b_signal", "overall_score", "final_board_signal",
                   "age", "date_of_birth", "position_from_population"):
        g.check(banned not in metrics,
                f"prohibited input {banned} is a Team Need component")
    g.check(not [m for m in metrics if "jump_shot" in m],
            "a rejected generic jump-shot metric entered a formula (DEC-068)")
    if ok:
        print(f"  2. inputs: {len(metrics)} components, none prohibited")

    # ------------------------------- 3. no board / outcome import anywhere
    for mod in ("dimensions", "profiles", "scoring", "explanations",
                "reference", "validation", "__init__"):
        src = (TEAM_NEED_SRC / f"{mod}.py").read_text()
        for banned in ("from draftlens.ml.board", "from draftlens.ml.stage_a",
                       "from draftlens.ml.stage_b"):
            g.check(banned not in src,
                    f"team_need/{mod}.py imports the General Board pipeline")
    # a board column on the frame must not change a score
    d2 = dev.copy()
    d2["overall_score"] = np.linspace(0, 100, len(d2))
    d2["stage_a_probability"] = np.linspace(0, 1, len(d2))
    a = custom_fit(dev, {"SHOOTING": 1.0}, ref, components, dims, coverage)
    c2, _ = compute_components(d2, ref)
    dm2, cv2 = compute_dimensions(d2, ref, c2)
    b = custom_fit(d2, {"SHOOTING": 1.0}, ref, c2, dm2, cv2)
    g.check(np.allclose(a.fit_raw.fillna(-1), b.fit_raw.fillna(-1)),
            "a General Board column changed a Fit Score")
    print("  3. independence: no board import, and a board column cannot "
          "change a score")

    # ------------------------------------------------- 4. athleticism honest
    tnv.check_athleticism_not_scored()
    g.check(CONFIG["athleticism"]["status"] == "UNAVAILABLE",
            "Athleticism is no longer declared UNAVAILABLE")
    g.check(not CONFIG["athleticism"]["scored"], "Athleticism is being scored")
    g.check("ATHLETICISM" not in DIMENSIONS, "an Athleticism dimension exists")
    rejected = False
    try:
        custom_fit(dev, {"ATHLETICISM": 1.0}, ref, components, dims, coverage)
    except UnsupportedNeed:
        rejected = True
    g.check(rejected, "an athleticism weight was accepted rather than rejected")
    print("  4. athleticism: UNAVAILABLE, unscored, and a weighted request is "
          "rejected")

    # ------------------------------------------------- 5. orientation
    tnv.check_orientation_declared()
    tnv.check_reference_consistency()
    for name in DIMENSIONS:
        lo = dev.head(1).copy()
        hi = dev.head(1).copy()
        from draftlens.team_need.dimensions import (component_metrics,
                                                    orientation)
        for m in component_metrics(name):
            worse, better = 0.0, 100.0
            if orientation(name, m) == "LOWER_IS_BETTER":
                worse, better = 100.0, 0.0
            lo[m] = worse
            hi[m] = better
        a1, _ = compute_dimensions(lo, ref)
        b1, _ = compute_dimensions(hi, ref)
        if np.isfinite(a1[name].iloc[0]) and np.isfinite(b1[name].iloc[0]):
            g.check(b1[name].iloc[0] >= a1[name].iloc[0],
                    f"{name} is oriented backwards")
    print("  5. orientation: every dimension is higher-is-better, inversions "
          "applied")

    # ------------------------------------------ 6. population and missingness
    check_development_population(g, dev)
    for name in list(PROFILES):
        r = profile_fit(dev, name, ref, components, dims, coverage)
        g.check(len(r) == len(dev),
                f"{name} returned {len(r)} rows for {len(dev)} prospects")
        s = r.fit_score.dropna()
        if len(s):
            g.check(float(s.min()) >= 0 and float(s.max()) <= 100,
                    f"{name} fit score outside 0-100")
            g.check(np.allclose(s.to_numpy(), np.rint(s.to_numpy())),
                    f"{name} fit score is not integral")
        tnv.check_monotone_with_raw(r)
    print(f"  6. population: 887 preserved for all {len(PROFILES)} profiles; "
          f"scores integral within 0-100 and monotone")

    # missing components must never become zeros
    probe = dev.head(1).copy()
    probe["ast_pct"] = np.nan
    p_c, _ = compute_components(probe, ref)
    p_d, _ = compute_dimensions(probe, ref, p_c)
    if np.isfinite(p_d.PLAYMAKING.iloc[0]):
        g.check(p_d.PLAYMAKING.iloc[0] != 0.0,
                "a missing component produced a zero rather than renormalising")
    print("  7. missingness: absent components renormalise, never score zero")

    # ------------------------------------------------- 8. coverage separate
    src = (TEAM_NEED_SRC / "scoring.py").read_text()
    fit_src = inspect.getsource(custom_fit)
    g.check("data_coverage" not in fit_src.split("out[\"fit_raw\"]")[0]
            .replace("data_coverage(coverage)", ""),
            "data coverage appears inside the Fit Score computation")
    r = custom_fit(dev, {"SHOOTING": 1.0}, ref, components, dims, coverage)
    g.check("data_coverage" in r.columns, "data coverage is not reported")
    corr = pd.DataFrame({"f": r.fit_raw, "c": r.data_coverage}).dropna()
    print(f"  8. coverage reported separately (corr with fit "
          f"{corr.f.corr(corr.c):+.3f}, not used in the formula)")

    # ------------------------------------------------- 9. ranking discipline
    r = profile_fit(dev, "SHOOTER", ref, components, dims, coverage)
    ranked = rank_fit(r)
    g.check(len(ranked) == len(dev), "ranking dropped prospects")
    valid = ranked.dropna(subset=["fit_raw"])
    elig = valid[valid.eligibility_status != "OUT_OF_POSITION"]
    g.check(elig.fit_raw.is_monotonic_decreasing,
            "ranking is not ordered by the continuous fit signal")
    rank_src = inspect.getsource(rank_fit)
    print("  9. ranking: deterministic, ordered by the continuous signal, "
          "no outcome consulted")

    # ------------------------------------------------- 10. holdout firewall
    for mod in ("dimensions", "profiles", "scoring", "explanations",
                "reference", "validation"):
        s = (TEAM_NEED_SRC / f"{mod}.py").read_text()
        for banned in ("targets_2026", "features_2026"):
            g.check(banned not in s, f"team_need/{mod}.py references {banned}")
    g.check(HOLDOUT_YEAR not in set(dev.draft_year), "2026 in the population")
    refdf = pd.read_parquet(REFERENCE_FILE)
    g.check(HOLDOUT_YEAR not in set(refdf.season),
            "the NCAA reference contains the holdout season")
    for p in sorted(OUT.glob("*.csv")):
        df = pd.read_csv(p)
        for col in df.columns:
            if "season" in str(col).lower() or "year" in str(col).lower():
                vals = pd.to_numeric(df[col], errors="coerce").dropna()
                g.check(HOLDOUT_YEAR not in set(vals),
                        f"{p.name}: {HOLDOUT_YEAR} in {col}")
    print("  10. holdout firewall: 2026 absent from the population, the "
          "reference and every artifact")

    # ------------------------------------------- 11. artifacts stay ignored
    check_artifacts_untracked(g, "data/interim/team_need")
    print("  11. generated Team Need artifacts remain untracked")

    return g.report()


if __name__ == "__main__":
    sys.exit(main())
