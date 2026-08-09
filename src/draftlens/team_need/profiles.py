"""The six predefined Team Need archetypes.

Every profile is a transparent combination of the factual dimensions. None has
a fitted weight, because Team Need has no target to fit against.

The important design choice is ARITHMETIC vs GEOMETRIC combination:

  Arithmetic mean allows compensation — a huge score on one pillar rescues a
  poor score on another. That is right when the pillars are substitutable
  evidence for one trait.

  Geometric mean does not compensate. That is right when the archetype REQUIRES
  all its pillars: a prospect who shoots brilliantly and defends poorly is not a
  3&D wing, and a guard who shoots well is not a stretch big. Conjunctive
  archetypes use the geometric mean for exactly this reason.

Position eligibility uses `position_3` (G/F/C/UNKNOWN) only — the sole
leakage-safe position source (DEC-067). UNKNOWN counts as eligible: excluding it
would penalise missing data, which historically correlates with going undrafted.
"""

import warnings

import numpy as np
import pandas as pd

from draftlens.team_need.dimensions import (CONFIG, combine, compute_components,
                                            compute_dimensions)
from draftlens.team_need.reference import (GLOBAL_GROUP, PercentileReference,
                                           percentile_frame)

PROFILES = CONFIG["profiles"]
ELIGIBLE, OUT_OF_POSITION, UNKNOWN_POSITION = ("ELIGIBLE", "OUT_OF_POSITION",
                                               "UNKNOWN_POSITION")


def profile_names():
    return list(PROFILES)


def eligibility(df, profile):
    """Deterministic position eligibility. Never reads a draft outcome."""
    rule = PROFILES[profile].get("eligibility")
    pos = df["position_3"].astype("string")
    if not rule:
        return pd.Series(ELIGIBLE, index=df.index)
    allowed = set(rule["position_3_in"])
    return pd.Series(
        np.where(pos.isna() | (pos == "UNKNOWN"), UNKNOWN_POSITION,
                 np.where(pos.isin(allowed), ELIGIBLE, OUT_OF_POSITION)),
        index=df.index)


def _pillar_values(pillar, df, components, dim_scores, reference):
    """One pillar of a profile, on the 0-100 peer-percentile scale."""
    source = pillar["source"]
    if source == "DIMENSION":
        return dim_scores[pillar["dimension"]].to_numpy(dtype="float64")
    if source == "MEAN":
        metrics = pillar["metrics"]
        if pillar.get("reference_group") == GLOBAL_GROUP:
            # e.g. Rim Protector blocks: absolute shot-blocking, not
            # "good for a guard" — otherwise a 6-foot guard reads as elite.
            vals = percentile_frame(df, {m: GLOBAL_GROUP for m in metrics},
                                    reference)
        else:
            vals = components[[m for m in metrics if m in components.columns]]
        block = vals.to_numpy(dtype="float64")
        # an all-missing row is the expected "pillar unavailable" case
        with np.errstate(invalid="ignore"), warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            return np.where(np.isfinite(block).any(axis=1),
                            np.nanmean(np.where(np.isfinite(block), block,
                                                np.nan), axis=1), np.nan)
    raise ValueError(source)


def score_profile(df, profile, reference=None, components=None,
                  dim_scores=None, combination=None):
    """Score one archetype for every prospect.

    Returns a frame with the profile score, its pillar values and the
    eligibility status. Score is NaN where the underlying evidence is missing —
    never 0, never 50.
    """
    if profile not in PROFILES:
        raise KeyError(f"unknown profile {profile}")
    reference = reference if reference is not None else PercentileReference()
    if components is None:
        components, _ = compute_components(df, reference)
    if dim_scores is None:
        dim_scores, _ = compute_dimensions(df, reference, components)

    spec = PROFILES[profile]
    method = combination or spec["combination"]

    if spec["combination"] == "DIMENSION":
        pillars = {spec["dimension"]:
                   dim_scores[spec["dimension"]].to_numpy(dtype="float64")}
        score = pillars[spec["dimension"]]
    else:
        pillars = {p["id"]: _pillar_values(p, df, components, dim_scores,
                                           reference)
                   for p in spec["pillars"]}
        stacked = np.column_stack(list(pillars.values()))
        score = np.array([combine(row, method) for row in stacked])
        # a conjunctive profile needs EVERY pillar; a missing one is not a zero
        score = np.where(np.isfinite(stacked).all(axis=1), score, np.nan)

    out = pd.DataFrame(
        {f"pillar_{k}": v for k, v in pillars.items()}, index=df.index)
    out["profile_score"] = score
    out["eligibility_status"] = eligibility(df, profile).to_numpy()
    return out


def score_all_profiles(df, reference=None, components=None, dim_scores=None):
    """Every archetype for every prospect, one column each."""
    reference = reference if reference is not None else PercentileReference()
    if components is None:
        components, _ = compute_components(df, reference)
    if dim_scores is None:
        dim_scores, _ = compute_dimensions(df, reference, components)
    out = pd.DataFrame(index=df.index)
    for name in PROFILES:
        r = score_profile(df, name, reference, components, dim_scores)
        out[name] = r.profile_score
        out[f"{name}__eligibility"] = r.eligibility_status
    return out
