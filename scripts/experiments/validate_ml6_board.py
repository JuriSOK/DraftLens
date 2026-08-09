"""ML-6 validation — hard-fails on a changed frozen stage, a dropped prospect,
a broken score, target leakage into the scoring path, or holdout bleed.

Shared assertions come from draftlens.ml.guards; only board-specific rules
live here.

  ./.venv/bin/python scripts/experiments/validate_ml6_board.py
"""

import inspect
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from draftlens.ml import board as board_mod
from draftlens.ml.board import (BOARD, build_board, combine_board_signals,
                                graded_relevance, load_config, overall_score,
                                transform_stage_b_signal)
from draftlens.ml.datasets import load_development
from draftlens.ml.guards import (Guard, check_artifacts_holdout_free,
                                 check_artifacts_untracked, check_chronology,
                                 check_development_population,
                                 check_source_never_loads_holdout)
from draftlens.ml.stage_a import STAGE_A
from draftlens.ml.stage_b import STAGE_B, draft_sizes
from draftlens.ml.validation import HOLDOUT_YEAR, folds
from draftlens.paths import ROOT, interim

OUT = interim("ml6")
CFG6 = load_config()

# Frozen stage anchors ML-6 is forbidden to move.
STAGE_A_ANCHOR = {"family": "LogisticRegression",
                  "feature_set": "SET_2_BOX_SHOT_PROFILE",
                  "normalization": "SEASON_RELATIVE", "class_weight": "balanced",
                  "C": 0.25, "calibration": "none"}
STAGE_B_ANCHOR = {"family": "Ridge", "alpha": 10.0, "target": "RAW_PICK",
                  "normalization": "STANDARD"}


def rule(t):
    print(f"\n{'=' * 78}\n{t}\n{'=' * 78}")


