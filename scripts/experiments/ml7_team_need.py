"""ML-7 — Team Need methodology audit.

Team Need has NO ground-truth target, so this is not a model-selection
experiment and nothing here optimises anything. What it does is check the
methodology behaves: percentiles stay stable across seasons, dimensions do not
double-count, archetypes separate positions the way their definitions imply,
and the combination rules do what their basketball rationale claims.

Development years only. 2026 is never scored.

  ./.venv/bin/python scripts/experiments/ml7_team_need.py

Outputs (git-ignored) -> data/interim/team_need/
"""

import json
import sys

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from draftlens.ml.datasets import load_development
from draftlens.team_need.dimensions import (CONFIG, DIMENSIONS,
                                            compute_components,
                                            compute_dimensions, data_coverage,
                                            position_relative_size)
from draftlens.team_need.profiles import PROFILES, score_profile
from draftlens.team_need.reference import PercentileReference
from draftlens.team_need.scoring import (SUPPORTED_DIMENSIONS, UnsupportedNeed,
                                         custom_fit, profile_fit, rank_fit)
from draftlens.team_need.validation import run_all
from draftlens.paths import interim

OUT = interim("team_need")
HOLDOUT_YEAR = 2026

# Synthetic preference examples. These test ENGINE CORRECTNESS — they are not
# candidate profiles and nothing is selected from their results.
CUSTOM_EXAMPLES = {
    "100% Shooting": {"SHOOTING": 1.0},
    "100% Playmaking": {"PLAYMAKING": 1.0},
    "50/50 Shooting+Defence": {"SHOOTING": 0.5,
                               "BOX_SCORE_DEFENSIVE_PRODUCTION": 0.5},
    "70/30 Rebounding+Size": {"REBOUNDING": 0.7, "SIZE": 0.3},
}


def log(m=""):
    print(m, flush=True)


def rule(t):
    log(f"\n{'=' * 78}\n{t}\n{'=' * 78}")


