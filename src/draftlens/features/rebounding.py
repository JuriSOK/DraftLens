"""Rebounding rates."""

import pandas as pd

from draftlens.features.rates import safe_div


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
