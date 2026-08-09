"""Evaluation metrics for both stages.

Two conventions are enforced here rather than left to callers:

  DEGENERATE FOLDS. A metric that cannot be computed returns None, never a
  flattering default. The 2025 Stage A fold has 2 undrafted prospects, so
  ROC-AUC is reported as None when a class is absent and flagged
  LOW NEGATIVE SUPPORT when the minority class is below threshold (DEC-075).

  TIE BREAKING. Ranking metrics break ties with a SEEDED permutation, not row
  order. ML-0 builds the population drafted-first, so a constant predictor that
  inherited row order scored a spurious NDCG of 1.000 — the ML-3 defect this
  guards against.

Stage B adds one further convention: every prediction is inverse-transformed to
the pick scale before `strength = -pick` is applied, so exactly one orientation
exists project-wide and Spearman can never come out sign-flipped by accident.
"""

import numpy as np
import pandas as pd
from scipy.stats import kendalltau, spearmanr
from sklearn.metrics import (average_precision_score, brier_score_loss,
                             f1_score, log_loss, ndcg_score, roc_auc_score)


# ------------------------------------------------------------------ shared
def to_unit(x):
    """Monotone map of an arbitrary score to (0,1) so probability metrics are
    computable. Rank-preserving; NOT a calibrated probability."""
    s = pd.Series(x)
    r = s.rank(method="average", na_option="keep")
    n = r.notna().sum()
    out = (r - 0.5) / n
    return out.fillna(0.5).clip(1e-6, 1 - 1e-6).to_numpy()


# ----------------------------------------------------------------- Stage A
def stage_a_metrics(y, p, low_support_threshold=5):
    y = np.asarray(y).astype(int)
    p = np.clip(np.asarray(p, dtype="float64"), 1e-9, 1 - 1e-9)
    n_pos, n_neg = int(y.sum()), int((y == 0).sum())
    out = dict(n=len(y), drafted=n_pos, undrafted=n_neg,
               base_rate=round(float(y.mean()), 4),
               low_negative_support=bool(min(n_pos, n_neg)
                                         < low_support_threshold))
    both = n_pos > 0 and n_neg > 0
    out["roc_auc"] = round(float(roc_auc_score(y, p)), 4) if both else None
    out["pr_auc"] = round(float(average_precision_score(y, p)), 4) if both else None
    out["log_loss"] = round(float(log_loss(y, p, labels=[0, 1])), 4)
    out["brier"] = round(float(brier_score_loss(y, p)), 4)
    return out


def board_metrics(y, p, ks, seed=20260808):
    """Precision@K / Recall@K / NDCG@K on the induced ranking.

    Ties are broken by a SEEDED random permutation, not by row order — see the
    module docstring.
    """
    y = np.asarray(y).astype(int)
    p = np.asarray(p, dtype="float64")
    rng = np.random.default_rng(seed)
    jitter = rng.permutation(len(p))
    order = np.lexsort((jitter, -p))
    ys = y[order]
    out = {}
    total_pos = int(y.sum())
    for name, k in ks.items():
        k = max(1, min(int(k), len(y)))
        hit = int(ys[:k].sum())
        out[f"precision_at_{name}"] = round(hit / k, 4)
        out[f"recall_at_{name}"] = round(hit / total_pos, 4) if total_pos else None
        disc = 1.0 / np.log2(np.arange(2, k + 2))
        dcg = float((ys[:k] * disc).sum())
        ideal = np.sort(y)[::-1][:k]
        idcg = float((ideal * disc).sum())
        out[f"ndcg_at_{name}"] = round(dcg / idcg, 4) if idcg > 0 else None
        out[f"k_{name}"] = k
    return out


def calibration_bins(y, p, n_bins=10):
    df = pd.DataFrame({"y": np.asarray(y).astype(int),
                       "p": np.asarray(p, dtype="float64")})
    df["bin"] = pd.qcut(df.p, q=n_bins, duplicates="drop", labels=False)
    g = df.groupby("bin").agg(n=("y", "size"), mean_pred=("p", "mean"),
                              observed=("y", "mean")).reset_index()
    g["gap"] = (g.mean_pred - g.observed).round(4)
    return g.round(4)


def expected_calibration_error(y, p):
    """ECE — support-weighted mean |predicted - observed| across the deciles.

    Reported alongside the max gap because a single sparse decile can dominate
    the max while the model is well behaved everywhere else (ML4_REPORT 13).
    """
    cb = calibration_bins(y, p)
    return round(float((cb.n * cb.gap.abs()).sum() / cb.n.sum()), 4)


# ----------------------------------------------------------------- Stage B
def strength(pred_pick):
    """CANONICAL ORIENTATION. Higher strength = better = earlier pick.

    The only place a sign is applied anywhere in Stage B.
    """
    return -np.asarray(pred_pick, dtype="float64")


def stage_b_metrics(actual_pick, pred_pick, size):
    """Rank metrics first — the product outputs an order, not a pick."""
    a = np.asarray(actual_pick, dtype="float64")
    p = np.asarray(pred_pick, dtype="float64")
    s_true, s_pred = strength(a), strength(p)
    n = len(a)
    out = dict(n=n)

    constant = float(np.std(s_pred)) == 0.0
    if constant or n < 3:
        out.update(spearman=None, kendall_tau=None, ndcg=None,
                   ndcg_at_5=None, ndcg_at_10=None, ndcg_at_14=None,
                   constant_prediction=True)
    else:
        out["spearman"] = round(float(spearmanr(s_pred, s_true).statistic), 4)
        out["kendall_tau"] = round(float(kendalltau(s_pred, s_true).statistic), 4)
        rel = (np.asarray(size, dtype="float64") + 1.0 - a).reshape(1, -1)
        sc = s_pred.reshape(1, -1)
        out["ndcg"] = round(float(ndcg_score(rel, sc)), 4)
        for k in (5, 10, 14):
            out[f"ndcg_at_{k}"] = round(float(ndcg_score(rel, sc, k=min(k, n))), 4)
        out["constant_prediction"] = False

    err = p - a
    out["mae_pick"] = round(float(np.mean(np.abs(err))), 4)
    out["rmse_pick"] = round(float(np.sqrt(np.mean(err ** 2))), 4)
    out["median_ae_pick"] = round(float(np.median(np.abs(err))), 4)

    # board-level, among in-scope NCAA early entrants only
    order = np.argsort(-s_pred, kind="stable")
    for label, cut in (("lottery", 14), ("first_round", 30)):
        k = min(cut, n)
        actual_in = a <= cut
        hit = int(actual_in[order[:k]].sum())
        tot = int(actual_in.sum())
        out[f"{label}_recall_at_{cut}"] = round(hit / tot, 4) if tot else None
    half = max(1, n // 2)
    out["top_half_concentration"] = round(
        float((a[order[:half]] <= np.median(a)).mean()), 4)
    return out


def tier_metrics(actual_tier, pred_tier):
    """Order-respecting tier metrics. The estimator producing `pred_tier` is
    multinomial and does NOT know the tiers are ordered — only this does."""
    a = np.asarray(actual_tier, dtype=int)
    p = np.asarray(pred_tier, dtype=int)
    d = np.abs(a - p)
    return dict(exact_tier_accuracy=round(float((d == 0).mean()), 4),
                adjacent_tier_accuracy=round(float((d <= 1).mean()), 4),
                ordered_distance_error=round(float(d.mean()), 4),
                macro_f1=round(float(f1_score(a, p, average="macro",
                                              labels=[0, 1, 2],
                                              zero_division=0)), 4))
