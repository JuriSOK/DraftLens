"""NCAA season x coarse-position reference distributions.

These power the SEASON_RELATIVE representation both stages use (DEC-081).

Leakage-safe on three counts:
  * Built from the FULL hoopR NCAA player population of a season — tens of
    thousands of players, the overwhelming majority not prospects. It is NOT the
    prospect sampling frame, so it cannot reintroduce the ML-1 sampling-frame
    leak.
  * Draft outcome is never consulted.
  * Season Y prospects are normalised against season Y, whose games conclude
    before the June draft. No later season is ever read.

No minimum-minute threshold is applied — that choice is deliberately deferred.
"""

import numpy as np
import pandas as pd

from data.matching import to_int_id
from features.basketball import aggregate_box_frame
from features.basketball import to_position_3
from features.basketball import per_40, per_game, safe_div
from features.basketball import efg_pct, ts_pct
from paths import MBB


def build_reference(years):
    """Season x coarse-position reference distributions from the FULL hoopR
    NCAA player population. Draft outcome is never consulted. No minimum-minute
    threshold is applied — that choice is deferred."""
    rows = []
    metrics = ["points_per_40", "reb_per_40", "assists_per_40", "steals_per_40",
               "blocks_per_40", "ts_pct", "efg_pct", "three_point_attempt_rate",
               "free_throw_rate", "minutes_per_game"]
    for y in years:
        box = pd.read_parquet(MBB / "player_box" / f"player_box_{y}.parquet")
        box["athlete_id"] = to_int_id(box.athlete_id)
        box = box[box.athlete_id.notna()]
        agg, _, _ = aggregate_box_frame(box, y)
        core = pd.read_parquet(MBB / "player_core" / f"player_core_{y}.parquet",
                               columns=["athlete_id", "position_abbreviation"])
        core["athlete_id"] = to_int_id(core.athlete_id)
        agg = agg.merge(core, on="athlete_id", how="left")
        agg["position_3"] = agg.position_abbreviation.map(to_position_3)
        m = pd.DataFrame(index=agg.index)
        m["points_per_40"] = per_40(agg.points, agg.minutes)
        m["reb_per_40"] = per_40(agg.total_rebounds, agg.minutes)
        m["assists_per_40"] = per_40(agg.assists, agg.minutes)
        m["steals_per_40"] = per_40(agg.steals, agg.minutes)
        m["blocks_per_40"] = per_40(agg.blocks, agg.minutes)
        m["ts_pct"] = ts_pct(agg.points, agg.field_goals_attempted,
                             agg.free_throws_attempted)
        m["efg_pct"] = efg_pct(agg.field_goals_made, agg.three_points_made,
                               agg.field_goals_attempted)
        m["three_point_attempt_rate"] = safe_div(agg.three_points_attempted,
                                                 agg.field_goals_attempted)
        m["free_throw_rate"] = safe_div(agg.free_throws_attempted,
                                        agg.field_goals_attempted)
        m["minutes_per_game"] = per_game(agg.minutes, agg.games_played)
        m["position_3"] = agg.position_3.values
        for pos, gg in m.groupby("position_3"):
            for met in metrics:
                v = gg[met].dropna()
                if v.empty:
                    continue
                rows.append(dict(season=y, position_3=pos, metric=met,
                                 count=int(v.size), mean=float(v.mean()),
                                 std=float(v.std(ddof=1)) if v.size > 1 else np.nan,
                                 median=float(v.median()),
                                 p10=float(v.quantile(.10)),
                                 p25=float(v.quantile(.25)),
                                 p75=float(v.quantile(.75)),
                                 p90=float(v.quantile(.90))))
    return pd.DataFrame(rows)
