"""Wikidata date-of-birth feasibility audit (DATA.md §23).

Read-only. Stdlib + pandas only (no new dependencies). Resolves the 2026 NCAA
prospect population and historical samples to Wikidata Q-IDs and retrieves
P569 (date of birth) only. No other Wikidata property is stored.

Run: ./.venv/bin/python scripts/audit_wikidata_dob.py
"""

import json
import re
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

UA = {"User-Agent": "DraftLens-research/0.1 (data feasibility audit; contact: project owner)"}
RAW = Path(__file__).resolve().parents[1] / "data" / "raw" / "hoopR-mbb-data"
CALLS = {"n": 0}
THROTTLE = 1.2


def api(url):
    CALLS["n"] += 1
    time.sleep(THROTTLE)
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=45) as r:
        return json.load(r)


def rule(t):
    print(f"\n{'=' * 78}\n{t}\n{'=' * 78}")


def norm(s):
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b\.?", "", s)
    return re.sub(r"\s+", " ", re.sub(r"[^a-z ]", "", s)).strip()


def wikitext(page):
    return api("https://en.wikipedia.org/w/api.php?action=parse&page="
               f"{urllib.parse.quote(page)}&prop=wikitext&format=json"
               )["parse"]["wikitext"]["*"]


def section(t, name):
    m = re.search(r"^(=+)\s*" + re.escape(name) + r"\s*=+\s*$", t, re.M)
    if not m:
        return None
    lvl, start = len(m.group(1)), m.end()
    nxt = re.search(r"^={2," + str(lvl) + r"}[^=]", t[start:], re.M)
    return t[start:start + (nxt.start() if nxt else len(t))]


# ---------------------------------------------------------------- parsing
def _cells(row):
    """Split a wikitable row into cells, stripping leading style attributes."""
    out = []
    for c in re.split(r"\n\s*\|", "\n" + row.strip()):
        c = c.strip()
        if not c:
            continue
        c = re.sub(r'^(?:[a-zA-Z-]+\s*=\s*"[^"]*"\s*)+\|', "", c).strip()
        c = re.sub(r"^(?:align|bgcolor|scope|style|colspan|rowspan)\s*=\s*[^|]*\|",
                   "", c).strip()
        out.append(c)
    return out


def _player_from_cell(cell):
    """Return (wikipedia_title, display) from a player cell, format-agnostic."""
    m = re.search(r"\{\{sortname\|([^}|]+)\|([^}|]+)((?:\|[^}]*)?)\}\}", cell)
    if m:
        first, last, extra = m.group(1).strip(), m.group(2).strip(), m.group(3) or ""
        disp = f"{first} {last}"
        dab = re.search(r"\|dab=([^|}]+)", extra)
        if dab:
            return f"{first} {last} ({dab.group(1).strip()})", disp
        pos3 = re.match(r"\|([^|=}]+)", extra)
        if pos3 and "nolink" not in pos3.group(1):
            return pos3.group(1).strip(), disp
        return disp, disp
    m = re.search(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", cell)
    if m:
        return m.group(1), (m.group(2) or m.group(1))
    txt = re.sub(r"<[^>]+>|\{\{[^}]*\}\}|'{2,}", "", cell).strip()
    return (txt, txt) if txt else (None, None)


def parse_picks(t):
    """Draft selections table -> [(wikipedia_title, display, school, is_ncaa)].

    Player is taken from the 3rd cell (Rnd, Pick, Player, ...) so the parser
    works whether the table uses {{sortname}} or plain wikilinks.
    """
    sec = section(t, "Draft selections")
    out = []
    for row in sec.split("\n|-"):
        cells = _cells(row)
        if len(cells) < 5:
            continue
        if not re.match(r"^\d+$", cells[0]):
            continue
        title, disp = _player_from_cell(cells[2])
        if not title:
            continue
        school, is_ncaa = None, False
        for tgt, lbl in re.findall(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]",
                                   " ".join(cells[5:])):
            if "men's basketball" in tgt:
                school, is_ncaa = (lbl or tgt), True
                break
        out.append((title, disp, school, is_ncaa))
    return out


