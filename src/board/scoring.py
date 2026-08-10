"""General Draft Board — combining Draft Probability and Draft Order into one
ranking.

The board answers one product question:

    Among declared NCAA early entrants, which prospects does the pre-draft
    record support, and how strongly?

Two frozen signals feed it:

    Draft Probability  P(drafted)                       trained on ALL early entrants
    Draft Order        conditional draft-order signal    trained on DRAFTED prospects only

Draft Order is applied to every prospect on the board, including those who
historically went undrafted. That is legitimate and it means one specific thing:

    "If this basketball profile were draftable, which part of the draft does it
     resemble?"

It is NOT a claim the prospect will be drafted, and NOT a pick assignment. The
underlying target is untouched: an undrafted prospect keeps `drafted = 0` and
`pick = NULL`. No synthetic pick is created anywhere in this module.

THREE SEPARATE PRODUCT SIGNALS, never collapsed into one label:
    Overall Score       0-100 ranking score      (this module)
    Draft Probability                            (the only real probability)
    Draft Order signal                           (never a literal pick)

The 2026 holdout is not reachable from here.
"""

import json

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, ndcg_score, roc_auc_score

from paths import CONFIG

CONFIG_PATH = CONFIG / "board.json"

# See docs/METHODOLOGY.md for the evidence behind this selection.
GENERAL_BOARD = {
    "method": "C_MULTIPLICATIVE",
    "stage_b_transform": "DRAFT_SLOT_UTILITY",
    "score_transform": "CURRENT_BOARD_PERCENTILE",
    "score_range": (0, 100),
    "score_dtype": "int",
}

NEUTRAL_QUALITY = 0.5   # Stage-B-missing fallback for percentile transforms


def load_config(path=CONFIG_PATH):
    return json.loads(path.read_text())


# ------------------------------------------------------------- orientation
def stage_b_orientation(predicted_pick):
    """CANONICAL: higher = better = earlier predicted pick.

    Shares the convention used throughout Stage B (`board.order
    .strength`); defined here too so board code never has to remember a sign.
    """
    return -np.asarray(predicted_pick, dtype="float64")


def within_board_percentile(values):
    """Percentile rank within one draft board, mapped to (0, 1).

    Uses the mid-rank convention so ties share a percentile, and never returns
    exactly 0 or 1 — a multiplicative board must not be able to zero out a
    prospect purely for being last on one axis.
    """
    s = pd.Series(np.asarray(values, dtype="float64"))
    r = s.rank(method="average", na_option="keep")
    n = int(r.notna().sum())
    if n == 0:
        return np.full(len(s), NEUTRAL_QUALITY)
    out = (r - 0.5) / n
    return out.fillna(NEUTRAL_QUALITY).to_numpy()


# -------------------------------------------------------- Stage B transform
def draft_slot_utility(predicted_pick, draft_size):
    """Predicted pick -> (0, 1] draft-slot utility, higher is better.

    Clipping to [1, draft_size] is PREDECLARED, not fitted: a prediction outside
    the slot range is not a meaningful draft position. On development
    out-of-fold data this touches 1 of 617 rows (0.16%), all on the low side.
    """
    p = np.asarray(predicted_pick, dtype="float64")
    size = np.asarray(draft_size, dtype="float64")
    clipped = np.clip(p, 1.0, size)
    return (size + 1.0 - clipped) / size


def historical_empirical_percentile(predicted_pick, reference_predictions):
    """Percentile of a prediction against a TRAINING-year reference distribution.

    The validation year never defines its own transform, so no future
    distributional information enters. The reference is in-sample for the fitted
    Stage B model, which makes it mildly optimistic — recorded, not hidden.
    """
    ref = np.sort(np.asarray(reference_predictions, dtype="float64"))
    q = stage_b_orientation(predicted_pick)
    ref_q = np.sort(stage_b_orientation(ref))
    if ref_q.size == 0:
        return np.full(len(q), NEUTRAL_QUALITY)
    pos = np.searchsorted(ref_q, q, side="left")
    return (pos + 0.5) / (ref_q.size + 1.0)


