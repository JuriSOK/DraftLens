"""ML-4 validation — hard-fails on holdout bleed, leakage, population loss,
selection-design violations or an unreproducible run.

Every check below corresponds to a stated ML-4 requirement. A WARN is a
finding worth reading; a FAIL means the phase result must not be trusted.

  ./.venv/bin/python scripts/experiments/validate_ml4_stage_a.py
"""

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from draftlens.leakage import DENIED, DENIED_SUBSTR
from draftlens.ml.datasets import load_development
from draftlens.ml.validation import (HOLDOUT_YEAR, folds,
                                     load_fold_config as load_config)
from ml4_stage_a_selection import (CFG4, INCUMBENT, LOW_SUPPORT_YEAR, OUT,
                                   SELECTED, feature_set)


from draftlens.paths import ROOT  # noqa: E402
CFG3 = load_config()
FAIL, WARN = [], []

# ML-3 results that ML-4 must reproduce bit-for-bit (DEC-078 / DEC-079).
ML3_ANCHORS = {
    "B4_BENCHMARK": dict(macro_auc=0.6943, macro_ndcg=0.7171,
                         year_sd=0.0219, worst_year_auc=0.6727),
    INCUMBENT: dict(macro_auc=0.6809, pooled_auc=0.6865, macro_brier=0.2262,
                    year_sd=0.0339, worst_year_auc=0.6458),
}


def rule(t):
    print(f"\n{'=' * 78}\n{t}\n{'=' * 78}")


def check(cond, msg, hard=True):
    if cond:
        return True
    (FAIL if hard else WARN).append(msg)
    print(f"  {'FAIL' if hard else 'WARN'}  {msg}")
    return False