def parse_early(t):
    """Early entrants section -> [(title, display, school, is_ncaa)]."""
    sec = section(t, "Early entrants")
    if not sec:
        return []
    out = []
    for line in sec.split("\n"):
        if not line.strip().startswith("*"):
            continue
        links = re.findall(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", line)
        if not links:
            continue
        player = next((l for l in links if "men's basketball" not in l[0]
                       and "basketball" not in l[0].lower().replace(" basketball", "")
                       or True), None)
        title, disp = links[0][0], links[0][1] or links[0][0]
        school, is_ncaa = None, False
        for tgt, lbl in links[1:]:
            if "men's basketball" in tgt:
                school, is_ncaa = (lbl or tgt), True
                break
        out.append((title, disp, school, is_ncaa))
    return out


# ------------------------------------------------- Wikipedia title -> QID
def titles_to_qids(titles):
    """Batched pageprops lookup. Returns {title: qid|None} and redirect map."""
    res, norm_map = {}, {}
    for i in range(0, len(titles), 50):
        chunk = [t for t in titles[i:i + 50] if t]
        q = ("https://en.wikipedia.org/w/api.php?action=query&prop=pageprops"
             "&ppprop=wikibase_item&redirects=1&format=json&titles="
             + urllib.parse.quote("|".join(chunk)))
        d = api(q).get("query", {})
        for r in d.get("normalized", []) + d.get("redirects", []):
            norm_map[r["from"]] = r["to"]
        for _, pg in d.get("pages", {}).items():
            res[pg["title"]] = pg.get("pageprops", {}).get("wikibase_item")
    final = {}
    for t in titles:
        cur = t
        for _ in range(3):
            cur = norm_map.get(cur, cur)
        final[t] = res.get(cur)
    return final


# ------------------------------------------------------- QID -> P569 only
def qids_to_dob(qids):
    """Returns {qid: (iso_time|None, precision|None)} using P569 ONLY."""
    out = {}
    qids = [q for q in qids if q]
    for i in range(0, len(qids), 50):
        chunk = qids[i:i + 50]
        q = ("https://www.wikidata.org/w/api.php?action=wbgetentities&props=claims"
             "&languages=en&format=json&ids=" + "|".join(chunk))
        d = api(q).get("entities", {})
        for qid, ent in d.items():
            claims = (ent.get("claims") or {}).get("P569")
            if not claims:
                out[qid] = (None, None)
                continue
            best = None
            for c in claims:
                dv = (c.get("mainsnak", {}).get("datavalue") or {}).get("value")
                if not dv:
                    continue
                if best is None or c.get("rank") == "preferred":
                    best = dv
            out[qid] = (best.get("time"), best.get("precision")) if best else (None, None)
    return out


PREC = {11: "FULL_DATE", 10: "MONTH_PRECISION", 9: "YEAR_PRECISION"}


def classify(title, qid, dob, prec):
    if qid is None:
        return "NO_ENTITY"
    if dob is None:
        return "NO_DOB"
    return "EXACT_LINK"


# ================================================================= AUDIT A
rule("AUDIT A — 2026 NCAA prospect population (early entrants ∪ drafted)")
t26 = wikitext("2026 NBA draft")
picks = parse_picks(t26)
early = parse_early(t26)
print(f"draft table rows parsed : {len(picks)}  (NCAA: {sum(p[3] for p in picks)})")
print(f"early entrant bullets   : {len(early)}  (NCAA: {sum(e[3] for e in early)})")

pop = {}
for title, disp, school, ncaa in picks:
    if ncaa:
        pop[norm(disp)] = {"title": title, "name": disp, "school": school,
                           "drafted": True}
for title, disp, school, ncaa in early:
    if not ncaa:
        continue
    k = norm(disp)
    if k in pop:
        pop[k]["early_entrant"] = True
    else:
        pop[k] = {"title": title, "name": disp, "school": school, "drafted": False,
                  "early_entrant": True}
for v in pop.values():
    v.setdefault("early_entrant", False)

print(f"\nunique 2026 NCAA prospects: {len(pop)}")
print(f"  drafted NCAA            : {sum(v['drafted'] for v in pop.values())}")
print(f"  declared, undrafted     : {sum(not v['drafted'] for v in pop.values())}")

titles = [v["title"] for v in pop.values()]
qmap = titles_to_qids(titles)
dmap = qids_to_dob(list(qmap.values()))

for v in pop.values():
    qid = qmap.get(v["title"])
    dob, prec = dmap.get(qid, (None, None))
    v.update(qid=qid, dob=dob, precision=prec,
             status=classify(v["title"], qid, dob, prec))

df26 = pd.DataFrame(pop.values())
print("\nlookup outcome:")
print(df26.status.value_counts().to_string())


def cov(sub, label):
    n = len(sub)
    if n == 0:
        print(f"  {label:<26} n=0")
        return
    ent = sub.qid.notna().sum()
    dob = sub.dob.notna().sum()
    full = (sub.precision == 11).sum()
    print(f"  {label:<26} n={n:<4} entity {100*ent/n:5.1f}%  "
          f"DOB {100*dob/n:5.1f}%  FULL-DATE {100*full/n:5.1f}%")


print("\n>>> 2026 COVERAGE")
cov(df26, "ALL NCAA prospects")
cov(df26[df26.drafted], "A. drafted")
cov(df26[~df26.drafted], "B. declared & undrafted")

rule("AUDIT D — P569 precision distribution (2026)")
p = df26.precision.map(lambda x: PREC.get(x, "MISSING") if pd.notna(x) else "MISSING")
print(p.value_counts().to_string())

# ================================================================= AUDIT B
rule("AUDIT B — historical samples (2011, 2015, 2020, 2022, 2025)")
hist_rows = []
for yr in [2011, 2015, 2020, 2022, 2025]:
    t = wikitext(f"{yr} NBA draft")
    pk, ee = parse_picks(t), parse_early(t)
    drafted = [(ti, di, sc) for ti, di, sc, n in pk if n]
    dset = {norm(d) for _, d, _ in drafted}
    undrafted = [(ti, di, sc) for ti, di, sc, n in ee if n and norm(di) not in dset]

    def spread(seq, k=10):
        if len(seq) <= k:
            return seq
        step = len(seq) / k
        return [seq[int(i * step)] for i in range(k)]

    for ti, di, sc in spread(drafted):
        hist_rows.append(dict(year=yr, title=ti, name=di, school=sc, drafted=True))
    for ti, di, sc in spread(undrafted):
        hist_rows.append(dict(year=yr, title=ti, name=di, school=sc, drafted=False))
    print(f"  {yr}: NCAA drafted={len(drafted):<3} NCAA declared-undrafted="
          f"{len(undrafted):<3} -> sampled {min(10,len(drafted))}+{min(10,len(undrafted))}")

hist = pd.DataFrame(hist_rows)
hq = titles_to_qids(list(hist.title))
hd = qids_to_dob(list(hq.values()))
hist["qid"] = hist.title.map(hq)
hist["dob"] = hist.qid.map(lambda q: hd.get(q, (None, None))[0])
hist["precision"] = hist.qid.map(lambda q: hd.get(q, (None, None))[1])

print(f"\nhistorical sample size: {len(hist)}")
print("\nper-year coverage:")
print(f"  {'year':<6}{'n':>4}{'entity%':>9}{'DOB%':>8}{'full%':>8}   "
      f"{'drafted DOB%':>13}{'undrafted DOB%':>15}")
for yr, g in hist.groupby("year"):
    d, u = g[g.drafted], g[~g.drafted]
    print(f"  {yr:<6}{len(g):>4}{100*g.qid.notna().mean():>8.1f}%"
          f"{100*g.dob.notna().mean():>7.1f}%{100*(g.precision==11).mean():>7.1f}%"
          f"{100*d.dob.notna().mean() if len(d) else float('nan'):>12.1f}%"
          f"{100*u.dob.notna().mean() if len(u) else float('nan'):>14.1f}%")

print("\noverall historical:")
cov(hist, "ALL")
cov(hist[hist.drafted], "drafted")
cov(hist[~hist.drafted], "declared & undrafted")
print("\nhistorical precision:")
print(hist.precision.map(lambda x: PREC.get(x, "MISSING") if pd.notna(x) else "MISSING")
      .value_counts().to_string())

# ================================================================= AUDIT F
rule("AUDIT F — join 2026 prospects to hoopR NCAA data")
core = pd.read_parquet(RAW / "player_core_2026.parquet")
box = pd.read_parquet(RAW / "player_box_2026.parquet")
core["_n"] = core.display_name.map(norm)
teams = box[["athlete_id", "team_display_name"]].drop_duplicates("athlete_id", keep="last")
teams = teams[teams.athlete_id.notna()].copy()
teams["athlete_id"] = pd.to_numeric(teams.athlete_id).astype("int64")
core["athlete_id"] = core.athlete_id.astype("int64")
ref = core.merge(teams, on="athlete_id", how="left")

matched = []
for _, r in df26.iterrows():
    hits = ref[ref._n == norm(r["name"])]
    aid = None
    if len(hits) == 1:
        aid = int(hits.iloc[0].athlete_id)
    elif len(hits) > 1 and r["school"]:
        key = str(r["school"]).lower().split()[0]
        ok = hits[hits.team_display_name.fillna("").str.lower().str.contains(key, regex=False)]
        if len(ok) == 1:
            aid = int(ok.iloc[0].athlete_id)
    matched.append(aid)
df26["hoopr_id"] = matched

hoopr_ok = df26.hoopr_id.notna()
dob_ok = df26.dob.notna()
n = len(df26)
print(f"prospects                       : {n}")
print(f"matched to hoopR athlete_id     : {hoopr_ok.sum()} ({100*hoopr_ok.mean():.1f}%)")
print(f"Wikidata DOB available          : {dob_ok.sum()} ({100*dob_ok.mean():.1f}%)")
print(f"BOTH hoopR stats AND DOB        : {(hoopr_ok & dob_ok).sum()} "
      f"({100*(hoopr_ok & dob_ok).mean():.1f}%)")

hh = df26[hoopr_ok].copy()
hh["hoopr_id"] = hh.hoopr_id.astype("int64")
j = hh.merge(core[["athlete_id", "position_abbreviation", "height", "weight",
                   "date_of_birth"]], left_on="hoopr_id", right_on="athlete_id", how="left")
print(f"\namong matched prospects (n={len(j)}):")
for c, lab in [("position_abbreviation", "position"), ("height", "height"),
               ("weight", "weight"), ("date_of_birth", "hoopR DOB")]:
    print(f"  {lab:<12} {100*j[c].notna().mean():5.1f}%")
print(f"  {'Wikidata DOB':<12} {100*j.dob.notna().mean():5.1f}%")

print(f"\n>>> FULL FEATURE READINESS (stats + position + DOB): "
      f"{100*((j.position_abbreviation.notna()) & (j.dob.notna())).mean():.1f}%")

df26.to_json(Path("/tmp/draftlens_2026_dob_audit.json"), orient="records")
hist.to_json(Path("/tmp/draftlens_hist_dob_audit.json"), orient="records")
print(f"\n[audit frames written to /tmp only — not to the repo]")
print(f"API calls this run: {CALLS['n']}")
