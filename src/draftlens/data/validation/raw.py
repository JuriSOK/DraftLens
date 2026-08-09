"""Validate acquired raw data and emit a data-quality profile.

Checks structure, coverage, parseability, manifest integrity (files unmodified
since acquisition), the feature/target firewall, and cross-season athlete_id
stability. Computes no model features.

The manifest check is the one that matters most: raw data is immutable
(CLAUDE.md rule 12), and a changed checksum means the analytical record no
longer rests on what was actually downloaded.
"""

import csv

import pandas as pd

from draftlens.data.acquisition.manifest import load_manifest, sha256_file
from draftlens.paths import MBB, RAW, rel

YEARS = list(range(2011, 2027))
NBA = RAW / "hoopr_nba"
POP, TGT, WD = RAW / "draft_population", RAW / "draft_targets", RAW / "wikidata"

FAIL, WARN = [], []


def rule(t):
    print(f"\n{'=' * 78}\n{t}\n{'=' * 78}")


def check(cond, msg, hard=True):
    if cond:
        return True
    (FAIL if hard else WARN).append(msg)
    print(f"  {'FAIL' if hard else 'WARN'}  {msg}")
    return False


def ids(series):
    """Dtype-safe athlete_id -> Int64 (player_core is int64, others float64)."""
    return pd.to_numeric(series, errors="coerce").dropna().astype("int64")


# ============================================================ manifest
def validate_manifest(skip_checksums):
    rule("MANIFEST INTEGRITY")
    man = load_manifest()
    check(len(man) > 0, "source_manifest.csv is empty")
    print(f"  manifest records: {len(man)}")
    missing, modified = 0, 0
    for lp, rec in man.items():
        p = ROOT / lp
        if not p.exists():
            missing += 1
            check(False, f"manifest file missing on disk: {lp}")
            continue
        if int(rec["file_size_bytes"]) != p.stat().st_size:
            modified += 1
            check(False, f"size changed since acquisition: {lp}")
        elif not skip_checksums and rec["sha256"] and sha256_file(p) != rec["sha256"]:
            modified += 1
            check(False, f"sha256 changed since acquisition (raw not immutable): {lp}")
    print(f"  files present: {len(man)-missing}/{len(man)} | modified: {modified}")
    return man


