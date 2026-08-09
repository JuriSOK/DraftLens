#!/usr/bin/env python3
"""Rank prospects by Team Need fit. Thin CLI.

Team Need answers "who best matches the traits we want?", not "who will be
drafted?" — it can and should rank a lower-Overall prospect first when that
prospect fits the request better.

Historical development classes only. The 2026 holdout is never scored.

  python scripts/run_team_need.py --profile SHOOTER --year 2024
  python scripts/run_team_need.py --weights SHOOTING=0.7,SIZE=0.3 --year 2023
  python scripts/run_team_need.py --list
"""

import argparse
import sys

import numpy as np
import pandas as pd

from draftlens.ml.datasets import load_development
from draftlens.team_need.dimensions import compute_components, compute_dimensions
from draftlens.team_need.explanations import explain
from draftlens.team_need.profiles import profile_names
from draftlens.team_need.reference import PercentileReference
from draftlens.team_need.scoring import (SUPPORTED_DIMENSIONS, UnsupportedNeed,
                                         custom_fit, profile_fit, rank_fit)

HOLDOUT_YEAR = 2026


def parse_weights(spec):
    out = {}
    for part in spec.split(","):
        if not part.strip():
            continue
        k, _, v = part.partition("=")
        out[k.strip().upper()] = float(v)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--profile", help=f"one of {profile_names()}")
    ap.add_argument("--weights",
                    help=f"custom need, e.g. SHOOTING=0.7,SIZE=0.3 "
                         f"(available: {SUPPORTED_DIMENSIONS})")
    ap.add_argument("--year", type=int, default=2024,
                    help="development draft class to rank (default 2024)")
    ap.add_argument("--top", type=int, default=12)
    ap.add_argument("--list", action="store_true",
                    help="list profiles and custom dimensions")
    a = ap.parse_args()

    if a.list:
        print("profiles :", ", ".join(profile_names()))
        print("custom   :", ", ".join(SUPPORTED_DIMENSIONS))
        print("ATHLETICISM is UNAVAILABLE — no athleticism measurement exists "
              "in the data and no proxy may be fabricated.")
        return 0
    if not a.profile and not a.weights:
        ap.error("give --profile or --weights (or --list)")
    if a.year == HOLDOUT_YEAR:
        print(f"  REFUSED: {HOLDOUT_YEAR} is the sealed holdout and is not "
              f"scored in ML-7.")
        return 1

    dev = load_development()
    if a.year not in set(dev.draft_year):
        print(f"  {a.year} is not a development class "
              f"{sorted(set(dev.draft_year))}")
        return 1
    cls = dev[dev.draft_year == a.year].reset_index(drop=True)

    ref = PercentileReference()
    components, raw = compute_components(cls, ref)
    dims, coverage = compute_dimensions(cls, ref, components)

    try:
        if a.profile:
            request = a.profile.upper()
            scored = profile_fit(cls, request, ref, components, dims, coverage)
            title = f"PROFILE: {request}"
        else:
            request = parse_weights(a.weights)
            scored = custom_fit(cls, request, ref, components, dims, coverage)
            title = "CUSTOM NEED: " + ", ".join(
                f"{k} {v:g}" for k, v in request.items())
    except (UnsupportedNeed, KeyError) as e:
        print(f"  UNSUPPORTED: {e}")
        return 1

    scored = scored.join(cls[["player_name", "position_3"]])
    ranked = rank_fit(scored)
    exp = explain(components, raw, request, index=ranked.index)

    print(f"{'=' * 78}\n{title} — {a.year} class ({len(cls)} prospects)\n{'=' * 78}")
    show = ranked.head(a.top)
    for _, r in show.iterrows():
        s = exp.loc[r.name]
        score = "n/a" if not np.isfinite(r.fit_score) else f"{int(r.fit_score):3d}"
        flag = "" if r.eligibility_status == "ELIGIBLE" else \
            f"  [{r.eligibility_status.lower().replace('_', ' ')}]"
        print(f"\n{int(r.fit_rank):>3}. {r.player_name:<26} {r.position_3:<8} "
              f"fit {score}{flag}")
        for c in s["strengths"]:
            d = "lower is better" if c["lower_is_better"] else ""
            print(f"       + {c['label']}: {c['percentile']:.0f}th percentile"
                  f"{'  (' + d + ')' if d else ''}")
        for c in s["limiting_components"]:
            print(f"       - {c['label']}: {c['percentile']:.0f}th percentile")
        for c in s["missing_components"]:
            print(f"       ? {c['label']}: {c['reason']}")

    print(f"\n{'=' * 78}")
    print(f"  Fit Score is a 0-100 PEER-RELATIVE trait score for the requested "
          f"need.\n  It is not a probability, not a predicted pick, and it does "
          f"NOT use the\n  General Draft Board. Mean data coverage "
          f"{100 * ranked.data_coverage.mean():.1f}%.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
