"""ML-2 validation + audits (redundancy, missingness, target sanity).

Hard-fails on population loss, leakage, invalid ranges and holdout bleed.
Target-aware audits are DEVELOPMENT ONLY — the 2026 target file is never opened.

  ./.venv/bin/python scripts/validate_ml2_features.py
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_model_dataset import OUT as ML0  # noqa: E402
from build_ml2_features import (AUDIT, DENOMINATORS, EXPECTED_ROWS,  # noqa: E402
                                IDENTITY, OUT as ML2, feature_columns)

DICT = Path(__file__).resolve().parents[1] / "config" / "ml2_feature_dictionary.csv"
DEV = "2014_2025"
FAIL, WARN = [], []

FORBIDDEN = {"drafted", "pick", "round", "drafting_team",
             "position_from_population", "class_from_population",
             "match_method", "match_confidence",
             "date_of_birth", "age", "current_age", "dob"}
FORBIDDEN_SUBSTR = ("jump_shot", "nba_", "mock", "consensus", "analyst")
# ratios that must lie in [0, 1]
UNIT_INTERVAL = ("fg_pct", "two_point_pct", "three_point_pct", "ft_pct",
                 "efg_pct", "ts_pct", "start_share", "layup_make_pct",
                 "dunk_make_pct", "tip_make_pct", "rim_make_pct",
                 "layup_attempt_share", "dunk_attempt_share",
                 "tip_attempt_share", "three_point_shot_attempt_share",
                 "rim_attempt_share", "assisted_made_fg_share",
                 "unassisted_made_fg_share", "assisted_layup_make_share",
                 "unassisted_layup_make_share", "assisted_dunk_make_share",
                 "unassisted_dunk_make_share", "three_point_attempt_rate",
                 "two_point_attempt_rate")
PERCENT_0_100 = ("usage_pct", "ast_pct", "tov_pct", "orb_pct", "drb_pct",
                 "trb_pct", "stl_pct", "blk_pct")


def rule(t):
    print(f"\n{'=' * 78}\n{t}\n{'=' * 78}")


def check(cond, msg, hard=True):
    if cond:
        return True
    (FAIL if hard else WARN).append(msg)
    print(f"  {'FAIL' if hard else 'WARN'}  {msg}")
    return False


def load_dev_targets():
    return pd.read_parquet(ML0 / f"targets_{DEV}.parquet")


def load_targets_guarded(label):
    if label == "2026":
        raise AssertionError("ML-2 must not load the 2026 target file")
    return pd.read_parquet(ML0 / f"targets_{label}.parquet")


def main():
    rep = {}
    rule("ML-2 VALIDATION")
    if not (ML2 / f"features_{DEV}.parquet").exists():
        print("  FAIL  ML-2 outputs missing — run build_ml2_features.py")
        return 1

    frames = {}
    for label, exp in EXPECTED_ROWS.items():
        f = pd.read_parquet(ML2 / f"features_{label}.parquet")
        frames[label] = f
        print(f"\n--- {label} ---")
        check(len(f) == exp, f"{label}: expected {exp} rows, got {len(f)}")
        check(not f.canonical_prospect_id.duplicated().any(),
              f"{label}: duplicate canonical_prospect_id")

        cols = {c.lower() for c in f.columns}
        bad = cols & FORBIDDEN
        check(not bad, f"{label}: forbidden columns present: {sorted(bad)}")
        sub = [c for c in cols if any(s in c for s in FORBIDDEN_SUBSTR)]
        check(not sub, f"{label}: forbidden-substring columns: {sub}")

        feats = feature_columns(f)
        num = f[feats]
        infs = {c: int(np.isinf(num[c].dropna()).sum()) for c in feats
                if np.isinf(num[c].dropna()).any()}
        check(not infs, f"{label}: infinities in {infs}")

        for c in UNIT_INTERVAL:
            if c in f.columns:
                v = f[c].dropna()
                n = int(((v < 0) | (v > 1)).sum())
                check(n == 0, f"{label}: {c} outside [0,1] on {n} rows")
        for c in PERCENT_0_100:
            if c in f.columns:
                v = f[c].dropna()
                n = int(((v < 0) | (v > 100)).sum())
                check(n == 0, f"{label}: {c} outside [0,100] on {n} rows")
        for c in feats:
            v = f[c].dropna()
            if c.endswith(("_per_40", "_per_game", "_per_100")) or \
                    c in ("free_throw_rate", "assist_to_turnover_ratio"):
                check(int((v < 0).sum()) == 0,
                      f"{label}: negative values in {c}")

        # ML-0 parity: every ML-0 prospect must survive into ML-2
        m0 = pd.read_parquet(ML0 / f"features_{label}.parquet")
        check(set(f.canonical_prospect_id) == set(m0.canonical_prospect_id),
              f"{label}: prospect set differs from ML-0 "
              f"(lost {len(set(m0.canonical_prospect_id) - set(f.canonical_prospect_id))})")
        check(set(f.draft_year) <= set(range(2011, 2027)),
              f"{label}: unexpected draft years")
        rep[label] = dict(rows=len(f), engineered=len(feats))

    # partition disjointness
    dev_ids = set(frames[DEV].canonical_prospect_id)
    hold_ids = set(frames["2026"].canonical_prospect_id)
    check(not (dev_ids & hold_ids), "2026 holdout overlaps development")

    # unresolved prospects retained (all undrafted — dropping biases the sample)
    dev = frames[DEV]
    unmatched = int(dev.hoopr_athlete_id.isna().sum())
    print(f"\n  unresolved prospects retained: {unmatched}")
    check(unmatched >= 8, f"unresolved prospects lost (found {unmatched}, expected >=8)")
    rep["unresolved_retained"] = unmatched

    # dictionary parity
    d = pd.read_csv(DICT)
    documented = set(d[d.status.isin(["APPROVED", "CAUTION"])].feature_name)
    built = set(feature_columns(dev)) | {"position_3"}
    check(built <= documented,
          f"undocumented engineered features: {sorted(built - documented)}")
    check(documented <= built | {"position_3"},
          f"documented but not built: {sorted(documented - built)}", hard=False)

    # ---------------------------------------------------------- audits
    rule("MISSINGNESS (development)")
    feats = feature_columns(dev)
    cov = pd.DataFrame({"feature": feats,
                        "coverage_pct": [round(100 * dev[c].notna().mean(), 2)
                                         for c in feats]}).sort_values("coverage_pct")
    print(cov.head(10).to_string(index=False))
    cov.to_csv(ML2 / "audit_coverage.csv", index=False)

    by_pos = dev.groupby("position_3")[feats].apply(
        lambda g: g.notna().mean().mul(100).round(1))
    by_pos.to_csv(ML2 / "audit_coverage_by_position.csv")
    by_year = dev.groupby("draft_year")[feats].apply(
        lambda g: g.notna().mean().mul(100).round(1))
    by_year.to_csv(ML2 / "audit_coverage_by_year.csv")
    print(f"\n  worst season-level coverage: "
          f"{by_year.min().min():.1f}% ({by_year.min().idxmin()})")

    rule("TARGET-AWARE SANITY (development only)")
    tgt = load_dev_targets()
    m = dev.merge(tgt[["canonical_prospect_id", "drafted"]],
                  on="canonical_prospect_id", how="inner")
    assert 2026 not in set(m.draft_year), "holdout guard"
    rows = []
    for c in feats:
        dd = pd.to_numeric(m.loc[m.drafted == 1, c], errors="coerce").dropna()
        uu = pd.to_numeric(m.loc[m.drafted == 0, c], errors="coerce").dropna()
        if len(dd) < 20 or len(uu) < 20:
            continue
        allv = pd.concat([dd, uu])
        r = allv.rank()
        n1, n2 = len(dd), len(uu)
        auc = (r.iloc[:n1].sum() - n1 * (n1 + 1) / 2) / (n1 * n2)
        rows.append(dict(feature=c, median_drafted=round(float(dd.median()), 3),
                         median_undrafted=round(float(uu.median()), 3),
                         rank_auc=round(float(auc), 3),
                         cov_drafted=round(100 * m.loc[m.drafted == 1, c].notna().mean(), 1),
                         cov_undrafted=round(100 * m.loc[m.drafted == 0, c].notna().mean(), 1)))
    ta = pd.DataFrame(rows)
    ta["separation"] = (ta.rank_auc - 0.5).abs()
    ta["cov_gap_pp"] = (ta.cov_drafted - ta.cov_undrafted).round(2)
    ta = ta.sort_values("separation", ascending=False)
    ta.to_csv(ML2 / "audit_target_association.csv", index=False)
    print(ta.head(10)[["feature", "median_drafted", "median_undrafted",
                       "rank_auc", "cov_gap_pp"]].to_string(index=False))
    top = ta.iloc[0]
    print(f"\n  strongest separation: {top.feature} rank_auc={top.rank_auc}")
    check(ta.separation.max() < 0.45,
          f"{top.feature} separates target almost perfectly "
          f"(rank_auc={top.rank_auc}) — investigate provenance")
    gap = ta.cov_gap_pp.abs().max()
    worst = ta.reindex(ta.cov_gap_pp.abs().sort_values(ascending=False).index)
    print(f"  largest drafted-vs-undrafted coverage gap: {gap:.2f}pp")
    print("  features whose DEFINEDNESS tracks the target (top 6):")
    print(worst.head(6)[["feature", "cov_drafted", "cov_undrafted",
                         "cov_gap_pp"]].to_string(index=False))
    check(gap < 10, f"coverage gap {gap:.2f}pp suggests target-linked missingness",
          hard=False)
    rep["max_rank_auc"] = float(ta.rank_auc.max())
    rep["max_cov_gap_pp"] = float(gap)

    rule("REDUNDANCY (development, engineered features only)")
    corr = dev[feats].corr().abs()   # triu(k=1) below excludes the diagonal
    pairs = (corr.where(np.triu(np.ones(corr.shape), 1).astype(bool))
             .stack().reset_index())
    pairs.columns = ["feature_a", "feature_b", "abs_corr"]
    high = pairs[pairs.abs_corr >= 0.95].sort_values("abs_corr", ascending=False)
    high.to_csv(ML2 / "audit_redundancy.csv", index=False)
    print(f"  pairs with |r| >= 0.95: {len(high)}")
    print(high.head(12).to_string(index=False))
    rep["redundant_pairs_ge_095"] = len(high)

    (ML2 / "validation_report.json").write_text(json.dumps(rep, indent=2,
                                                           default=str))
    rule("RESULT")
    print(f"  hard failures: {len(FAIL)}\n  warnings     : {len(WARN)}")
    for x in FAIL:
        print(f"   FAIL {x}")
    for x in WARN:
        print(f"   WARN {x}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
