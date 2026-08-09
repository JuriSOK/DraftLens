"""ML-8 — NBA comparable methodology audit.

There is no ground-truth "correct comparable", so nothing here optimises
anything. What it does is check the methodology behaves: that the top three are
stable under reasonable changes to the representation and the metric, that no
single dimension is carrying the result, that the third neighbour is not
arbitrary, and that the dimensions are not measuring the same thing twice.

Development NCAA prospects only. No 2026 prospect is scored.

  ./.venv/bin/python scripts/experiments/ml8_comparables.py

Outputs (git-ignored) -> data/interim/comparables/
"""

import json
import sys
import warnings

import numpy as np
import pandas as pd

from draftlens.comparables.explanations import explain_comparables
from draftlens.comparables.reference import (MIN_GAMES, MIN_MINUTES,
                                             REFERENCE_SEASONS,
                                             build_ncaa_reference, build_pool,
                                             load_ncaa_reference, load_pool)
from draftlens.comparables.similarity import (METRICS, MIN_SHARED_COVERAGE,
                                              build_distance_reference,
                                              find_comparables, pairwise_distances,
                                              prepare_pool, similarity_scores,
                                              within_pool_percentile)
from draftlens.comparables.space import (COMMON_METRICS, DIMENSION_NAMES,
                                         DIMENSIONS, build_nba_space,
                                         build_ncaa_space)
from draftlens.comparables import validation as cv
from draftlens.ml.datasets import load_development
from draftlens.paths import interim

warnings.filterwarnings("ignore", category=RuntimeWarning)
OUT = interim("comparables")
HOLDOUT_YEAR = 2026
AUDIT_N = 200          # prospects sampled for the stability audits
SEED = 20260808


def log(m=""):
    print(m, flush=True)


def rule(t):
    log(f"\n{'=' * 78}\n{t}\n{'=' * 78}")


def top3(prospect_dims, pool, pool_dims, idx, names, dimensions=None,
         metric="EUCLIDEAN", dist_ref=None):
    """{prospect index -> tuple of the three NBA ids}, for overlap comparisons."""
    out = {}
    for i in idx:
        r = find_comparables(prospect_dims.loc[i], pool, pool_dims,
                             dimensions=dimensions, metric=metric,
                             prospect_name=names.get(i),
                             distance_reference=dist_ref)
        if r["status"] == "OK":
            out[i] = tuple(c["nba_player_id"] for c in r["comparables"])
    return out


def overlap(a, b):
    """Mean size of the intersection of two top-3 sets, over shared prospects."""
    keys = set(a) & set(b)
    if not keys:
        return np.nan, 0
    vals = [len(set(a[k]) & set(b[k])) for k in keys]
    return float(np.mean(vals)), len(keys)