def main():
    rule("ML-6 VALIDATION")
    needed = ["oof_board.parquet", "board_fold_results.csv",
              "board_method_comparison.csv", "incremental_value.csv",
              "stage_b_extrapolation_audit.csv", "ml6_summary.json"]
    missing = [f for f in needed if not (OUT / f).exists()]
    if missing:
        print(f"  FAIL  ML-6 outputs missing {missing} — run "
              f"scripts/experiments/ml6_board_selection.py")
        return 1

    g = Guard()
    dev = load_development()
    oof = pd.read_parquet(OUT / "oof_board.parquet")
    fold_df = pd.read_csv(OUT / "board_fold_results.csv")

    # ------------------------------------------- 1. frozen stages unchanged
    for k, want in STAGE_A_ANCHOR.items():
        g.check(STAGE_A[k] == want,
                f"Stage A {k} is {STAGE_A[k]}, frozen value is {want}")
    for k, want in STAGE_B_ANCHOR.items():
        g.check(STAGE_B[k] == want,
                f"Stage B {k} is {STAGE_B[k]}, frozen value is {want}")
    g.check(STAGE_B["normalization"] == "STANDARD",
            "Stage B was switched to SEASON_RELATIVE — prohibited (DEC-095)")
    print("  1. frozen stages: Stage A and Stage B configurations unchanged")

    # ----------------------------------------------- 2. population integrity
    check_development_population(g, dev)
    expected_oof = int(dev.draft_year.isin(
        [vy for _, _, vy in folds()]).sum())
    g.check(len(oof) == expected_oof,
            f"board has {len(oof)} out-of-fold rows, expected {expected_oof}")
    g.check(oof.canonical_prospect_id.nunique() == len(oof),
            "duplicate prospects on the board")
    for vy, grp in oof.groupby("draft_year"):
        want = int((dev.draft_year == vy).sum())
        g.check(len(grp) == want,
                f"{vy}: board has {len(grp)} prospects, population has {want} "
                f"— the board dropped prospects")
    print(f"  2. population: 887 development / {len(oof)} out-of-fold, "
          f"no prospect dropped from any board")

    # ------------------------------------------------------ 3. 2026 firewall
    g.check(HOLDOUT_YEAR not in set(dev.draft_year), "2026 in development")
    g.check(HOLDOUT_YEAR not in set(oof.draft_year), "2026 on the board")
    g.check(HOLDOUT_YEAR not in set(fold_df.validate_year), "2026 evaluated")
    check_artifacts_holdout_free(g, OUT)
    check_source_never_loads_holdout(
        g, ROOT / "src" / "draftlens" / "ml" / "board.py",
        ROOT / "scripts" / "run_board.py",
        ROOT / "scripts" / "experiments" / "ml6_board_selection.py")
    g.check(CFG6["holdout_year"] == HOLDOUT_YEAR,
            "config declares the wrong holdout year")
    print("  3. holdout firewall: 2026 absent from population, board, "
          "artifacts and source")

    check_chronology(g)
    print("  4. chronology: no future year trains an earlier validation year")

    # -------------------------------- 5. no target leakage into the scoring path
    params = set(inspect.signature(build_board).parameters)
    for banned in ("drafted", "pick", "actual_pick", "actual_drafted",
                   "relevance", "y", "target"):
        g.check(banned not in params,
                f"build_board accepts target information: {banned}")
    src = inspect.getsource(build_board)
    g.check("graded_relevance" not in src,
            "the scoring path can reach evaluation relevance")
    b = build_board(np.array([0.5, 0.9]), np.array([30.0, 5.0]),
                    np.full(2, 60.0))
    for banned in ("drafted", "pick", "actual_drafted", "actual_pick"):
        g.check(banned not in b.columns,
                f"build_board output carries target column {banned}")
    print("  5. target separation: production scoring needs only pre-draft "
          "inputs")

    # ------------------------------------------------- 6. no synthetic pick
    rel = graded_relevance(oof.actual_drafted, oof.actual_pick, oof.draft_size
                           if "draft_size" in oof else
                           oof.draft_year.map(draft_sizes()))
    und = (oof.actual_drafted == 0).to_numpy()
    g.check(bool(np.all(rel[und] == 0.0)),
            "an undrafted prospect received non-zero graded relevance")
    g.check(bool(oof.loc[oof.actual_drafted == 0, "actual_pick"].isna().all()),
            "an undrafted prospect was given a pick value")
    dr = oof[oof.actual_drafted == 1]
    for sentinel in (0, 61, 100, 999):
        g.check(int((dr.actual_pick == sentinel).sum()) == 0,
                f"synthetic sentinel pick {sentinel} present")
    print("  6. no synthetic pick: undrafted keep pick=NULL and relevance=0")

    # ---------------------------------------------- 7. board signal integrity
    g.check(bool(np.isfinite(oof.final_board_signal).all()),
            "the board signal contains NaN or inf")
    g.check(bool(np.isfinite(oof.stage_a_probability).all()),
            "Stage A produced a non-finite probability")
    stage_a_ok = np.isfinite(oof.stage_a_probability)
    g.check(bool(np.isfinite(oof.final_board_signal[stage_a_ok]).all()),
            "a prospect Stage A could score has no board signal — Stage B "
            "failure must not remove a prospect from the board")
    g.check(bool(((oof.stage_a_probability >= 0)
                  & (oof.stage_a_probability <= 1)).all()),
            "Stage A probability outside [0, 1]")
    print("  7. board signal: finite for every prospect Stage A can score")

    # ------------------------------------------------------ 8. Overall Score
    g.check(bool(((oof.overall_score >= 0) & (oof.overall_score <= 100)).all()),
            "Overall Score outside 0-100")
    g.check(str(oof.overall_score.dtype).startswith("int"),
            f"Overall Score is {oof.overall_score.dtype}, must be integer")
    for vy, grp in oof.groupby("draft_year"):
        o = grp.sort_values("final_board_signal", ascending=False)
        g.check(bool(o.overall_score.is_monotonic_decreasing),
                f"{vy}: Overall Score order disagrees with the board signal")
        # equal signals must receive equal scores
        for sig, sub in o.groupby("final_board_signal"):
            g.check(sub.overall_score.nunique() == 1,
                    f"{vy}: equal board signals received different scores")
    print(f"  8. Overall Score: integer, within 0-100, order matches the board "
          f"in all {oof.draft_year.nunique()} classes")

    # --------------------------------------- 9. selection discipline / config
    methods = [m["id"] for m in CFG6["board_methods"]]
    transforms = [t["id"] for t in CFG6["stage_b_transforms"]]
    g.check(BOARD["method"] in methods,
            f"selected method {BOARD['method']} was not predeclared")
    g.check(BOARD["stage_b_transform"] in transforms,
            f"selected transform {BOARD['stage_b_transform']} not predeclared")
    g.check("A_STAGE_A_ONLY" in methods,
            "the Stage A-only reference board is not among the candidates")
    ran = {c.split("|")[0] for c in fold_df.config}
    g.check(ran == set(methods),
            f"methods evaluated {sorted(ran)} != declared {sorted(methods)}")
    src6 = (ROOT / "src" / "draftlens" / "ml" / "board.py").read_text()
    for banned in ("0.3 *", "0.7 *", "0.6 *", "0.4 *", "0.2 *", "0.8 *"):
        g.check(banned not in src6,
                f"board.py contains what looks like a tuned blend weight: "
                f"{banned}")
    print(f"  9. selection discipline: {len(methods)} predeclared methods, "
          f"Stage A-only retained, no tuned blend weight")

    # ------------------------------------------------ 10. score monotonicity
    rng = np.random.default_rng(0)
    sig = rng.uniform(size=500)
    sc = overall_score(sig)
    order = np.argsort(-sig)
    g.check(bool(np.all(np.diff(sc[order]) <= 0)),
            "overall_score is not monotone in the board signal")
    q = transform_stage_b_signal(np.array([5.0, 25.0, 45.0]),
                                 np.full(3, 60.0), BOARD["stage_b_transform"])
    g.check(bool(np.all(np.diff(q) < 0)),
            "the Stage B transform is not higher-is-better")
    comb = combine_board_signals(np.array([0.2, 0.8]), np.array([0.5, 0.5]),
                                 BOARD["method"])
    g.check(comb[1] > comb[0],
            "the board signal is not increasing in Stage A probability")
    print("  10. monotonicity: transform, combination and score all "
          "order-preserving")

    # ----------------------------------------------- 11. determinism / repro
    before = pd.read_csv(OUT / "board_fold_results.csv")
    rerun = subprocess.run(
        [sys.executable,
         str(ROOT / "scripts" / "experiments" / "ml6_board_selection.py")],
        capture_output=True, text=True, cwd=ROOT)
    if g.check(rerun.returncode == 0,
               f"the ML-6 run is not re-runnable:\n{rerun.stderr[-1500:]}"):
        after = pd.read_csv(OUT / "board_fold_results.csv")
        a = before.sort_values(["config", "validate_year"]).reset_index(drop=True)
        b2 = after.sort_values(["config", "validate_year"]).reset_index(drop=True)
        g.check(a.round(6).equals(b2.round(6)),
                "a second run produced different board results")
    print("  11. determinism: an independent re-run reproduced every fold metric")

    # -------------------------------------------- 12. artifacts stay ignored
    check_artifacts_untracked(g, "data/interim/ml6")
    ignored = subprocess.run(
        ["git", "check-ignore", "-q", str(OUT / "oof_board.parquet")], cwd=ROOT)
    g.check(ignored.returncode == 0,
            "ML-6 board artifacts are not covered by .gitignore")
    print("  12. generated board artifacts remain untracked and git-ignored")

    return g.report()


if __name__ == "__main__":
    sys.exit(main())
