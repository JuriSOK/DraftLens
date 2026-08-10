"""NBA player-season metrics, on the same semantics as the NCAA feature layer.

The hoopR NBA source is LONG format — one row per (player, season, category,
stat). It carries player totals and per-game averages only: there are no team
totals, no opponent totals and no shot-level events. That constrains what can
honestly be compared across leagues, and the constraint is respected rather
than worked around:

  ACCEPTED. Shooting percentages, shot-mix ratios and per-minute rates. Each
  has an IDENTICAL formula in both leagues, so the same question is being asked
  of both populations.

  REJECTED. Every possession-based percentage the NCAA layer computes — AST%,
  TOV%, ORB%, DRB%, STL%, BLK%, usage% — because they need team AND opponent
  context. NBA team totals could be reconstructed by summing players, but
  opponent totals cannot (there is no game-level NBA data here), and ESPN
  attributes a traded player's whole season to one team, which would silently
  corrupt the denominator. Recreating them would mean two metrics with the same
  name and different meanings.

  REJECTED. Everything shot-level — rim-attempt share, finishing, assisted
  share — there is no NBA shot file.

  REJECTED. Height and weight. The NBA source has none, and they are never
  fabricated.

WHY PER-MINUTE RATES ARE COMPARABLE AT ALL. A per-40-minute rate is not
compared across leagues directly — it is percentile-ranked WITHIN its own
league first. The 40-vs-48-minute game length, pace and competition differences
all cancel, because the question asked of both populations is identical: where
does this player sit among his own league's peers?
"""

import re

import numpy as np
import pandas as pd

from features.basketball import per_40, safe_div
from features.basketball import efg_pct, ts_pct
from paths import RAW

NBA_DIR = RAW / "hoopr_nba" / "player_season_stats"

# stat_name -> output column, for the plain numeric `totals` rows.
TOTALS = {
    "points": "points", "assists": "assists", "turnovers": "turnovers",
    "offensiveRebounds": "offensive_rebounds",
    "defensiveRebounds": "defensive_rebounds",
    "totalRebounds": "total_rebounds", "steals": "steals", "blocks": "blocks",
    "fouls": "personal_fouls",
}
# Combined "made-attempted" rows, whose `value` is null and whose
# `display_value` holds e.g. "247-538". Verified to parse for 100% of rows.
PAIRS = {
    "fieldGoalsMade-fieldGoalsAttempted": ("field_goals_made",
                                           "field_goals_attempted"),
    "threePointFieldGoalsMade-threePointFieldGoalsAttempted":
        ("three_points_made", "three_points_attempted"),
    "freeThrowsMade-freeThrowsAttempted": ("free_throws_made",
                                           "free_throws_attempted"),
}
AVERAGES = {"gamesPlayed": "games_played", "gamesStarted": "games_started",
            "avgMinutes": "minutes_per_game"}

_PAIR_RE = re.compile(r"^\s*(-?[\d.]+)\s*-\s*([\d.]+)\s*$")


def parse_pair(display_value):
    """Split a "made-attempted" display string into two numeric series."""
    s = pd.Series(display_value).astype("string")
    m = s.str.extract(_PAIR_RE)
    return (pd.to_numeric(m[0], errors="coerce"),
            pd.to_numeric(m[1], errors="coerce"))


def load_season(year, path=None):
    """One NBA season, pivoted to one row per player with raw counting stats."""
    path = path or NBA_DIR / f"player_season_stats_{year}.parquet"
    d = pd.read_parquet(path)

    ident = (d[["athlete_id", "athlete_display_name",
                "athlete_position_abbreviation", "team_id",
                "team_display_name"]]
             .drop_duplicates("athlete_id").set_index("athlete_id"))

    tot = d[(d.category == "totals") & d.stat_name.isin(TOTALS)]
    wide = tot.pivot_table(index="athlete_id", columns="stat_name",
                           values="value", aggfunc="first").rename(
                               columns=TOTALS)

    pair_rows = d[d.stat_name.isin(PAIRS)]
    for stat, (made_col, att_col) in PAIRS.items():
        sub = pair_rows[(pair_rows.category == "totals")
                        & (pair_rows.stat_name == stat)]
        made, att = parse_pair(sub.display_value)
        made.index = sub.athlete_id.to_numpy()
        att.index = sub.athlete_id.to_numpy()
        wide[made_col] = made
        wide[att_col] = att

    avg = d[(d.category == "averages") & d.stat_name.isin(AVERAGES)]
    wide = wide.join(avg.pivot_table(index="athlete_id", columns="stat_name",
                                     values="value", aggfunc="first")
                     .rename(columns=AVERAGES))

    out = ident.join(wide, how="inner").reset_index()
    out["season"] = year
    out["minutes"] = out.minutes_per_game * out.games_played
    return out


def build_metrics(df):
    """Common metrics, using the SAME formulas as the NCAA feature layer.

    `efg_pct`, `ts_pct` and `safe_div` are imported from
    `features` rather than reimplemented — two implementations of one
    formula is a defect, and a divergent one here would silently break the
    cross-league comparison this module exists to support.
    """
    f = pd.DataFrame(index=df.index)
    minutes = pd.to_numeric(df.minutes, errors="coerce")
    fga = pd.to_numeric(df.field_goals_attempted, errors="coerce")

    # shooting efficiency — identical formulas in both leagues
    f["three_point_pct"] = safe_div(df.three_points_made,
                                    df.three_points_attempted)
    f["ft_pct"] = safe_div(df.free_throws_made, df.free_throws_attempted)
    f["efg_pct"] = efg_pct(df.field_goals_made, df.three_points_made, fga)
    f["ts_pct"] = ts_pct(df.points, fga, df.free_throws_attempted)

    # shot mix — identical ratios
    f["three_point_attempt_rate"] = safe_div(df.three_points_attempted, fga)
    f["free_throw_rate"] = safe_div(df.free_throws_attempted, fga)

    # per-40 rates — the same question of both leagues once percentile-ranked
    f["points_per_40"] = per_40(df.points, minutes)
    f["fga_per_40"] = per_40(fga, minutes)
    f["assists_per_40"] = per_40(df.assists, minutes)
    f["turnovers_per_40"] = per_40(df.turnovers, minutes)
    f["oreb_per_40"] = per_40(df.offensive_rebounds, minutes)
    f["dreb_per_40"] = per_40(df.defensive_rebounds, minutes)
    f["steals_per_40"] = per_40(df.steals, minutes)
    f["blocks_per_40"] = per_40(df.blocks, minutes)
    return f


def load_player_seasons(years):
    """Every NBA player-season in `years`, with common metrics attached."""
    frames = []
    for y in years:
        d = load_season(y)
        m = build_metrics(d)
        frames.append(pd.concat([d.reset_index(drop=True),
                                 m.reset_index(drop=True)], axis=1))
    out = pd.concat(frames, ignore_index=True)
    return out.loc[:, ~out.columns.duplicated()]
