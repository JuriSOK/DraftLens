"""ML-5 — Stage B target-design and model-selection experiment.

HISTORICAL EVIDENCE. This reproduces the experiment that selected the frozen
Stage B methodology (DEC-086..091) and the numbers in
docs/experiments/ML5_STAGE_B.md. The selection itself lives in
`draftlens.ml.stage_b.STAGE_B`; this script must not be used to change it.

Full factorial: 12 models x 4 targets, all predeclared, all evaluated on all 7
folds. No random CV. 2026 is never loaded, predicted or evaluated, and undrafted
prospects never enter Stage B — no synthetic pick is ever created.

  ./.venv/bin/python scripts/experiments/ml5_stage_b_selection.py

Outputs (git-ignored) -> data/interim/ml5/
"""

import json
import sys

import numpy as np
import pandas as pd
from scipy.stats import kendalltau, spearmanr
from sklearn.linear_model import LogisticRegression

from draftlens.ml.baselines import STAGE_B_BASELINES as BASELINES
from draftlens.ml.datasets import load_stage_b as _load_stage_b
from draftlens.ml.metrics import stage_b_metrics, strength, tier_metrics
from draftlens.ml.stage_a import feature_set
from draftlens.ml.stage_b import (build_estimator, build_pipeline, draft_sizes,
                                  tier_of, to_pick, to_target)
from draftlens.ml.validation import (HOLDOUT_YEAR, assert_no_holdout, folds,
                                     load_fold_config)
from draftlens.paths import CONFIG_ML, interim

CFG5 = json.loads((CONFIG_ML / "stage_b.json").read_text())
CFG3 = load_fold_config()
OUT = interim("ml5")
SEED = CFG5["seed"]
DRAFT_SIZE = draft_sizes(CFG5)
TIERS = CFG5["tier_target"]["boundaries"]

SELECTED_TARGET = "RAW_PICK"
SELECTED_MODEL = "RIDGE_a10"


def load_stage_b(robustness=False):
    """Stage B population with each year's structural draft size attached."""
    d = _load_stage_b(robustness)
    d["draft_size"] = d.draft_year.map(DRAFT_SIZE)
    assert d.draft_size.notna().all(), "draft size missing for a year"
    assert (d.pick <= d.draft_size).all(), "a pick exceeds its declared draft size"
    return d


def make_estimator(model):
    """Adapter: model dict -> the shared Stage B estimator builder."""
    return build_estimator(model["family"], dict(model["params"]), SEED)


def make_pipeline(model, feats, estimator=None):
    """Adapter: model dict -> the shared Stage B pipeline builder."""
    fam = (model or {}).get("family", "Ridge")
    params = dict((model or {}).get("params", {})) or None
    return build_pipeline(feats, fam, params, SEED, estimator=estimator)


def fit_predict(model, target, train, valid, feats):
    """Returns predicted PICK for the validation year.

    The target is z-scored on TRAIN-FOLD statistics only so that one alpha grid
    means the same amount of regularisation on all four target scales; the step
    is exactly invertible and rank-preserving, so nothing reported depends on it.
    """
    y_tr = to_target(train.pick, train.draft_size, target)
    mu, sd = float(np.mean(y_tr)), float(np.std(y_tr))
    sd = sd if sd > 0 else 1.0
    pipe = make_pipeline(model, feats)
    pipe.fit(train, (y_tr - mu) / sd)
    y_hat = pipe.predict(valid) * sd + mu
    return to_pick(y_hat, valid.draft_size, target), pipe


def log(m=""):
    print(m, flush=True)


def rule(t):
    log(f"\n{'=' * 78}\n{t}\n{'=' * 78}")


# ------------------------------------------------------------- population


# ---------------------------------------------------------------- targets








# --------------------------------------------------------------- estimator






# -------------------------------------------------------------- baselines








# ---------------------------------------------------------------- metrics




# ------------------------------------------------------------------- runs
def run_fold_set(dev, fold_list, rows, oof, label, predict_fn, extra=None):
    for fold, tr_years, vy in fold_list:
        train = assert_no_holdout(dev[dev.draft_year.isin(tr_years)].copy(),
                                  "train").reset_index(drop=True)
        valid = assert_no_holdout(dev[dev.draft_year == vy].copy(),
                                  "validate").reset_index(drop=True)
        pred_pick = predict_fn(train, valid)
        m = stage_b_metrics(valid.pick, pred_pick, valid.draft_size)
        rows.append(dict(config=label, fold=fold, validate_year=vy,
                         n_train=len(train), **(extra or {}), **m))
        oof.append(pd.DataFrame({
            "config": label, "draft_year": vy,
            "canonical_prospect_id": valid.canonical_prospect_id.values,
            "actual_pick": valid.pick.values,
            "predicted_pick": pred_pick,
            "strength": strength(pred_pick)}))


