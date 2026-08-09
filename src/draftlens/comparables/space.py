"""The shared NCAA/NBA statistical space.

Raw production is never compared across leagues. 19 NCAA points per game and 19
NBA points per game are not the same event: pace, spacing, role and competition
all differ. Instead each league's values are converted to percentiles WITHIN
THEIR OWN LEAGUE AND SEASON, and the resulting profile SHAPES are compared.

That normalisation is also what makes per-minute rates legitimate here. A
per-40 rate is never compared to a per-40 rate directly — it is ranked among
its own league's peers first, so the 40-vs-48-minute game length, pace and
competition differences cancel entirely. The question asked of both populations
is identical: where does this player sit among his own league?

STYLE vs QUALITY. Six role dimensions, and they are deliberately not all
"higher is better":

  QUALITY   SHOOTING_EFFICIENCY — more efficient is better, unambiguously.
  ROLE      SCORING_ROLE, CREATION, REBOUNDING, DEFENSIVE_ACTIVITY — these are
            volume/involvement axes. A high-usage scorer is not "better" than a
            low-usage specialist; he is different.
  STYLE     PERIMETER_ORIENTATION — neither end is better. A stretch shooter
            and a rim-attacking big sit at opposite ends and both are valid.

That mix is the point. If every dimension were "higher is better", an elite
prospect would simply match elite NBA players regardless of role, and the
system would be a goodness ranking wearing a similarity costume.

Equal weight per DIMENSION, not per metric — so shooting's three metrics do not
outvote creation's one.
"""

import warnings

import numpy as np
import pandas as pd

# Every dimension: metrics, orientation and what kind of axis it is.
# `invert` flips a metric so the dimension reads in one consistent direction.
DIMENSIONS = {
    "SHOOTING_EFFICIENCY": {
        "kind": "QUALITY",
        "metrics": ["three_point_pct", "ft_pct", "efg_pct"],
        "invert": [],
        "reads": "higher = more efficient scorer",
    },
    "SCORING_ROLE": {
        "kind": "ROLE",
        "metrics": ["points_per_40", "fga_per_40"],
        "invert": [],
        "reads": "higher = larger share of the offence runs through him",
    },
    "CREATION": {
        "kind": "ROLE",
        "metrics": ["assists_per_40"],
        "invert": [],
        "reads": "higher = more of a passing/creation role",
    },
    "REBOUNDING": {
        "kind": "ROLE",
        "metrics": ["oreb_per_40", "dreb_per_40"],
        "invert": [],
        "reads": "higher = more of a rebounding role",
    },
    "DEFENSIVE_ACTIVITY": {
        "kind": "ROLE",
        "metrics": ["steals_per_40", "blocks_per_40"],
        "invert": [],
        "reads": "higher = more box-score defensive events; NOT defensive quality",
    },
    "PERIMETER_ORIENTATION": {
        "kind": "STYLE",
        "metrics": ["three_point_attempt_rate", "free_throw_rate"],
        "invert": ["free_throw_rate"],
        "reads": "high = perimeter-oriented shot diet; low = interior/contact. "
                 "Neither end is better.",
    },
}

COMMON_METRICS = sorted({m for d in DIMENSIONS.values() for m in d["metrics"]})
DIMENSION_NAMES = list(DIMENSIONS)

# Reference-group policy. NBA labels map deterministically to G/F/C, so
# position-relative normalisation is testable — but GLOBAL is the shipped
# choice; see the ML-8 report.
GLOBAL_GROUP = "GLOBAL"


def _percentile_within(values, reference_values):
    """Percentile of each value against a reference distribution, 0-100.

    NaN in, NaN out. A missing metric is MISSING, never 0 — treating an absent
    measurement as the worst possible one would make missingness a signal.
    """
    v = pd.to_numeric(pd.Series(values), errors="coerce").to_numpy(
        dtype="float64")
    ref = pd.to_numeric(pd.Series(reference_values), errors="coerce").to_numpy(
        dtype="float64")
    ref = np.sort(ref[np.isfinite(ref)])
    out = np.full(len(v), np.nan)
    if ref.size == 0:
        return out
    ok = np.isfinite(v)
    # mid-rank: ties share a percentile
    lo = np.searchsorted(ref, v[ok], side="left")
    hi = np.searchsorted(ref, v[ok], side="right")
    out[ok] = 100.0 * (lo + hi) / (2.0 * ref.size)
    return np.clip(out, 0.0, 100.0)


