"""Transparent basketball feature engineering.

Consumes the built prospect dataset (`data.build`) plus raw player_box (for
team/opponent context) and produces the feature layer both Draft Probability
and Draft Order consume. The built dataset is never mutated.

Four constraints are structural, not stylistic:
  * population position/class and match metadata are never used — their
    availability is decided by the draft outcome, not by basketball.
  * only the coarse leakage-safe G/F/C position is ever engineered.
  * no generic jump_shot_* derived feature (the hoopR schema breaks at 2020/21).
  * no age or date of birth.

HOLDOUT GUARD: this module never opens a targets file. Feature values for the
holdout year are produced by exactly the same formulas as development, which
is what makes a later single evaluation meaningful.

SAFE DIVISION POLICY: an undefined ratio is NULL, never 0 and never infinity.
0 made from 0 attempts is UNKNOWN, not 0%. No epsilon is ever added. This is a
leakage guard as much as a correctness one — substituting 0 would encode
"never attempted" as "attempted and failed", and attempt frequency correlates
with the draft outcome.

Nothing in this module reads draft outcome, pick, NBA data, age or DOB.
"""

import numpy as np
import pandas as pd

from data.matching import to_int_id
from paths import CONFIG, INTERIM, MBB

OUT = INTERIM / "features"
DATASET = INTERIM / "dataset"
DICT_PATH = CONFIG / "feature_dictionary.csv"
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

# Free-throw possession coefficient used by the conventional TS%, possession,
# usage and turnover-rate formulas. Named rather than hidden as a literal.
FT_POSSESSION_COEF = 0.44

UNKNOWN = "UNKNOWN"

# hoopR label -> canonical coarse position. Leakage-safe: the vocabulary and
# availability are near-identical for drafted and undrafted prospects. This is
# the ONLY leakage-safe pre-draft position source (see docs/DATA.md); the
# Wikipedia label must NOT be used — drafted prospects inherit it from the
# DRAFT RESULTS table (fine PG/SG/SF/PF/C labels) while undrafted prospects
# inherit it from the early-entrant list (broad G/F). Measured on 2014-2025, it
# resolves to a five-position label for 100% of drafted versus 7.7% of
# undrafted — the label's granularity encodes the outcome, so it is on the
# model deny list.
HOOPR_TO_3 = {
    "G": "G", "PG": "G", "SG": "G",
    "F": "F", "SF": "F", "PF": "F",
    "C": "C",
    "ATH": UNKNOWN, "NA": UNKNOWN, "": UNKNOWN,
}


def normalize_label(raw):
    """Uppercase, strip whitespace, unify separators. Lookup key only — the raw
    value is always preserved by the caller."""
    if raw is None:
        return ""
    s = str(raw).strip().upper().replace("\\", "/").replace("-", "/")
    s = s.replace(" ", "")
    return "" if s in ("", "NAN", "NA", "NONE") else s


def to_position_3(hoopr_label):
    """Canonical coarse position (G/F/C) from hoopR. THE leakage-safe path."""
    return HOOPR_TO_3.get(normalize_label(hoopr_label), UNKNOWN)


# ------------------------------------------------------------------- rates
def safe_div(num, den):
    """Element-wise division that yields NaN wherever the result is undefined.

    Undefined means: denominator missing, denominator <= 0, or numerator
    missing. Never returns inf; never substitutes 0 for an undefined ratio.
    """
    num = pd.to_numeric(pd.Series(num), errors="coerce")
    den = pd.to_numeric(pd.Series(den), errors="coerce")
    den = den.reindex(num.index) if len(den) == len(num) else den
    ok = den.notna() & (den > 0) & num.notna()
    out = pd.Series(np.nan, index=num.index, dtype="float64")
    out[ok] = num[ok].astype("float64") / den[ok].astype("float64")
    return out.replace([np.inf, -np.inf], np.nan)


def per_game(stat, games):
    return safe_div(stat, games)


def per_40(stat, minutes):
    """40 * stat / minutes. NULL when minutes are 0 or missing."""
    stat = pd.to_numeric(pd.Series(stat), errors="coerce")
    return safe_div(40.0 * stat, minutes)


def per_100(stat, possessions):
    stat = pd.to_numeric(pd.Series(stat), errors="coerce")
    return safe_div(100.0 * stat, possessions)