# ============================================================ hoopR MBB
def validate_mbb():
    rule("HOOPR MBB — coverage, schema, quality profile")
    rows = []
    for y in YEARS:
        pc = MBB / "player_core" / f"player_core_{y}.parquet"
        pb = MBB / "player_box" / f"player_box_{y}.parquet"
        sh = MBB / "shots" / f"shots_{y}.parquet"
        if not check(pc.exists() and pb.exists() and sh.exists(),
                     f"MBB {y}: missing one of player_core/player_box/shots"):
            continue
        core = pd.read_parquet(pc)
        box = pd.read_parquet(pb)
        shots = pd.read_parquet(sh)

        check(len(core) > 0, f"MBB {y}: player_core empty")
        check(len(box) > 0, f"MBB {y}: player_box empty")
        check(len(shots) > 0, f"MBB {y}: shots empty", hard=False)

        need_core = {"athlete_id", "display_name", "position_abbreviation",
                     "height", "weight", "date_of_birth"}
        need_box = {"athlete_id", "team_id", "game_id", "minutes", "points",
                    "field_goals_made", "field_goals_attempted",
                    "three_point_field_goals_made", "three_point_field_goals_attempted",
                    "free_throws_made", "free_throws_attempted", "offensive_rebounds",
                    "defensive_rebounds", "rebounds", "assists", "steals", "blocks",
                    "turnovers", "fouls", "starter"}
        need_shots = {"athlete_id_1", "type_text", "scoring_play", "score_value"}
        check(need_core <= set(core.columns),
              f"MBB {y}: player_core missing {sorted(need_core - set(core.columns))}")
        check(need_box <= set(box.columns),
              f"MBB {y}: player_box missing {sorted(need_box - set(box.columns))}")
        check(need_shots <= set(shots.columns),
              f"MBB {y}: shots missing {sorted(need_shots - set(shots.columns))}")

        cid, bid = ids(core.athlete_id), ids(box.athlete_id)
        check(len(cid) == len(core), f"MBB {y}: player_core athlete_id not numeric-safe")
        cover = len(set(bid) & set(cid)) / max(1, len(set(bid)))
        check(cover > 0.95, f"MBB {y}: box->core id coverage only {100*cover:.1f}%",
              hard=False)

        def fill(c):
            if c not in core.columns:
                return float("nan")
            s = core[c]
            nn = s.notna()
            if s.dtype == object:
                nn = nn & (s.astype(str).str.strip() != "")
            return 100 * nn.mean()

        rows.append(dict(season=y, core_rows=len(core), unique_ids=core.athlete_id.nunique(),
                         box_rows=len(box), shot_rows=len(shots),
                         teams=int(box.team_id.nunique()),
                         pos_fill=round(fill("position_abbreviation"), 1),
                         height_fill=round(fill("height"), 1),
                         weight_fill=round(fill("weight"), 1),
                         dob_fill=round(fill("date_of_birth"), 2),
                         box_core_cov=round(100 * cover, 2)))
    df = pd.DataFrame(rows)
    print("\n  season  core_rows  uniq_ids   box_rows    shot_rows  teams  pos%  hgt%  "
          "wgt%   dob%  box→core%")
    for _, r in df.iterrows():
        print(f"  {r.season:<7}{r.core_rows:>9,}{r.unique_ids:>10,}{r.box_rows:>11,}"
              f"{r.shot_rows:>13,}{r.teams:>7}{r.pos_fill:>6.1f}{r.height_fill:>6.1f}"
              f"{r.weight_fill:>6.1f}{r.dob_fill:>7.2f}{r.box_core_cov:>10.2f}")
    print(f"\n  TOTALS  core={df.core_rows.sum():,}  box={df.box_rows.sum():,}  "
          f"shots={df.shot_rows.sum():,}")
    low = df[df.shot_rows < df.shot_rows.median() * 0.6]
    if len(low):
        print(f"  NOTE: unusually low shot volume in {list(low.season)}")
    return df


# ============================================================ hoopR NBA
def validate_nba():
    rule("HOOPR NBA — player_season_stats coverage")
    rows = []
    for y in YEARS:
        p = NBA / "player_season_stats" / f"player_season_stats_{y}.parquet"
        if not check(p.exists(), f"NBA {y}: player_season_stats missing"):
            continue
        d = pd.read_parquet(p)
        check(len(d) > 0, f"NBA {y}: empty")
        need = {"athlete_id", "athlete_display_name", "athlete_position_abbreviation",
                "season", "category", "stat_name", "value"}
        check(need <= set(d.columns), f"NBA {y}: missing {sorted(need - set(d.columns))}")
        names = set(d.stat_name.unique())
        core_stats = {"points", "assists", "totalRebounds", "steals", "blocks",
                      "turnovers", "gamesPlayed", "avgMinutes"}
        check(core_stats <= names,
              f"NBA {y}: missing stat dimensions {sorted(core_stats - names)}", hard=False)
        rows.append(dict(season=y, rows=len(d), players=d.athlete_id.nunique(),
                         stats=d.stat_name.nunique()))
    df = pd.DataFrame(rows)
    print("\n  season      rows  players  stat_names")
    for _, r in df.iterrows():
        print(f"  {r.season:<8}{r.rows:>8,}{r.players:>9,}{r.stats:>12}")
    print(f"\n  TOTALS rows={df.rows.sum():,}  player-seasons={df.players.sum():,}")
    return df


