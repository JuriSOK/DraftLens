"""Fit Score: custom weighted needs and predefined archetypes.

FIT SCORE SCALE — a deliberate departure from the Overall Score. Dimension
scores are already NCAA peer percentiles, so a weighted combination of them
already carries absolute trait meaning on 0-100: "72" means "this profile sits
around the 72nd percentile of NCAA peers on the traits you asked for". Re-ranking
within the draft class would destroy exactly that meaning — "92nd percentile
three-point volume" would collapse into "4th of 49 in this class".

The General Draft Board goes the other way (class-relative) because a board rank
IS what that mode means. The two scores are different by design, and neither is
a probability.

WEIGHTS ARE PREFERENCES. Nothing here is fitted. Team Need has no ground-truth
target, so there is no quantity to optimise against — and optimising against
draft outcomes would answer the General Board's question instead.
"""

import numpy as np
import pandas as pd

from draftlens.team_need.dimensions import (ATHLETICISM, CONFIG,
                                            compute_components,
                                            compute_dimensions, data_coverage)
from draftlens.team_need.profiles import (ELIGIBLE, OUT_OF_POSITION, PROFILES,
                                          UNKNOWN_POSITION, score_profile)
from draftlens.team_need.reference import PercentileReference

CUSTOM = CONFIG["custom_mode"]
SUPPORTED_DIMENSIONS = list(CUSTOM["supported_dimensions"])
OPTIONAL_DIMENSIONS = [CUSTOM["optional_dimension"]]
UNAVAILABLE_DIMENSIONS = list(CUSTOM["unavailable_dimensions"])
MIN_SUPPORTED_WEIGHT = CONFIG["coverage"]["custom_min_supported_weight"]

UNAVAILABLE = "UNAVAILABLE"


class UnsupportedNeed(ValueError):
    """A custom request the engine will not answer, rather than answer badly."""


def validate_weights(weights):
    """Check a custom request before scoring anything.

    Athleticism is rejected outright, never silently dropped or redistributed:
    there is no athleticism measurement in the data, and manufacturing one from
    box-score statistics is prohibited (ML_SPEC §18.2).
    """
    if not isinstance(weights, dict) or not weights:
        raise UnsupportedNeed("provide a mapping of dimension -> weight")

    unknown = [k for k in weights
               if k not in SUPPORTED_DIMENSIONS + OPTIONAL_DIMENSIONS
               + UNAVAILABLE_DIMENSIONS]
    if unknown:
        raise UnsupportedNeed(f"unknown dimension(s): {sorted(unknown)}")

    negative = [k for k, v in weights.items() if float(v) < 0]
    if negative:
        raise UnsupportedNeed(f"weights must be >= 0; negative: {sorted(negative)}")

    for name in UNAVAILABLE_DIMENSIONS:
        if float(weights.get(name, 0)) > 0:
            raise UnsupportedNeed(
                f"{name} is UNAVAILABLE: there is no athleticism measurement in "
                f"the data and no proxy may be fabricated from box-score "
                f"statistics. Its weight is not silently redistributed — remove "
                f"it or set it to 0.")

    active = {k: float(v) for k, v in weights.items() if float(v) > 0}
    if not active:
        raise UnsupportedNeed("at least one weight must be > 0")
    return active


def custom_fit(df, weights, reference=None, components=None, dim_scores=None,
               coverage=None):
    """Score a custom team need.

        fit_raw = sum(w_i * d_i) / sum(w_i)   over REQUESTED and AVAILABLE dims

    `supported_weight` records how much of the requested weight actually landed
    on a scorable dimension. Below the declared minimum the Fit Score is
    UNAVAILABLE rather than a number built from a fraction of what was asked —
    a prospect missing the one dimension a team weighted at 70% has not been
    evaluated for that need.
    """
    active = validate_weights(weights)
    reference = reference if reference is not None else PercentileReference()
    if components is None:
        components, _ = compute_components(df, reference)
    if dim_scores is None or coverage is None:
        dim_scores, coverage = compute_dimensions(df, reference, components)

    total = sum(active.values())
    num = np.zeros(len(df), dtype="float64")
    supported = np.zeros(len(df), dtype="float64")
    for name, w in active.items():
        d = dim_scores[name].to_numpy(dtype="float64")
        ok = np.isfinite(d)
        num += np.where(ok, d * w, 0.0)
        supported += np.where(ok, w, 0.0)

    with np.errstate(invalid="ignore", divide="ignore"):
        fit_raw = np.where(supported > 0, num / np.where(supported > 0,
                                                         supported, 1.0), np.nan)
    frac = supported / total
    fit_raw = np.where(frac >= MIN_SUPPORTED_WEIGHT, fit_raw, np.nan)

    out = pd.DataFrame(index=df.index)
    out["fit_raw"] = fit_raw
    out["fit_score"] = fit_score(fit_raw)
    out["supported_weight_fraction"] = frac
    out["data_coverage"] = data_coverage(coverage).to_numpy()
    out["eligibility_status"] = ELIGIBLE
    out["status"] = np.where(np.isfinite(fit_raw), "OK", UNAVAILABLE)
    return out


def profile_fit(df, profile, reference=None, components=None, dim_scores=None,
                coverage=None, combination=None):
    """Score one predefined archetype, on the same Fit Score scale."""
    reference = reference if reference is not None else PercentileReference()
    if components is None:
        components, _ = compute_components(df, reference)
    if dim_scores is None or coverage is None:
        dim_scores, coverage = compute_dimensions(df, reference, components)

    r = score_profile(df, profile, reference, components, dim_scores,
                      combination)
    out = pd.DataFrame(index=df.index)
    for c in r.columns:
        if c.startswith("pillar_"):
            out[c] = r[c]
    out["fit_raw"] = r.profile_score
    out["fit_score"] = fit_score(r.profile_score)
    out["data_coverage"] = data_coverage(coverage).to_numpy()
    out["eligibility_status"] = r.eligibility_status
    out["status"] = np.where(np.isfinite(r.profile_score), "OK", UNAVAILABLE)
    return out


def fit_score(fit_raw):
    """Integer 0-100. NaN stays NaN — an unavailable score is not a zero."""
    v = np.asarray(fit_raw, dtype="float64")
    out = np.full(len(v), np.nan)
    ok = np.isfinite(v)
    out[ok] = np.rint(np.clip(v[ok], 0.0, 100.0))
    return out


def rank_fit(scored, enforce_eligibility=True):
    """Board order for a need: best fit first.

    Ordering is by the CONTINUOUS `fit_raw`, so integer rounding never reorders
    anything. Ties are genuine ties. Nothing here consults a draft outcome, an
    actual pick or any NBA information — Team Need does not know they exist.
    """
    df = scored.copy()
    rank_order = {ELIGIBLE: 0, UNKNOWN_POSITION: 0, OUT_OF_POSITION: 1}
    df["_elig"] = (df.eligibility_status.map(rank_order).fillna(0)
                   if enforce_eligibility else 0)
    df["_missing"] = (~np.isfinite(df.fit_raw)).astype(int)
    df = df.sort_values(["_missing", "_elig", "fit_raw"],
                        ascending=[True, True, False], kind="stable")
    df["fit_rank"] = np.arange(1, len(df) + 1)
    return df.drop(columns=["_elig", "_missing"])
