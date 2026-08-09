"""ML-6 — General Draft Board combination experiment.

Builds out-of-fold Stage A and Stage B signals for every development
validation year, then evaluates a small PREDECLARED set of combination rules.
No weight search: every method here has a closed mathematical form.

The core question is NOT "how do we blend two stages" but "does Stage B add
ordering information Stage A does not already have". Stage A-only is a
legitimate answer.

2026 is never loaded, scored or ranked.

  ./.venv/bin/python scripts/experiments/ml6_board_selection.py

Outputs (git-ignored) -> data/interim/ml6/
"""

import json
import math
import sys

import numpy as np
import pandas as pd

from draftlens.ml.board import (BOARD, combine_board_signals, graded_relevance,
                                overall_score, transform_stage_b_signal,
                                within_board_percentile)
from draftlens.ml.datasets import load_development
from draftlens.ml.metrics import (board_binary_metrics, board_graded_metrics,
                                  board_order_metrics)
from draftlens.ml.stage_a import STAGE_A, feature_set
from draftlens.ml.stage_a import fit_predict_fold as stage_a_fold
from draftlens.ml.stage_b import STAGE_B, draft_sizes
from draftlens.ml.stage_b import fit_predict_fold as stage_b_fold
from draftlens.ml.validation import folds, load_fold_config
from draftlens.paths import CONFIG_ML, interim

CFG6 = json.loads((CONFIG_ML / "ml6_board.json").read_text())
OUT = interim("ml6")
SEED = CFG6["seed"]
LOW_SUPPORT_YEAR = CFG6["evaluation"]["low_support_year"]
COVID_YEARS = CFG6["evaluation"]["covid_years"]

TRANSFORMS = [t["id"] for t in CFG6["stage_b_transforms"]]
METHODS = [m["id"] for m in CFG6["board_methods"]]
REFERENCE = "A_STAGE_A_ONLY"


def log(m=""):
    print(m, flush=True)


def rule(t):
    log(f"\n{'=' * 78}\n{t}\n{'=' * 78}")


# --------------------------------------------------------- OOF construction
def build_oof(dev, fold_list, feats):
    """Out-of-fold Stage A and Stage B signals for every development prospect.

    Stage A trains on ALL early entrants of the training years; Stage B trains
    on the DRAFTED subset only. Both then score every validation-year prospect.
    The Stage B training-year predictions are retained so the historical
    empirical transform has a training-only reference.
    """
    rows = []
    for _, tr_years, vy in fold_list:
        tr_all = dev[dev.draft_year.isin(tr_years)].reset_index(drop=True)
        va = dev[dev.draft_year == vy].reset_index(drop=True)
        tr_drafted = tr_all[tr_all.drafted == 1].reset_index(drop=True)

        p_a, _ = stage_a_fold(tr_all, va, feats)
        p_b, pipe_b = stage_b_fold(tr_drafted, va, feats,
                                   family=STAGE_B["family"],
                                   params={"alpha": STAGE_B["alpha"]},
                                   target=STAGE_B["target"])
        # training-year reference for HISTORICAL_EMPIRICAL_PERCENTILE
        ref, _ = stage_b_fold(tr_drafted, tr_all, feats,
                              family=STAGE_B["family"],
                              params={"alpha": STAGE_B["alpha"]},
                              target=STAGE_B["target"])
        rows.append(pd.DataFrame({
            "draft_year": vy,
            "canonical_prospect_id": va.canonical_prospect_id.values,
            "stage_a_probability": p_a,
            "stage_b_raw_pick": p_b,
            "actual_drafted": va.drafted.values,
            "actual_pick": va.pick.values,
            "draft_size": va.draft_size.values,
            "_ref": [ref] * len(va),
        }))
    return pd.concat(rows, ignore_index=True)


def extrapolation_audit(oof):
    """Stage B was trained only on drafted players but scores the whole board.
    Report what that actually produces before anything is built on it."""
    rows = []
    for label, mask in (("drafted", oof.actual_drafted == 1),
                        ("undrafted", oof.actual_drafted == 0),
                        ("all", slice(None))):
        g = oof[mask] if not isinstance(mask, slice) else oof
        p = g.stage_b_raw_pick
        rows.append(dict(
            group=label, n=len(g), min=round(float(p.min()), 2),
            p05=round(float(p.quantile(.05)), 2),
            median=round(float(p.median()), 2),
            p95=round(float(p.quantile(.95)), 2),
            max=round(float(p.max()), 2), mean=round(float(p.mean()), 2),
            below_1=int((p < 1).sum()),
            above_draft_size=int((p > g.draft_size).sum()),
            missing=int(p.isna().sum())))
    return pd.DataFrame(rows)


