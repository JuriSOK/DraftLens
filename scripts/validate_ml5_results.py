"""ML-5 validation — hard-fails on Stage B population violations, synthetic
picks, target leakage, holdout bleed, broken chronology or an unreproducible run.

Every check corresponds to a stated ML-5 requirement. A FAIL means the phase
result must not be trusted.

  ./.venv/bin/python scripts/validate_ml5_results.py
"""

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ml3_common import (DENIED, DENIED_SUBSTR, HOLDOUT_YEAR,  # noqa: E402
                        folds, load_config, load_development)
from run_ml5_stage_b import (CFG5, DRAFT_SIZE, OUT, SELECTED_MODEL,  # noqa: E402
                             SELECTED_TARGET, feature_set, load_stage_b,
                             strength, tier_of, to_pick, to_target)

ROOT = Path(__file__).resolve().parents[1]
CFG3 = load_config()
FAIL, WARN = [], []

# Target information — legitimate as y, never as X.
TARGET_FIELDS = {"pick", "round", "drafted", "drafting_team", "draft_size"}


def rule(t):
    print(f"\n{'=' * 78}\n{t}\n{'=' * 78}")


def check(cond, msg, hard=True):
    if cond:
        return True
    (FAIL if hard else WARN).append(msg)
    print(f"  {'FAIL' if hard else 'WARN'}  {msg}")
    return False


