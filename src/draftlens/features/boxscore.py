"""Season aggregation of NCAA box scores.

Transfer policy: a prospect's draft-year record is their TOTAL production across
every NCAA team played for that season — one row per prospect, with n_teams
retained as metadata.
"""

import pandas as pd

from draftlens.data.identity.matching import to_int_id
from draftlens.paths import MBB

# Output column -> hoopR source column.
BOX_SUMS = {
    "minutes": "minutes", "points": "points",
    "field_goals_made": "field_goals_made",
    "field_goals_attempted": "field_goals_attempted",
    "three_points_made": "three_point_field_goals_made",
    "three_points_attempted": "three_point_field_goals_attempted",
    "free_throws_made": "free_throws_made",
    "free_throws_attempted": "free_throws_attempted",
    "offensive_rebounds": "offensive_rebounds",
    "defensive_rebounds": "defensive_rebounds",
    "total_rebounds": "rebounds",
    "assists": "assists", "turnovers": "turnovers",
    "steals": "steals", "blocks": "blocks", "personal_fouls": "fouls",
}


def aggregate_box_frame(box, year):
    """Pure season-aggregation logic (kept separate so it is unit-testable).

    Exact duplicate (athlete_id, game_id) rows are dropped before summing so
    statistics are never double counted. Did-not-play rows are excluded, so
    `games_played` counts appearances rather than roster inclusions.
    """
    before = len(box)
    box = box.drop_duplicates(subset=["athlete_id", "game_id"], keep="first")
    dupes_removed = before - len(box)

    box["_dnp"] = box.did_not_play.fillna(False).astype(bool)
    played = box[~box._dnp].copy()
    for src in BOX_SUMS.values():
        played[src] = pd.to_numeric(played[src], errors="coerce")

    agg = played.groupby("athlete_id").agg(
        **{out: (src, "sum") for out, src in BOX_SUMS.items()})
    agg["games_played"] = played.groupby("athlete_id").size()
    agg["games_started"] = (played.assign(_s=played.starter.fillna(False).astype(bool))
                            .groupby("athlete_id")._s.sum())
    agg["n_teams"] = played.groupby("athlete_id").team_id.nunique()
    agg["primary_school"] = (played.sort_values("game_date")
                             .groupby("athlete_id").team_location.last())
    agg["ncaa_season"] = year
    return agg.reset_index(), dupes_removed, before


def aggregate_box(year, ids):
    box = pd.read_parquet(MBB / "player_box" / f"player_box_{year}.parquet")
    box["athlete_id"] = to_int_id(box.athlete_id)
    box = box[box.athlete_id.isin(ids)].copy()
    return aggregate_box_frame(box, year)
