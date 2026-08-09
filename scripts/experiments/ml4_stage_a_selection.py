"""ML-4 — Stage A candidate-model selection experiment.

HISTORICAL EVIDENCE. This reproduces the experiment that selected the frozen
Stage A methodology (DEC-080..085) and the numbers in
docs/experiments/ML4_STAGE_A.md. The selection itself lives in
`draftlens.ml.stage_a.STAGE_A`; this script must not be used to change it.

Evaluates a small PREDECLARED set of configurations — no search, no random CV.
2026 is never loaded, predicted or evaluated.

  ./.venv/bin/python scripts/experiments/ml4_stage_a_selection.py

Outputs (git-ignored) -> data/interim/ml4/
"""

import json
import math
import sys

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression

from draftlens.leakage import DENIED, DENIED_SUBSTR
from draftlens.ml.baselines import b4_position_percentile_composite
from draftlens.ml.datasets import load_development, load_robustness
from draftlens.ml.metrics import (board_metrics, calibration_bins,
                                  expected_calibration_error, stage_a_metrics)
from draftlens.ml.preprocessing import season_relative
from draftlens.ml.stage_a import build_estimator, build_pipeline, feature_set
from draftlens.ml.validation import (HOLDOUT_YEAR, LOW_SUPPORT_YEAR,
                                     assert_no_holdout, folds,
                                     load_fold_config)
from draftlens.paths import CONFIG_ML, interim

CFG4 = json.loads((CONFIG_ML / "stage_a.json").read_text())
CFG3 = load_fold_config()
OUT = interim("ml4")
SEED = CFG4["seed"]
LOW = CFG3["low_negative_support_threshold"]
INCUMBENT = "LR_C1.0_INCUMBENT"       # ML-3 selection (DEC-078)
SELECTED = "LR_SEASONREL_C0.25"       # ML-4 selection (DEC-081)


def log(m=""):
    print(m, flush=True)


def rule(t):
    log(f"\n{'=' * 78}\n{t}\n{'=' * 78}")


def ks_for(v):
    return {"drafted": int(v.drafted.sum()), "top25": math.ceil(0.25 * len(v))}


def make_estimator(cand):
    """Adapter: candidate dict -> the shared Stage A estimator builder."""
    return build_estimator(cand["family"], cand["class_weight"],
                           dict(cand["params"]), SEED)


def make_pipeline(cand, feats):
    """Adapter: candidate dict -> the shared Stage A pipeline builder."""
    return build_pipeline(feats, cand["family"], cand["class_weight"],
                          dict(cand["params"]), SEED)


# ------------------------------------------------------------- calibration
def fit_predict(cand, train, valid, feats, calibration="none"):
    """Returns validation probabilities.

    calibration != "none" uses TEMPORAL_HOLDOUT: the base model is fitted on
    every training year except the last, the calibrator on that last training
    year only, and both are strictly earlier than the outer validation year.

    "none_reduced" is the CONTROL: the same shortened base fit with no
    calibrator attached. Without it an AUC change under calibration cannot be
    told apart from the cost of surrendering a training year.
    """
    if calibration == "none":
        pipe = make_pipeline(cand, feats)
        pipe.fit(train, train.drafted)
        return pipe.predict_proba(valid)[:, 1], pipe, None

    years = sorted(train.draft_year.unique())
    cal_year = years[-1]
    base_tr = train[train.draft_year < cal_year]
    cal_tr = train[train.draft_year == cal_year]
    assert cal_year < int(valid.draft_year.iloc[0]), "calibrator must precede validation"
    pipe = make_pipeline(cand, feats)
    pipe.fit(base_tr, base_tr.drafted)
    raw_cal = pipe.predict_proba(cal_tr)[:, 1]
    raw_val = pipe.predict_proba(valid)[:, 1]
    if calibration == "none_reduced":
        return raw_val, pipe, cal_year
    if calibration == "sigmoid":
        cal = LogisticRegression(max_iter=1000)
        cal.fit(raw_cal.reshape(-1, 1), cal_tr.drafted)
        p = cal.predict_proba(raw_val.reshape(-1, 1))[:, 1]
    elif calibration == "isotonic":
        iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
        iso.fit(raw_cal, cal_tr.drafted)
        p = iso.predict(raw_val)
    else:
        raise ValueError(calibration)
    return np.clip(p, 1e-6, 1 - 1e-6), pipe, cal_year