def transform_stage_b_signal(predicted_pick, draft_size, method,
                             reference_predictions=None):
    """Turn a raw Stage B predicted pick into a (0, 1] quality on one board.

    Missing predictions receive the NEUTRAL value rather than a low one: rows
    with missing basketball data were disproportionately undrafted historically,
    so penalising missingness would smuggle the outcome back in as a feature.
    """
    p = np.asarray(predicted_pick, dtype="float64")
    missing = ~np.isfinite(p)

    if method == "WITHIN_BOARD_PERCENTILE":
        q = within_board_percentile(np.where(missing, np.nan,
                                             stage_b_orientation(p)))
    elif method == "DRAFT_SLOT_UTILITY":
        q = draft_slot_utility(np.where(missing, np.nan, p), draft_size)
        if missing.any():
            neutral = float(np.nanmedian(q)) if np.isfinite(q).any() \
                else NEUTRAL_QUALITY
            q = np.where(missing, neutral, q)
    elif method == "HISTORICAL_EMPIRICAL_PERCENTILE":
        if reference_predictions is None:
            raise ValueError("HISTORICAL_EMPIRICAL_PERCENTILE needs a "
                             "training-year reference distribution")
        q = historical_empirical_percentile(np.where(missing, np.nan, p),
                                            reference_predictions)
        q = np.where(missing, NEUTRAL_QUALITY, q)
    else:
        raise ValueError(method)

    q = np.array(q, dtype="float64", copy=True)   # pandas views are read-only
    q[~np.isfinite(q)] = NEUTRAL_QUALITY
    return q


# ------------------------------------------------------------- combination
def combine_board_signals(p_drafted, stage_b_quality, method):
    """Combine the two frozen signals into one board signal, higher is better.

    No method here carries a fitted weight. `C_MULTIPLICATIVE` is an
    expectation — probability of entering the draft times the conditional
    quality of the slot the profile resembles — which is why it is preferred
    over any weighted sum of two differently-scaled quantities.
    """
    p = np.asarray(p_drafted, dtype="float64")
    q = np.asarray(stage_b_quality, dtype="float64")

    if method == "A_STAGE_A_ONLY":
        return p
    if method == "B_STAGE_B_ONLY":
        return q
    if method == "C_MULTIPLICATIVE":
        return p * q
    if method == "D_RANK_FUSION":
        # geometric mean of within-board percentile ranks; scale-free, no weights
        return np.sqrt(within_board_percentile(p) * within_board_percentile(q))
    if method == "E_LEXICOGRAPHIC":
        # Stage A decile band dominates; Stage B orders inside the band. Deciles
        # are a predeclared standard granularity, NOT tuned on validation.
        pa = within_board_percentile(p)
        band = np.floor(np.clip(pa, 0.0, 0.999999) * 10.0)
        return band + within_board_percentile(q) * 0.999
    if method == "F_EQUAL_WEIGHT_SUM":
        # HEURISTIC reference. The single equal-weight point; no other split is
        # evaluated anywhere in this project.
        return 0.5 * within_board_percentile(p) + 0.5 * within_board_percentile(q)
    raise ValueError(method)


# ------------------------------------------------------- graded relevance
def graded_relevance(drafted, pick, draft_size):
    """Board-evaluation relevance: 0 for undrafted, (0, 1] for drafted.

    THIS IS NOT A TARGET. It exists only to score a ranking. It never becomes a
    synthetic pick for an undrafted prospect and Stage B is never trained on it.

    Linear in draft slot and normalised by that year's verified draft size, so a
    late pick in a 58-pick draft is not penalised against a 60-pick draft. No
    exponential value curve: no external source justifies one here, and
    curvature is not a free parameter to tune.
    """
    d = np.asarray(drafted).astype(int)
    p = pd.to_numeric(pd.Series(pick), errors="coerce").to_numpy(dtype="float64")
    size = np.asarray(draft_size, dtype="float64")
    rel = np.zeros(len(d), dtype="float64")
    ok = (d == 1) & np.isfinite(p)
    rel[ok] = (size[ok] + 1.0 - p[ok]) / size[ok]
    return np.clip(rel, 0.0, 1.0)