# ------------------------------------------------------------- evaluation
def evaluate(oof, method, transform):
    """Per-fold metrics for one (method, Stage B transform) pair."""
    rows, pooled = [], []
    for vy, g in oof.groupby("draft_year"):
        g = g.reset_index(drop=True)
        q = transform_stage_b_signal(g.stage_b_raw_pick, g.draft_size,
                                     transform, g._ref.iloc[0])
        sig = combine_board_signals(g.stage_a_probability, q, method)
        rel = graded_relevance(g.actual_drafted, g.actual_pick, g.draft_size)
        ks = {"drafted": int(g.actual_drafted.sum()),
              "top25": math.ceil(0.25 * len(g))}

        m = dict(config=f"{method}|{transform}", method=method,
                 transform=transform, validate_year=int(vy))
        m.update(board_binary_metrics(g.actual_drafted, sig, ks))
        m.update(board_graded_metrics(rel, sig))
        d = g[g.actual_drafted == 1]
        m.update(board_order_metrics(d.actual_pick,
                                     sig[(g.actual_drafted == 1).to_numpy()]))
        rows.append(m)
        pooled.append(pd.DataFrame({"drafted": g.actual_drafted.values,
                                    "signal": sig,
                                    "signal_pct": within_board_percentile(sig)}))
    fold_df = pd.DataFrame(rows)
    pooled_df = pd.concat(pooled, ignore_index=True)
    # pooled AUC uses the within-board percentile so that boards of different
    # scale are comparable when concatenated across years
    pooled_auc = board_binary_metrics(pooled_df.drafted, pooled_df.signal_pct,
                                      {"drafted": int(pooled_df.drafted.sum())})
    return fold_df, pooled_auc


def summarise(fold_df, pooled_auc):
    scored = fold_df[fold_df.roc_auc.notna()]
    return dict(
        config=fold_df.config.iloc[0], method=fold_df.method.iloc[0],
        transform=fold_df["transform"].iloc[0],
        binary_macro_auc=round(float(scored.roc_auc.mean()), 4),
        binary_pooled_auc=pooled_auc["roc_auc"],
        macro_ap=round(float(scored.average_precision.mean()), 4),
        graded_ndcg=round(float(fold_df.graded_ndcg.mean()), 4),
        graded_ndcg_at_30=round(float(fold_df.graded_ndcg_at_30.mean()), 4),
        drafted_spearman=round(float(fold_df.drafted_spearman.mean()), 4),
        drafted_kendall=round(float(fold_df.drafted_kendall.mean()), 4),
        precision_at_drafted=round(float(fold_df.precision_at_drafted.mean()), 4),
        recall_at_top25=round(float(fold_df.recall_at_top25.mean()), 4),
        auc_year_sd=round(float(scored.roc_auc.std()), 4),
        auc_worst_year=round(float(scored.roc_auc.min()), 4),
        graded_year_sd=round(float(fold_df.graded_ndcg.std()), 4),
        graded_worst_year=round(float(fold_df.graded_ndcg.min()), 4))


def incremental_value(all_folds, reference_config):
    """Fold-by-fold delta of every candidate against the Stage A-only board.

    This is the evidence that decides whether Stage B enters the Overall Score.
    A candidate that wins on the mean while losing most folds has not earned it.
    """
    ref = all_folds[all_folds.config == reference_config].set_index("validate_year")
    out = []
    for cfg, g in all_folds.groupby("config"):
        if cfg == reference_config:
            continue
        g = g.set_index("validate_year")
        row = dict(config=cfg)
        for metric in ("graded_ndcg", "drafted_spearman", "roc_auc",
                       "precision_at_drafted"):
            d = (g[metric] - ref[metric]).dropna()
            row[f"{metric}_mean_delta"] = round(float(d.mean()), 4)
            row[f"{metric}_improved"] = int((d > 0).sum())
            row[f"{metric}_worsened"] = int((d < 0).sum())
            row[f"{metric}_worst_delta"] = round(float(d.min()), 4)
        out.append(row)
    return pd.DataFrame(out)


