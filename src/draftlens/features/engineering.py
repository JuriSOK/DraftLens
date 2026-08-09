"""Transparent basketball feature engineering.

Consumes the ML-0 prospect dataset plus raw player_box (for team/opponent
context) and produces the feature layer both stages consume. ML-0 files are
never mutated.

Four constraints are structural, not stylistic:
  DEC-065  population position/class and match metadata are never used
  DEC-067  only the coarse leakage-safe G/F/C position
  DEC-068  no generic jump_shot_* derived feature (schema breaks at 2020/21)
  DEC-044  no age or date of birth

HOLDOUT GUARD: this module never opens a targets_*.parquet file. Feature values
for the holdout year are produced by exactly the same formulas as development,
which is what makes a later single evaluation meaningful.
"""

import numpy as np
import pandas as pd

from draftlens.data.identity.matching import to_int_id
from draftlens.features.defense import blk_pct, stl_pct
from draftlens.features.playmaking import ast_pct, tov_pct, usage_pct
from draftlens.features.positions import UNKNOWN, to_position_3
from draftlens.features.rates import (FT_POSSESSION_COEF, per_40, per_100,
                                      per_game, safe_div, team_possessions)
from draftlens.features.rebounding import rebound_pct
from draftlens.features.shooting import efg_pct, ts_pct
from draftlens.paths import CONFIG_FEATURES, INTERIM, MBB

OUT = INTERIM / "ml2"
ML0 = INTERIM / "ml0"
DICT_PATH = CONFIG_FEATURES / "feature_dictionary.csv"
PARTITIONS = {"2011_2013": range(2011, 2014), "2014_2025": range(2014, 2026),
              "2026": range(2026, 2027)}
EXPECTED_ROWS = {"2011_2013": 125, "2014_2025": 887, "2026": 26}

IDENTITY = ["canonical_prospect_id", "draft_year", "player_name",
            "normalized_name", "college", "hoopr_athlete_id"]
# Retained beside the ratios so later phases can reason about reliability.
DENOMINATORS = ["games_played", "minutes", "field_goals_attempted",
                "three_points_attempted", "free_throws_attempted",
                "shot_records", "fg_attempts_shotfile", "team_minutes",
                "team_possessions", "opp_possessions"]
# Audit metadata — NOT predictive features (data completeness must not become a
# signal without review).
AUDIT = ["shot_fga_coverage_ratio", "n_teams", "experience_years"]


# ------------------------------------------------- team / opponent context
def team_context(year, athlete_ids):
    """Team and opponent totals summed over each prospect's PLAYED games only.

    Reconstructed from player_box by game (DATA.md §22.2 verified 99.89% points
    reconciliation and a 100% opponent self-join). No future game or season is
    reachable: only rows from season `year` are read.
    """
    cols = ["game_id", "team_id", "athlete_id", "minutes", "did_not_play",
            "field_goals_made", "field_goals_attempted",
            "three_point_field_goals_attempted", "free_throws_attempted",
            "offensive_rebounds", "defensive_rebounds", "rebounds",
            "assists", "turnovers"]
    box = pd.read_parquet(MBB / "player_box" / f"player_box_{year}.parquet",
                          columns=cols)
    box["athlete_id"] = to_int_id(box.athlete_id)
    box = box.drop_duplicates(subset=["athlete_id", "game_id"], keep="first")
    box = box[~box.did_not_play.fillna(False).astype(bool)]

    num = ["minutes", "field_goals_made", "field_goals_attempted",
           "three_point_field_goals_attempted", "free_throws_attempted",
           "offensive_rebounds", "defensive_rebounds", "rebounds",
           "assists", "turnovers"]
    for c in num:
        box[c] = pd.to_numeric(box[c], errors="coerce")

    tg = box.groupby(["game_id", "team_id"], as_index=False)[num].sum()
    tg = tg.rename(columns={c: f"tm_{c}" for c in num})

    # opponent = the other team in the same game
    opp = tg.rename(columns={"team_id": "opp_team_id",
                             **{f"tm_{c}": f"opp_{c}" for c in num}})
    pair = tg.merge(opp, on="game_id")
    pair = pair[pair.team_id != pair.opp_team_id]

    played = box[box.athlete_id.isin(athlete_ids)][["athlete_id", "game_id",
                                                    "team_id"]]
    j = played.merge(pair, on=["game_id", "team_id"], how="left")
    agg = j.groupby("athlete_id").sum(numeric_only=True)
    agg = agg.drop(columns=[c for c in ("game_id", "team_id", "opp_team_id")
                            if c in agg.columns])
    return agg.reset_index()