# ------------------------------------------------------------ overall score
def overall_score(board_signal, method="CURRENT_BOARD_PERCENTILE",
                  reference_signals=None):
    """Final board signal -> integer 0-100 Overall Draft Score.

    ORDER-PRESERVING BY CONSTRUCTION: both transforms are monotone in the board
    signal, so score order can never disagree with board order (enforced by
    test). Equal signals receive equal scores; integer rounding may also tie two
    close-but-distinct signals, in which case the continuous board signal
    remains the authoritative order. Ties are never broken by name, outcome or
    any NBA information.

    NOT a probability and NOT a predicted pick.
    """
    s = np.asarray(board_signal, dtype="float64")
    if method == "CURRENT_BOARD_PERCENTILE":
        pct = within_board_percentile(s)
    elif method == "HISTORICAL_EMPIRICAL_PERCENTILE":
        if reference_signals is None:
            raise ValueError("HISTORICAL_EMPIRICAL_PERCENTILE needs a frozen "
                             "historical reference distribution")
        ref = np.sort(np.asarray(reference_signals, dtype="float64"))
        pos = np.searchsorted(ref, s, side="left")
        pct = (pos + 0.5) / (ref.size + 1.0)
    else:
        raise ValueError(method)
    return np.rint(np.clip(pct, 0.0, 1.0) * 100).astype(int)


def rank_board(df, signal_col="final_board_signal", score_col="overall_score"):
    """Sort one draft class into board order: best prospect first.

    Ordering is by the CONTINUOUS signal, so integer-score ties never reorder
    anything. `board_rank` is 1-based and dense.
    """
    out = df.sort_values(signal_col, ascending=False, kind="stable").copy()
    out["board_rank"] = np.arange(1, len(out) + 1)
    if score_col in out.columns:
        assert out[score_col].is_monotonic_decreasing, \
            "overall_score disagrees with board order"
    return out.reset_index(drop=True)


def build_board(p_drafted, stage_b_predicted_pick, draft_size,
                method=None, transform=None, score_method=None,
                reference_predictions=None, reference_signals=None):
    """One draft class -> board signal + Overall Score, using the frozen method.

    This is the production path. It needs ONLY pre-draft features (already
    reduced to the two stage outputs), the frozen estimators that produced them,
    and the frozen transforms. No target value is an input.
    """
    method = method or GENERAL_BOARD["method"]
    transform = transform or GENERAL_BOARD["stage_b_transform"]
    score_method = score_method or GENERAL_BOARD["score_transform"]

    q = transform_stage_b_signal(stage_b_predicted_pick, draft_size, transform,
                                 reference_predictions)
    signal = combine_board_signals(p_drafted, q, method)
    return pd.DataFrame({
        "stage_a_probability": np.asarray(p_drafted, dtype="float64"),
        "stage_b_quality": q,
        "final_board_signal": signal,
        "overall_score": overall_score(signal, score_method, reference_signals),
    })


# ----------------------------------------------------------------- evaluation
def board_binary_metrics(drafted, signal, ks):
    """Does the board rank drafted prospects above undrafted ones?

    The board signal is a RANKING score, not a probability, so no Brier or log
    loss is computed here — scoring an arbitrary rank score as if it were a
    probability would be exactly the false precision the product avoids
    elsewhere.
    """
    y = np.asarray(drafted).astype(int)
    s = np.asarray(signal, dtype="float64")
    n_pos, n_neg = int(y.sum()), int((y == 0).sum())
    out = dict(n=len(y), drafted=n_pos, undrafted=n_neg,
               low_negative_support=bool(min(n_pos, n_neg) < 5))
    both = n_pos > 0 and n_neg > 0
    out["roc_auc"] = round(float(roc_auc_score(y, s)), 4) if both else None
    out["average_precision"] = round(float(average_precision_score(y, s)), 4) \
        if both else None

    order = np.argsort(-s, kind="stable")
    ys = y[order]
    for name, k in ks.items():
        k = max(1, min(int(k), len(y)))
        hit = int(ys[:k].sum())
        out[f"precision_at_{name}"] = round(hit / k, 4)
        out[f"recall_at_{name}"] = round(hit / n_pos, 4) if n_pos else None
        out[f"k_{name}"] = k
    return out