def main():
    cfg = load_fold_config()
    fold_list = folds(cfg)
    dev = load_development()
    dev["draft_size"] = dev.draft_year.map(draft_sizes())
    feats = feature_set(STAGE_A["feature_set"], cfg)

    rule("SETUP — FROZEN STAGES")
    log(f"  Stage A: {STAGE_A}")
    log(f"  Stage B: {STAGE_B}")
    log(f"  development {len(dev)} rows "
        f"({int(dev.drafted.sum())} drafted / "
        f"{int((dev.drafted == 0).sum())} undrafted)")
    log(f"  outer folds: {[vy for _, _, vy in fold_list]}")

    rule("OUT-OF-FOLD BOARD SIGNAL CONSTRUCTION")
    oof = build_oof(dev, fold_list, feats)
    log(f"  {len(oof)} out-of-fold prospects across "
        f"{oof.draft_year.nunique()} validation years")
    log(f"  drafted {int(oof.actual_drafted.sum())} / "
        f"undrafted {int((oof.actual_drafted == 0).sum())}")
    log(f"  missing Stage A: {int(oof.stage_a_probability.isna().sum())}  "
        f"missing Stage B: {int(oof.stage_b_raw_pick.isna().sum())}")

    rule("STAGE B ALL-PROSPECT EXTRAPOLATION AUDIT")
    audit = extrapolation_audit(oof)
    log(audit.to_string(index=False))
    audit.to_csv(OUT / "stage_b_extrapolation_audit.csv", index=False)
    log("\n  Stage B is applied to undrafted prospects as a CONDITIONAL signal:")
    log("  'if this profile were draftable, which part of the draft does it")
    log("  resemble?' — never a pick assignment. Targets are untouched.")

    rule("CANDIDATE BOARDS")
    all_folds, summaries = [], []
    for method in METHODS:
        uses_b = next(m for m in CFG6["board_methods"]
                      if m["id"] == method)["uses_stage_b"]
        for transform in (TRANSFORMS if uses_b else TRANSFORMS[:1]):
            fold_df, pooled = evaluate(oof, method, transform)
            all_folds.append(fold_df)
            summaries.append(summarise(fold_df, pooled))
        log(f"  ran {method}")
    all_folds = pd.concat(all_folds, ignore_index=True)
    summary = pd.DataFrame(summaries).sort_values("graded_ndcg", ascending=False)

    rule("BOARD METHOD COMPARISON (sorted by graded NDCG)")
    cols = ["config", "binary_macro_auc", "binary_pooled_auc", "macro_ap",
            "graded_ndcg", "drafted_spearman", "drafted_kendall",
            "precision_at_drafted", "recall_at_top25", "graded_year_sd",
            "graded_worst_year"]
    log(summary[cols].to_string(index=False, max_colwidth=42))

    ref_cfg = f"{REFERENCE}|{TRANSFORMS[0]}"
    rule(f"INCREMENTAL VALUE OF STAGE B  (vs {REFERENCE})")
    inc = incremental_value(all_folds, ref_cfg)
    log(inc[["config", "graded_ndcg_mean_delta", "graded_ndcg_improved",
             "graded_ndcg_worsened", "graded_ndcg_worst_delta",
             "drafted_spearman_mean_delta", "drafted_spearman_improved",
             "roc_auc_mean_delta", "roc_auc_improved"]]
        .to_string(index=False, max_colwidth=42))

    rule("LOW-SUPPORT AND COVID SENSITIVITY")
    ex = all_folds[all_folds.validate_year != LOW_SUPPORT_YEAR]
    sens = (ex.groupby("config")
            .agg(graded_ndcg_excl_2025=("graded_ndcg", "mean"),
                 auc_excl_2025=("roc_auc", "mean"),
                 spearman_excl_2025=("drafted_spearman", "mean")).round(4))
    full = (all_folds.groupby("config")
            .agg(graded_ndcg_all=("graded_ndcg", "mean"),
                 auc_all=("roc_auc", "mean")).round(4))
    sens = full.join(sens)
    sens["graded_shift"] = (sens.graded_ndcg_excl_2025
                            - sens.graded_ndcg_all).round(4)
    sens["auc_shift"] = (sens.auc_excl_2025 - sens.auc_all).round(4)
    log(sens.sort_values("graded_ndcg_excl_2025", ascending=False)
        .to_string(max_colwidth=42))
    covid = all_folds[all_folds.validate_year.isin(COVID_YEARS)]
    log(f"\n  COVID years {COVID_YEARS}: "
        f"graded NDCG by config (mean over {len(COVID_YEARS)} folds)")
    log(covid.groupby("config").graded_ndcg.mean().round(4)
        .sort_values(ascending=False).to_string())

    # ---------------------------------------------------- selected board
    rule(f"SELECTED BOARD — {BOARD['method']} | {BOARD['stage_b_transform']}")
    sel_cfg = f"{BOARD['method']}|{BOARD['stage_b_transform']}"
    sel = all_folds[all_folds.config == sel_cfg]
    log(sel[["validate_year", "n", "drafted", "roc_auc", "average_precision",
             "graded_ndcg", "drafted_spearman", "drafted_kendall",
             "precision_at_drafted", "low_negative_support"]]
        .to_string(index=False))

    rule("OVERALL SCORE TRANSFORMATION")
    q = np.concatenate([
        transform_stage_b_signal(g.stage_b_raw_pick, g.draft_size,
                                 BOARD["stage_b_transform"], g._ref.iloc[0])
        for _, g in oof.groupby("draft_year")])
    order = np.concatenate([g.index.to_numpy()
                            for _, g in oof.groupby("draft_year")])
    oof = oof.loc[order].reset_index(drop=True)
    oof["stage_b_quality"] = q
    oof["final_board_signal"] = np.concatenate([
        combine_board_signals(g.stage_a_probability, g.stage_b_quality,
                              BOARD["method"])
        for _, g in oof.groupby("draft_year")])

    # frozen historical reference for the absolute-scale score option
    ref_signals = np.sort(oof.final_board_signal.to_numpy())
    scores = {}
    for st in ("CURRENT_BOARD_PERCENTILE", "HISTORICAL_EMPIRICAL_PERCENTILE"):
        vals = []
        for _, g in oof.groupby("draft_year"):
            vals.append(pd.Series(
                overall_score(g.final_board_signal, st, ref_signals),
                index=g.index))
        scores[st] = pd.concat(vals).sort_index()
    oof["overall_score"] = scores[BOARD["score_transform"]]
    oof["overall_score_alt"] = scores["HISTORICAL_EMPIRICAL_PERCENTILE"]

    cmp_rows = []
    for st, s in scores.items():
        per_year = []
        for vy, g in oof.groupby("draft_year"):
            v = s.loc[g.index]
            per_year.append(dict(year=vy, mn=int(v.min()), mx=int(v.max()),
                                 med=float(v.median())))
        py = pd.DataFrame(per_year)
        cmp_rows.append(dict(
            transform=st, overall_min=int(s.min()), overall_max=int(s.max()),
            mean_class_max=round(float(py.mx.mean()), 1),
            mean_class_min=round(float(py.mn.mean()), 1),
            class_median_spread=round(float(py.med.max() - py.med.min()), 1),
            n_distinct=int(s.nunique())))
    cmp = pd.DataFrame(cmp_rows)
    log(cmp.to_string(index=False))
    log("\n  class_median_spread = how much the median score moves between "
        "draft classes.\n  A class-relative score pins every class to the same "
        "median by construction;\n  an absolute score lets a weak class score "
        "lower overall.")
    cmp.to_csv(OUT / "score_transform_comparison.csv", index=False)

    # monotonicity is a hard requirement, not an aspiration
    for vy, g in oof.groupby("draft_year"):
        o = g.sort_values("final_board_signal", ascending=False)
        assert o.overall_score.is_monotonic_decreasing, \
            f"{vy}: overall_score disagrees with board order"
    log("\n  monotonicity: score order matches board order in all "
        f"{oof.draft_year.nunique()} classes")

    # ------------------------------------------------------------ artifacts
    keep = ["draft_year", "canonical_prospect_id", "stage_a_probability",
            "stage_b_raw_pick", "stage_b_quality", "final_board_signal",
            "overall_score", "overall_score_alt", "actual_drafted",
            "actual_pick"]
    oof[keep].to_parquet(OUT / "oof_board.parquet", index=False)
    all_folds.to_csv(OUT / "board_fold_results.csv", index=False)
    summary.to_csv(OUT / "board_method_comparison.csv", index=False)
    inc.to_csv(OUT / "incremental_value.csv", index=False)
    sens.reset_index().to_csv(OUT / "low_support_sensitivity.csv", index=False)

    rep = dict(seed=SEED, selected=BOARD, oof_rows=len(oof),
               development_rows=len(dev),
               n_methods=len(METHODS), n_transforms=len(TRANSFORMS),
               reference_board=ref_cfg,
               top=summary.head(8).to_dict("records"),
               extrapolation=audit.to_dict("records"))
    (OUT / "ml6_summary.json").write_text(json.dumps(rep, indent=2, default=str))
    log(f"\n  outputs -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
