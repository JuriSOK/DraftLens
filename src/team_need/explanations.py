"""Deterministic explanations for a Team Need score.

Structured components only — no generative model, no subjective scouting prose.
The UI renders these later; this module decides WHAT is said, never how it reads.

Two rules keep explanations honest:

  A MISSING COMPONENT IS NEVER A WEAKNESS. If a prospect has too few three-point
  attempts to judge their shooting, that is an absence of evidence, not evidence
  of poor shooting. Missing components are listed separately.

  THE STATISTIC IS QUOTED IN ITS NATURAL DIRECTION. An inverted component is
  reported as the statistic a scout recognises — "18th percentile turnover rate"
  — with a flag saying lower is better, rather than as its inversion.
"""

import numpy as np
import pandas as pd

from team_need.dimensions import (CONFIG, DIMENSIONS,
                                            component_metrics, orientation)
from team_need.profiles import PROFILES

# A component is called a strength / limiter only past these percentiles.
STRENGTH_MIN = 60.0
LIMITER_MAX = 40.0

METRIC_LABELS = {
    "three_point_pct": "three-point efficiency",
    "three_point_attempt_rate": "three-point volume",
    "ft_pct": "free-throw touch",
    "efg_pct": "effective field-goal percentage",
    "ast_pct": "assist rate",
    "tov_pct": "turnover rate",
    "stl_pct": "steal rate",
    "blk_pct": "block rate",
    "orb_pct": "offensive rebounding rate",
    "drb_pct": "defensive rebounding rate",
    "height": "height",
    "weight": "weight",
    "rim_attempt_share": "share of shots at the rim",
    "free_throw_rate": "free-throw rate",
    "rim_make_pct": "finishing at the rim",
    "unassisted_made_fg_share": "self-created shot share",
}


def metric_label(metric):
    return METRIC_LABELS.get(metric, metric.replace("_", " "))


def relevant_metrics(request):
    """Which components matter for this need.

    `request` is a profile name or a dict of custom dimension weights. Only
    components that actually feed the requested score are eligible to appear.
    """
    if isinstance(request, str):
        spec = PROFILES[request]
        if spec["combination"] == "DIMENSION":
            dims = [spec["dimension"]]
            extra = []
        else:
            dims, extra = [], []
            for p in spec["pillars"]:
                if p["source"] == "DIMENSION":
                    dims.append(p["dimension"])
                else:
                    extra += list(p["metrics"])
        out = []
        for d in dims:
            out += component_metrics(d)
        return list(dict.fromkeys(out + extra)), dims
    dims = [k for k, w in request.items() if float(w) > 0]
    out = []
    for d in dims:
        out += component_metrics(d)
    return list(dict.fromkeys(out)), dims


def _dimension_of(metric, dims):
    """Owning dimension, preferring one the request actually asked for.

    Falls back to any dimension containing the metric so that orientation is
    still resolved for profiles built from bare metrics rather than whole
    dimensions (the Shooter pillars, for example).
    """
    for d in dims:
        if d in DIMENSIONS and metric in component_metrics(d):
            return d
    for d in DIMENSIONS:
        if metric in component_metrics(d):
            return d
    return None


def explain(components, raw_percentiles, request, index=None,
            n_strengths=2, n_limiters=2):
    """Structured explanation rows for every prospect.

    Returns a frame with `strengths`, `limiting_components` and
    `missing_components`, each a list of dicts the UI can render directly.
    """
    metrics, dims = relevant_metrics(request)
    metrics = [m for m in metrics if m in components.columns]
    idx = index if index is not None else components.index

    strengths, limiters, missing = [], [], []
    oriented = components[metrics]
    natural = raw_percentiles[metrics]

    for i in idx:
        o = oriented.loc[i]
        n = natural.loc[i]
        present = [m for m in metrics if np.isfinite(o[m])]
        absent = [m for m in metrics if not np.isfinite(o[m])]

        ranked = sorted(present, key=lambda m: (-float(o[m]), m))
        s = [_component(m, o[m], n[m], dims) for m in ranked[:n_strengths]
             if float(o[m]) >= STRENGTH_MIN]
        low = sorted(present, key=lambda m: (float(o[m]), m))
        lim = [_component(m, o[m], n[m], dims) for m in low[:n_limiters]
               if float(o[m]) <= LIMITER_MAX]

        strengths.append(s)
        limiters.append(lim)
        # absence of evidence, listed separately and never called a weakness
        missing.append([{"metric": m, "label": metric_label(m),
                         "reason": "insufficient evidence"} for m in absent])

    return pd.DataFrame({"strengths": strengths,
                         "limiting_components": limiters,
                         "missing_components": missing}, index=idx)


def _component(metric, oriented_value, natural_value, dims):
    d = _dimension_of(metric, dims)
    lower_better = (d is not None
                    and orientation(d, metric) == "LOWER_IS_BETTER")
    return {"metric": metric,
            "label": metric_label(metric),
            "percentile": round(float(natural_value), 1),
            "oriented_percentile": round(float(oriented_value), 1),
            "lower_is_better": bool(lower_better),
            "dimension": d}