def main():
    rule("ML-4 VALIDATION")
    needed = ["candidate_results.csv", "model_comparison.csv",
              "outer_fold_predictions.parquet", "calibration_results.csv",
              "low_support_sensitivity.csv", "selected_model_coefficients.csv"]
    missing = [f for f in needed if not (OUT / f).exists()]
    if missing:
        print(f"  FAIL  ML-4 outputs missing {missing} — run ml4_stage_a_selection.py")
        return 1

    dev = load_development()
    fold_df = pd.read_csv(OUT / "candidate_results.csv")
    summary = pd.read_csv(OUT / "model_comparison.csv")
    oof = pd.read_parquet(OUT / "outer_fold_predictions.parquet")
    cal = pd.read_csv(OUT / "calibration_results.csv")
    coef = pd.read_csv(OUT / "selected_model_coefficients.csv", index_col=0)

    # ---------------------------------------------------- 1. holdout firewall
    check(HOLDOUT_YEAR not in set(dev.draft_year), "2026 present in development")
    check(HOLDOUT_YEAR not in set(fold_df.validate_year), "2026 validated")
    check(HOLDOUT_YEAR not in set(oof.draft_year), "2026 in predictions")
    check(HOLDOUT_YEAR not in set(cal.get("calibrator_fit_year", pd.Series())),
          "2026 used to fit a calibrator")
    for f in CFG3["folds"]:
        check(HOLDOUT_YEAR not in range(f["train"][0], f["train"][1] + 1),
              f"fold {f['fold']} trains on 2026")
    for p in OUT.glob("*"):
        if p.suffix in (".csv", ".parquet"):
            df = pd.read_csv(p, index_col=0) if p.suffix == ".csv" \
                else pd.read_parquet(p)
            for col in df.columns:
                if any(k in str(col) for k in ("year", "season")):
                    vals = pd.to_numeric(df[col], errors="coerce").dropna()
                    check(HOLDOUT_YEAR not in set(vals),
                          f"{p.name}: {HOLDOUT_YEAR} in column {col}")
    check(not any("2026" in str(c) for c in fold_df.columns),
          "a 2026 column exists in the results")
    print("  1. holdout firewall: 2026 absent from folds, fits and artifacts")

    # ------------------------------------------------- 2. temporal legitimacy
    for fold, tr, vy in folds(CFG3):
        check(max(tr) < vy, f"fold {fold}: a training year is not before {vy}")
    print("  2. temporal ordering: no future year trains an earlier fold")

    # --------------------------------------------- 3. calibration legitimacy
    if len(cal):
        check(bool(cal.strictly_earlier.all()),
              "a calibrator was fitted on data at or after its validation year")
        check((cal.calibrator_fit_year < cal.outer_validation_year).all(),
              "calibrator_fit_year >= outer_validation_year")
        print(f"  3. calibration: all {len(cal)} calibrator fits strictly "
              f"precede their validation year")
    else:
        check(False, "no calibration records were produced")

    # ---------------------------------------------------- 4. feature safety
    for name in ("SET_2_BOX_SHOT_PROFILE", "SET_2R_REDUCED"):
        feats = feature_set(name)
        bad = [c for c in feats if c in DENIED
               or any(s in c.lower() for s in DENIED_SUBSTR)]
        check(not bad, f"denied features entered {name}: {bad}")
    # The fitted model must not carry a denied column either. Compare on the
    # bare column name: DENIED holds exact names ("age"), and substring-matching
    # it would flag legitimate features such as usage_pct. Only DENIED_SUBSTR
    # is a substring rule.
    bare = [str(i).split("__", 1)[-1] for i in coef.index]
    bad_coef = [n for n in bare if n in DENIED
                or any(s in n.lower() for s in DENIED_SUBSTR)]
    check(not bad_coef, f"denied feature present in the fitted model: {bad_coef}")
    print("  4. feature safety: no denied feature reached X or the fitted model")

    # ------------------------------------------------- 5. population integrity
    check(len(dev) == 887, f"development population is {len(dev)}, expected 887")
    check(int(dev.drafted.sum()) == 431, "drafted count changed")
    check(int((dev.drafted == 0).sum()) == 456, "undrafted count changed")
    unresolved = int(dev.hoopr_athlete_id.isna().sum())
    check(unresolved >= 8, f"unresolved prospects lost ({unresolved})")
    print(f"  5. population: 887 / 431 / 456, unresolved retained {unresolved}")

    # ------------------------------------ 6. no complete-case deletion anywhere
    for name, g in oof.groupby("config"):
        for vy, gg in g.groupby("draft_year"):
            expect = int((dev.draft_year == vy).sum())
            check(len(gg) == expect,
                  f"{name} {vy}: {len(gg)} predictions for {expect} prospects")
            check(gg.p.notna().all(), f"{name} {vy}: null predictions")
            check(((gg.p >= 0) & (gg.p <= 1)).all(),
                  f"{name} {vy}: predictions outside [0,1]")
    unresolved_ids = set(dev[dev.hoopr_athlete_id.isna()].canonical_prospect_id)
    validated = set(fold_df.validate_year)
    eligible = {i for i in unresolved_ids
                if dev.loc[dev.canonical_prospect_id == i, "draft_year"].iloc[0]
                in validated}
    for name, g in oof.groupby("config"):
        check(eligible <= set(g.canonical_prospect_id),
              f"{name}: unresolved prospects were dropped")
    print(f"  6. prediction counts complete for {oof.config.nunique()} configs; "
          f"{len(eligible)} unresolved prospects retained")

    # ------------------------------------------- 7. ML-3 anchors must not move
    idx = summary.set_index("config")
    for cfg, expected in ML3_ANCHORS.items():
        if not check(cfg in idx.index, f"{cfg} missing from the comparison"):
            continue
        for metric, want in expected.items():
            got = float(idx.loc[cfg, metric])
            check(abs(got - want) < 5e-4,
                  f"{cfg}.{metric} = {got}, ML-3 recorded {want} "
                  f"— an ML-3 result changed")
    print("  7. ML-3 anchors reproduced: B4 benchmark and incumbent unchanged")

    # ------------------------------------------------- 8. selection design
    check(CFG4["selection_design"]["chosen"] == "PREDECLARED_FIXED_CONFIGURATIONS",
          "selection design is not the predeclared one")
    check(CFG4["selection_design"].get("no_random_cv") is True,
          "no_random_cv is not asserted in the config")
    declared = [c["id"] for c in CFG4["candidates"]]
    check(len(declared) == len(set(declared)), "duplicate candidate ids")
    ran = {c.split("+")[0] for c in fold_df.config} - {"B4_BENCHMARK"}
    check(ran == set(declared),
          f"configurations evaluated differ from those declared: "
          f"extra={sorted(ran - set(declared))} "
          f"missing={sorted(set(declared) - ran)}")
    check(SELECTED in declared, f"the selected model {SELECTED} was not declared")
    print(f"  8. selection design: {len(declared)} predeclared configs, "
          f"all evaluated, none added after the fact")

    # ------------------------------------------------ 9. fold coverage / flags
    expected_folds = {vy for _, _, vy in folds(CFG3)}
    for name, g in fold_df.groupby("config"):
        check(set(g.validate_year) == expected_folds,
              f"{name}: evaluated on {sorted(set(g.validate_year))}, "
              f"expected {sorted(expected_folds)}")
    ls = fold_df[fold_df.validate_year == LOW_SUPPORT_YEAR].low_negative_support
    check(bool(ls.all()), f"{LOW_SUPPORT_YEAR} not flagged LOW NEGATIVE SUPPORT")
    others = fold_df[fold_df.validate_year != LOW_SUPPORT_YEAR]
    check(not others.low_negative_support.any(),
          "a year other than 2025 was flagged low support")
    print(f"  9. every config ran all {len(expected_folds)} folds; "
          f"{LOW_SUPPORT_YEAR} flagged LOW NEGATIVE SUPPORT")

    # ------------------------------------------------ 10. determinism / repro
    rerun = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "experiments" / "ml4_stage_a_selection.py")],
        capture_output=True, text=True, cwd=ROOT)
    if check(rerun.returncode == 0, "the ML-4 run is not re-runnable"):
        again = pd.read_csv(OUT / "candidate_results.csv")
        same = (fold_df.sort_values(["config", "validate_year"])
                .reset_index(drop=True).round(6))
        new = (again.sort_values(["config", "validate_year"])
               .reset_index(drop=True).round(6))
        check(same.equals(new),
              "a second run produced different results — the run is not "
              "deterministic and the selection cannot be reproduced")
    print("  10. determinism: an independent re-run reproduced every fold metric")

    # ---------------------------------------------- 11. artifacts stay ignored
    tracked = subprocess.run(["git", "ls-files", "data/interim/ml4"],
                             capture_output=True, text=True, cwd=ROOT)
    check(not tracked.stdout.strip(),
          f"ML-4 artifacts are tracked by Git: {tracked.stdout.split()[:5]}")
    ignored = subprocess.run(
        ["git", "check-ignore", "-q", str(OUT / "candidate_results.csv")],
        cwd=ROOT)
    check(ignored.returncode == 0, "ML-4 outputs are not covered by .gitignore")
    print("  11. generated artifacts remain untracked and git-ignored")

    rule("RESULT")
    print(f"  hard failures: {len(FAIL)}\n  warnings     : {len(WARN)}")
    for m in FAIL:
        print(f"   FAIL {m}")
    for m in WARN:
        print(f"   WARN {m}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