def league_percentiles(df, reference, metrics=None, group_col=None,
                       season_col=None):
    """Percentile-rank `df`'s metrics against `reference`, within the league.

    `reference` is the population that defines "peers": the NCAA season
    population for a prospect, the NBA reference pool for an NBA player.
    Passing `season_col` ranks each season against its own peers; passing
    `group_col` additionally ranks within a coarse position group.
    """
    metrics = metrics if metrics is not None else COMMON_METRICS
    out = pd.DataFrame(index=df.index)
    for m in metrics:
        if m not in df.columns or m not in reference.columns:
            out[m] = np.nan
            continue
        col = np.full(len(df), np.nan)
        if season_col and season_col in df.columns \
                and season_col in reference.columns:
            for season, idx in df.groupby(season_col).groups.items():
                ref_s = reference[reference[season_col] == season]
                if ref_s.empty:
                    ref_s = reference
                pos_i = df.index.get_indexer(idx)
                col[pos_i] = _sub_percentile(df.loc[idx], ref_s, m, group_col)
        else:
            col = _sub_percentile(df, reference, m, group_col)
        out[m] = col
    return out


def _sub_percentile(sub, ref, metric, group_col):
    if not group_col or group_col not in sub.columns \
            or group_col not in ref.columns:
        return _percentile_within(sub[metric], ref[metric])
    vals = np.full(len(sub), np.nan)
    for grp, idx in sub.groupby(group_col).groups.items():
        r = ref[ref[group_col] == grp]
        if len(r) < 30:          # too thin to define a position percentile
            r = ref
        vals[sub.index.get_indexer(idx)] = _percentile_within(
            sub.loc[idx, metric], r[metric])
    return vals


def to_dimensions(percentiles, dimensions=None):
    """Collapse metric percentiles into role dimensions, 0-100.

    Equal weight per metric inside a dimension, and equal weight per dimension
    downstream — so a statistical family with more columns does not dominate
    the distance simply by being better represented in the source data.

    A dimension is NaN when it has no available metric; it is never 0 and never
    50, because a filled value would be indistinguishable from real evidence.
    """
    dimensions = dimensions if dimensions is not None else DIMENSIONS
    out = pd.DataFrame(index=percentiles.index)
    for name, spec in dimensions.items():
        cols = [m for m in spec["metrics"] if m in percentiles.columns]
        if not cols:
            out[name] = np.nan
            continue
        block = percentiles[cols].to_numpy(dtype="float64").copy()
        for j, m in enumerate(cols):
            if m in spec["invert"]:
                block[:, j] = 100.0 - block[:, j]
        # an all-missing row is the expected "dimension unavailable" case
        with np.errstate(invalid="ignore"), warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            mean = np.where(np.isfinite(block).any(axis=1),
                            np.nanmean(np.where(np.isfinite(block), block,
                                                np.nan), axis=1), np.nan)
        out[name] = mean
    return out


def build_ncaa_space(prospects, ncaa_reference, group_col=None,
                     season_col="draft_year", ref_season_col="season"):
    """A prospect's position in the common space, ranked among NCAA peers."""
    ref = ncaa_reference.rename(columns={ref_season_col: season_col}) \
        if ref_season_col != season_col and ref_season_col in ncaa_reference \
        else ncaa_reference
    pct = league_percentiles(prospects, ref, group_col=group_col,
                             season_col=season_col)
    return to_dimensions(pct), pct


def build_nba_space(pool, group_col=None):
    """An NBA player's position in the common space, ranked among NBA peers.

    The pool is both the population being ranked and its own reference: these
    are the players a prospect can be compared to, so they define the scale.
    """
    pct = league_percentiles(pool, pool, group_col=group_col)
    return to_dimensions(pct), pct