def run_tier_model(dev, fold_list, rows, oof, feats):
    """Multinomial logistic over three tiers. NOT true ordinal regression —
    the estimator does not know the tiers are ordered; only the evaluation does.
    Ranking is induced from the expected tier index."""
    label = "TIER3_MULTINOMIAL_LR"
    for fold, tr_years, vy in fold_list:
        train = assert_no_holdout(dev[dev.draft_year.isin(tr_years)].copy(),
                                  "train").reset_index(drop=True)
        valid = assert_no_holdout(dev[dev.draft_year == vy].copy(),
                                  "validate").reset_index(drop=True)
        est = LogisticRegression(C=0.25, max_iter=5000, random_state=SEED)
        pipe = make_pipeline(None, feats, estimator=est)
        y_tr = tier_of(train.pick)
        pipe.fit(train, y_tr)
        proba = pipe.predict_proba(valid)
        classes = pipe.named_steps["clf"].classes_
        expected = proba @ classes.astype("float64")
        pred_tier = classes[proba.argmax(axis=1)]
        actual_tier = tier_of(valid.pick)

        # rank by expected tier index (lower = better) -> pseudo-pick scale
        m = stage_b_metrics(valid.pick, expected * 20.0 + 1.0, valid.draft_size)
        # a tier model cannot claim a pick-scale error
        for k in ("mae_pick", "rmse_pick", "median_ae_pick"):
            m[k] = None
        m.update(tier_metrics(actual_tier, pred_tier))
        rows.append(dict(config=label, fold=fold, validate_year=vy,
                         n_train=len(train), family="MultinomialLR",
                         target="TIER_3", feature_set="SET_2_BOX_SHOT_PROFILE",
                         **m))
        oof.append(pd.DataFrame({
            "config": label, "draft_year": vy,
            "canonical_prospect_id": valid.canonical_prospect_id.values,
            "actual_pick": valid.pick.values,
            "predicted_pick": np.nan,
            "strength": strength(expected)}))


# -------------------------------------------------------------- aggregate
def aggregate(fold_df, oof_df):
    num = ["spearman", "kendall_tau", "ndcg", "ndcg_at_14", "mae_pick",
           "rmse_pick", "median_ae_pick", "lottery_recall_at_14"]
    agg = {f"macro_{c}": (c, "mean") for c in num}
    agg["year_sd_spearman"] = ("spearman", "std")
    agg["worst_year_spearman"] = ("spearman", "min")
    agg["worst_year_ndcg"] = ("ndcg", "min")
    macro = fold_df.groupby("config").agg(**agg).round(4).reset_index()

    pooled = []
    for name, g in oof_df.groupby("config"):
        gg = g.dropna(subset=["strength"])
        if gg.strength.std() == 0 or len(gg) < 3:
            pooled.append(dict(config=name, pooled_spearman=None,
                               pooled_kendall=None))
            continue
        # pooled rank quality is computed WITHIN year then pooled by
        # concatenating out-of-fold pairs; a raw cross-year Spearman would
        # compare picks from drafts of different sizes.
        st = strength(gg.actual_pick.to_numpy(dtype="float64"))
        pooled.append(dict(
            config=name,
            pooled_spearman=round(float(spearmanr(gg.strength, st).statistic), 4),
            pooled_kendall=round(float(kendalltau(gg.strength, st).statistic), 4)))
    return macro.merge(pd.DataFrame(pooled), on="config", how="left")


def target_rank_equivalence(oof_df, model_id="RIDGE_a10"):
    """Do the target transformations actually change the induced ranking?

    RAW_PICK, PICK_PERCENTILE and DRAFT_VALUE are affine images of one another
    within a draft year, so for a LINEAR model they cannot change the order at
    all — the only reason their rank correlation is below 1.0 is that draft size
    varies 58-60 across years. LOG_PICK is the one genuinely non-affine
    transformation and is the only one that can move the ranking.
    """
    base = (oof_df[oof_df.config == f"{model_id}|RAW_PICK"]
            .set_index("canonical_prospect_id").strength)
    rows = []
    for t in ("PICK_PERCENTILE", "DRAFT_VALUE", "LOG_PICK"):
        x = (oof_df[oof_df.config == f"{model_id}|{t}"]
             .set_index("canonical_prospect_id").strength)
        j = pd.concat([base.rename("a"), x.rename("b")], axis=1).dropna()
        rows.append(dict(model=model_id, target_a="RAW_PICK", target_b=t,
                         rank_correlation=round(
                             float(spearmanr(j.a, j.b).statistic), 6),
                         affine_of_raw_pick=t != "LOG_PICK"))
    return pd.DataFrame(rows)