def main():
    dev = load_development()
    assert HOLDOUT_YEAR not in set(dev.draft_year), "HOLDOUT GUARD"
    ncaa_ref = load_ncaa_reference()
    names = dev.player_name.to_dict()

    rule("SETUP")
    log(f"  development prospects : {len(dev)}")
    log(f"  NBA reference seasons : {REFERENCE_SEASONS[0]}-{REFERENCE_SEASONS[-1]}")
    log(f"  NBA eligibility       : >= {MIN_MINUTES} min, >= {MIN_GAMES} games")
    log(f"  common dimensions     : {len(DIMENSION_NAMES)} "
        f"({len(COMMON_METRICS)} metrics)")
    log(f"  guards                : {cv.run_all()}")

    pool = prepare_pool(load_pool())
    nba_dims, nba_pct = build_nba_space(pool)
    ncaa_dims, ncaa_pct = build_ncaa_space(dev, ncaa_ref)
    cv.check_pool_unique(pool)

    rng = np.random.default_rng(SEED)
    scorable = [i for i in dev.index
                if np.isfinite(ncaa_dims.loc[i].to_numpy(dtype="float64")).sum()
                >= int(np.ceil(MIN_SHARED_COVERAGE * len(DIMENSION_NAMES)))]
    audit_idx = list(rng.choice(scorable, size=min(AUDIT_N, len(scorable)),
                                replace=False))
    log(f"  scorable prospects    : {len(scorable)} of {len(dev)}")
    log(f"  audit sample          : {len(audit_idx)}")

    dist_ref = build_distance_reference(ncaa_dims, nba_dims, max_prospects=300)
    log(f"  distance reference    : {len(dist_ref)} pairings, "
        f"median {np.median(dist_ref):.1f}")

    # ------------------------------------------------ 1. dimension coverage
    rule("DIMENSION COVERAGE")
    cov = pd.DataFrame({
        "ncaa_prospects_pct": (100 * ncaa_dims.notna().mean()).round(1),
        "nba_pool_pct": (100 * nba_dims.notna().mean()).round(1),
        "kind": [DIMENSIONS[d]["kind"] for d in ncaa_dims.columns],
        "n_metrics": [len(DIMENSIONS[d]["metrics"]) for d in ncaa_dims.columns]})
    log(cov.to_string())
    cov.to_csv(OUT / "dimension_coverage.csv")

    # ------------------------------------------------------ 2. redundancy
    rule("REDUNDANCY — dimension correlations within each league")
    for label, dims in (("NCAA", ncaa_dims), ("NBA", nba_dims)):
        c = dims.corr(method="spearman").round(2)
        log(f"\n  {label}:")
        log(c.to_string())
        c.to_csv(OUT / f"redundancy_{label.lower()}.csv")
        pairs = [(a, b, float(c.loc[a, b]))
                 for i, a in enumerate(dims.columns) for b in dims.columns[i + 1:]]
        worst = max(pairs, key=lambda t: abs(t[2]))
        log(f"  strongest pair: {worst[0]} ~ {worst[1]} = {worst[2]:+.2f}")
    shared = {}
    cols = list(DIMENSIONS)
    for i, a in enumerate(cols):
        for b in cols[i + 1:]:
            ov = set(DIMENSIONS[a]["metrics"]) & set(DIMENSIONS[b]["metrics"])
            if ov:
                shared[f"{a}~{b}"] = sorted(ov)
    log(f"\n  metrics shared between dimensions: "
        f"{shared if shared else 'NONE — no double counting'}")

    # ---------------------------------------- 3. NBA representation stability
    rule("NBA REPRESENTATION STABILITY (top-3 overlap, 0-3)")
    base = top3(ncaa_dims, pool, nba_dims, audit_idx, names, dist_ref=dist_ref)
    rows = []
    for rep in ("LATEST_SEASON", "CAREER"):
        alt_pool = prepare_pool(build_pool(rep))
        alt_dims, _ = build_nba_space(alt_pool)
        alt = top3(ncaa_dims, alt_pool, alt_dims, audit_idx, names,
                   dist_ref=dist_ref)
        m, n = overlap(base, alt)
        rows.append(dict(representation=rep, mean_top3_overlap=round(m, 2),
                         pct_of_3=round(100 * m / 3, 1), prospects=n,
                         pool_size=len(alt_pool)))
    log(pd.DataFrame(rows).to_string(index=False))
    log(f"\n  baseline: RECENT_MULTI_SEASON, pool {len(pool)}")
    pd.DataFrame(rows).to_csv(OUT / "representation_stability.csv", index=False)

    # ------------------------------------------ 4. similarity-metric stability
    rule("SIMILARITY METRIC STABILITY (vs EUCLIDEAN)")
    rows = []
    for metric in METRICS:
        alt = top3(ncaa_dims, pool, nba_dims, audit_idx, names, metric=metric,
                   dist_ref=None)
        m, n = overlap(base, alt)
        rows.append(dict(metric=metric, mean_top3_overlap=round(m, 2),
                         pct_of_3=round(100 * m / 3, 1), prospects=n))
    log(pd.DataFrame(rows).to_string(index=False))
    pd.DataFrame(rows).to_csv(OUT / "metric_stability.csv", index=False)

    # ------------------------------- 5. leave-one-dimension-out stability
    rule("LEAVE-ONE-DIMENSION-OUT STABILITY")
    rows = []
    for d in DIMENSION_NAMES:
        keep = [x for x in DIMENSION_NAMES if x != d]
        alt = top3(ncaa_dims, pool, nba_dims, audit_idx, names, dimensions=keep,
                   dist_ref=None)
        m, n = overlap(base, alt)
        rows.append(dict(dropped=d, kind=DIMENSIONS[d]["kind"],
                         mean_top3_overlap=round(m, 2),
                         pct_of_3=round(100 * m / 3, 1)))
    loo = pd.DataFrame(rows).sort_values("mean_top3_overlap")
    log(loo.to_string(index=False))
    log("\n  A system whose top three collapse when one dimension is removed is")
    log("  fragile. Higher overlap = no single dimension is carrying the result.")
    loo.to_csv(OUT / "leave_one_out_stability.csv", index=False)

    # ---------------------------------- 6. global vs position-relative
    rule("GLOBAL vs POSITION-RELATIVE NORMALISATION")
    nba_pos, _ = build_nba_space(pool, group_col="position_3")
    ncaa_pos, _ = build_ncaa_space(dev, ncaa_ref, group_col="position_3")
    alt = top3(ncaa_pos, pool, nba_pos, audit_idx, names, dist_ref=None)
    m, n = overlap(base, alt)
    log(f"  top-3 overlap with the GLOBAL baseline: {m:.2f} of 3 "
        f"({100 * m / 3:.1f}%) over {n} prospects")
    log("  Position-relative normalisation asks a different question: it would")
    log("  erase the cross-position resemblance the product exists to surface —")
    log("  a stretch big resembling a wing is a finding, not an error.")

    # ------------------------------------------- 7. neighbour margin
    rule("NEIGHBOUR MARGIN (3rd vs 4th)")
    margins, d1, d3 = [], [], []
    M = nba_dims[DIMENSION_NAMES].to_numpy(dtype="float64")
    for i in audit_idx:
        p = ncaa_dims.loc[i, DIMENSION_NAMES].to_numpy(dtype="float64")
        d, _ = pairwise_distances(p, M)
        d = np.sort(d[np.isfinite(d)])
        if len(d) > 3:
            margins.append(d[3] - d[2])
            d1.append(d[0])
            d3.append(d[2])
    mg = pd.Series(margins)
    log(f"  3rd-vs-4th margin: median {mg.median():.2f}  "
        f"p25 {mg.quantile(.25):.2f}  p75 {mg.quantile(.75):.2f}  "
        f"min {mg.min():.2f}")
    log(f"  distance to #1: median {np.median(d1):.2f} | "
        f"to #3: median {np.median(d3):.2f}")
    log(f"  margin as a share of the #3 distance: "
        f"median {np.median(np.array(margins) / np.array(d3)) * 100:.1f}%")
    pd.DataFrame({"margin": margins, "d1": d1, "d3": d3}).to_csv(
        OUT / "neighbour_margins.csv", index=False)

    # ------------------------------------------ 8. similarity-score transforms
    rule("SIMILARITY SCORE TRANSFORMS")
    rows = []
    for i in audit_idx[:60]:
        p = ncaa_dims.loc[i, DIMENSION_NAMES].to_numpy(dtype="float64")
        d, _ = pairwise_distances(p, M)
        wp = within_pool_percentile(d)
        gp = similarity_scores(d, dist_ref)
        o = np.argsort(d)[:3]
        rows.append(dict(prospect=names[i],
                         within_pool=[round(float(wp[j]), 2) for j in o],
                         global_ref=[int(round(float(gp[j]))) for j in o],
                         distances=[round(float(d[j]), 1) for j in o]))
    sc = pd.DataFrame(rows)
    log("  WITHIN_POOL_PERCENTILE is identical for every prospect by "
        "construction:")
    log(f"    {sc.within_pool.iloc[0]}   {sc.within_pool.iloc[1]}   "
        f"{sc.within_pool.iloc[2]}")
    log("  GLOBAL_DISTANCE_PERCENTILE varies with how good the match actually is:")
    for _, r in sc.head(5).iterrows():
        log(f"    {r.prospect:<24} {r.global_ref}   distances {r.distances}")
    gvals = [v for r in sc.global_ref for v in r]
    log(f"\n  global-reference score range over the sample: "
        f"{min(gvals)}-{max(gvals)}")
    sc.to_csv(OUT / "score_transform_comparison.csv", index=False)

    # ----------------------------------------------- 9. self-match guard
    rule("HISTORICAL SELF-MATCH GUARD")
    pool_keys = set(pool["_name_key"])
    from draftlens.data.identity.normalization import normalize_name
    in_pool = [i for i in dev.index
               if normalize_name(dev.loc[i, "player_name"]) in pool_keys]
    log(f"  development prospects who later appear in the NBA pool: "
        f"{len(in_pool)}")
    violations = 0
    for i in in_pool:
        if i not in ncaa_dims.index:
            continue
        r = find_comparables(ncaa_dims.loc[i], pool, nba_dims,
                             prospect_name=dev.loc[i, "player_name"],
                             distance_reference=dist_ref)
        if r["status"] != "OK":
            continue
        try:
            cv.check_no_self_match(r, dev.loc[i, "player_name"])
        except AssertionError:
            violations += 1
    log(f"  self-match violations: {violations} (must be 0)")

    # -------------------------------------------- 10. face validity
    rule("HISTORICAL FACE VALIDITY (development prospects only)")
    log("  A sanity audit of whether neighbours are close IN THE DIMENSIONS.")
    log("  Formulas are NOT changed because a name looks wrong, and no NBA")
    log("  career outcome is consulted.\n")
    examples = ["Trae Young", "Zach Edey", "Mikal Bridges", "Tyrese Haliburton",
                "Jalen Williams", "Walker Kessler"]
    face = {}
    for nm in examples:
        m = dev.player_name == nm
        if not m.any():
            continue
        i = dev.index[m][0]
        r = find_comparables(ncaa_dims.loc[i], pool, nba_dims, prospect_name=nm,
                             distance_reference=dist_ref)
        if r["status"] != "OK":
            continue
        cv.check_result(r)
        cv.check_no_self_match(r, nm)
        comps = ", ".join(f"{c['nba_player_name']} ({c['similarity_score']})"
                          for c in r["comparables"])
        log(f"  {nm:<22} {int(dev.loc[i, 'draft_year'])}  ->  {comps}")
        face[nm] = r["comparables"]

    rep = dict(nba_seasons=REFERENCE_SEASONS, nba_pool=len(pool),
               dimensions=DIMENSION_NAMES, metrics=COMMON_METRICS,
               audit_sample=len(audit_idx),
               scorable_prospects=len(scorable),
               representation_stability=rows if False else None,
               leave_one_out=loo.to_dict("records"),
               margin_median=float(mg.median()),
               self_match_violations=violations,
               face_validity={k: [{kk: vv for kk, vv in c.items()
                                   if kk in ("rank", "nba_player_name",
                                             "similarity_score",
                                             "raw_distance")}
                                  for c in v] for k, v in face.items()})
    (OUT / "ml8_summary.json").write_text(json.dumps(rep, indent=2, default=str))
    log(f"\n  outputs -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