def board_graded_metrics(relevance, signal, ks=(14, 30)):
    """Graded NDCG over the FULL board — the one metric that rewards both jobs
    at once: drafted above undrafted, and early picks above late ones."""
    rel = np.asarray(relevance, dtype="float64").reshape(1, -1)
    s = np.asarray(signal, dtype="float64").reshape(1, -1)
    n = rel.shape[1]
    out = {"graded_ndcg": round(float(ndcg_score(rel, s)), 4)}
    for k in ks:
        out[f"graded_ndcg_at_{k}"] = round(float(ndcg_score(rel, s,
                                                            k=min(k, n))), 4)
    return out


def board_order_metrics(actual_pick, signal):
    """Among ACTUALLY DRAFTED prospects only: does the board preserve draft
    order? This is what tells us whether the combination kept Draft Order's
    value."""
    from board.order import strength
    p = np.asarray(actual_pick, dtype="float64")
    s = np.asarray(signal, dtype="float64")
    n = len(p)
    if n < 3 or float(np.std(s)) == 0.0:
        return dict(drafted_n=n, drafted_spearman=None, drafted_kendall=None,
                    drafted_ndcg=None, drafted_ndcg_at_14=None)
    from scipy.stats import kendalltau, spearmanr
    true_strength = strength(p)
    rel = (p.max() + 1.0 - p).reshape(1, -1)
    sc = s.reshape(1, -1)
    return dict(
        drafted_n=n,
        drafted_spearman=round(float(spearmanr(s, true_strength).statistic), 4),
        drafted_kendall=round(float(kendalltau(s, true_strength).statistic), 4),
        drafted_ndcg=round(float(ndcg_score(rel, sc)), 4),
        drafted_ndcg_at_14=round(float(ndcg_score(rel, sc, k=min(14, n))), 4))


