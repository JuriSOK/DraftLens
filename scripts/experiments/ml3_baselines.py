"""ML-3 — temporal baselines and preprocessing experiment.

HISTORICAL EVIDENCE. Reproduces docs/experiments/ML3_BASELINES.md and the
DEC-078 / DEC-079 anchors.

ORIGINAL: — temporal baselines and preprocessing experiments (Stage A).

Establishes reproducible expanding-window validation, the five ML_SPEC §15
baselines, and a small named grid of preprocessing choices. The goal is
methodological orientation, not leaderboard performance.

2026 is never loaded, never predicted, never evaluated.

  ./.venv/bin/python scripts/experiments/ml3_baselines.py

Outputs (git-ignored) -> data/interim/ml3/
"""

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from draftlens.leakage import DENIED, DENIED_SUBSTR
from draftlens.ml.baselines import (COMPOSITE_COLS, b0_prevalence,
                                    b1_scoring_only, b2_standardised_composite,
                                    b4_position_percentile_composite)
from draftlens.ml.datasets import (load_development, load_robustness,
                                   resolve_features)
from draftlens.ml.metrics import board_metrics, calibration_bins, stage_a_metrics
from draftlens.ml.preprocessing import make_pipeline, position_median_impute
from draftlens.ml.validation import (HOLDOUT_YEAR, assert_no_holdout, folds,
                                     load_fold_config as load_config)
from draftlens.paths import interim

CFG = load_config()
SEED = CFG["seed"]
LOW = CFG["low_negative_support_threshold"]


def log(m=""):
    print(m, flush=True)


def rule(t):
    log(f"\n{'=' * 78}\n{t}\n{'=' * 78}")


def ks_for(valid):
    return {"drafted": int(valid.drafted.sum()),
            "top25": math.ceil(0.25 * len(valid))}


# --------------------------------------------------------------- experiments
def named_configs():
    """Small, predeclared grid. No search — every configuration is named."""
    cfgs = []
    for fs in ["SET_0_MINIMAL", "SET_1_BOX_EFFICIENCY",
               "SET_2_BOX_SHOT_PROFILE", "SET_3_BROADER_CLEAN"]:
        for cw in [None, "balanced"]:
            cfgs.append(dict(name=f"LR|{fs}|B_TRAIN_MEDIAN|STANDARD|ONEHOT|"
                                  f"{cw or 'none'}|C=1.0",
                             feature_set=fs, strategy="B_TRAIN_MEDIAN",
                             scaling="STANDARD", position="ONEHOT",
                             class_weight=cw, C=1.0))
    cfgs.append(dict(name="LR|SET_3_BROADER_CLEAN|A_CONSERVATIVE_EXCLUSION|"
                          "STANDARD|ONEHOT|balanced|C=1.0",
                     feature_set="SET_3_BROADER_CLEAN",
                     strategy="A_CONSERVATIVE_EXCLUSION", scaling="STANDARD",
                     position="ONEHOT", class_weight="balanced", C=1.0))
    base = "SET_2_BOX_SHOT_PROFILE"
    variants = [
        ("A_CONSERVATIVE_EXCLUSION", "STANDARD", "ONEHOT", None, 1.0),
        ("B2_POSITION_MEDIAN", "STANDARD", "ONEHOT", None, 1.0),
        ("C_HIGH_COVERAGE", "STANDARD", "ONEHOT", None, 1.0),
        ("B_TRAIN_MEDIAN", "NONE", "ONEHOT", None, 1.0),
        ("B_TRAIN_MEDIAN", "STANDARD", "NONE", None, 1.0),
        ("B_TRAIN_MEDIAN", "STANDARD", "ONEHOT", None, 0.1),
    ]
    for strat, sc, pos, cw, C in variants:
        cfgs.append(dict(name=f"LR|{base}|{strat}|{sc}|{pos}|"
                              f"{cw or 'none'}|C={C}",
                         feature_set=base, strategy=strat, scaling=sc,
                         position=pos, class_weight=cw, C=C))
    return cfgs


