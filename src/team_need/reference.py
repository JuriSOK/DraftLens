"""NCAA peer reference distributions for Team Need percentiles.

Team Need converts heterogeneous basketball statistics onto one interpretable
scale: *where does this prospect sit among comparable NCAA players?* That needs
a broad reference population, not the small declared-entrant frame.

This extends the ML-2 reference (10 metrics, summary statistics only) to the
full set of Team Need metrics, stored as a 101-point quantile grid per
season x reference-group x metric so any percentile can be interpolated.

THREE PROPERTIES MAKE THIS LEAKAGE-SAFE, and all three matter:

  * The reference is the FULL NCAA player population of a season — tens of
    thousands of players, the overwhelming majority not prospects. It is NOT
    the prospect sampling frame, so it cannot reintroduce the ML-1
    sampling-frame leak.
  * No draft outcome is ever read. Team Need has no outcome target at all.
  * Season Y prospects are compared against season Y peers, whose games conclude
    before the draft. No later season is consulted.

REFERENCE POPULATION FILTER. Players below `MIN_MINUTES` / `MIN_GAMES` are
excluded from the reference. A percentile against a population full of
eight-minute walk-ons is not a meaningful basketball statement — the median
would sit far below any rotation player. The prospect being *scored* is never
filtered; only the peer group is.
"""

import numpy as np
import pandas as pd

from data.matching import to_int_id
from features.basketball import aggregate_box_frame
from features.basketball import build_features, team_context
from features.basketball import to_position_3
from paths import MBB, interim

OUT = interim("team_need")
REFERENCE_FILE = OUT / "ncaa_percentile_reference.parquet"

# Reference-population filter. A season-long rate needs a season of evidence.
MIN_MINUTES = 200
MIN_GAMES = 10

# Quantile grid resolution: 0..100 inclusive, one point per percentile.
GRID = np.arange(0, 101)

# Reference group "GLOBAL" pools every position; the coarse position codes give
# a within-position peer group. Which group each metric uses is a per-dimension
# decision recorded in config/features/team_need.json.
GLOBAL_GROUP = "GLOBAL"

# Every metric Team Need can percentile-rank.
REFERENCE_METRICS = [
    # shooting
    "three_point_pct", "three_point_attempt_rate", "three_pa_per_40",
    "ft_pct", "efg_pct", "ts_pct", "two_point_pct",
    # playmaking
    "ast_pct", "assists_per_40", "assist_to_turnover_ratio", "tov_pct",
    "usage_pct",
    # box-score defensive production
    "stl_pct", "blk_pct", "drb_pct", "personal_fouls_per_40",
    # rebounding
    "orb_pct", "trb_pct",
    # size
    "height", "weight",
    # rim pressure
    "rim_attempt_share", "dunk_attempt_share", "layup_attempt_share",
    "free_throw_rate", "rim_make_pct", "unassisted_made_fg_share",
]


def _season_frame(year):
    """Every NCAA player of one season, on the ML-2 feature definitions.

    Uses the same `build_features` the prospect layer uses, so a prospect's
    value and its peer group are computed by identical code — a percentile is
    meaningless if the two sides are calculated differently.
    """
    box = pd.read_parquet(MBB / "player_box" / f"player_box_{year}.parquet")
    box["athlete_id"] = to_int_id(box.athlete_id)
    box = box[box.athlete_id.notna()]
    agg, _, _ = aggregate_box_frame(box, year)
    agg["athlete_id"] = agg.athlete_id.astype("int64")

    ctx = team_context(year, set(agg.athlete_id))
    ctx["athlete_id"] = ctx.athlete_id.astype("int64")
    d = agg.merge(ctx, on="athlete_id", how="left")

    from features.shot_profile import aggregate_shots_frame
    sh = pd.read_parquet(
        MBB / "shots" / f"shots_{year}.parquet",
        columns=["athlete_id_1", "athlete_id_2", "type_text", "scoring_play",
                 "score_value"])
    sh["athlete_id_1"] = to_int_id(sh.athlete_id_1)
    sh = sh[sh.athlete_id_1.notna()].copy()
    shots = aggregate_shots_frame(sh)
    shots["athlete_id"] = shots.athlete_id.astype("int64")
    d = d.merge(shots, on="athlete_id", how="left", suffixes=("", "_sh"))

    core = pd.read_parquet(
        MBB / "player_core" / f"player_core_{year}.parquet",
        columns=["athlete_id", "position_abbreviation", "height", "weight"])
    core["athlete_id"] = to_int_id(core.athlete_id)
    core = core[core.athlete_id.notna()]
    core["athlete_id"] = core.athlete_id.astype("int64")
    d = d.merge(core, on="athlete_id", how="left")
    d["position_3"] = d.position_abbreviation.map(to_position_3)

    # The same identity-preserving primitives the ML-0 build adds, so the peer
    # group is computed by exactly the code path the prospect layer uses.
    d["two_points_made"] = d.field_goals_made - d.three_points_made
    d["two_points_attempted"] = (d.field_goals_attempted
                                 - d.three_points_attempted)

    feats = build_features(d).reset_index(drop=True)
    keep = pd.concat([d[["athlete_id", "position_3", "minutes",
                         "games_played"]].reset_index(drop=True), feats], axis=1)
    return keep.loc[:, ~keep.columns.duplicated()]