def validate():
    """Recompute the board across every frozen fold and check it end to end.

    No experiment artifact is read: the out-of-fold board below is produced
    live from the frozen Draft Probability / Draft Order estimators, exactly
    as it would be for a real prospect. There is no ground truth for a "board"
    beyond the metrics this asserts — what can be checked is that nothing
    outcome-derived reaches the scoring path and that the output obeys its
    contract.

      ./.venv/bin/python scripts/validate.py
    """
    import inspect

    from board.order import DRAFT_ORDER, draft_sizes, strength
    from board.order import fit_predict_fold as order_fold
    from board.probability import DRAFT_PROBABILITY, feature_set
    from board.probability import fit_predict_fold as probability_fold
    from data.build import load_development
    from validation import (Guard, HOLDOUT_YEAR, check_chronology,
                            check_development_population, folds)

    g = Guard()
    dev = load_development()
    dev["draft_size"] = dev.draft_year.map(draft_sizes())
    feats = feature_set(DRAFT_PROBABILITY["feature_set"])

    rows = []
    for _, tr_years, vy in folds():
        tr_all = dev[dev.draft_year.isin(tr_years)].reset_index(drop=True)
        va = dev[dev.draft_year == vy].reset_index(drop=True)
        tr_dr = tr_all[tr_all.drafted == 1].reset_index(drop=True)
        p_a, _ = probability_fold(tr_all, va, feats)
        p_b, _ = order_fold(tr_dr, va, feats, family=DRAFT_ORDER["family"],
                            params={"alpha": DRAFT_ORDER["alpha"]},
                            target=DRAFT_ORDER["target"])
        b = build_board(p_a, p_b, va.draft_size)
        b["draft_year"] = vy
        b["canonical_prospect_id"] = va.canonical_prospect_id.to_numpy()
        b["actual_drafted"] = va.drafted.to_numpy()
        b["actual_pick"] = va.pick.to_numpy()
        b["draft_size"] = va.draft_size.to_numpy()
        rows.append(b)
    oof = pd.concat(rows, ignore_index=True)

    # 1. population integrity
    check_development_population(g, dev)
    g.check(oof.canonical_prospect_id.nunique() == len(oof),
            "duplicate prospects on the board")
    for vy, grp in oof.groupby("draft_year"):
        want = int((dev.draft_year == vy).sum())
        g.check(len(grp) == want,
                f"{vy}: board has {len(grp)} prospects, population has {want} "
                f"— the board dropped prospects")
    print(f"  1. population: 887 development / {len(oof)} out-of-fold, "
          f"no prospect dropped from any board")

    # 2. holdout firewall
    g.check(HOLDOUT_YEAR not in set(dev.draft_year), "2026 in development")
    g.check(HOLDOUT_YEAR not in set(oof.draft_year), "2026 on the board")
    print("  2. holdout firewall: 2026 absent from population and board")

    check_chronology(g)
    print("  3. chronology: no future year trains an earlier validation year")

    # 4. no target leakage into the scoring path
    params = set(inspect.signature(build_board).parameters)
    for banned in ("drafted", "pick", "actual_pick", "actual_drafted",
                   "relevance", "y", "target"):
        g.check(banned not in params,
                f"build_board accepts target information: {banned}")
    src = inspect.getsource(build_board)
    g.check("graded_relevance" not in src,
            "the scoring path can reach evaluation relevance")
    print("  4. target separation: production scoring needs only pre-draft "
          "inputs")

    # 5. no synthetic pick
    rel = graded_relevance(oof.actual_drafted, oof.actual_pick, oof.draft_size)
    und = (oof.actual_drafted == 0).to_numpy()
    g.check(bool(np.all(rel[und] == 0.0)),
            "an undrafted prospect received non-zero graded relevance")
    g.check(bool(oof.loc[oof.actual_drafted == 0, "actual_pick"].isna().all()),
            "an undrafted prospect was given a pick value")
    print("  5. no synthetic pick: undrafted keep pick=NULL and relevance=0")

    # 6. board signal integrity
    g.check(bool(np.isfinite(oof.final_board_signal).all()),
            "the board signal contains NaN or inf")
    g.check(bool(((oof.stage_a_probability >= 0)
                  & (oof.stage_a_probability <= 1)).all()),
            "Draft Probability outside [0, 1]")
    print("  6. board signal: finite, Draft Probability within [0, 1]")

    # 7. Overall Score
    g.check(bool(((oof.overall_score >= 0) & (oof.overall_score <= 100)).all()),
            "Overall Score outside 0-100")
    g.check(str(oof.overall_score.dtype).startswith("int"),
            f"Overall Score is {oof.overall_score.dtype}, must be integer")
    for vy, grp in oof.groupby("draft_year"):
        o = grp.sort_values("final_board_signal", ascending=False)
        g.check(bool(o.overall_score.is_monotonic_decreasing),
                f"{vy}: Overall Score order disagrees with the board signal")
    print(f"  7. Overall Score: integer, within 0-100, order matches the "
          f"board in all {oof.draft_year.nunique()} classes")

    # 8. frozen configuration unchanged
    g.check(DRAFT_PROBABILITY == {
        "family": "LogisticRegression", "feature_set": "SET_2_BOX_SHOT_PROFILE",
        "normalization": "SEASON_RELATIVE", "missing_strategy": "B_TRAIN_MEDIAN",
        "position_handling": "ONEHOT", "scaling": "STANDARD",
        "class_weight": "balanced", "C": 0.25, "calibration": "none"},
        "Draft Probability configuration changed")
    g.check(DRAFT_ORDER["family"] == "Ridge" and DRAFT_ORDER["alpha"] == 10.0
            and DRAFT_ORDER["target"] == "RAW_PICK",
            "Draft Order configuration changed")
    g.check(GENERAL_BOARD["method"] == "C_MULTIPLICATIVE",
            "General Board method changed")
    print("  8. frozen configuration: Draft Probability, Draft Order and "
          "General Board unchanged")

    return g.report()