def run_baseline(name, fn, dev, fold_list, rows, oof):
    for fold, tr_years, vy in fold_list:
        train = assert_no_holdout(dev[dev.draft_year.isin(tr_years)], "train")
        valid = assert_no_holdout(dev[dev.draft_year == vy], "validate")
        p = fn(train, valid)
        m = stage_a_metrics(valid.drafted, p, LOW)
        m.update(board_metrics(valid.drafted, p, ks_for(valid)))
        rows.append(dict(config=name, kind="baseline", fold=fold,
                         train_years=f"{tr_years[0]}-{tr_years[-1]}",
                         validate_year=vy, **m))
        oof.append(pd.DataFrame({"config": name, "draft_year": vy,
                                 "canonical_prospect_id":
                                     valid.canonical_prospect_id.values,
                                 "y": valid.drafted.values, "p": p}))


def run_lr(cfg, dev, fold_list, rows, oof, coefs):
    for fold, tr_years, vy in fold_list:
        train = assert_no_holdout(dev[dev.draft_year.isin(tr_years)].copy(),
                                  "train").reset_index(drop=True)
        valid = assert_no_holdout(dev[dev.draft_year == vy].copy(),
                                  "validate").reset_index(drop=True)
        feats = resolve_features(CFG, cfg["feature_set"], train,
                                 cfg["strategy"])
        if not feats:
            continue
        if cfg["strategy"] == "B2_POSITION_MEDIAN":
            train, valid = position_median_impute(train, valid, feats)
        pipe = make_pipeline(feats, cfg["strategy"], cfg["position"],
                             cfg["scaling"], cfg["class_weight"], cfg["C"],
                             SEED)
        pipe.fit(train, train.drafted)
        p = pipe.predict_proba(valid)[:, 1]
        m = stage_a_metrics(valid.drafted, p, LOW)
        m.update(board_metrics(valid.drafted, p, ks_for(valid)))
        rows.append(dict(config=cfg["name"], kind="model", fold=fold,
                         train_years=f"{tr_years[0]}-{tr_years[-1]}",
                         validate_year=vy, n_features=len(feats), **m))
        oof.append(pd.DataFrame({"config": cfg["name"], "draft_year": vy,
                                 "canonical_prospect_id":
                                     valid.canonical_prospect_id.values,
                                 "y": valid.drafted.values, "p": p}))
        if vy == max(f[2] for f in fold_list):
            clf = pipe.named_steps["clf"]
            names = list(feats)
            if cfg["position"] == "ONEHOT":
                names += list(pipe.named_steps["pre"]
                              .named_transformers_["pos"]
                              .get_feature_names_out(["position_3"]))
            for nm, c in zip(names, clf.coef_[0]):
                coefs.append(dict(config=cfg["name"], feature=nm,
                                  coefficient=round(float(c), 4)))