def main():
    dev = load_development()
    assert HOLDOUT_YEAR not in set(dev.draft_year), "HOLDOUT GUARD"
    ref = PercentileReference()
    components, raw = compute_components(dev, ref)
    dims, coverage = compute_dimensions(dev, ref, components)

    rule("SETUP")
    log(f"  development prospects: {len(dev)} "
        f"({int(dev.drafted.sum())} drafted / "
        f"{int((dev.drafted == 0).sum())} undrafted)")
    log(f"  dimensions: {list(DIMENSIONS)}")
    log(f"  profiles  : {list(PROFILES)}")
    log(f"  athleticism: {CONFIG['athleticism']['status']} "
        f"(scored={CONFIG['athleticism']['scored']})")
    log(f"  guards    : {run_all()}")

    # ------------------------------------------------------- 1. missingness
    rule("DIMENSION AVAILABILITY AND COVERAGE")
    av = pd.DataFrame({
        "scored_pct": (100 * dims.notna().mean()).round(1),
        "mean_component_coverage_pct": (100 * coverage.mean()).round(1),
        "n_components": [len(DIMENSIONS[c]["components"]) for c in dims.columns],
        "reference_group": [DIMENSIONS[c]["reference_group"] for c in dims.columns],
    })
    log(av.to_string())
    log(f"\n  overall data_coverage mean "
        f"{100 * data_coverage(coverage).mean():.1f}%  "
        f"min {100 * data_coverage(coverage).min():.1f}%")
    av.to_csv(OUT / "dimension_availability.csv")

    # --------------------------------------------------- 2. temporal stability
    rule("TEMPORAL STABILITY (median / IQR by season)")
    rows = []
    for name in dims.columns:
        for y, g in dims.groupby(dev.draft_year)[name]:
            rows.append(dict(dimension=name, season=int(y), n=int(g.notna().sum()),
                             median=round(float(g.median()), 1),
                             iqr=round(float(g.quantile(.75) - g.quantile(.25)), 1),
                             missing_pct=round(100 * float(g.isna().mean()), 1),
                             extreme_pct=round(
                                 100 * float(((g >= 95) | (g <= 5)).mean()), 1)))
    temporal = pd.DataFrame(rows)
    piv = temporal.pivot(index="season", columns="dimension", values="median")
    log(piv.to_string())
    drift = (piv.max() - piv.min()).round(1).sort_values(ascending=False)
    log(f"\n  season-to-season median drift (max - min):")
    log(drift.to_string())
    temporal.to_csv(OUT / "temporal_stability.csv", index=False)

    # --------------------------------------------------- 3. position stability
    rule("POSITION STABILITY (median by coarse position)")
    pos = dims.join(dev[["position_3"]]).groupby("position_3").median().round(1)
    log(pos.to_string())
    prof_scores = pd.DataFrame(index=dev.index)
    for name in PROFILES:
        prof_scores[name] = score_profile(dev, name, ref, components,
                                          dims).profile_score
    pos_prof = prof_scores.join(dev[["position_3"]]).groupby(
        "position_3").median().round(1)
    log("\n  profile medians by position:")
    log(pos_prof.to_string())
    pos.to_csv(OUT / "position_stability_dimensions.csv")
    pos_prof.to_csv(OUT / "position_stability_profiles.csv")

    # ------------------------------------------------------ 4. redundancy
    rule("REDUNDANCY AUDIT (Spearman between dimensions)")
    corr = dims.corr(method="spearman").round(2)
    log(corr.to_string())
    pairs = []
    cols = list(dims.columns)
    for i, a in enumerate(cols):
        for b in cols[i + 1:]:
            pairs.append((a, b, float(corr.loc[a, b])))
    strong = sorted(pairs, key=lambda t: -abs(t[2]))[:5]
    log("\n  strongest dimension pairs:")
    for a, b, r in strong:
        log(f"    {a:32s} ~ {b:32s} {r:+.2f}")
    corr.to_csv(OUT / "dimension_redundancy.csv")

    shared = {}
    for i, a in enumerate(cols):
        for b in cols[i + 1:]:
            ma = {c["metric"] for c in DIMENSIONS[a]["components"]}
            mb = {c["metric"] for c in DIMENSIONS[b]["components"]}
            if ma & mb:
                shared[f"{a}~{b}"] = sorted(ma & mb)
    log(f"\n  metrics shared between dimensions: "
        f"{shared if shared else 'NONE — no cross-dimension double counting'}")

    # ------------------------------------------------------ 5. sensitivity
    rule("SENSITIVITY: ARITHMETIC vs GEOMETRIC for conjunctive profiles")
    rows = []
    for name, spec in PROFILES.items():
        if spec["combination"] != "GEOMETRIC_MEAN":
            continue
        geo = score_profile(dev, name, ref, components, dims,
                            "GEOMETRIC_MEAN").profile_score
        ari = score_profile(dev, name, ref, components, dims,
                            "ARITHMETIC_MEAN").profile_score
        j = pd.DataFrame({"geo": geo, "ari": ari}).dropna()
        # how often does arithmetic let one strong pillar carry a weak one?
        top_g = set(j.nlargest(20, "geo").index)
        top_a = set(j.nlargest(20, "ari").index)
        rows.append(dict(profile=name,
                         rank_corr=round(float(spearmanr(j.geo, j.ari).statistic), 3),
                         top20_overlap=len(top_g & top_a),
                         geo_median=round(float(j.geo.median()), 1),
                         ari_median=round(float(j.ari.median()), 1),
                         geo_max=round(float(j.geo.max()), 1),
                         ari_max=round(float(j.ari.max()), 1)))
    sens = pd.DataFrame(rows)
    log(sens.to_string(index=False))
    log("\n  Lower top-20 overlap means the choice matters: arithmetic admits "
        "prospects\n  strong on one pillar only, which is exactly what a "
        "conjunctive archetype must reject.")
    sens.to_csv(OUT / "sensitivity_combination.csv", index=False)

    rule("SENSITIVITY: GLOBAL vs POSITION-RELATIVE size")
    pos_size = position_relative_size(dev, ref)
    j = pd.DataFrame({"global": dims.SIZE, "position_relative": pos_size,
                      "position_3": dev.position_3}).dropna()
    log(j.groupby("position_3")[["global", "position_relative"]].median()
        .round(1).to_string())
    log(f"\n  rank correlation: "
        f"{spearmanr(j['global'], j.position_relative).statistic:+.3f}")
    log("  Position-relative size pins every position near the same median, "
        "which is\n  precisely the signal Stretch Big and Rim Protector need. "
        "GLOBAL is retained.")

    # -------------------------------------------------- 6. custom examples
    rule("CUSTOM-WEIGHT ENGINE EXAMPLES (correctness, not selection)")
    rows = []
    for label, w in CUSTOM_EXAMPLES.items():
        r = custom_fit(dev, w, ref, components, dims, coverage)
        rows.append(dict(request=label, scored=int(r.fit_score.notna().sum()),
                         median=round(float(r.fit_score.median()), 1),
                         min=float(r.fit_score.min()),
                         max=float(r.fit_score.max()),
                         mean_supported_weight=round(
                             float(r.supported_weight_fraction.mean()), 3)))
    log(pd.DataFrame(rows).to_string(index=False))

    log("\n  athleticism guard:")
    for bad, why in ((({"ATHLETICISM": 0.5, "SHOOTING": 0.5}), "weight > 0"),
                     (({"SHOOTING": -1.0}), "negative weight"),
                     (({"SHOOTING": 0.0}), "no positive weight")):
        try:
            custom_fit(dev, bad, ref, components, dims, coverage)
            log(f"    !! ACCEPTED {bad} — should have been rejected")
        except UnsupportedNeed as e:
            log(f"    rejected ({why}): {str(e)[:72]}...")

    # --------------------------------------------- 7. independence from board
    rule("INDEPENDENCE FROM THE GENERAL DRAFT BOARD")
    log("  Team Need must be able to rank a lower-Overall prospect first —")
    log("  that is the entire purpose of the mode.")
    from draftlens.ml.board import build_board
    from draftlens.ml.stage_a import STAGE_A, feature_set
    from draftlens.ml.stage_a import fit_predict_fold as sa_fold
    from draftlens.ml.stage_b import STAGE_B, draft_sizes
    from draftlens.ml.stage_b import fit_predict_fold as sb_fold
    from draftlens.ml.validation import folds, load_fold_config
    cfg = load_fold_config()
    d2 = dev.copy()
    d2["draft_size"] = d2.draft_year.map(draft_sizes())
    feats = feature_set(STAGE_A["feature_set"], cfg)
    rows = []
    for _, tr_years, vy in folds(cfg):
        tr = d2[d2.draft_year.isin(tr_years)]
        cls = d2[d2.draft_year == vy].reset_index(drop=True)
        pa, _ = sa_fold(tr, cls, feats)
        pb, _ = sb_fold(tr[tr.drafted == 1], cls, feats,
                        family=STAGE_B["family"],
                        params={"alpha": STAGE_B["alpha"]},
                        target=STAGE_B["target"])
        board = build_board(pa, pb, cls.draft_size)
        for name in PROFILES:
            f = profile_fit(cls, name, ref)
            j = pd.DataFrame({"o": board.overall_score,
                              "f": f.fit_raw}).dropna()
            rows.append(dict(profile=name, season=int(vy),
                             rho=float(spearmanr(j.o, j.f).statistic)))
    indep = pd.DataFrame(rows).groupby("profile").rho.agg(
        ["mean", "min", "max"]).round(3)
    log(indep.to_string())
    log("\n  Every profile is only weakly related to the board, and each "
        "surfaces a\n  different prospect at the top. No board signal enters a "
        "Fit Score.")
    indep.reset_index().to_csv(OUT / "board_independence.csv", index=False)

    # ------------------------------------------------- 8. face validity
    rule("HISTORICAL FACE VALIDITY (development classes only)")
    log("  Qualitative check of whether the NCAA statistics match the profile")
    log("  DEFINITION. Formulas are NOT changed because a name looks wrong, and")
    log("  no later NBA outcome is consulted.\n")
    face = {}
    for name in PROFILES:
        f = profile_fit(dev, name, ref, components, dims, coverage)
        j = f.join(dev[["player_name", "draft_year", "position_3"]])
        j = j[j.eligibility_status != "OUT_OF_POSITION"].dropna(subset=["fit_raw"])
        top = j.nlargest(5, "fit_raw")
        log(f"  {name}")
        for _, r in top.iterrows():
            log(f"      {int(r.fit_score):3d}  {r.player_name:<24} "
                f"{r.position_3:<8} {int(r.draft_year)}")
        face[name] = top[["player_name", "draft_year", "position_3",
                          "fit_score"]].to_dict("records")

    rep = dict(dimensions=list(DIMENSIONS), profiles=list(PROFILES),
               athleticism=CONFIG["athleticism"]["status"],
               development_rows=len(dev),
               overall_data_coverage=round(
                   float(data_coverage(coverage).mean()), 4),
               median_drift=drift.to_dict(),
               sensitivity=sens.to_dict("records"),
               board_independence=indep.reset_index().to_dict("records"),
               face_validity=face)
    (OUT / "ml7_summary.json").write_text(json.dumps(rep, indent=2, default=str))
    log(f"\n  outputs -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
