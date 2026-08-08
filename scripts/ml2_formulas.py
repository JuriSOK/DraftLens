"""ML-2 basketball formulas — pure, deterministic, unit-testable.

Every formula here is documented in config/ml2_feature_dictionary.csv. Nothing
in this module reads draft outcome, pick, NBA data, age or date of birth.

SAFE DIVISION POLICY (DEC-069): an undefined ratio is NULL, never 0 and never
infinity. 0 made from 0 attempts is UNKNOWN, not 0%. No epsilon is ever added.
"""

import numpy as np
import pandas as pd

# Free-throw possession coefficient used by the conventional TS%, possession,
# usage and turnover-rate formulas. Documented rather than hidden.
FT_POSSESSION_COEF = 0.44


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


# ------------------------------------------------------ shooting efficiency
def fg_pct(fgm, fga):
    return safe_div(fgm, fga)


def efg_pct(fgm, fg3m, fga):
    """(FGM + 0.5 * 3PM) / FGA — credits the extra point of a made three."""
    fgm = pd.to_numeric(pd.Series(fgm), errors="coerce")
    fg3m = pd.to_numeric(pd.Series(fg3m), errors="coerce")
    return safe_div(fgm + 0.5 * fg3m, fga)


def ts_pct(points, fga, fta):
    """PTS / (2 * (FGA + 0.44 * FTA)). Free throws come from player_box only —
    the shot file holds made free throws exclusively (DATA.md §22.3)."""
    fga = pd.to_numeric(pd.Series(fga), errors="coerce")
    fta = pd.to_numeric(pd.Series(fta), errors="coerce")
    return safe_div(points, 2.0 * (fga + FT_POSSESSION_COEF * fta))


# ------------------------------------------------------------- opportunity
def per_game(stat, games):
    return safe_div(stat, games)


def per_40(stat, minutes):
    """40 * stat / minutes. NULL when minutes are 0 or missing."""
    stat = pd.to_numeric(pd.Series(stat), errors="coerce")
    return safe_div(40.0 * stat, minutes)


def per_100(stat, possessions):
    stat = pd.to_numeric(pd.Series(stat), errors="coerce")
    return safe_div(100.0 * stat, possessions)


# ---------------------------------------------------- team context / usage
def team_possessions(fga, fta, orb, tov):
    """Conventional estimate: FGA + 0.44*FTA - ORB + TOV.

    Returned as a plain numeric series (may legitimately be 0 only for an empty
    team-season, which safe_div then treats as undefined downstream).
    """
    fga, fta, orb, tov = (pd.to_numeric(pd.Series(x), errors="coerce")
                          for x in (fga, fta, orb, tov))
    return fga + FT_POSSESSION_COEF * fta - orb + tov


def usage_pct(fga, fta, tov, minutes, tm_fga, tm_fta, tm_tov, tm_minutes):
    """100 * ((FGA + 0.44*FTA + TOV) * (TmMP/5)) /
             (MP * (TmFGA + 0.44*TmFTA + TmTOV))

    Team totals are summed over the prospect's PLAYED games only.
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


def stl_pct(stl, minutes, tm_minutes, opp_possessions):
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