def run_candidate(cand, dev, fold_list, calibration, rows, oof, cal_years):
    feats = feature_set(cand["feature_set"])
    label = cand["id"] + ("" if calibration == "none" else f"+{calibration}")
    for fold, tr_years, vy in fold_list:
        train = assert_no_holdout(dev[dev.draft_year.isin(tr_years)].copy(),
                                  "train").reset_index(drop=True)
        valid = assert_no_holdout(dev[dev.draft_year == vy].copy(),
                                  "validate").reset_index(drop=True)
        if cand["norm"] == "SEASON_RELATIVE":
            train, valid = season_relative(train, feats), season_relative(valid, feats)
        p, pipe, cal_year = fit_predict(cand, train, valid, feats, calibration)
        if cal_year is not None and calibration != "none_reduced":
            cal_years.append(dict(config=label, outer_validation_year=vy,
                                  calibrator_fit_year=cal_year,
                                  strictly_earlier=bool(cal_year < vy)))
        m = stage_a_metrics(valid.drafted, p, LOW)
        m.update(board_metrics(valid.drafted, p, ks_for(valid)))
        rows.append(dict(config=label, family=cand["family"],
                         feature_set=cand["feature_set"], norm=cand["norm"],
                         class_weight=cand["class_weight"] or "none",
                         calibration=calibration, n_features=len(feats),
                         fold=fold, validate_year=vy, **m))
        oof.append(pd.DataFrame({"config": label, "draft_year": vy,
                                 "canonical_prospect_id":
                                     valid.canonical_prospect_id.values,
                                 "y": valid.drafted.values, "p": p}))
    return feats


def aggregate(fold_df, oof_df, meta):
    macro = (fold_df.groupby("config")
             .agg(macro_auc=("roc_auc", "mean"), macro_ap=("pr_auc", "mean"),
                  macro_brier=("brier", "mean"),
                  macro_logloss=("log_loss", "mean"),
                  macro_ndcg=("ndcg_at_drafted", "mean"),
                  macro_prec=("precision_at_drafted", "mean"),
                  year_sd=("roc_auc", "std"), worst_year_auc=("roc_auc", "min"))
             .round(4).reset_index())
    pooled = []
    for name, g in oof_df.groupby("config"):
        m = stage_a_metrics(g.y, g.p, LOW)
        cb = calibration_bins(g.y, g.p)
        pooled.append(dict(config=name, pooled_auc=m["roc_auc"],
                           pooled_ap=m["pr_auc"], pooled_brier=m["brier"],
                           max_cal_gap=round(float(cb.gap.abs().max()), 4),
                           ece=expected_calibration_error(g.y, g.p),
                           p_min=round(float(g.p.min()), 3),
                           p_max=round(float(g.p.max()), 3)))
    return macro.merge(pd.DataFrame(pooled), on="config").merge(
        pd.DataFrame(meta), on="config", how="left")


def coefficient_report(cand, dev, fold_list, feats):
    """Per-fold coefficients for the selected model plus the full-window fit.

    Sign consistency across folds is the interpretability evidence: a feature
    whose sign flips between folds is not a finding, it is collinearity.
    """
    per_fold = {}
    for fold, tr_years, vy in fold_list:
        train = assert_no_holdout(dev[dev.draft_year.isin(tr_years)].copy(),
                                  "coef").reset_index(drop=True)
        if cand["norm"] == "SEASON_RELATIVE":
            train = season_relative(train, feats)
        pipe = make_pipeline(cand, feats)
        pipe.fit(train, train.drafted)
        names = pipe.named_steps["pre"].get_feature_names_out()
        per_fold[vy] = pd.Series(pipe.named_steps["clf"].coef_[0], index=names)

    full = assert_no_holdout(dev.copy(), "coef-full").reset_index(drop=True)
    if cand["norm"] == "SEASON_RELATIVE":
        full = season_relative(full, feats)
    pipe = make_pipeline(cand, feats)
    pipe.fit(full, full.drafted)
    names = pipe.named_steps["pre"].get_feature_names_out()
    coef = pd.DataFrame(per_fold)
    coef["full_window"] = pd.Series(pipe.named_steps["clf"].coef_[0],
                                    index=names)
    fold_cols = [c for c in coef.columns if c != "full_window"]
    coef["sign_consistent"] = (np.sign(coef[fold_cols]).nunique(axis=1) == 1)
    coef["fold_sd"] = coef[fold_cols].std(axis=1)
    return coef.round(4).sort_values("full_window", key=abs, ascending=False)


