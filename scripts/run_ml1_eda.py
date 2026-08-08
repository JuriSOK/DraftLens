"""ML-1 — exploratory data analysis, leakage and stability audit.

Characterises the corrected ML-0.1 development population before any feature
engineering. Trains nothing, fits nothing, imputes nothing, scales nothing.

HOLDOUT GUARD: all target-aware analysis is restricted to 2014-2025 by
`dev_only()`, which refuses any frame containing draft_year 2026. The 2026
target file is never opened by this script.

  ./.venv/bin/python scripts/run_ml1_eda.py

Outputs (git-ignored) -> data/interim/ml1/
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_model_dataset import EXPECTED, MBB, OUT as ML0  # noqa: E402
from positions import UNKNOWN, parse_five_position, to_position_3  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "data" / "interim" / "ml1"
DEV, ROB, HOLD = "2014_2025", "2011_2013", "2026"

PRIMITIVES = [
    "games_played", "games_started", "minutes", "points",
    "field_goals_made", "field_goals_attempted",
    "two_points_made", "two_points_attempted",
    "three_points_made", "three_points_attempted",
    "free_throws_made", "free_throws_attempted",
    "offensive_rebounds", "defensive_rebounds", "total_rebounds",
    "assists", "turnovers", "steals", "blocks", "personal_fouls",
    "jump_shot_attempts", "jump_shot_makes", "layup_attempts", "layup_makes",
    "dunk_attempts", "dunk_makes", "tip_attempts", "tip_makes",
    "three_point_shot_attempts", "three_point_shot_makes",
    "assisted_made_field_goals", "unassisted_made_field_goals",
    "assisted_layup_makes", "unassisted_layup_makes",
    "assisted_dunk_makes", "unassisted_dunk_makes",
    "shot_records", "fg_attempts_shotfile", "fg_makes_shotfile",
    "height", "weight",
]
NOTES = []


def log(m=""):
    print(m, flush=True)


def rule(t):
    log(f"\n{'=' * 78}\n{t}\n{'=' * 78}")


def note(sev, msg):
    NOTES.append({"severity": sev, "note": msg})
    log(f"  [{sev}] {msg}")


def load(label):
    f = pd.read_parquet(ML0 / f"features_{label}.parquet")
    # position_3 comes from hoopR — the only leakage-safe source (DEC-065).
    f["position_3"] = f.hoopr_position.map(to_position_3)
    f["position_5"] = UNKNOWN     # no leakage-safe five-position source exists
    # match_method / the raw population labels live in the crosswalk, not the
    # feature file (DEC-065). They are joined here for AUDIT purposes only and
    # must never become model features.
    cw = pd.read_parquet(ML0 / "identity_crosswalk.parquet")[
        ["canonical_prospect_id", "match_method", "match_confidence",
         "position_from_population", "class_from_population"]]
    return f.merge(cw, on="canonical_prospect_id", how="left")


def load_target(label):
    if label == HOLD:
        raise AssertionError("ML-1 must not load the 2026 target file")
    return pd.read_parquet(ML0 / f"targets_{label}.parquet")


def dev_only(df):
    """Structural guard: target-aware analysis may never touch the holdout."""
    if 2026 in set(df.draft_year.unique()):
        raise AssertionError("HOLDOUT GUARD: 2026 reached a target-aware path")
    return df


def merged(label):
    f, t = load(label), load_target(label)
    m = f.merge(t[["canonical_prospect_id", "drafted", "pick"]],
                on="canonical_prospect_id", how="inner")
    return dev_only(m)


# ------------------------------------------------------------ 3. profile
def year_quality(m, label):
    rows = []
    for y, g in m.groupby("draft_year"):
        rows.append(dict(
            draft_year=int(y), prospects=len(g), drafted=int(g.drafted.sum()),
            undrafted=int((g.drafted == 0).sum()),
            drafted_pct=round(100 * g.drafted.mean(), 1),
            matched=int(g.hoopr_athlete_id.notna().sum()),
            unmatched=int((g.match_method == "UNMATCHED").sum()),
            ambiguous=int((g.match_method == "AMBIGUOUS").sum()),
            box_coverage_pct=round(100 * g.games_played.notna().mean(), 1),
            shots_coverage_pct=round(100 * g.shot_records.notna().mean(), 1),
            median_games=float(g.games_played.median()),
            median_minutes=round(float(g.minutes.median()), 1),
            pos5_pct=round(100 * (g.position_5 != UNKNOWN).mean(), 1),
            pos3_pct=round(100 * (g.position_3 != UNKNOWN).mean(), 1),
            height_pct=round(100 * g.height.notna().mean(), 1),
            weight_pct=round(100 * g.weight.notna().mean(), 1)))
    df = pd.DataFrame(rows)
    df.to_csv(OUT / f"year_quality_{label}.csv", index=False)
    return df


# ---------------------------------------------------- 8. distributions
def primitive_summary(m, label):
    rows = []
    for c in PRIMITIVES:
        if c not in m.columns:
            continue
        s = pd.to_numeric(m[c], errors="coerce")
        v = s.dropna()
        rows.append(dict(
            field=c, non_null=int(v.size),
            missing_pct=round(100 * s.isna().mean(), 2),
            min=float(v.min()) if v.size else np.nan,
            p01=float(v.quantile(.01)) if v.size else np.nan,
            p05=float(v.quantile(.05)) if v.size else np.nan,
            median=float(v.median()) if v.size else np.nan,
            p95=float(v.quantile(.95)) if v.size else np.nan,
            p99=float(v.quantile(.99)) if v.size else np.nan,
            max=float(v.max()) if v.size else np.nan,
            zeros=int((v == 0).sum()),
            zero_pct=round(100 * (v == 0).mean(), 2) if v.size else np.nan))
    df = pd.DataFrame(rows)
    df.to_csv(OUT / f"primitive_summary_{label}.csv", index=False)
    return df


# ------------------------------------------------------ 9. anomalies
def anomaly_audit(m):
    a = {}
    pairs = [("field_goals_made", "field_goals_attempted"),
             ("two_points_made", "two_points_attempted"),
             ("three_points_made", "three_points_attempted"),
             ("free_throws_made", "free_throws_attempted"),
             ("jump_shot_makes", "jump_shot_attempts"),
             ("layup_makes", "layup_attempts"),
             ("dunk_makes", "dunk_attempts"),
             ("tip_makes", "tip_attempts"),
             ("three_point_shot_makes", "three_point_shot_attempts")]
    for made, att in pairs:
        d = m.dropna(subset=[made, att])
        a[f"{made}>{att}"] = int((d[made] > d[att]).sum())
    for c in PRIMITIVES:
        if c in m:
            v = pd.to_numeric(m[c], errors="coerce").dropna()
            n = int((v < 0).sum())
            if n:
                a[f"negative_{c}"] = n
    d = m.dropna(subset=["games_played"])
    a["games_started>games_played"] = int((d.games_started > d.games_played).sum())
    a["n_teams<1"] = int((m.n_teams.dropna() < 1).sum())
    a["duplicate_prospect_year"] = int(
        m.duplicated(subset=["draft_year", "normalized_name"]).sum())
    d2 = m.dropna(subset=["assisted_made_field_goals", "fg_makes_shotfile"])
    a["assisted_makes>fg_makes_shotfile"] = int(
        (d2.assisted_made_field_goals > d2.fg_makes_shotfile).sum())
    d3 = m.dropna(subset=["fg_attempts_shotfile", "field_goals_attempted"])
    a["shotfile_FGA_exceeds_box_FGA_by_>20pct"] = int(
        (d3.fg_attempts_shotfile > 1.2 * d3.field_goals_attempted).sum())
    return a


# -------------------------------------------- 10. opportunity effect
def opportunity(m):
    d = m.dropna(subset=["minutes", "games_played"])
    rows = []
    for c in ["points", "total_rebounds", "assists", "steals", "blocks",
              "field_goals_attempted", "three_points_attempted",
              "free_throws_attempted", "turnovers"]:
        v = d.dropna(subset=[c])
        rows.append(dict(total=c,
                         corr_with_minutes=round(float(v[c].corr(v.minutes)), 3),
                         corr_with_games=round(float(v[c].corr(v.games_played)), 3)))
    return pd.DataFrame(rows)


# ----------------------------------------------------- 11/12. drift
def season_drift(m):
    fields = ["minutes", "points", "three_points_attempted",
              "free_throws_attempted", "assists", "total_rebounds", "steals",
              "blocks", "height", "weight", "games_played",
              "jump_shot_attempts", "layup_attempts", "dunk_attempts"]
    med = m.groupby("draft_year")[fields].median().round(2)
    med.to_csv(OUT / "season_drift_medians.csv")
    drift = []
    for c in fields:
        s = med[c].dropna()
        if len(s) < 3:
            continue
        rel = (s.max() - s.min()) / s.median() if s.median() else np.nan
        drift.append(dict(field=c, min_year_median=float(s.min()),
                          max_year_median=float(s.max()),
                          median_of_years=float(s.median()),
                          relative_range=round(float(rel), 3)))
    return med, pd.DataFrame(drift).sort_values("relative_range", ascending=False)


def covid_blocks(m):
    blocks = {"2019-2020": (2019, 2020), "2021-2022": (2021, 2022),
              "2023-2025": (2023, 2025)}
    rows = []
    for name, (lo, hi) in blocks.items():
        g = m[m.draft_year.between(lo, hi)]
        rows.append(dict(block=name, prospects=len(g),
                         drafted_pct=round(100 * g.drafted.mean(), 1),
                         median_games=float(g.games_played.median()),
                         median_minutes=round(float(g.minutes.median()), 1),
                         median_points=float(g.points.median()),
                         median_fga=float(g.field_goals_attempted.median()),
                         shots_coverage_pct=round(
                             100 * g.shot_records.notna().mean(), 1)))
    return pd.DataFrame(rows)


# ------------------------------------------- 13/14. missingness
def missingness(m, label):
    rows = []
    for c in PRIMITIVES + ["hoopr_position", "experience_years"]:
        if c not in m.columns:
            continue
        rows.append(dict(field=c, missing=int(m[c].isna().sum()),
                         missing_pct=round(100 * m[c].isna().mean(), 2)))
    df = pd.DataFrame(rows)
    df.to_csv(OUT / f"missingness_{label}.csv", index=False)
    return df


def missingness_by_target(m):
    rows = []
    for c in PRIMITIVES + ["hoopr_position", "experience_years"]:
        if c not in m.columns:
            continue
        d = 100 * m.loc[m.drafted == 1, c].notna().mean()
        u = 100 * m.loc[m.drafted == 0, c].notna().mean()
        rows.append(dict(field=c, drafted_coverage_pct=round(float(d), 2),
                         undrafted_coverage_pct=round(float(u), 2),
                         gap_pp=round(float(d - u), 2)))
    df = pd.DataFrame(rows).sort_values("gap_pp", key=abs, ascending=False)
    df.to_csv(OUT / "missingness_by_target.csv", index=False)
    return df


def missingness_patterns(m):
    pat = pd.DataFrame({
        "unmatched": m.hoopr_athlete_id.isna(),
        "box_absent": m.games_played.isna(),
        "shots_absent": m.shot_records.isna(),
        "height_absent": m.height.isna(),
        "weight_absent": m.weight.isna()})
    grp = (pat.groupby(list(pat.columns)).size()
              .reset_index(name="prospects").sort_values("prospects",
                                                         ascending=False))
    grp.to_csv(OUT / "missingness_patterns.csv", index=False)
    return grp


# -------------------------------------------- 15/16/17. shot audits
def shot_coverage(m):
    rows = []
    for y, g in m.groupby("draft_year"):
        w = g.dropna(subset=["shot_records", "field_goals_attempted"])
        ratio = (w.fg_attempts_shotfile / w.field_goals_attempted.replace(0, np.nan))
        rows.append(dict(draft_year=int(y),
                         prospects=len(g),
                         with_shots=int(g.shot_records.notna().sum()),
                         with_shots_pct=round(100 * g.shot_records.notna().mean(), 1),
                         median_shot_records=float(g.shot_records.median()),
                         median_shotfile_FGA_over_box_FGA=round(
                             float(ratio.median()), 3) if len(ratio.dropna()) else np.nan))
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "shot_coverage.csv", index=False)
    return df


def shot_type_schema(years):
    """type_text vocabulary per season, straight from the raw shots files."""
    rows = []
    for y in years:
        p = MBB / "shots" / f"shots_{y}.parquet"
        if not p.exists():
            continue
        s = pd.read_parquet(p, columns=["type_text", "scoring_play",
                                        "athlete_id_2", "score_value"])
        vc = s.type_text.value_counts()
        for k, v in vc.items():
            rows.append(dict(season=y, type_text=k, count=int(v),
                             pct=round(100 * v / len(s), 3)))
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "shot_type_schema.csv", index=False)
    return df


def assist_linkage(years):
    rows = []
    for y in years:
        p = MBB / "shots" / f"shots_{y}.parquet"
        if not p.exists():
            continue
        s = pd.read_parquet(p, columns=["type_text", "scoring_play",
                                        "athlete_id_2"])
        fg = s[~s.type_text.astype(str).str.contains("FreeThrow", na=False)]
        made = fg[fg.scoring_play.fillna(False).astype(bool)]
        rows.append(dict(season=y, fg_attempts=len(fg), fg_makes=len(made),
                         made_with_assister=int(made.athlete_id_2.notna().sum()),
                         assisted_rate_pct=round(
                             100 * made.athlete_id_2.notna().mean(), 2)))
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "assist_linkage.csv", index=False)
    return df


# -------------------------------------- 18/19. target-association audit
def target_association(m):
    """Descriptive drafted-vs-undrafted comparison. NOT feature selection."""
    rows = []
    for c in PRIMITIVES:
        if c not in m.columns:
            continue
        d = pd.to_numeric(m.loc[m.drafted == 1, c], errors="coerce").dropna()
        u = pd.to_numeric(m.loc[m.drafted == 0, c], errors="coerce").dropna()
        if len(d) < 20 or len(u) < 20:
            continue
        pooled = np.sqrt((d.var(ddof=1) + u.var(ddof=1)) / 2)
        smd = (d.mean() - u.mean()) / pooled if pooled else np.nan
        # rank-biserial via Mann-Whitney U, computed from ranks (no scipy)
        allv = pd.concat([d, u])
        r = allv.rank()
        n1, n2 = len(d), len(u)
        u1 = r.iloc[:n1].sum() - n1 * (n1 + 1) / 2
        auc = u1 / (n1 * n2)
        rows.append(dict(field=c, median_drafted=float(d.median()),
                         median_undrafted=float(u.median()),
                         std_mean_diff=round(float(smd), 3),
                         rank_auc=round(float(auc), 3)))
    df = pd.DataFrame(rows)
    df["separation"] = (df.rank_auc - 0.5).abs().round(3)
    df = df.sort_values("separation", ascending=False)
    df.to_csv(OUT / "target_association.csv", index=False)
    return df


def pick_association(m):
    d = dev_only(m[m.drafted == 1].dropna(subset=["pick"]))
    rows = []
    for c in PRIMITIVES:
        if c not in d.columns:
            continue
        v = d.dropna(subset=[c])
        if len(v) < 30:
            continue
        rows.append(dict(field=c, n=len(v),
                         spearman_with_pick=round(
                             float(v[c].rank().corr(
                                 v["pick"].astype(float).rank())), 3)))
    df = pd.DataFrame(rows)
    df["abs_rho"] = df.spearman_with_pick.abs()
    df = df.sort_values("abs_rho", ascending=False)
    df.to_csv(OUT / "pick_association.csv", index=False)
    return df


# --------------------------------------------- 20/21. unresolved audit
def unresolved(m):
    u = m[m.match_method.isin(["UNMATCHED", "AMBIGUOUS"])].copy()
    cols = ["draft_year", "player_name", "college", "match_method", "drafted"]
    u[cols].to_csv(OUT / "unresolved_prospects.csv", index=False)
    return u[cols]


# --------------------------------------------------- 23. holdout check
def holdout_schema_check(dev_cols):
    """Non-target-aware only: schema, coverage, position mapping."""
    h = load(HOLD)
    same = set(h.columns) == set(dev_cols)
    out = dict(rows=len(h), schema_matches_development=bool(same),
               matched_pct=round(100 * h.hoopr_athlete_id.notna().mean(), 1),
               box_coverage_pct=round(100 * h.games_played.notna().mean(), 1),
               shots_coverage_pct=round(100 * h.shot_records.notna().mean(), 1),
               position_5_pct=round(100 * (h.position_5 != UNKNOWN).mean(), 1),
               position_3_pct=round(100 * (h.position_3 != UNKNOWN).mean(), 1),
               height_pct=round(100 * h.height.notna().mean(), 1),
               weight_pct=round(100 * h.weight.notna().mean(), 1),
               leakage_columns=[c for c in h.columns
                                if c.lower() in ("drafted", "pick", "round",
                                                 "date_of_birth", "age")])
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rep = {}

    rule("1. POPULATION CONFIRMATION")
    dev = merged(DEV)
    rob = merged(ROB)
    for lab, m in ((DEV, dev), (ROB, rob)):
        exp = EXPECTED[lab]
        n, nd, nu = len(m), int(m.drafted.sum()), int((m.drafted == 0).sum())
        ok = (n, nd, nu) == exp
        log(f"  {lab}: {n} rows / {nd} drafted / {nu} undrafted "
            f"-> {'MATCHES GATE' if ok else 'MISMATCH ' + str(exp)}")
        if not ok:
            note("BLOCKER", f"{lab} population does not match gate {exp}")
        rep[f"population_{lab}"] = dict(total=n, drafted=nd, undrafted=nu)

    rule("2. CLASS BALANCE BY YEAR (development)")
    yq = year_quality(dev, DEV)
    log(yq[["draft_year", "prospects", "drafted", "undrafted", "drafted_pct",
            "matched", "median_games", "median_minutes", "pos5_pct",
            "pos3_pct"]].to_string(index=False))
    bal = yq.drafted_pct
    rep["class_balance"] = dict(min=float(bal.min()), max=float(bal.max()),
                                median=float(bal.median()),
                                spread_pp=round(float(bal.max() - bal.min()), 1))
    log(f"\n  drafted% min={bal.min()} max={bal.max()} median={bal.median()} "
        f"spread={bal.max()-bal.min():.1f}pp")
    weak = yq[(yq.undrafted < 5) | (yq.drafted < 5)]
    for _, r in weak.iterrows():
        note("HIGH", f"{int(r.draft_year)} has only {int(r.undrafted)} undrafted "
                     f"of {int(r.prospects)} — Stage A metrics unstable there")
    rep["weak_years"] = [int(y) for y in weak.draft_year]

    rule("3. POSITION AUDIT")
    raw = dev.hoopr_position.fillna("<missing>").value_counts()
    log("  hoopR position labels (leakage-safe source):")
    log("   " + "  ".join(f"{k}={v}" for k, v in raw.items()))
    p5 = 100 * (dev.position_5 != UNKNOWN).mean()
    p3 = 100 * (dev.position_3 != UNKNOWN).mean()
    log(f"\n  canonical position_5 coverage: {p5:.1f}%")
    log(f"  canonical position_3 coverage: {p3:.1f}%")
    pos = pd.DataFrame({"raw_label": raw.index, "count": raw.values})
    pos.to_csv(OUT / "position_audit.csv", index=False)
    rep["position"] = dict(position_5_coverage_pct=round(float(p5), 1),
                           position_3_coverage_pct=round(float(p3), 1),
                           hoopr_labels=dev.hoopr_position.value_counts()
                           .head(10).to_dict())
    note("BLOCKER", "no leakage-safe PG/SG/SF/PF/C source exists: the only "
                    "fine-grained label (position_from_population) is "
                    "outcome-contaminated (100% vs 7.7% resolvable), so the "
                    "DEC-009 five-position scheme cannot be populated")
    log("\n  drafted rate by canonical position_3 (descriptive only):")
    pt = (dev.groupby("position_3")
             .agg(prospects=("drafted", "size"), drafted=("drafted", "sum")))
    pt["drafted_pct"] = (100 * pt.drafted / pt.prospects).round(1)
    log(pt.to_string())
    pt.to_csv(OUT / "position_by_target.csv")

    rule("4. PRIMITIVE DISTRIBUTIONS")
    ps = primitive_summary(dev, DEV)
    log(ps[["field", "missing_pct", "min", "median", "p99", "max",
            "zero_pct"]].to_string(index=False))

    rule("5. ANOMALY AUDIT")
    an = anomaly_audit(dev)
    bad = {k: v for k, v in an.items() if v}
    log(f"  checks run: {len(an)} | non-zero findings: {len(bad)}")
    for k, v in bad.items():
        note("MEDIUM" if "exceeds" in k else "HIGH", f"{k}: {v} rows")
    if not bad:
        log("  no impossible values found")
    rep["anomalies"] = an

    rule("6. OPPORTUNITY EFFECT")
    op = opportunity(dev)
    log(op.to_string(index=False))
    op.to_csv(OUT / "opportunity_correlations.csv", index=False)
    rep["opportunity_min_corr_minutes"] = float(op.corr_with_minutes.min())

    rule("7. SEASON DRIFT")
    med, drift = season_drift(dev)
    log(drift.to_string(index=False))
    drift.to_csv(OUT / "season_drift_summary.csv", index=False)
    rep["drift_top"] = drift.head(5).to_dict("records")

    rule("8. COVID BLOCKS")
    cb = covid_blocks(dev)
    log(cb.to_string(index=False))
    cb.to_csv(OUT / "covid_blocks.csv", index=False)
    rep["covid"] = cb.to_dict("records")

    rule("9. MISSINGNESS")
    miss = missingness(dev, DEV)
    nz = miss[miss.missing > 0]
    log(nz.to_string(index=False))
    mbt = missingness_by_target(dev)
    log("\n  largest drafted-vs-undrafted coverage gaps:")
    log(mbt.head(8).to_string(index=False))
    rep["max_coverage_gap_pp"] = float(mbt.gap_pp.abs().max())
    if mbt.gap_pp.abs().max() > 10:
        note("HIGH", f"coverage gap {mbt.gap_pp.abs().max():.1f}pp — "
                     f"target-linked missingness")

    log("\n  missingness co-occurrence patterns:")
    pats = missingness_patterns(dev)
    log(pats.head(8).to_string(index=False))

    rule("10. SHOT COVERAGE / SCHEMA / ASSIST LINKAGE")
    sc = shot_coverage(dev)
    log(sc.to_string(index=False))
    years = sorted(dev.draft_year.unique())
    sts = shot_type_schema(years)
    piv = sts.pivot_table(index="type_text", columns="season", values="pct")
    log("\n  type_text share by season (%):")
    log(piv.round(2).to_string())
    first = set(sts[sts.season == years[0]].type_text)
    last = set(sts[sts.season == years[-1]].type_text)
    stable = first == last
    rep["shot_type_vocab_stable"] = bool(stable)
    rep["shot_type_dropped"] = sorted(first - last)
    rep["shot_type_added"] = sorted(last - first)
    if not stable:
        note("BLOCKER",
             f"shot type_text vocabulary changes across the window: "
             f"dropped {sorted(first - last)}, added {sorted(last - first)}. "
             f"'Three Point Jump Shot' was a separate category through 2020 and "
             f"is folded into 'JumpShot' from 2021, so jump_shot_* counts are "
             f"NOT comparable across that boundary")
    al = assist_linkage(years)
    log("\n  assist linkage by season:")
    log(al.to_string(index=False))
    rep["assist_rate_range"] = [float(al.assisted_rate_pct.min()),
                                float(al.assisted_rate_pct.max())]

    rule("11. TARGET-ASSOCIATION SANITY (development only)")
    ta = target_association(dev)
    log(ta.head(12).to_string(index=False))
    top = ta.iloc[0]
    log(f"\n  strongest separation: {top.field} rank_auc={top.rank_auc}")
    if ta.separation.max() > 0.45:
        note("BLOCKER", f"{top.field} separates the target almost perfectly "
                        f"(rank_auc={top.rank_auc}) — investigate provenance")
    rep["max_rank_auc"] = float(ta.rank_auc.max())

    log("\n  pick association among drafted (leakage check):")
    pa = pick_association(dev)
    log(pa.head(8).to_string(index=False))
    if pa.abs_rho.max() > 0.9:
        note("BLOCKER", f"{pa.iloc[0].field} nearly determines pick "
                        f"(rho={pa.iloc[0].spearman_with_pick})")
    rep["max_pick_rho"] = float(pa.abs_rho.max())

    rule("12. UNRESOLVED PROSPECTS")
    un = unresolved(dev)
    log(un.to_string(index=False))
    nd, nu = int(un.drafted.sum()), int((un.drafted == 0).sum())
    log(f"\n  unresolved: {len(un)} ({nd} drafted / {nu} undrafted)")
    base = dev.drafted.mean()
    rep["unresolved"] = dict(total=len(un), drafted=nd, undrafted=nu,
                             population_drafted_pct=round(100 * base, 1))
    if len(un) and (nd == 0 or nu == 0):
        note("MEDIUM", "all unresolved prospects share one class — dropping "
                       "them would bias the sample")

    rule("13. ROBUSTNESS PERIOD 2011-2013")
    ry = year_quality(rob, ROB)
    log(ry[["draft_year", "prospects", "drafted", "undrafted", "drafted_pct",
            "matched", "box_coverage_pct", "shots_coverage_pct", "pos5_pct",
            "pos3_pct", "height_pct"]].to_string(index=False))
    rep["robustness"] = dict(
        rows=len(rob), drafted_pct=round(100 * rob.drafted.mean(), 1),
        match_pct=round(100 * rob.hoopr_athlete_id.notna().mean(), 1),
        pos5_pct=round(100 * (rob.position_5 != UNKNOWN).mean(), 1),
        box_pct=round(100 * rob.games_played.notna().mean(), 1))

    rule("14. HOLDOUT SCHEMA CHECK (no target-aware analysis)")
    hs = holdout_schema_check(load(DEV).columns)
    for k, v in hs.items():
        log(f"  {k}: {v}")
    rep["holdout_2026"] = hs
    if hs["leakage_columns"]:
        note("BLOCKER", f"2026 features contain {hs['leakage_columns']}")

    rep["notes"] = NOTES
    (OUT / "ml1_summary.json").write_text(json.dumps(rep, indent=2, default=str))

    rule("ML-1 RESULT")
    blockers = [n for n in NOTES if n["severity"] == "BLOCKER"]
    log(f"  notes: {len(NOTES)}  blockers: {len(blockers)}")
    for n in NOTES:
        log(f"   [{n['severity']}] {n['note']}")
    log(f"\n  outputs -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