def aggregate(fold_df, oof_df):
    """Year-macro (equal weight per year) and pooled (all OOF predictions)."""
    macro = (fold_df.groupby("config")
             .agg(folds=("fold", "size"),
                  macro_roc_auc=("roc_auc", "mean"),
                  macro_pr_auc=("pr_auc", "mean"),
                  macro_log_loss=("log_loss", "mean"),
                  macro_brier=("brier", "mean"),
                  roc_auc_sd=("roc_auc", "std"),
                  worst_roc_auc=("roc_auc", "min"),
                  macro_prec_at_drafted=("precision_at_drafted", "mean"),
                  macro_ndcg_at_drafted=("ndcg_at_drafted", "mean"))
             .round(4).reset_index())
    pooled = []
    for name, g in oof_df.groupby("config"):
        m = stage_a_metrics(g.y, g.p, LOW)
        pooled.append(dict(config=name, pooled_roc_auc=m["roc_auc"],
                           pooled_pr_auc=m["pr_auc"],
                           pooled_log_loss=m["log_loss"],
                           pooled_brier=m["brier"]))
    return macro.merge(pd.DataFrame(pooled), on="config")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    dev = load_development()
    fold_list = folds(CFG)

    rule("POPULATION & FOLDS")
    log(f"  development rows: {len(dev)} "
        f"(drafted {int(dev.drafted.sum())}, "
        f"undrafted {int((dev.drafted == 0).sum())})")
    log(f"  unresolved prospects retained: "
        f"{int(dev.hoopr_athlete_id.isna().sum())}")
    for fold, tr, vy in fold_list:
        v = dev[dev.draft_year == vy]
        flag = " <- LOW NEGATIVE SUPPORT" if int((v.drafted == 0).sum()) < LOW else ""
        log(f"  fold {fold}: train {tr[0]}-{tr[-1]} "
            f"(n={int(dev.draft_year.isin(tr).sum())})  validate {vy} "
            f"(n={len(v)}, drafted={int(v.drafted.sum())}, "
            f"undrafted={int((v.drafted == 0).sum())}){flag}")

    rows, oof, coefs = [], [], []

    rule("BASELINES (ML_SPEC §15)")
    for name, fn in [("B0_PREVALENCE", b0_prevalence),
                     ("B1_SCORING_ONLY", b1_scoring_only),
                     ("B2_STANDARDISED_COMPOSITE", b2_standardised_composite),
                     ("B4_POSITION_PERCENTILE_COMPOSITE",
                      b4_position_percentile_composite)]:
        run_baseline(name, fn, dev, fold_list, rows, oof)
        log(f"  ran {name}")

    rule("LOGISTIC REGRESSION CONFIGURATIONS")
    cfgs = named_configs()
    log(f"  {len(cfgs)} named configurations x {len(fold_list)} folds")
    for c in cfgs:
        run_lr(c, dev, fold_list, rows, oof, coefs)

    fold_df = pd.DataFrame(rows)
    oof_df = pd.concat(oof, ignore_index=True)
    fold_df.to_csv(OUT / "fold_results.csv", index=False)
    oof_df.to_parquet(OUT / "oof_predictions.parquet", index=False)
    pd.DataFrame(coefs).to_csv(OUT / "logreg_coefficients.csv", index=False)

    summary = aggregate(fold_df, oof_df)
    summary = summary.sort_values("macro_roc_auc", ascending=False)
    summary.to_csv(OUT / "configuration_summary.csv", index=False)

    rule("CONFIGURATION SUMMARY (sorted by year-macro ROC-AUC)")
    show = ["config", "macro_roc_auc", "pooled_roc_auc", "macro_pr_auc",
            "macro_brier", "roc_auc_sd", "worst_roc_auc",
            "macro_ndcg_at_drafted"]
    log(summary[show].to_string(index=False, max_colwidth=52))

    rule("PER-FOLD DETAIL — BASELINES + BEST LR")
    best = summary.iloc[0].config
    sel = fold_df[fold_df.config.isin(
        ["B0_PREVALENCE", "B1_SCORING_ONLY", "B2_STANDARDISED_COMPOSITE",
         "B4_POSITION_PERCENTILE_COMPOSITE", best])]
    log(sel[["config", "validate_year", "n", "drafted", "undrafted",
             "base_rate", "roc_auc", "pr_auc", "log_loss", "brier",
             "low_negative_support"]].to_string(index=False, max_colwidth=44))

    rule("CALIBRATION (out-of-fold, development)")
    cal_rows = []
    for name in ["B0_PREVALENCE", "B2_STANDARDISED_COMPOSITE", best]:
        g = oof_df[oof_df.config == name]
        cb = calibration_bins(g.y, g.p)
        cb.insert(0, "config", name)
        cal_rows.append(cb)
        log(f"\n  {name}")
        log(cb[["bin", "n", "mean_pred", "observed", "gap"]]
            .to_string(index=False))
    pd.concat(cal_rows, ignore_index=True).to_csv(OUT / "calibration_bins.csv",
                                                  index=False)

    rule("LOGISTIC REGRESSION COEFFICIENT SANITY (final fold)")
    model_summary = summary[summary.config.str.startswith("LR|")]
    best_lr = model_summary.iloc[0].config
    log(f"  best LR by year-macro ROC-AUC: {best_lr}\n")
    cdf = pd.DataFrame(coefs)
    sub = cdf[cdf.config == best_lr]
    cb = sub.reindex(sub.coefficient.abs().sort_values(ascending=False).index)
    log(cb.head(12)[["feature", "coefficient"]].to_string(index=False))
    rep_best_lr = best_lr

    rule("ROBUSTNESS 2011-2013 (secondary; not used for selection)")
    rob = robustness_check(dev, best_lr, cfgs)
    log(rob.to_string(index=False))
    rob.to_csv(OUT / "robustness_2011_2013.csv", index=False)

    rule("STAGE B — ML_SPEC §15 BASELINE 5 (descriptive only)")
    sb = stage_b_naive_pick(dev, fold_list)
    log(sb.to_string(index=False))
    sb.to_csv(OUT / "stage_b_naive_pick.csv", index=False)

    rep = dict(sklearn_seed=SEED, best_lr=rep_best_lr,
               development_rows=len(dev),
               unresolved_retained=int(dev.hoopr_athlete_id.isna().sum()),
               n_configs=len(summary), n_folds=len(fold_list),
               best_by_macro_roc_auc=best,
               summary=summary.head(8).to_dict("records"))
    (OUT / "ml3_summary.json").write_text(json.dumps(rep, indent=2,
                                                     default=str))
    log(f"\n  outputs -> {OUT}")
    return 0


