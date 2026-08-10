"""Factual basketball dimensions, on an NCAA peer-percentile scale.

Each dimension is a small set of non-redundant metrics, converted to percentiles
against the season's NCAA population and combined by an equal-weight rule. There
are no fitted coefficients anywhere: Team Need has no ground-truth target, so
there is nothing to fit against and any weight learned from draft outcomes would
be answering a different question.

Three rules are enforced in code rather than left to callers:

  ORIENTATION. Every component percentile is oriented HIGHER = BETTER FOR THE
  TRAIT before combination. `tov_pct` is inverted; a caller can never
  accidentally reward turnovers.

  MISSING IS NEVER ZERO. An absent component is dropped and the dimension
  renormalises over what remains. Filling with 0 would make missingness a
  signal, and missing-data rows were disproportionately undrafted historically
  (DEC-071) — that is how the outcome would sneak back in.

  RELIABILITY. A rate computed from a handful of attempts is noise, so a
  component whose denominator falls below its declared minimum is treated as
  MISSING, not as a real low value. 2-for-4 from three is not evidence.

Nothing here reads a draft outcome, a pick, a General Board signal, age, or a
contaminated position label.
"""

import json
import warnings

import numpy as np
import pandas as pd

from paths import CONFIG
from team_need.reference import (GLOBAL_GROUP, PercentileReference,
                                           percentile_frame)

CONFIG_PATH = CONFIG / "team_need.json"

ATHLETICISM = "ATHLETICISM"


def load_config(path=CONFIG_PATH):
    return json.loads(path.read_text())


CONFIG = load_config()
DIMENSIONS = CONFIG["dimensions"]
RELIABILITY = CONFIG["reliability_minimums"]
MIN_COMPONENT_FRACTION = CONFIG["coverage"]["dimension_min_component_fraction"]


def component_metrics(dimension):
    return [c["metric"] for c in DIMENSIONS[dimension]["components"]]


def orientation(dimension, metric):
    for c in DIMENSIONS[dimension]["components"]:
        if c["metric"] == metric:
            return c["orientation"]
    raise KeyError(f"{metric} is not a component of {dimension}")


def reference_spec():
    """metric -> reference group, resolved across every dimension.

    A metric used by two dimensions must resolve to the same group, otherwise
    the same statistic would mean two different things on one board.
    """
    spec = {}
    for name, d in DIMENSIONS.items():
        for c in d["components"]:
            group = d["reference_group"]
            prev = spec.get(c["metric"])
            if prev is not None and prev != group:
                raise ValueError(
                    f"{c['metric']} is declared {prev} in one dimension and "
                    f"{group} in {name} — a metric must mean one thing")
            spec[c["metric"]] = group
    return spec


def apply_reliability(df, percentiles):
    """Blank out component percentiles whose denominator is too thin.

    Returns a copy; the prospect is never dropped, only that one component.
    """
    out = percentiles.copy()
    for metric, rule in RELIABILITY.items():
        if metric not in out.columns:
            continue
        den = pd.to_numeric(df.get(rule["denominator"]), errors="coerce")
        out.loc[(den.isna() | (den < rule["min"])).to_numpy(), metric] = np.nan
    return out


def orient(percentiles, dimension):
    """Flip LOWER_IS_BETTER components so higher always means better."""
    out = percentiles.copy()
    for c in DIMENSIONS[dimension]["components"]:
        if c["orientation"] == "LOWER_IS_BETTER" and c["metric"] in out.columns:
            out[c["metric"]] = 100.0 - out[c["metric"]]
    return out


def _min_components(n):
    return max(1, int(np.ceil(MIN_COMPONENT_FRACTION * n)))


def combine(values, method="ARITHMETIC_MEAN"):
    """Combine oriented 0-100 pillar values.

    ARITHMETIC_MEAN allows one strong pillar to compensate for a weak one.
    GEOMETRIC_MEAN does not — which is the point for conjunctive archetypes: a
    prospect elite at shooting and poor at defence is not a 3&D wing.
    """
    v = np.asarray(values, dtype="float64")
    if v.size == 0 or not np.isfinite(v).any():
        return np.nan
    v = v[np.isfinite(v)]
    if method == "ARITHMETIC_MEAN":
        return float(np.mean(v))
    if method == "GEOMETRIC_MEAN":
        # a 0 pillar legitimately zeroes a conjunctive profile; clip only to
        # keep the logarithm finite
        return float(np.exp(np.mean(np.log(np.clip(v, 1e-9, None)))))
    raise ValueError(method)


def compute_components(df, reference=None):
    """Oriented, reliability-filtered component percentiles for every metric.

    Returns (components, raw_percentiles). `raw_percentiles` keeps the
    un-inverted values so explanations can quote the statistic a scout
    recognises ("18th percentile turnover rate") rather than its inversion.
    """
    reference = reference if reference is not None else PercentileReference()
    spec = reference_spec()
    raw = percentile_frame(df, spec, reference)
    raw = apply_reliability(df, raw)

    oriented = raw.copy()
    for name in DIMENSIONS:
        flipped = orient(raw[[m for m in component_metrics(name)
                              if m in raw.columns]], name)
        for m in flipped.columns:
            oriented[m] = flipped[m]
    return oriented, raw


def compute_dimensions(df, reference=None, components=None):
    """Score every dimension for every prospect.

    Returns (scores, coverage) — both DataFrames indexed like `df`. A dimension
    is NaN where too few components are available; it is never 0 and never 50.
    """
    if components is None:
        components, _ = compute_components(df, reference)

    scores = pd.DataFrame(index=df.index)
    coverage = pd.DataFrame(index=df.index)
    for name, d in DIMENSIONS.items():
        metrics = [m for m in component_metrics(name) if m in components.columns]
        block = components[metrics].to_numpy(dtype="float64")
        available = np.isfinite(block).sum(axis=1)
        need = _min_components(len(metrics))
        # rows with no available component produce an empty slice; that is the
        # expected "dimension unavailable" case, not an error
        with np.errstate(invalid="ignore"), warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            mean = np.nanmean(np.where(np.isfinite(block), block, np.nan),
                              axis=1)
        scores[name] = np.where(available >= need, mean, np.nan)
        coverage[name] = available / max(1, len(metrics))
    return scores, coverage


def data_coverage(coverage):
    """Overall fraction of dimension components available.

    Reported ALONGSIDE a Fit Score and never inside it. A prospect must not
    score higher merely because more data exists for them.
    """
    return coverage.mean(axis=1)


def position_relative_size(df, reference=None):
    """SIZE on the position-relative reference, for the sensitivity analysis.

    Not part of the shipped SIZE dimension — see the config rationale: making
    size position-relative places every centre near the 50th percentile and
    destroys what Rim Protector and Stretch Big are asking about.
    """
    reference = reference if reference is not None else PercentileReference()
    pct = percentile_frame(df, {"height": "POSITION", "weight": "POSITION"},
                           reference)
    return pct.mean(axis=1)