# ----------------------------------------------------------- feature build
def build_features(d):
    """d: one row per prospect, already carrying ML-0 primitives AND the
    tm_* / opp_* team-context columns. Returns the engineered feature frame."""
    f = pd.DataFrame(index=d.index)

    tm_min = d.get("tm_minutes")
    f["team_minutes"] = tm_min
    f["team_possessions"] = team_possessions(
        d.get("tm_field_goals_attempted"), d.get("tm_free_throws_attempted"),
        d.get("tm_offensive_rebounds"), d.get("tm_turnovers"))
    f["opp_possessions"] = team_possessions(
        d.get("opp_field_goals_attempted"), d.get("opp_free_throws_attempted"),
        d.get("opp_offensive_rebounds"), d.get("opp_turnovers"))

    g, mins = d.games_played, d.minutes

    # PLAYING_TIME -------------------------------------------------------
    f["minutes_per_game"] = per_game(mins, g)
    f["start_share"] = safe_div(d.games_started, g)

    # SHOOTING_EFFICIENCY -------------------------------------------------
    f["fg_pct"] = safe_div(d.field_goals_made, d.field_goals_attempted)
    f["two_point_pct"] = safe_div(d.two_points_made, d.two_points_attempted)
    f["three_point_pct"] = safe_div(d.three_points_made,
                                    d.three_points_attempted)
    f["ft_pct"] = safe_div(d.free_throws_made, d.free_throws_attempted)
    f["efg_pct"] = efg_pct(d.field_goals_made, d.three_points_made,
                           d.field_goals_attempted)
    f["ts_pct"] = ts_pct(d.points, d.field_goals_attempted,
                         d.free_throws_attempted)

    # SHOOTING_VOLUME -----------------------------------------------------
    f["three_point_attempt_rate"] = safe_div(d.three_points_attempted,
                                             d.field_goals_attempted)
    f["two_point_attempt_rate"] = safe_div(d.two_points_attempted,
                                           d.field_goals_attempted)
    f["free_throw_rate"] = safe_div(d.free_throws_attempted,
                                    d.field_goals_attempted)
    f["fga_per_40"] = per_40(d.field_goals_attempted, mins)
    f["three_pa_per_40"] = per_40(d.three_points_attempted, mins)
    f["fta_per_40"] = per_40(d.free_throws_attempted, mins)

    # SCORING -------------------------------------------------------------
    f["points_per_game"] = per_game(d.points, g)
    f["points_per_40"] = per_40(d.points, mins)
    f["points_per_100"] = per_100(d.points, f.team_possessions)

    # PLAYMAKING ----------------------------------------------------------
    f["assists_per_game"] = per_game(d.assists, g)
    f["turnovers_per_game"] = per_game(d.turnovers, g)
    f["assists_per_40"] = per_40(d.assists, mins)
    f["turnovers_per_40"] = per_40(d.turnovers, mins)
    f["assist_to_turnover_ratio"] = safe_div(d.assists, d.turnovers)
    f["ast_pct"] = ast_pct(d.assists, mins, tm_min,
                           d.get("tm_field_goals_made"), d.field_goals_made)
    f["tov_pct"] = tov_pct(d.turnovers, d.field_goals_attempted,
                           d.free_throws_attempted)

    # REBOUNDING ----------------------------------------------------------
    f["rebounds_per_game"] = per_game(d.total_rebounds, g)
    f["oreb_per_40"] = per_40(d.offensive_rebounds, mins)
    f["dreb_per_40"] = per_40(d.defensive_rebounds, mins)
    f["reb_per_40"] = per_40(d.total_rebounds, mins)
    f["orb_pct"] = rebound_pct(d.offensive_rebounds, mins, tm_min,
                               d.get("tm_offensive_rebounds"),
                               d.get("opp_defensive_rebounds"))
    f["drb_pct"] = rebound_pct(d.defensive_rebounds, mins, tm_min,
                               d.get("tm_defensive_rebounds"),
                               d.get("opp_offensive_rebounds"))
    f["trb_pct"] = rebound_pct(d.total_rebounds, mins, tm_min,
                               d.get("tm_rebounds"), d.get("opp_rebounds"))

    # DEFENSIVE_PRODUCTION (box-score production, NOT defensive quality) ---
    f["steals_per_game"] = per_game(d.steals, g)
    f["blocks_per_game"] = per_game(d.blocks, g)
    f["steals_per_40"] = per_40(d.steals, mins)
    f["blocks_per_40"] = per_40(d.blocks, mins)
    f["personal_fouls_per_40"] = per_40(d.personal_fouls, mins)
    f["stl_pct"] = stl_pct(d.steals, mins, tm_min, f.opp_possessions)
    f["blk_pct"] = blk_pct(d.blocks, mins, tm_min,
                           d.get("opp_field_goals_attempted"),
                           d.get("opp_three_point_field_goals_attempted"))

    # SHOT_PROFILE — stable families only (DEC-068 bars generic jump shots) -
    sf = d.fg_attempts_shotfile
    f["layup_attempt_share"] = safe_div(d.layup_attempts, sf)
    f["dunk_attempt_share"] = safe_div(d.dunk_attempts, sf)
    f["tip_attempt_share"] = safe_div(d.tip_attempts, sf)
    f["three_point_shot_attempt_share"] = safe_div(d.three_point_shot_attempts,
                                                   sf)
    rim = (pd.to_numeric(d.layup_attempts, errors="coerce")
           + pd.to_numeric(d.dunk_attempts, errors="coerce")
           + pd.to_numeric(d.tip_attempts, errors="coerce"))
    f["rim_attempt_share"] = safe_div(rim, sf)
    f["layup_make_pct"] = safe_div(d.layup_makes, d.layup_attempts)
    f["dunk_make_pct"] = safe_div(d.dunk_makes, d.dunk_attempts)
    f["tip_make_pct"] = safe_div(d.tip_makes, d.tip_attempts)
    rim_makes = (pd.to_numeric(d.layup_makes, errors="coerce")
                 + pd.to_numeric(d.dunk_makes, errors="coerce")
                 + pd.to_numeric(d.tip_makes, errors="coerce"))
    f["rim_make_pct"] = safe_div(rim_makes, rim)

    # CREATION — shot-event assist linkage, made field goals only ----------
    made_sf = d.fg_makes_shotfile
    f["assisted_made_fg_share"] = safe_div(d.assisted_made_field_goals, made_sf)
    f["unassisted_made_fg_share"] = safe_div(d.unassisted_made_field_goals,
                                             made_sf)
    f["assisted_layup_make_share"] = safe_div(d.assisted_layup_makes,
                                              d.layup_makes)
    f["unassisted_layup_make_share"] = safe_div(d.unassisted_layup_makes,
                                                d.layup_makes)
    f["assisted_dunk_make_share"] = safe_div(d.assisted_dunk_makes,
                                             d.dunk_makes)
    f["unassisted_dunk_make_share"] = safe_div(d.unassisted_dunk_makes,
                                               d.dunk_makes)

    # PHYSICAL / POSITION --------------------------------------------------
    f["height"] = pd.to_numeric(d.height, errors="coerce")
    f["weight"] = pd.to_numeric(d.weight, errors="coerce")
    f["position_3"] = d.hoopr_position.map(to_position_3) \
        if "hoopr_position" in d.columns else UNKNOWN

    # ROLE ----------------------------------------------------------------
    f["usage_pct"] = usage_pct(d.field_goals_attempted,
                               d.free_throws_attempted, d.turnovers, mins,
                               d.get("tm_field_goals_attempted"),
                               d.get("tm_free_throws_attempted"),
                               d.get("tm_turnovers"), tm_min)

    # per-100 variants (candidate columns; redundancy assessed in ML-3)
    f["assists_per_100"] = per_100(d.assists, f.team_possessions)
    f["turnovers_per_100"] = per_100(d.turnovers, f.team_possessions)
    f["rebounds_per_100"] = per_100(d.total_rebounds, f.team_possessions)
    f["steals_per_100"] = per_100(d.steals, f.team_possessions)
    f["blocks_per_100"] = per_100(d.blocks, f.team_possessions)

    # audit metadata (never predictive without review)
    f["shot_fga_coverage_ratio"] = safe_div(d.fg_attempts_shotfile,
                                            d.field_goals_attempted)
    return f