def alpha_coefficient_stability(dev, fold_list, feats, target="RAW_PICK"):
    """Coefficient volatility along the ridge path.

    Rank metrics separate the alphas by less than their own fold-to-fold noise,
    so interpretability becomes the tiebreak — and PRODUCT.md 16 requires the
    board to explain why one prospect outranks another.
    """
    rows = []
    for m in CFG5["models"]:
        if m["family"] != "Ridge":
            continue
        per_fold = {}
        for fold, tr_years, vy in fold_list:
            tr = dev[dev.draft_year.isin(tr_years)].reset_index(drop=True)
            y = to_target(tr.pick, tr.draft_size, target)
            pipe = make_pipeline(m, feats)
            pipe.fit(tr, (y - y.mean()) / y.std())
            per_fold[vy] = pd.Series(
                -pipe.named_steps["clf"].coef_,
                index=pipe.named_steps["pre"].get_feature_names_out())
        c = pd.DataFrame(per_fold)
        rows.append(dict(
            model=m["id"], alpha=m["params"]["alpha"],
            sign_consistent=int((np.sign(c).nunique(axis=1) == 1).sum()),
            n_terms=len(c),
            mean_coef_fold_sd=round(float(c.std(axis=1).mean()), 4),
            max_abs_coef=round(float(c.abs().max().max()), 4)))
    return pd.DataFrame(rows)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    dev = load_stage_b()
    fold_list = folds(CFG3)
    feats_full = feature_set("SET_2_BOX_SHOT_PROFILE")
    feats_red = feature_set("SET_2R_REDUCED")

    rule("SETUP — STAGE B POPULATION")
    log(f"  drafted early entrants 2014-2025: {len(dev)} "
        f"(expected {CFG5['expected_rows']})")
    log(f"  undrafted rows in Stage B: "
        f"{int((dev.drafted == 0).sum())}  (must be 0)")
    log(f"  unresolved prospects in Stage B: "
        f"{int(dev.hoopr_athlete_id.isna().sum())}")
    log(f"  features: SET_2 = {len(feats_full)} | SET_2R = {len(feats_red)}")
    by_year = dev.groupby("draft_year").agg(
        n=("pick", "size"), min_pick=("pick", "min"), max_pick=("pick", "max"),
        draft_size=("draft_size", "first"))
    log("\n" + by_year.to_string())

    rule("HISTORICAL PICK DISTRIBUTION")
    log(dev.pick.describe().round(2).to_string())
    trad = np.select([dev.pick <= 14, dev.pick <= 30, dev.pick <= 45],
                     ["1-14", "15-30", "31-45"], "46-60")
    ct4 = pd.crosstab(dev.draft_year, trad)
    log("\n  traditional 4 tiers — cells below 5: "
        f"{int((ct4 < 5).sum().sum())} of {ct4.size}")
    log(ct4.to_string())
    ct3 = pd.crosstab(dev.draft_year,
                      pd.Series(tier_of(dev.pick), index=dev.index)
                      .map({0: "1_lottery", 1: "2_rest_of_r1", 2: "3_round_2"}))
    log("\n  adopted 3 tiers — cells below 5: "
        f"{int((ct3 < 5).sum().sum())} of {ct3.size}")
    log(ct3.to_string())
    ct4.to_csv(OUT / "tier_support_4.csv")
    ct3.to_csv(OUT / "tier_support_3.csv")

    rows, oof = [], []

    rule("BASELINES")
    for bid, fn in BASELINES.items():
        run_fold_set(dev, fold_list, rows, oof, bid,
                     lambda tr, va, f=fn: f(tr, va),
                     extra=dict(family="baseline", target="-",
                                feature_set="-"))
        log(f"  ran {bid}")

    rule(f"{len(CFG5['models'])} MODELS x {len(CFG5['targets'])} TARGETS "
         f"x {len(fold_list)} FOLDS")
    for model in CFG5["models"]:
        for tgt in CFG5["targets"]:
            label = f"{model['id']}|{tgt['id']}"
            run_fold_set(
                dev, fold_list, rows, oof, label,
                lambda tr, va, m=model, t=tgt["id"]:
                    fit_predict(m, t, tr, va, feats_full)[0],
                extra=dict(family=model["family"], target=tgt["id"],
                           feature_set="SET_2_BOX_SHOT_PROFILE"))
        log(f"  ran {model['id']} on all {len(CFG5['targets'])} targets")

    rule("REDUCED FEATURE SET (collinearity sensitivity)")
    for mid in CFG5["design"]["reduced_set_models"]:
        model = next(m for m in CFG5["models"] if m["id"] == mid)
        for tgt in CFG5["targets"]:
            label = f"{mid}|{tgt['id']}|SET_2R"
            run_fold_set(
                dev, fold_list, rows, oof, label,
                lambda tr, va, m=model, t=tgt["id"]:
                    fit_predict(m, t, tr, va, feats_red)[0],
                extra=dict(family=model["family"], target=tgt["id"],
                           feature_set="SET_2R_REDUCED"))
        log(f"  ran {mid} on SET_2R")

    rule("ORDINAL TIER EXPERIMENT")
    run_tier_model(dev, fold_list, rows, oof, feats_full)
    log("  ran TIER3_MULTINOMIAL_LR")

    fold_df = pd.DataFrame(rows)
    oof_df = pd.concat(oof, ignore_index=True)
    summary = aggregate(fold_df, oof_df).sort_values("macro_spearman",
                                                     ascending=False)

    rule("TARGET COMPARISON (averaged over all 12 models)")
    cont = fold_df[fold_df.target.isin([t["id"] for t in CFG5["targets"]])
                   & (fold_df.feature_set == "SET_2_BOX_SHOT_PROFILE")]
    tc = (cont.groupby("target")
          .agg(macro_spearman=("spearman", "mean"),
               macro_kendall=("kendall_tau", "mean"),
               macro_ndcg=("ndcg", "mean"),
               macro_mae=("mae_pick", "mean"),
               macro_rmse=("rmse_pick", "mean"),
               sd=("spearman", "std"), worst=("spearman", "min"))
          .round(4).sort_values("macro_spearman", ascending=False).reset_index())
    log(tc.to_string(index=False))
    tc.to_csv(OUT / "target_comparison.csv", index=False)

    rule("DOES A TARGET TRANSFORM CHANGE THE RANKING?")
    eq = target_rank_equivalence(oof_df)
    log(eq.to_string(index=False))
    log("\n  An affine transform cannot reorder a linear model's predictions;"
        "\n  the shortfall from 1.000 is only draft size varying 58-60 by year.")
    eq.to_csv(OUT / "target_rank_equivalence.csv", index=False)

    rule("RIDGE PATH — COEFFICIENT STABILITY (the interpretability tiebreak)")
    astab = alpha_coefficient_stability(dev, fold_list, feats_full)
    log(astab.to_string(index=False))
    astab.to_csv(OUT / "alpha_coefficient_stability.csv", index=False)

    rule("TOP CONFIGURATIONS BY MACRO SPEARMAN")
    cols = ["config", "macro_spearman", "pooled_spearman", "macro_kendall_tau",
            "macro_ndcg", "macro_mae_pick", "macro_rmse_pick",
            "year_sd_spearman", "worst_year_spearman"]
    log(summary[cols].head(20).to_string(index=False, max_colwidth=30))

    rule("BASELINES AND TIER MODEL")
    log(summary[summary.config.str.startswith(("B5", "TIER"))][cols]
        .to_string(index=False, max_colwidth=30))

    fold_df.to_csv(OUT / "fold_results.csv", index=False)
    oof_df.to_parquet(OUT / "oof_stage_b_predictions.parquet", index=False)
    summary.to_csv(OUT / "model_comparison.csv", index=False)

    rule(f"SELECTED — {SELECTED_MODEL} on {SELECTED_TARGET}")
    sel = f"{SELECTED_MODEL}|{SELECTED_TARGET}"
    log(fold_df[fold_df.config == sel][
        ["validate_year", "n", "n_train", "spearman", "kendall_tau", "ndcg",
         "ndcg_at_14", "mae_pick", "rmse_pick", "median_ae_pick",
         "lottery_recall_at_14"]].to_string(index=False))

    rule("RESIDUAL / EXACT-PICK UNCERTAINTY")
    g = oof_df[oof_df.config == sel].copy()
    g["abs_err"] = (g.predicted_pick - g.actual_pick).abs()
    res = dict(mae=round(float(g.abs_err.mean()), 2),
               median_ae=round(float(g.abs_err.median()), 2),
               p90_abs_err=round(float(g.abs_err.quantile(0.9)), 2),
               within_5=round(float((g.abs_err <= 5).mean()), 4),
               within_10=round(float((g.abs_err <= 10).mean()), 4),
               within_15=round(float((g.abs_err <= 15).mean()), 4),
               pred_range=[round(float(g.predicted_pick.min()), 1),
                           round(float(g.predicted_pick.max()), 1)],
               actual_range=[int(g.actual_pick.min()), int(g.actual_pick.max())])
    for k, v in res.items():
        log(f"  {k:16s} {v}")
    by_tier = g.assign(tier=tier_of(g.actual_pick)).groupby("tier").agg(
        n=("abs_err", "size"), mae=("abs_err", "mean"),
        mean_pred=("predicted_pick", "mean"),
        mean_actual=("actual_pick", "mean")).round(2)
    log("\n  error by actual tier (0=lottery, 1=rest of R1, 2=round 2):")
    log(by_tier.to_string())
    pd.DataFrame([res]).to_csv(OUT / "residual_summary.csv", index=False)

    rule("INTERPRETABILITY — SELECTED MODEL COEFFICIENTS")
    model = next(m for m in CFG5["models"] if m["id"] == SELECTED_MODEL)
    per_fold = {}
    for fold, tr_years, vy in fold_list:
        train = dev[dev.draft_year.isin(tr_years)].reset_index(drop=True)
        y = to_target(train.pick, train.draft_size, SELECTED_TARGET)
        pipe = make_pipeline(model, feats_full)
        pipe.fit(train, (y - y.mean()) / y.std())
        names = pipe.named_steps["pre"].get_feature_names_out()
        # negate so a POSITIVE coefficient means "better draft position"
        per_fold[vy] = pd.Series(-pipe.named_steps["clf"].coef_, index=names)
    full = dev.reset_index(drop=True)
    y = to_target(full.pick, full.draft_size, SELECTED_TARGET)
    pipe = make_pipeline(model, feats_full)
    pipe.fit(full, (y - y.mean()) / y.std())
    coef = pd.DataFrame(per_fold)
    coef["full_window"] = pd.Series(
        -pipe.named_steps["clf"].coef_,
        index=pipe.named_steps["pre"].get_feature_names_out())
    fc = [c for c in coef.columns if c != "full_window"]
    coef["sign_consistent"] = np.sign(coef[fc]).nunique(axis=1) == 1
    coef["fold_sd"] = coef[fc].std(axis=1)
    coef = coef.round(4).sort_values("full_window", key=abs, ascending=False)
    log("  (positive = pushes toward an EARLIER pick)")
    log(coef.to_string())
    log(f"\n  sign-consistent across all 7 folds: "
        f"{int(coef.sign_consistent.sum())}/{len(coef)}")
    coef.to_csv(OUT / "selected_model_coefficients.csv")

    rule("ROBUSTNESS — 2011-2013 (applied AFTER selection, never used to select)")
    rob = load_stage_b(robustness=True)
    log(f"  drafted early entrants 2011-2013: {len(rob)}")
    rob_rows = []
    for vy in sorted(rob.draft_year.unique()):
        va = rob[rob.draft_year == vy].reset_index(drop=True)
        pred, _ = fit_predict(model, SELECTED_TARGET, dev, va, feats_full)
        m = stage_b_metrics(va.pick, pred, va.draft_size)
        rob_rows.append(dict(validate_year=int(vy), **m))
    rob_df = pd.DataFrame(rob_rows)
    log(rob_df[["validate_year", "n", "spearman", "kendall_tau", "ndcg",
                "mae_pick", "rmse_pick", "lottery_recall_at_14"]]
        .to_string(index=False))
    log(f"\n  robustness macro Spearman: {rob_df.spearman.mean():.4f}  "
        f"(development macro: "
        f"{float(summary.loc[summary.config == sel, 'macro_spearman'].iloc[0]):.4f})")
    rob_df.to_csv(OUT / "robustness_2011_2013.csv", index=False)

    rep = dict(seed=SEED, stage="B",
               selected_target=SELECTED_TARGET, selected_model=SELECTED_MODEL,
               design=CFG5["design"]["chosen"],
               n_models=len(CFG5["models"]), n_targets=len(CFG5["targets"]),
               n_folds=len(fold_list), development_rows=len(dev),
               undrafted_in_stage_b=int((dev.drafted == 0).sum()),
               residuals=res,
               robustness_macro_spearman=round(float(rob_df.spearman.mean()), 4),
               top=summary.head(10).to_dict("records"),
               target_comparison=tc.to_dict("records"))
    (OUT / "ml5_summary.json").write_text(json.dumps(rep, indent=2, default=str))
    log(f"\n  outputs -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
