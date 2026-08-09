"""General Draft Board — combining Stage A and Stage B into one ranking.

Implemented in ML-6 (DEC-096..100). The board answers one product question:

    Among declared NCAA early entrants, which prospects does the pre-draft
    record support, and how strongly?

Two frozen signals feed it:

    Stage A  P(drafted)            trained on ALL early entrants
    Stage B  conditional draft-order signal   trained on DRAFTED prospects only

Stage B is applied to every prospect on the board, including those who
historically went undrafted. That is legitimate and it means one specific thing:

    "If this basketball profile were draftable, which part of the draft does it
     resemble?"

It is NOT a claim the prospect will be drafted, and NOT a pick assignment. The
underlying target is untouched: an undrafted prospect keeps `drafted = 0` and
`pick = NULL`. No synthetic pick is created anywhere in this module.

THREE SEPARATE PRODUCT SIGNALS, never collapsed into one label:
    Overall Draft Score      0-100 ranking score      (this module)
    Draft Probability        Stage A                  (the only real probability)
    Draft Position Signal    Stage B                  (never a literal pick)

The 2026 holdout is not reachable from here.
"""

import json

import numpy as np
import pandas as pd

from draftlens.paths import CONFIG_ML

CONFIG_PATH = CONFIG_ML / "ml6_board.json"

# ML-6 selection. See docs/experiments/ML6_BOARD.md for the evidence.
BOARD = {
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

    Shares the convention used throughout Stage B (`draftlens.ml.metrics
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
    method = method or BOARD["method"]
    transform = transform or BOARD["stage_b_transform"]
    score_method = score_method or BOARD["score_transform"]

    q = transform_stage_b_signal(stage_b_predicted_pick, draft_size, transform,
                                 reference_predictions)
    signal = combine_board_signals(p_drafted, q, method)
    return pd.DataFrame({
        "stage_a_probability": np.asarray(p_drafted, dtype="float64"),
        "stage_b_quality": q,
        "final_board_signal": signal,
        "overall_score": overall_score(signal, score_method, reference_signals),
    })
