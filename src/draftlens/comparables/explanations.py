"""Deterministic decomposition of why two profiles are close.

Structured fields only — no generative model, no scouting prose. The UI renders
these later; this module decides WHAT is said.

The output is a per-dimension delta, split into what the two profiles share and
where they diverge. That is the honest description of a distance: a distance is
a sum over dimensions, so it can always be reported dimension by dimension.

LANGUAGE GUARD. These describe a STATISTICAL RESEMBLANCE and nothing else.
"Projected", "ceiling", "floor", "will become" and "expected career" are
prohibited — the comparison is descriptive, not predictive.
"""

import numpy as np

from draftlens.comparables.space import DIMENSIONS, DIMENSION_NAMES

# Dimensions closer than this are "shared"; farther are "differences".
CLOSE_PERCENTILE_GAP = 15.0
FAR_PERCENTILE_GAP = 25.0

LABELS = {
    "SHOOTING_EFFICIENCY": "shooting efficiency",
    "SCORING_ROLE": "scoring role",
    "CREATION": "passing / creation role",
    "REBOUNDING": "rebounding role",
    "DEFENSIVE_ACTIVITY": "box-score defensive activity",
    "PERIMETER_ORIENTATION": "perimeter vs interior shot diet",
}


def dimension_label(dimension):
    return LABELS.get(dimension, dimension.replace("_", " ").lower())


def explain_pair(prospect_row, nba_row, dimensions=None, n_close=3, n_far=2):
    """Per-dimension comparison of one prospect against one NBA player.

    Returns `dimension_delta` (every shared dimension), `closest_dimensions`
    and `largest_differences`. A dimension missing for either side is reported
    as unavailable and never counted as a difference — absence of evidence is
    not evidence of divergence.
    """
    dimensions = list(dimensions if dimensions is not None else DIMENSION_NAMES)
    deltas, missing = [], []
    for d in dimensions:
        a = prospect_row.get(d, np.nan)
        b = nba_row.get(d, np.nan)
        if not (np.isfinite(a) and np.isfinite(b)):
            missing.append({"dimension": d, "label": dimension_label(d),
                            "reason": "not available for both players"})
            continue
        deltas.append({
            "dimension": d,
            "label": dimension_label(d),
            "kind": DIMENSIONS[d]["kind"],
            "prospect_percentile": round(float(a), 1),
            "nba_percentile": round(float(b), 1),
            "delta": round(float(a - b), 1),
            "abs_delta": round(abs(float(a - b)), 1),
        })

    ranked = sorted(deltas, key=lambda x: (x["abs_delta"], x["dimension"]))
    close = [d for d in ranked if d["abs_delta"] <= CLOSE_PERCENTILE_GAP][:n_close]
    far = [d for d in reversed(ranked)
           if d["abs_delta"] >= FAR_PERCENTILE_GAP][:n_far]
    return {"dimension_delta": deltas,
            "closest_dimensions": close,
            "largest_differences": far,
            "unavailable_dimensions": missing}


def explain_comparables(prospect_row, pool_dims, pool, result, dimensions=None):
    """Attach a per-dimension explanation to each returned comparable."""
    if result.get("status") != "OK":
        return result
    by_id = {int(i): k for k, i in enumerate(pool.athlete_id.to_numpy())}
    out = dict(result)
    enriched = []
    for c in result["comparables"]:
        row = pool_dims.iloc[by_id[c["nba_player_id"]]]
        e = explain_pair(prospect_row, row, dimensions)
        enriched.append({**c, **{k: e[k] for k in
                                 ("closest_dimensions", "largest_differences",
                                  "dimension_delta", "unavailable_dimensions")}})
    out["comparables"] = enriched
    return out