def robustness_check(dev, best_lr_name, cfgs):
    """Apply the SELECTED configuration to 2011-2013 as a secondary check.

    Trains on the full 2014-2025 development window and validates on the
    earlier robustness years. Those years are NEVER used to choose the
    configuration; this only reports how it behaves there.
    """
    from draftlens.ml.metrics import stage_a_metrics as _m
    cfg = next(c for c in cfgs if c["name"] == best_lr_name)
    rob = load_robustness()
    rows = []
    train = dev.reset_index(drop=True)
    feats = resolve_features(CFG, cfg["feature_set"], train, cfg["strategy"])
    pipe = make_pipeline(feats, cfg["strategy"], cfg["position"],
                         cfg["scaling"], cfg["class_weight"], cfg["C"], SEED)
    pipe.fit(train, train.drafted)
    for y, g in rob.groupby("draft_year"):
        p = pipe.predict_proba(g)[:, 1]
        m = _m(g.drafted, p, LOW)
        m.update(board_metrics(g.drafted, p, ks_for(g)))
        rows.append(dict(validate_year=int(y), **{k: m[k] for k in
                    ("n", "drafted", "undrafted", "base_rate", "roc_auc",
                     "pr_auc", "log_loss", "brier",
                     "precision_at_drafted", "ndcg_at_drafted")}))
    return pd.DataFrame(rows)


def stage_b_naive_pick(dev, fold_list):
    """ML_SPEC §15 baseline (5): naive mean historical pick by position_3.
    Simple and deliberately un-optimised. Drafted prospects only."""
    rows = []
    for fold, tr_years, vy in fold_list:
        tr = dev[(dev.draft_year.isin(tr_years)) & (dev.drafted == 1)]
        va = dev[(dev.draft_year == vy) & (dev.drafted == 1)].dropna(
            subset=["pick"])
        if len(va) < 5:
            continue
        gmean = float(tr["pick"].mean())
        pmean = tr.groupby("position_3")["pick"].mean()
        pred = va.position_3.map(pmean).fillna(gmean).astype(float)
        actual = va["pick"].astype(float)
        rho = float(pred.rank().corr(actual.rank())) if pred.nunique() > 1 else np.nan
        rows.append(dict(fold=fold, validate_year=vy, n_drafted=len(va),
                         mae=round(float((pred - actual).abs().mean()), 2),
                         rmse=round(float(np.sqrt(((pred - actual) ** 2)
                                                  .mean())), 2),
                         spearman=round(rho, 4) if rho == rho else None))
    return pd.DataFrame(rows)


if __name__ == "__main__":
    sys.exit(main())