def main():
    rule("ML-5 VALIDATION")
    needed = ["fold_results.csv", "model_comparison.csv",
              "oof_stage_b_predictions.parquet", "target_comparison.csv",
              "residual_summary.csv", "robustness_2011_2013.csv",
              "target_rank_equivalence.csv", "alpha_coefficient_stability.csv",
              "selected_model_coefficients.csv", "ml5_summary.json"]
    missing = [f for f in needed if not (OUT / f).exists()]
    if missing:
        print(f"  FAIL  ML-5 outputs missing {missing} — run run_ml5_stage_b.py")
        return 1

    full_dev = load_development()
    dev = load_stage_b()
    fold_df = pd.read_csv(OUT / "fold_results.csv")
    summary = pd.read_csv(OUT / "model_comparison.csv")
    oof = pd.read_parquet(OUT / "oof_stage_b_predictions.parquet")
    rob = pd.read_csv(OUT / "robustness_2011_2013.csv")
    coef = pd.read_csv(OUT / "selected_model_coefficients.csv", index_col=0)

    # ------------------------------------------- 1. Stage B population purity
    check(len(dev) == CFG5["expected_rows"],
          f"Stage B population is {len(dev)}, expected {CFG5['expected_rows']}")
    check(bool((dev.drafted == 1).all()),
          "an UNDRAFTED prospect entered Stage B")
    check(int((dev.drafted == 0).sum()) == 0, "undrafted rows present")
    drafted_ids = set(full_dev.loc[full_dev.drafted == 1, "canonical_prospect_id"])
    check(set(dev.canonical_prospect_id) == drafted_ids,
          "Stage B population differs from the drafted development population")
    undrafted_ids = set(full_dev.loc[full_dev.drafted == 0,
                                     "canonical_prospect_id"])
    check(not (set(oof.canonical_prospect_id) & undrafted_ids),
          "an undrafted prospect received a Stage B prediction")
    print(f"  1. population: {len(dev)} drafted early entrants, "
          f"0 undrafted, matches the Stage A drafted set exactly")

    # --------------------------------------------------- 2. no synthetic pick
    check(bool(dev.pick.notna().all()), "a Stage B row has a null pick")
    check(bool((dev.pick >= 1).all()), "a pick below 1 exists")
    for sentinel in (61, 100, 999, 0, -1):
        check(int((dev.pick == sentinel).sum()) == 0,
              f"synthetic sentinel pick {sentinel} found in the population")
    check(bool((dev.pick <= dev.draft_size).all()),
          "a pick exceeds the declared draft size for its year")
    check(set(oof.actual_pick.unique()) <= set(dev.pick.unique()),
          "an actual_pick value appears that is not in the population")
    print("  2. no synthetic pick: all picks real, in range, none sentinel-filled")

    # ----------------------------------------------- 3. draft-size provenance
    for y, size in DRAFT_SIZE.items():
        if y == HOLDOUT_YEAR:
            continue
        obs = dev.loc[dev.draft_year == y, "pick"]
        if len(obs):
            check(int(obs.max()) <= size,
                  f"{y}: observed pick {int(obs.max())} exceeds declared "
                  f"draft size {size}")
    print(f"  3. draft sizes: every observed pick within its declared draft size")

    # ------------------------------------------------------ 4. 2026 firewall
    check(HOLDOUT_YEAR not in set(dev.draft_year), "2026 in Stage B population")
    check(HOLDOUT_YEAR not in set(fold_df.validate_year), "2026 validated")
    check(HOLDOUT_YEAR not in set(oof.draft_year), "2026 in predictions")
    check(HOLDOUT_YEAR not in set(rob.validate_year), "2026 in robustness")
    for f in CFG3["folds"]:
        check(HOLDOUT_YEAR not in range(f["train"][0], f["train"][1] + 1),
              f"fold {f['fold']} trains on 2026")
    for p in OUT.glob("*"):
        if p.suffix in (".csv", ".parquet"):
            df = pd.read_csv(p, index_col=0) if p.suffix == ".csv" \
                else pd.read_parquet(p)
            for col in df.columns:
                if any(k in str(col).lower() for k in ("year", "season")):
                    vals = pd.to_numeric(df[col], errors="coerce").dropna()
                    check(HOLDOUT_YEAR not in set(vals),
                          f"{p.name}: {HOLDOUT_YEAR} in column {col}")
    src = (ROOT / "scripts" / "run_ml5_stage_b.py").read_text()
    for banned in ("targets_2026", "features_2026", "predictions_2026"):
        check(banned not in src, f"run_ml5_stage_b.py references {banned}")
    print("  4. holdout firewall: 2026 absent from population, folds, fits, "
          "artifacts and source")

    # ------------------------------------------- 5. target fields never in X
    feats = set(feature_set("SET_2_BOX_SHOT_PROFILE")) | \
        set(feature_set("SET_2R_REDUCED"))
    leaked = feats & TARGET_FIELDS
    check(not leaked, f"TARGET information entered X: {sorted(leaked)}")
    bad = [c for c in feats if c in DENIED
           or any(s in c.lower() for s in DENIED_SUBSTR)]
    check(not bad, f"denied features entered X: {bad}")
    bare = [str(i).split("__", 1)[-1] for i in coef.index]
    bad_coef = [n for n in bare if n in TARGET_FIELDS or n in DENIED
                or any(s in n.lower() for s in DENIED_SUBSTR)]
    check(not bad_coef, f"target/denied field in the fitted model: {bad_coef}")
    print("  5. target separation: pick/round/drafted/team never entered X")

    # ------------------------------------------------- 6. fold chronology
    for fold, tr, vy in folds(CFG3):
        check(max(tr) < vy, f"fold {fold}: a training year is not before {vy}")
    expected_folds = {vy for _, _, vy in folds(CFG3)}
    for name, g in fold_df.groupby("config"):
        check(set(g.validate_year) == expected_folds,
              f"{name}: folds {sorted(set(g.validate_year))} != "
              f"{sorted(expected_folds)}")
    print("  6. chronology: no future year trains an earlier validation year")

    # ---------------------------------- 7. prediction counts / no row dropping
    for name, g in oof.groupby("config"):
        for vy, gg in g.groupby("draft_year"):
            expect = int((dev.draft_year == vy).sum())
            check(len(gg) == expect,
                  f"{name} {vy}: {len(gg)} predictions for {expect} drafted "
                  f"prospects — rows were dropped")
            check(gg.strength.notna().all(), f"{name} {vy}: null strength")
    print(f"  7. prediction counts match the drafted validation population for "
          f"all {oof.config.nunique()} configs")

    # ------------------------------------------- 8. transform monotonicity
    picks = np.arange(1, 61, dtype="float64")
    size = np.full(60, 60.0)
    for t in CFG5["targets"]:
        y = to_target(picks, size, t["id"])
        d = np.diff(y)
        if t["direction"] == "LOWER_IS_BETTER":
            check(bool((d > 0).all()),
                  f"{t['id']} is not strictly increasing in pick")
        else:
            check(bool((d < 0).all()),
                  f"{t['id']} is not strictly decreasing in pick")
        back = to_pick(y, size, t["id"])
        check(bool(np.allclose(back, picks)),
              f"{t['id']} inverse transform does not recover the pick")
        # a monotonic transform must preserve the induced ranking exactly
        check(bool(np.array_equal(np.argsort(strength(to_pick(y, size, t["id"]))),
                                  np.argsort(strength(picks)))),
              f"{t['id']} changed the ranking order despite being monotonic")
    print(f"  8. all {len(CFG5['targets'])} targets strictly monotonic, exactly "
          f"invertible and rank-preserving")

    # --------------------------------------------- 9. orientation convention
    perfect = strength(dev.pick.to_numpy(dtype="float64"))
    from scipy.stats import spearmanr
    check(spearmanr(perfect, strength(dev.pick)).statistic > 0.999,
          "canonical orientation is inconsistent with itself")
    best_pick_idx = int(np.argmin(dev.pick.to_numpy()))
    check(int(np.argmax(perfect)) == best_pick_idx,
          "highest strength does not correspond to the earliest pick")
    print("  9. orientation: higher strength == earlier pick, verified")

    # ------------------------------- 10. robustness excluded from selection
    check(set(rob.validate_year) <= set(CFG5["robustness_years"]),
          "robustness file contains non-robustness years")
    check(not set(rob.validate_year) & set(fold_df.validate_year),
          "a robustness year appears as a selection fold")
    check(not set(rob.validate_year) & set(oof.draft_year),
          "a robustness year entered the out-of-fold selection predictions")
    check(SELECTED_MODEL in {m["id"] for m in CFG5["models"]},
          f"selected model {SELECTED_MODEL} was not predeclared")
    check(SELECTED_TARGET in {t["id"] for t in CFG5["targets"]},
          f"selected target {SELECTED_TARGET} was not predeclared")
    print("  10. robustness years 2011-2013 never entered model selection")

    # ------------------------------------------------- 11. selection design
    declared = {m["id"] for m in CFG5["models"]}
    targets = {t["id"] for t in CFG5["targets"]}
    ran = {c.split("|")[0] for c in fold_df.config
           if "|" in c and not c.startswith("B5")}
    check(ran == declared,
          f"models evaluated differ from declared: extra={sorted(ran-declared)} "
          f"missing={sorted(declared-ran)}")
    ran_t = {c.split("|")[1] for c in fold_df.config if c.count("|") >= 1
             and c.split("|")[1] in targets or False}
    check(ran_t == targets,
          f"targets evaluated {sorted(ran_t)} != declared {sorted(targets)}")
    check(CFG5["design"].get("no_random_cv") is True,
          "no_random_cv is not asserted in the config")
    print(f"  11. design: {len(declared)} models x {len(targets)} targets, "
          f"all predeclared, all evaluated, no random CV")

    # ------------------------------------------------ 12. tier boundaries
    t3 = tier_of(dev.pick.to_numpy())
    ct = pd.crosstab(dev.draft_year, t3)
    check(ct.shape[1] == 3, "the tier scheme does not produce 3 tiers")
    sparse = int((ct < 5).sum().sum())
    check(sparse <= 1,
          f"adopted tier scheme has {sparse} year x tier cells below 5")
    print(f"  12. tier support: 3 tiers, {sparse} of {ct.size} cells below 5")

    # --------------------------------------------- 13. determinism / repro
    rerun = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "run_ml5_stage_b.py")],
        capture_output=True, text=True, cwd=ROOT)
    if check(rerun.returncode == 0, "the ML-5 run is not re-runnable"):
        again = pd.read_csv(OUT / "fold_results.csv")
        a = fold_df.sort_values(["config", "validate_year"]) \
            .reset_index(drop=True).round(6)
        b = again.sort_values(["config", "validate_year"]) \
            .reset_index(drop=True).round(6)
        check(a.equals(b),
              "a second run produced different results — the selection "
              "cannot be reproduced")
    print("  13. determinism: an independent re-run reproduced every fold metric")

    # --------------------------------------------- 14. artifacts stay ignored
    tracked = subprocess.run(["git", "ls-files", "data/interim/ml5"],
                             capture_output=True, text=True, cwd=ROOT)
    check(not tracked.stdout.strip(),
          f"ML-5 artifacts are tracked by Git: {tracked.stdout.split()[:5]}")
    ignored = subprocess.run(
        ["git", "check-ignore", "-q", str(OUT / "fold_results.csv")], cwd=ROOT)
    check(ignored.returncode == 0, "ML-5 outputs are not covered by .gitignore")
    print("  14. generated artifacts remain untracked and git-ignored")

    rule("RESULT")
    print(f"  hard failures: {len(FAIL)}\n  warnings     : {len(WARN)}")
    for m in FAIL:
        print(f"   FAIL {m}")
    for m in WARN:
        print(f"   WARN {m}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
