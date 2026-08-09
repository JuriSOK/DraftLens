"""Playmaking, usage and ball security.

Team totals are always summed over the prospect's PLAYED games only (DEC-072),
never the full team season — a player who missed half a season did not share
the floor with those possessions.
"""

import pandas as pd

from draftlens.features.rates import FT_POSSESSION_COEF, safe_div


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