def low_support_sensitivity(fold_df, base="LR_C1.0_INCUMBENT"):
    """Re-rank with the LOW NEGATIVE SUPPORT fold removed.

    2025 validates on 28 prospects of whom exactly 2 are undrafted. An ROC-AUC
    computed against 2 negatives is nearly noise, yet it carries a full 1/7 of
    every year-macro average. Any candidate whose ranking depends on that fold
    has not actually been shown to be better.
    """
    piv = fold_df.pivot_table(index="validate_year", columns="config",
                              values="roc_auc")
    ex = piv.drop(index=LOW_SUPPORT_YEAR)
    t = pd.DataFrame({"macro_all7": piv.mean().round(4),
                      "macro_excl_low": ex.mean().round(4),
                      "sd_excl_low": ex.std(ddof=1).round(4),
                      "worst_excl_low": ex.min().round(4)})
    t["shift"] = (t.macro_excl_low - t.macro_all7).round(4)
    t["vs_incumbent"] = (t.macro_excl_low - t.macro_excl_low[base]).round(4)
    return t.sort_values("macro_excl_low", ascending=False).reset_index()


def paired_vs_incumbent(fold_df, base="LR_C1.0_INCUMBENT"):
    """Fold-paired differences. With 7 folds the spread of the difference
    matters more than its mean; a gain smaller than its own fold SD is not
    evidence of a better model."""
    piv = fold_df.pivot_table(index="validate_year", columns="config",
                              values="roc_auc")
    rows = []
    for c in piv.columns:
        if c == base:
            continue
        d = (piv[c] - piv[base]).dropna()
        rows.append(dict(config=c, mean_diff=round(float(d.mean()), 4),
                         sd_diff=round(float(d.std(ddof=1)), 4),
                         wins=int((d > 0).sum()), losses=int((d < 0).sum()),
                         worst_fold_diff=round(float(d.min()), 4)))
    return pd.DataFrame(rows).sort_values("mean_diff", ascending=False)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    dev = load_development()
    fold_list = folds(CFG3)

    rule("SETUP")
    log(f"  development {len(dev)} rows "
        f"({int(dev.drafted.sum())} drafted / {int((dev.drafted==0).sum())} undrafted)"
        f"; unresolved retained {int(dev.hoopr_athlete_id.isna().sum())}")
    log(f"  selection design: {CFG4['selection_design']['chosen']}")
    log(f"  outer folds: {[vy for _, _, vy in fold_list]}")
    log(f"  SET_2 = {len(feature_set('SET_2_BOX_SHOT_PROFILE'))} features | "
        f"SET_2R = {len(feature_set('SET_2R_REDUCED'))} features")

    rows, oof, cal_years, meta = [], [], [], []

    rule("B4 BENCHMARK (unchanged from ML-3)")
    for fold, tr_years, vy in fold_list:
        train = dev[dev.draft_year.isin(tr_years)]
        valid = dev[dev.draft_year == vy]
        p = b4_position_percentile_composite(train, valid)
        m = stage_a_metrics(valid.drafted, p, LOW)
        m.update(board_metrics(valid.drafted, p, ks_for(valid)))
        rows.append(dict(config="B4_BENCHMARK", family="heuristic",
                         feature_set="-", norm="-", class_weight="none",
                         calibration="none", n_features=6, fold=fold,
                         validate_year=vy, **m))
        oof.append(pd.DataFrame({"config": "B4_BENCHMARK", "draft_year": vy,
                                 "canonical_prospect_id":
                                     valid.canonical_prospect_id.values,
                                 "y": valid.drafted.values, "p": p}))
    meta.append(dict(config="B4_BENCHMARK", complexity="heuristic (6 metrics)"))

    rule(f"{len(CFG4['candidates'])} PREDECLARED CANDIDATES x {len(fold_list)} FOLDS")
    for cand in CFG4["candidates"]:
        feats = run_candidate(cand, dev, fold_list, "none", rows, oof, cal_years)
        meta.append(dict(config=cand["id"],
                         complexity=f"{cand['family']} ({len(feats)}f)"))
        log(f"  ran {cand['id']}")

    fold_df = pd.DataFrame(rows)
    oof_df = pd.concat(oof, ignore_index=True)
    summary = aggregate(fold_df, oof_df, meta).sort_values("macro_auc",
                                                           ascending=False)

    rule("UNCALIBRATED RESULTS (sorted by year-macro ROC-AUC)")
    cols = ["config", "macro_auc", "pooled_auc", "macro_ap", "macro_brier",
            "macro_ndcg", "year_sd", "worst_year_auc", "max_cal_gap", "ece"]
    log(summary[cols].to_string(index=False, max_colwidth=26))

    rule(f"LOW-SUPPORT SENSITIVITY (drop {LOW_SUPPORT_YEAR}: only 2 negatives)")
    sens = low_support_sensitivity(fold_df)
    log(sens.to_string(index=False, max_colwidth=26))

    rule("FOLD-PAIRED DIFFERENCES vs INCUMBENT")
    paired = paired_vs_incumbent(fold_df)
    log(paired.head(14).to_string(index=False, max_colwidth=26))

    # ---- calibration on the strongest finalists only
    rule("CALIBRATION (temporal holdout: calibrator fitted on last TRAIN year)")
    # Finalists are picked from the LOW-SUPPORT-ROBUST ranking, not the all-7
    # one: a candidate that leads only because of the 2-negative fold should
    # not earn a calibration study. The incumbent is always included — whether
    # calibration rescues its 0.140 gap is a question ML-4 must answer.
    order = [c for c in sens.config if c in {x["id"] for x in CFG4["candidates"]}]
    lr_best = next(c for c in order if c.startswith("LR"))
    others = [c for c in order if not c.startswith("LR")][:2]
    finalists = list(dict.fromkeys([lr_best, "LR_C1.0_INCUMBENT"] + others))
    log(f"  finalists: {finalists}")
    for cid in finalists:
        cand = next(c for c in CFG4["candidates"] if c["id"] == cid)
        for method in ("none_reduced", "sigmoid", "isotonic"):
            feats = run_candidate(cand, dev, fold_list, method, rows, oof,
                                  cal_years)
            meta.append(dict(config=f"{cid}+{method}",
                             complexity=f"{cand['family']} ({len(feats)}f) "
                                        f"+{method}"))

    fold_df = pd.DataFrame(rows)
    oof_df = pd.concat(oof, ignore_index=True)
    summary = aggregate(fold_df, oof_df, meta).sort_values("macro_auc",
                                                           ascending=False)

    cal_df = pd.DataFrame(cal_years)
    log(f"\n  calibrator-fit years all strictly earlier than outer validation: "
        f"{bool(cal_df.strictly_earlier.all()) if len(cal_df) else 'n/a'}")
    cal_view = summary[summary.config.str.contains(r"\+")].copy()
    base_ids = sorted({c.split("+")[0] for c in cal_view.config})
    log("\n  calibration comparison:")
    log(summary[summary.config.isin(base_ids) | summary.config.isin(cal_view.config)]
        [["config", "macro_auc", "macro_brier", "macro_logloss",
          "max_cal_gap", "ece", "p_min", "p_max", "year_sd"]]
        .sort_values("config").to_string(index=False, max_colwidth=30))

    rule("FINAL COMPARISON TABLE")
    log(summary[cols + ["complexity"]].head(14)
        .to_string(index=False, max_colwidth=26))

    sens = low_support_sensitivity(fold_df)
    paired = paired_vs_incumbent(fold_df)

    rule(f"SELECTED MODEL — COEFFICIENTS ({SELECTED})")
    sel_cand = next(c for c in CFG4["candidates"] if c["id"] == SELECTED)
    coef = coefficient_report(sel_cand, dev, fold_list,
                              feature_set(sel_cand["feature_set"]))
    log(coef.to_string())
    log(f"\n  sign-consistent across all 7 folds: "
        f"{int(coef.sign_consistent.sum())}/{len(coef)}")

    fold_df.to_csv(OUT / "candidate_results.csv", index=False)
    coef.to_csv(OUT / "selected_model_coefficients.csv")
    oof_df.to_parquet(OUT / "outer_fold_predictions.parquet", index=False)
    summary.to_csv(OUT / "model_comparison.csv", index=False)
    cal_df.to_csv(OUT / "calibration_results.csv", index=False)
    sens.to_csv(OUT / "low_support_sensitivity.csv", index=False)
    paired.to_csv(OUT / "paired_vs_incumbent.csv", index=False)

    rep = dict(seed=SEED, selection_design=CFG4["selection_design"]["chosen"],
               n_candidates=len(CFG4["candidates"]), n_folds=len(fold_list),
               development_rows=len(dev),
               unresolved_retained=int(dev.hoopr_athlete_id.isna().sum()),
               calibrators_all_historical=bool(cal_df.strictly_earlier.all())
               if len(cal_df) else None,
               low_support_year=LOW_SUPPORT_YEAR,
               top=summary.head(10).to_dict("records"),
               top_low_support_robust=sens.head(10).to_dict("records"))
    (OUT / "ml4_summary.json").write_text(json.dumps(rep, indent=2,
                                                     default=str))
    log(f"\n  outputs -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