def team_possessions(fga, fta, orb, tov):
    """Conventional estimate: FGA + 0.44*FTA - ORB + TOV.

    Returned as a plain numeric series (may legitimately be 0 only for an empty
    team-season, which safe_div then treats as undefined downstream).
    """
    fga, fta, orb, tov = (pd.to_numeric(pd.Series(x), errors="coerce")
                          for x in (fga, fta, orb, tov))
    return fga + FT_POSSESSION_COEF * fta - orb + tov


# --------------------------------------------------------------- shooting
def fg_pct(fgm, fga):
    return safe_div(fgm, fga)


def efg_pct(fgm, fg3m, fga):
    """(FGM + 0.5 * 3PM) / FGA — credits the extra point of a made three."""
    fgm = pd.to_numeric(pd.Series(fgm), errors="coerce")
    fg3m = pd.to_numeric(pd.Series(fg3m), errors="coerce")
    return safe_div(fgm + 0.5 * fg3m, fga)


def ts_pct(points, fga, fta):
    """PTS / (2 * (FGA + 0.44 * FTA)). Free throws come from player_box only —
    the shot file holds made free throws exclusively."""
    fga = pd.to_numeric(pd.Series(fga), errors="coerce")
    fta = pd.to_numeric(pd.Series(fta), errors="coerce")
    return safe_div(points, 2.0 * (fga + FT_POSSESSION_COEF * fta))


# -------------------------------------------------------------- playmaking
def usage_pct(fga, fta, tov, minutes, tm_fga, tm_fta, tm_tov, tm_minutes):
    """100 * ((FGA + 0.44*FTA + TOV) * (TmMP/5)) /
             (MP * (TmFGA + 0.44*TmFTA + TmTOV))
    """
    fga, fta, tov, minutes = (pd.to_numeric(pd.Series(x), errors="coerce")
                              for x in (fga, fta, tov, minutes))
    tm_fga, tm_fta, tm_tov, tm_minutes = (
        pd.to_numeric(pd.Series(x), errors="coerce")
        for x in (tm_fga, tm_fta, tm_tov, tm_minutes))
    num = (fga + FT_POSSESSION_COEF * fta + tov) * (tm_minutes / 5.0)
    den = minutes * (tm_fga + FT_POSSESSION_COEF * tm_fta + tm_tov)
    return 100.0 * safe_div(num, den)


def tov_pct(tov, fga, fta):
    """100 * TOV / (FGA + 0.44*FTA + TOV) — share of the player's own
    possessions ending in a turnover."""
    tov, fga, fta = (pd.to_numeric(pd.Series(x), errors="coerce")
                     for x in (tov, fga, fta))
    return 100.0 * safe_div(tov, fga + FT_POSSESSION_COEF * fta + tov)


def ast_pct(ast, minutes, tm_minutes, tm_fgm, fgm):
    """100 * AST / (((MP / (TmMP/5)) * TmFG) - FG)

    Share of team-mate field goals assisted while on the floor.
    """
    ast, minutes, tm_minutes, tm_fgm, fgm = (
        pd.to_numeric(pd.Series(x), errors="coerce")
        for x in (ast, minutes, tm_minutes, tm_fgm, fgm))
    share = safe_div(minutes, tm_minutes / 5.0)
    den = share * tm_fgm - fgm
    return 100.0 * safe_div(ast, den)


# -------------------------------------------------------------- rebounding
def rebound_pct(reb, minutes, tm_minutes, tm_reb, opp_reb):
    """100 * (REB * (TmMP/5)) / (MP * (TmREB + OppREB)).

    Pass (ORB, TmORB, OppDRB) for ORB%, (DRB, TmDRB, OppORB) for DRB%,
    (TRB, TmTRB, OppTRB) for TRB%.
    """
    reb, minutes, tm_minutes, tm_reb, opp_reb = (
        pd.to_numeric(pd.Series(x), errors="coerce")
        for x in (reb, minutes, tm_minutes, tm_reb, opp_reb))
    return 100.0 * safe_div(reb * (tm_minutes / 5.0),
                            minutes * (tm_reb + opp_reb))