# =================================================== population / targets
def validate_population():
    rule("DRAFT POPULATION & TARGETS — coverage, firewall, class balance")
    rows = []
    for y in YEARS:
        pp, tp = POP / f"draft_population_{y}.csv", TGT / f"draft_targets_{y}.csv"
        if not check(pp.exists() and tp.exists(), f"draft {y}: population/target missing"):
            continue
        pop = pd.read_csv(pp)
        tgt = pd.read_csv(tp)

        # FIREWALL: no outcome column may appear in the population file
        leaked = {"pick", "round", "drafting_team", "drafted"} & set(pop.columns)
        check(not leaked, f"FIREWALL BREACH {y}: outcome columns in population: {leaked}")
        check("pick" in tgt.columns, f"draft {y}: targets missing pick column")

        check(pop.normalized_name.duplicated().sum() == 0,
              f"draft {y}: duplicate normalized_name in population")
        check(set(pop.normalized_name) == set(tgt.normalized_name),
              f"draft {y}: population/target key mismatch")
        check(len(pop) > 0 and (pop.early_entrant.astype(str).isin(
            ["True", "False"]).all()), f"draft {y}: bad early_entrant values")

        drafted = int(tgt.drafted.astype(str).eq("True").sum())
        picks = tgt[tgt.drafted.astype(str).eq("True")]["pick"]
        check(picks.notna().all(), f"draft {y}: drafted rows with null pick")
        check(picks.between(1, 60).all(), f"draft {y}: pick outside 1-60", hard=False)
        undrafted_ee = pop[~pop.early_entrant.astype(str).eq("True")]
        rows.append(dict(draft_year=y, population=len(pop), drafted=drafted,
                         undrafted=len(pop) - drafted,
                         drafted_pct=round(100 * drafted / len(pop), 1),
                         early_entrants=int(pop.early_entrant.astype(str)
                                            .eq("True").sum()),
                         non_ee=len(undrafted_ee)))
    df = pd.DataFrame(rows)
    print("\n  year   population  drafted  undrafted  drafted%  early_ent  non_EE")
    for _, r in df.iterrows():
        print(f"  {r.draft_year:<7}{r.population:>10}{r.drafted:>9}{r.undrafted:>11}"
              f"{r.drafted_pct:>9.1f}{r.early_entrants:>11}{r.non_ee:>8}")
    tot = df.population.sum()
    print(f"\n  TOTAL population {tot:,} | drafted {df.drafted.sum():,} | "
          f"undrafted {df.undrafted.sum():,} "
          f"({100*df.undrafted.sum()/tot:.1f}%)")
    imb = df[(df.drafted_pct > 90) | (df.undrafted < 5)]
    if len(imb):
        print(f"  IMBALANCE WATCH: {list(imb.draft_year)} "
              f"(undrafted class < 5 or drafted% > 90)")
    return df


# ========================================== cross-season ID stability
def id_stability():
    rule("CROSS-SEASON athlete_id STABILITY (hoopR MBB player_core)")
    frames = []
    for y in YEARS:
        p = MBB / "player_core" / f"player_core_{y}.parquet"
        if not p.exists():
            continue
        d = pd.read_parquet(p)[["athlete_id", "display_name"]].copy()
        d["athlete_id"] = pd.to_numeric(d.athlete_id, errors="coerce").astype("Int64")
        d["season"] = y
        d["nname"] = d.display_name.map(normalize_name)
        frames.append(d)
    allp = pd.concat(frames, ignore_index=True).dropna(subset=["athlete_id"])

    per_id = allp.groupby("athlete_id").agg(seasons=("season", "nunique"),
                                            names=("nname", "nunique"))
    multi = per_id[per_id.seasons > 1]
    print(f"  distinct athlete_ids (2011-2026) : {len(per_id):,}")
    print(f"  appearing in >1 season           : {len(multi):,} "
          f"({100*len(multi)/len(per_id):.1f}%)")
    stable = int((multi.names == 1).sum())
    print(f"  ...of which one normalized name  : {stable:,} "
          f"({100*stable/max(1,len(multi)):.2f}%)  <- ID STABILITY")
    print(f"  ...with >1 name (rename/collision): {len(multi)-stable:,}")

    per_name = allp.groupby("nname").agg(ids=("athlete_id", "nunique"),
                                         seasons=("season", "nunique"))
    multi_name = per_name[per_name.seasons > 1]
    split = int((multi_name.ids > 1).sum())
    print(f"\n  normalized names in >1 season    : {len(multi_name):,}")
    print(f"  ...mapping to >1 athlete_id      : {split:,} "
          f"({100*split/max(1,len(multi_name)):.1f}%)")
    print("     (expected: common names shared by different real players,")
    print("      plus any genuine ID changes — not separable without more work)")
    check(100 * stable / max(1, len(multi)) > 95,
          f"athlete_id stability below 95% ({100*stable/max(1,len(multi)):.1f}%)",
          hard=False)
    return dict(distinct=len(per_id), multi=len(multi), stable=stable,
                names_multi=len(multi_name), names_split=split)