def build_reference(years, min_minutes=MIN_MINUTES, min_games=MIN_GAMES,
                    log=print):
    """101-point quantile grids per season x reference group x metric."""
    rows = []
    for year in years:
        d = _season_frame(year)
        n_all = len(d)
        d = d[(d.minutes >= min_minutes) & (d.games_played >= min_games)]
        log(f"  {year}: {n_all:>6} NCAA players -> {len(d):>5} in reference "
            f"(>= {min_minutes} min, >= {min_games} games)")
        groups = [(GLOBAL_GROUP, d)] + [(p, g) for p, g in d.groupby("position_3")
                                        if p != "UNKNOWN"]
        for group, g in groups:
            for metric in REFERENCE_METRICS:
                if metric not in g.columns:
                    continue
                v = pd.to_numeric(g[metric], errors="coerce").dropna()
                v = v[np.isfinite(v)]
                if len(v) < 50:      # too thin to define percentiles
                    continue
                qs = np.percentile(v.to_numpy(dtype="float64"), GRID)
                rows.append(pd.DataFrame({
                    "season": year, "reference_group": group, "metric": metric,
                    "q": GRID, "value": qs, "n": len(v)}))
    ref = pd.concat(rows, ignore_index=True)
    return ref


def load_reference(path=REFERENCE_FILE):
    if not path.exists():
        raise FileNotFoundError(
            f"{path} missing — run scripts/build.py team_need")
    return pd.read_parquet(path)


class PercentileReference:
    """Interpolating percentile lookup over the quantile grids.

    A prospect's value is placed against its season's peer distribution and
    reported on 0-100. Values outside the observed range clamp to 0 or 100
    rather than extrapolating — a percentile is bounded by definition.
    """

    def __init__(self, ref=None):
        self._ref = ref if ref is not None else load_reference()
        self._grids = {}
        for (season, group, metric), g in self._ref.groupby(
                ["season", "reference_group", "metric"], sort=False):
            g = g.sort_values("q")
            self._grids[(int(season), str(group), str(metric))] = (
                g.value.to_numpy(dtype="float64"),
                g.q.to_numpy(dtype="float64"),
                int(g.n.iloc[0]))

    def has(self, season, group, metric):
        return (int(season), str(group), str(metric)) in self._grids

    def support(self, season, group, metric):
        key = (int(season), str(group), str(metric))
        return self._grids[key][2] if key in self._grids else 0

    def percentile(self, values, season, group, metric):
        """Percentile (0-100) of each value against its peer distribution.

        NaN in -> NaN out. A missing value is MISSING, never 0 — treating an
        absent measurement as the worst possible one would make missingness a
        signal, which is the failure mode this project has refused throughout.
        """
        v = pd.to_numeric(pd.Series(values), errors="coerce").to_numpy(
            dtype="float64")
        key = (int(season), str(group), str(metric))
        if key not in self._grids:
            return np.full(len(v), np.nan)
        xs, qs, _ = self._grids[key]
        # np.interp needs an increasing x; quantile values are non-decreasing.
        out = np.interp(v, xs, qs, left=0.0, right=100.0)
        out[~np.isfinite(v)] = np.nan
        return np.clip(out, 0.0, 100.0)


def percentile_frame(df, spec, reference, season_col="draft_year"):
    """Percentile-rank many metrics for a frame of prospects.

    `spec` maps metric -> reference group ("GLOBAL" or "POSITION"). Each
    prospect is compared within their own season, and — for POSITION metrics —
    within their own coarse position.
    """
    out = pd.DataFrame(index=df.index)
    for metric, group_kind in spec.items():
        col = np.full(len(df), np.nan)
        for season, idx in df.groupby(season_col).groups.items():
            sub = df.loc[idx]
            pos_i = df.index.get_indexer(idx)
            if group_kind == "GLOBAL":
                col[pos_i] = reference.percentile(sub[metric], season,
                                                  GLOBAL_GROUP, metric)
            else:
                vals = np.full(len(sub), np.nan)
                for pos, pidx in sub.groupby("position_3").groups.items():
                    p_i = sub.index.get_indexer(pidx)
                    grp = pos if reference.has(season, pos, metric) \
                        else GLOBAL_GROUP
                    vals[p_i] = reference.percentile(sub.loc[pidx, metric],
                                                     season, grp, metric)
                col[pos_i] = vals
        out[metric] = col
    return out