# ---------------------------------------------- box-score defensive production
def stl_pct(stl, minutes, tm_minutes, opp_possessions):
    """NOT defensive quality. There is no matchup data, no opponent shooting
    when defended, no on/off context and no deterrence measure. Steals and
    blocks are noisy and position-confounded. Anything built on these
    functions must be labelled "box-score defensive production" wherever it
    reaches a user."""
    stl, minutes, tm_minutes, opp_possessions = (
        pd.to_numeric(pd.Series(x), errors="coerce")
        for x in (stl, minutes, tm_minutes, opp_possessions))
    return 100.0 * safe_div(stl * (tm_minutes / 5.0),
                            minutes * opp_possessions)


def blk_pct(blk, minutes, tm_minutes, opp_fga, opp_fg3a):
    """Blocks as a share of opponent TWO-point attempts faced."""
    blk, minutes, tm_minutes, opp_fga, opp_fg3a = (
        pd.to_numeric(pd.Series(x), errors="coerce")
        for x in (blk, minutes, tm_minutes, opp_fga, opp_fg3a))
    return 100.0 * safe_div(blk * (tm_minutes / 5.0),
                            minutes * (opp_fga - opp_fg3a))


# ----------------------------------------------------- season box aggregation
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


# --------------------------------------------------------- physical attributes
def physical(year, ids):
    """Height/weight from the hoopR player core file.

    Coverage varies by season (76.7-99.2% and 57.1-94.7%), so both are treated
    as source-missing rather than structurally absent. Date of birth is NOT
    read here: its availability is outcome-correlated and it is a prohibited
    model feature.
    """
    core = pd.read_parquet(MBB / "player_core" / f"player_core_{year}.parquet")
    core["athlete_id"] = to_int_id(core.athlete_id)
    core = core[core.athlete_id.isin(ids)]
    keep = core[["athlete_id", "position_abbreviation", "height", "weight",
                 "experience_years"]].copy()
    return keep.rename(columns={"position_abbreviation": "hoopr_position"})


# --------------------------------------------------- team / opponent context
def team_context(year, athlete_ids):
    """Team and opponent totals summed over each prospect's PLAYED games only.

    Reconstructed from player_box by game (verified 99.89% points
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
    """d: one row per prospect, already carrying the built-dataset primitives
    AND the tm_* / opp_* team-context columns. Returns the engineered feature
    frame."""
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

    # SHOT_PROFILE — stable families only (generic jump shots are excluded) -
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

    # per-100 variants (candidate columns; redundancy assessed against per-40)
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


def engineer_year(year, raw):
    """Raw (pre-engineering) primitives for one season -> the full engineered
    feature row, including team context. `raw` must carry `hoopr_athlete_id`
    plus every column `build_features` reads (as produced by
    `data.build.raw_prospect_features`). Pulled out of `assemble` so a
    population other than the approved partitions (e.g. the declared-pool
    product board in `declared.py`) can reach the identical engineered layer
    without duplicating this logic."""
    ids = set(pd.to_numeric(raw.hoopr_athlete_id, errors="coerce")
              .dropna().astype("int64"))
    ctx = team_context(year, ids)
    ctx["athlete_id"] = ctx.athlete_id.astype("int64")
    raw = raw.copy()
    raw["_aid"] = pd.to_numeric(raw.hoopr_athlete_id, errors="coerce")
    d = raw.merge(ctx.rename(columns={"athlete_id": "_aid"}),
                  on="_aid", how="left").reset_index(drop=True)
    f = build_features(d).reset_index(drop=True)
    cols = [c for c in DENOMINATORS if c in d.columns] + \
           [c for c in AUDIT if c in d.columns]
    keep = pd.concat([d[IDENTITY], d[cols], f], axis=1)
    return keep.loc[:, ~keep.columns.duplicated()]


def assemble(label, years):
    base = pd.read_parquet(DATASET / f"features_{label}.parquet")
    frames = []
    for y in years:
        b = base[base.draft_year == y].copy()
        if b.empty:
            continue
        frames.append(engineer_year(y, b))
    out = pd.concat(frames, ignore_index=True)
    return out.loc[:, ~out.columns.duplicated()]


def feature_columns(df):
    skip = set(IDENTITY) | set(DENOMINATORS) | set(AUDIT) | {"position_3"}
    return [c for c in df.columns
            if c not in skip and pd.api.types.is_numeric_dtype(df[c])]