# ============================================================== 2026
def validate_2026(mbb_df):
    rule("2026 READINESS")
    pop = pd.read_csv(POP / "draft_population_2026.csv")
    tgt = pd.read_csv(TGT / "draft_targets_2026.csv")
    wd = pd.read_csv(WD / "wikidata_dob_2026.csv")
    print(f"  reconstructed 2026 population : {len(pop)}")
    print(f"  drafted (target file)         : {int(tgt.drafted.astype(str).eq('True').sum())}")
    check(len(wd) == len(pop), "2026: Wikidata rows != population rows")
    check("pick" not in pop.columns and "drafted" not in pop.columns,
          "2026: firewall breach in population file")
    check("date_of_birth" not in pop.columns, "2026: DOB leaked into population file")

    core = pd.read_parquet(MBB / "player_core" / "player_core_2026.parquet")
    box = pd.read_parquet(MBB / "player_box" / "player_box_2026.parquet")
    core["_n"] = core.display_name.map(normalize_name)
    tm = box[["athlete_id", "team_display_name"]].dropna(subset=["athlete_id"])
    tm = tm.drop_duplicates("athlete_id", keep="last")
    tm["athlete_id"] = pd.to_numeric(tm.athlete_id).astype("int64")
    core["athlete_id"] = core.athlete_id.astype("int64")
    ref = core.merge(tm, on="athlete_id", how="left")

    hit = 0
    for _, r in pop.iterrows():
        h = ref[ref._n == normalize_name(r.player_name)]
        if len(h) == 1:
            hit += 1
        elif len(h) > 1 and isinstance(r.college, str):
            key = r.college.lower().split()[0]
            if len(h[h.team_display_name.fillna("").str.lower()
                     .str.contains(key, regex=False)]) == 1:
                hit += 1
    print(f"  matched to hoopR NCAA data    : {hit}/{len(pop)} "
          f"({100*hit/len(pop):.1f}%)")
    dob = int((wd.date_of_birth.notna() & (wd.date_of_birth.astype(str) != "")).sum())
    print(f"  Wikidata DOB (display-only)   : {dob}/{len(wd)} "
          f"({100*dob/len(wd):.1f}%)")
    check(hit / len(pop) > 0.9, f"2026 hoopR match rate {100*hit/len(pop):.1f}% < 90%")
    return dict(population=len(pop), matched=hit, dob=dob)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-checksums", action="store_true")
    a = ap.parse_args()

    validate_manifest(a.skip_checksums)
    mbb = validate_mbb()
    validate_nba()
    validate_population()
    id_stability()
    validate_2026(mbb)

    rule("RESULT")
    print(f"  hard failures: {len(FAIL)}")
    print(f"  warnings     : {len(WARN)}")
    for m in FAIL:
        print(f"   FAIL {m}")
    for m in WARN:
        print(f"   WARN {m}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
