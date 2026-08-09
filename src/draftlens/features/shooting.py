"""Shooting efficiency."""

import pandas as pd

from draftlens.features.rates import FT_POSSESSION_COEF, safe_div


def fg_pct(fgm, fga):
    return safe_div(fgm, fga)


def efg_pct(fgm, fg3m, fga):
    """(FGM + 0.5 * 3PM) / FGA — credits the extra point of a made three."""
    fgm = pd.to_numeric(pd.Series(fgm), errors="coerce")
    fg3m = pd.to_numeric(pd.Series(fg3m), errors="coerce")
    return safe_div(fgm + 0.5 * fg3m, fga)


def ts_pct(points, fga, fta):
    """PTS / (2 * (FGA + 0.44 * FTA)). Free throws come from player_box only —
    the shot file holds made free throws exclusively (DATA.md 22.3)."""
    fga = pd.to_numeric(pd.Series(fga), errors="coerce")
    fta = pd.to_numeric(pd.Series(fta), errors="coerce")
    return safe_div(points, 2.0 * (fga + FT_POSSESSION_COEF * fta))