ENGINEERED = None       # populated on first build; excludes identity/denoms


def assemble(label, years):
    base = pd.read_parquet(ML0 / f"features_{label}.parquet")
    frames = []
    for y in years:
        b = base[base.draft_year == y].copy()
        if b.empty:
            continue
        ids = set(pd.to_numeric(b.hoopr_athlete_id, errors="coerce")
                  .dropna().astype("int64"))
        ctx = team_context(y, ids)
        ctx["athlete_id"] = ctx.athlete_id.astype("int64")
        b["_aid"] = pd.to_numeric(b.hoopr_athlete_id, errors="coerce")
        d = b.merge(ctx.rename(columns={"athlete_id": "_aid"}),
                    on="_aid", how="left").reset_index(drop=True)
        f = build_features(d).reset_index(drop=True)
        cols = [c for c in DENOMINATORS if c in d.columns] + \
               [c for c in AUDIT if c in d.columns]
        keep = pd.concat([d[IDENTITY], d[cols], f], axis=1)
        frames.append(keep)
    out = pd.concat(frames, ignore_index=True)
    return out.loc[:, ~out.columns.duplicated()]


def feature_columns(df):
    skip = set(IDENTITY) | set(DENOMINATORS) | set(AUDIT) | {"position_3"}
    return [c for c in df.columns
            if c not in skip and pd.api.types.is_numeric_dtype(df[c])]
