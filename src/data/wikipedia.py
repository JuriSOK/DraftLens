"""Reconstruct the historical draft prospect population and draft targets.

Source: English Wikipedia "<year> NBA draft" articles via the MediaWiki Action
API (CC BY-SA 4.0; attribution required for reuse of derived tables).

WHAT THIS MODULE WRITES vs WHAT THE MODELS USE. Acquisition writes the broad
reconstruction — declared early entrants AND drafted NCAA players — so the raw
record stays complete and auditable. The ML sampling frame is NARROWER: the
approved population is final NCAA early entrants only, and
`data.population.load_population` filters to `early_entrant == True`.
The earlier union rule was superseded because population
membership itself carried post-draft information (ML_SPEC 3.2).

Known limitation: undrafted automatically-eligible seniors are not recoverable
from any pre-draft source and are therefore absent (DEC-039).

FIREWALL (DATA.md 11): pre-draft identity is written to
data/raw/draft_population/ and draft outcomes to data/raw/draft_targets/. They
are never written to the same file, so a feature build cannot reach an outcome
by accident.

The Wikipedia markup for these articles is not uniform — four table styles
appear across 2011-2026 — so the parsers below handle each explicitly rather
than assuming a schema.
"""

import csv
import json
import re
import urllib.parse

from data.acquire import http_get, http_json
from data.matching import normalize_name
from paths import RAW

POP_DIR = RAW / "draft_population"
TGT_DIR = RAW / "draft_targets"
WD_DIR = RAW / "wikidata"

WP_API = "https://en.wikipedia.org/w/api.php"
WD_API = "https://www.wikidata.org/w/api.php"
THROTTLE = 3.0

POP_FIELDS = ["draft_year", "player_name", "normalized_name", "college", "position",
              "class", "population_source", "early_entrant", "wikipedia_title"]
TGT_FIELDS = ["draft_year", "normalized_name", "player_name", "wikipedia_title",
              "drafted", "pick", "round", "drafting_team"]

CLASS_MAP = {"fr": "freshman", "so": "sophomore", "jr": "junior", "sr": "senior",
             "gr": "graduate", "5th": "5th year", "rs": "redshirt"}


# ------------------------------------------------------------- wiki utils
def wikitext(page):
    url = (f"{WP_API}?action=parse&page={urllib.parse.quote(page)}"
           "&prop=wikitext&format=json")
    return http_json(url, throttle=THROTTLE)["parse"]["wikitext"]["*"]


def wikitext_revision(revid):
    """Wikitext of one specific, fixed revision — used only for the declared
    (pre-withdrawal) snapshot below, so the acquired list is reproducible and
    does not silently change if the live article is edited later."""
    url = f"{WP_API}?action=parse&oldid={revid}&prop=wikitext&format=json"
    return http_json(url, throttle=THROTTLE)["parse"]["wikitext"]["*"]


def section(text, name):
    m = re.search(r"^(=+)\s*" + re.escape(name) + r"\s*=+\s*$", text, re.M)
    if not m:
        return None
    lvl, start = len(m.group(1)), m.end()
    nxt = re.search(r"^={2," + str(lvl) + r"}[^=]", text[start:], re.M)
    return text[start:start + (nxt.start() if nxt else len(text))]


def strip_markup(s):
    s = re.sub(r"<ref[^>]*>.*?</ref>|<ref[^>]*/>", "", s, flags=re.S)
    s = re.sub(r"<[^>]+>", "", s)
    s = re.sub(r"\{\{[^{}]*\}\}", "", s)
    s = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", r"\2", s)
    s = re.sub(r"\[\[([^\]]+)\]\]", r"\1", s)
    return re.sub(r"\s+", " ", s.replace("'''", "").replace("''", "")).strip()


def cells(row):
    """Split a wikitable row into cells, dropping leading style attributes.

    Handles both markup styles seen across 2011-2026 articles: cells on their
    own line ("\\n| value"), header cells ("\\n! scope=row| v") and
    inline cells ("| a || b || c").
    """
    out = []
    for seg in re.split(r"\n\s*[|!]", "\n" + row.strip()):
        for c in seg.split("||"):
            c = c.strip()
            if not c:
                continue
            c = re.sub(r'^(?:[a-zA-Z-]+\s*=\s*"[^"]*"\s*)+\|', "", c).strip()
            c = re.sub(r"^(?:align|bgcolor|scope|style|colspan|rowspan|width)"
                       r"\s*=\s*[^|]*\|", "", c).strip()
            if c:
                out.append(c)
    return out


def player_from_cell(cell):
    """(wikipedia_title, display_name). Handles {{sortname}} and plain wikilinks."""
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
    txt = strip_markup(cell)
    txt = re.sub(r"[*#~^+]+$", "", txt).strip()
    return (txt, txt) if txt else (None, None)


LINK_RE = r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]"


def collect_school_candidates(text):
    """Every wikilink target that could plausibly name a basketball team."""
    return {tgt for tgt, _ in re.findall(LINK_RE, text)
            if "basketball" in tgt.lower()}


def resolve_canonical(targets):
    """Map each link target to its canonical article title via the MediaWiki
    redirect system (batched, 50 titles per request)."""
    tl, canon = sorted(targets), {}
    for i in range(0, len(tl), 50):
        chunk = tl[i:i + 50]
        q = (f"{WP_API}?action=query&redirects=1&format=json&titles="
             + urllib.parse.quote("|".join(chunk)))
        d = http_json(q, throttle=THROTTLE).get("query", {})
        alias = {r["from"]: r["to"]
                 for r in d.get("normalized", []) + d.get("redirects", [])}
        for t in chunk:
            c = t
            for _ in range(3):
                c = alias.get(c, c)
            canon[t] = c
    return canon


def is_ncaa_program(canonical_title):
    """True iff the canonical article is a US college basketball PROGRAM page.

    Rule (DEC-063): the canonical title ends with "basketball" AND carries no
    parenthetical disambiguator.

    Wikipedia is inconsistent about the "men's" infix — "Duke Blue Devils men's
    basketball" but "Georgia Bulldogs basketball" — and several programs are
    reached through redirects, so the title must be canonicalised first. The
    discriminator is the parenthesis: college programs are titled
    "<Team> [men's] basketball", whereas foreign clubs, leagues and player
    articles use "(men's basketball)" / "(basketball)" as a disambiguator
    (e.g. "Beşiktaş J.K. (men's basketball)", "Anthony Edwards (basketball)").
    """
    c = str(canonical_title)
    return c.endswith("basketball") and "(" not in c


def find_school(text, ncaa_targets):
    """(college_label, is_ncaa) using the pre-resolved NCAA target set."""
    for tgt, lbl in re.findall(LINK_RE, text):
        if tgt in ncaa_targets:
            # labels can carry templates, e.g. [[...|Hawai{{okina}}i]]
            return strip_markup(lbl or tgt), True
    return None, False


def find_class(text):
    m = re.search(r"\(\[\[([A-Za-z0-9 ]+)\|", text)
    if m:
        return m.group(1).strip().lower()
    m = re.search(r"\((freshman|sophomore|junior|senior|graduate|5th year|"
                  r"redshirt[a-z ]*)\)", text, re.I)
    if m:
        return m.group(1).lower()
    m = re.search(r"\((Fr|So|Jr|Sr|Gr)\.\)", text)
    if m:
        return CLASS_MAP.get(m.group(1).lower(), m.group(1).lower())
    return None


# ----------------------------------------------------------------- parsers
def parse_picks(text, ncaa_targets):
    """All draft selections -> list of dicts (both NCAA and non-NCAA)."""
    sec = section(text, "Draft selections")
    if sec is None:
        raise ValueError("no 'Draft selections' section")
    out = []
    for row in sec.split("\n|-"):
        cs = cells(row)
        if len(cs) < 5 or not re.match(r"^\d+$", cs[0]):
            continue
        rnd = int(cs[0])
        pick_txt = strip_markup(cs[1])
        m = re.search(r"\d+", pick_txt)
        if not m:
            continue
        pick = int(m.group(0))
        title, disp = player_from_cell(cs[2])
        if not title:
            continue
        pos = strip_markup(cs[3]) if len(cs) > 3 else None
        team_txt = cs[5] if len(cs) > 5 else ""
        tm = re.search(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", team_txt)
        team = (tm.group(2) or tm.group(1)) if tm else strip_markup(team_txt)
        school_blob = " ".join(cs[6:]) if len(cs) > 6 else ""
        college, is_ncaa = find_school(school_blob, ncaa_targets)
        out.append(dict(round=rnd, pick=pick, wikipedia_title=title, player_name=disp,
                        position=pos, drafting_team=team, college=college,
                        is_ncaa=is_ncaa, klass=find_class(school_blob)))
    return out


def _entrant_from_text(blob, title, disp, ncaa_targets):
    college, is_ncaa = find_school(blob, ncaa_targets)
    pm = re.search(r"[–—-]\s*([A-Z]{1,2}(?:/[A-Z]{1,2})?)\s*,", blob)
    return dict(wikipedia_title=title, player_name=disp,
                position=pm.group(1) if pm else None,
                college=college, is_ncaa=is_ncaa, klass=find_class(blob))


def parse_early_entrants(text, ncaa_targets):
    """Final early entrants -> list of dicts (NCAA flag included).

    Two markup styles occur across 2011-2026: bulleted lists (most years) and
    wikitables (e.g. 2014). Bullets are tried first; tables are the fallback.
    """
    sec = section(text, "Early entrants")
    if sec is None:
        return []

    out = []
    for line in sec.split("\n"):
        if not line.strip().startswith("*"):
            continue
        links = re.findall(LINK_RE, line)
        # The first link is the player ONLY when it is not the school link.
        # Prospects without a Wikipedia article have their name as plain text
        # before the position dash (e.g. "* {{flagicon|USA}} Casdon Jardine -
        # G/F, [[Hawaii Rainbow Warriors basketball|Hawai{{okina}}i]]"), and
        # taking links[0] there would name the prospect after their school.
        if links and links[0][0] not in ncaa_targets:
            title = links[0][0]
            disp = links[0][1] or links[0][0]
        else:
            plain = re.sub(r"^\s*\*+\s*", "", line)
            plain = re.sub(r"\{\{flagicon\|[^}]*\}\}", "", plain)
            plain = re.split(r"[–—]|\s-\s", plain)[0]
            disp = strip_markup(plain)
            if not disp:
                continue
            title = ""          # no Wikipedia article for this prospect
        out.append(_entrant_from_text(line, title, disp, ncaa_targets))
    if out:
        return out

    # table fallback: | {{sortname|First|Last}} || [[School]] || [[Class]]
    for row in sec.split("\n|-"):
        cs = cells(row)
        if not cs:
            continue
        title, disp = player_from_cell(cs[0])
        if not title or len(title) > 60:
            continue
        blob = " ".join(cs)
        if not re.search(r"\[\[|\{\{sortname", cs[0]):
            continue
        out.append(_entrant_from_text(blob, title, disp, ncaa_targets))
    return out


# --------------------------------------------------------------- per year
def build_year(year, report):
    text = wikitext(f"{year} NBA draft")
    canon = resolve_canonical(collect_school_candidates(text))
    ncaa_targets = {t for t, c in canon.items() if is_ncaa_program(c)}
    picks = parse_picks(text, ncaa_targets)
    early = parse_early_entrants(text, ncaa_targets)

    ncaa_picks = [p for p in picks if p["is_ncaa"]]
    ncaa_early = [e for e in early if e["is_ncaa"]]

    pop, tgt = {}, {}
    for p in ncaa_picks:
        k = normalize_name(p["player_name"])
        pop[k] = dict(draft_year=year, player_name=p["player_name"], normalized_name=k,
                      college=p["college"], position=p["position"], **{"class": p["klass"]},
                      population_source="drafted", early_entrant=False,
                      wikipedia_title=p["wikipedia_title"])
        tgt[k] = dict(draft_year=year, normalized_name=k, player_name=p["player_name"],
                      wikipedia_title=p["wikipedia_title"], drafted=True,
                      pick=p["pick"], round=p["round"], drafting_team=p["drafting_team"])
    for e in ncaa_early:
        k = normalize_name(e["player_name"])
        if k in pop:
            pop[k]["early_entrant"] = True
            pop[k]["population_source"] = "early_entrant+drafted"
            pop[k]["class"] = pop[k]["class"] or e["klass"]
            pop[k]["college"] = pop[k]["college"] or e["college"]
        else:
            pop[k] = dict(draft_year=year, player_name=e["player_name"],
                          normalized_name=k, college=e["college"],
                          position=e["position"], **{"class": e["klass"]},
                          population_source="early_entrant", early_entrant=True,
                          wikipedia_title=e["wikipedia_title"])
            tgt[k] = dict(draft_year=year, normalized_name=k,
                          player_name=e["player_name"],
                          wikipedia_title=e["wikipedia_title"], drafted=False,
                          pick="", round="", drafting_team="")

    n_drafted = sum(1 for t in tgt.values() if t["drafted"])
    row = dict(draft_year=year, total_picks=len(picks), ncaa_drafted=len(ncaa_picks),
               ncaa_early_entrants=len(ncaa_early), population=len(pop),
               drafted=n_drafted, undrafted=len(pop) - n_drafted,
               drafted_pct=round(100 * n_drafted / len(pop), 1) if pop else 0.0,
               flags="")

    # ---- validation assertions (flag, never silently accept)
    flags = []
    if len(picks) < 30:
        flags.append(f"IMPLAUSIBLE_PICKS({len(picks)})")
    if len(picks) > 70:
        flags.append(f"EXCESS_PICKS({len(picks)})")
    if len(ncaa_picks) < 15:
        flags.append(f"LOW_NCAA_DRAFTED({len(ncaa_picks)})")
    if len(ncaa_early) < 5:
        flags.append(f"LOW_EARLY_ENTRANTS({len(ncaa_early)})")
    if len(pop) != len(set(pop)):
        flags.append("DUPLICATE_POPULATION_KEY")
    if len(pop) - n_drafted < 3:
        flags.append(f"TINY_UNDRAFTED_CLASS({len(pop)-n_drafted})")
    if n_drafted != len(ncaa_picks):
        flags.append(f"DRAFTED_MISMATCH({n_drafted}vs{len(ncaa_picks)})")
    row["flags"] = ";".join(flags)
    report.append(row)
    return list(pop.values()), list(tgt.values()), row


def write_csv(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})


# --------------------------------------------------- declared (pre-withdrawal)
DECLARED_FIELDS = ["draft_year", "player_name", "normalized_name", "college",
                   "position", "class", "wikipedia_title"]

# One fixed Wikipedia revision per year: the first revision captured after the
# NBA's official initial early-entry announcement, BEFORE any withdrawal. Each
# revision's "Early entrants" section at that point in time enumerates exactly
# the players named in the cited NBA.com press release (e.g. for 2026:
# https://www.nba.com/news/2026-nba-draft-early-entry-candidates, "the NBA
# announced 71 players ... who filed as early entry candidates"). Recorded as
# a fixed revid (not "the live article") so this is reproducible and does not
# silently change if the article is edited later. Adding a year requires
# looking up its announcement date and the first revision after it via the
# MediaWiki API (action=query&prop=revisions&rvstart=<date>&rvdir=older) —
# never inventing one. Absence of an entry means "not yet acquired", not zero
# declared players.
DECLARED_SNAPSHOTS = {
    2026: dict(revid=1351570404, captured="2026-04-28T20:21:02Z",
               announcement_date="2026-04-27",
               canonical_url="https://www.nba.com/news/2026-nba-draft-early-entry-candidates",
               note="NBA announced 71 players (60 NCAA, 11 international) who "
                    "filed as early entry candidates. This snapshot predates "
                    "both subsequent withdrawal rounds (May 29 and June 16)."),
}


def build_declared(year, report=None):
    """The ORIGINAL declared NCAA pool for `year`, before any withdrawal.

    Distinct from `build_year` above, which reconstructs the FINAL population
    (after withdrawal deadlines) that `data.population.load_population`
    serves as the ML sampling frame. This function serves PRODUCT/DISPLAY
    population status only (DECLARED vs WITHDRAWN vs FINAL_ENTRY) — its output
    must never be joined into a feature frame as a model input.

    Returns None if no snapshot is recorded for `year` (see DECLARED_SNAPSHOTS)
    rather than fabricating one.
    """
    snap = DECLARED_SNAPSHOTS.get(year)
    if snap is None:
        return None, None

    text = wikitext_revision(snap["revid"])
    canon = resolve_canonical(collect_school_candidates(text))
    ncaa_targets = {t for t, c in canon.items() if is_ncaa_program(c)}
    entrants = parse_early_entrants(text, ncaa_targets)
    ncaa = [e for e in entrants if e["is_ncaa"]]

    pop = {}
    for e in ncaa:
        k = normalize_name(e["player_name"])
        pop[k] = dict(draft_year=year, player_name=e["player_name"],
                      normalized_name=k, college=e["college"],
                      position=e["position"], **{"class": e["klass"]},
                      wikipedia_title=e["wikipedia_title"])

    row = dict(draft_year=year, total_declared=len(entrants),
              ncaa_declared=len(ncaa), revid=snap["revid"],
              captured=snap["captured"])
    if report is not None:
        report.append(row)
    return list(pop.values()), row


def acquire_declared(years):
    """Rebuild draft_declared_<year>.csv for every year with a recorded
    snapshot in `years`. Written to data/raw/draft_population/ alongside (but
    never merged with) draft_population_<year>.csv — same firewall directory,
    same "no outcome column, ever" rule, since this is pre-draft declaration
    information exactly like the final population file."""
    from data.acquire import load_manifest, manifest_record, sha256_file, utcnow, write_manifest
    from paths import rel

    records = load_manifest()
    report = []
    for y in years:
        pop, row = build_declared(y, report)
        if pop is None:
            print(f"  {y}: no declared snapshot recorded — skipped "
                  f"(see wikipedia.DECLARED_SNAPSHOTS)")
            continue
        path = POP_DIR / f"draft_declared_{y}.csv"
        write_csv(path, DECLARED_FIELDS, pop)
        records[rel(path)] = manifest_record(
            source_family="wikipedia", dataset="draft_declared",
            season_or_year=y,
            canonical_url=f"https://en.wikipedia.org/w/index.php?"
                          f"title={y}_NBA_draft&oldid={row['revid']}",
            local_path=rel(path), downloaded_at_utc=utcnow(),
            file_size_bytes=path.stat().st_size, sha256=sha256_file(path),
            row_count=len(pop),
            license="CC BY-SA 4.0 (English Wikipedia) — attribution required",
            notes=f"initial declared NCAA pool, revid={row['revid']} "
                 f"(captured {row['captured']}), before any withdrawal; "
                 f"underlying primary source: {DECLARED_SNAPSHOTS[y]['canonical_url']}")
        print(f"  {y}: declared_total={row['total_declared']} "
              f"ncaa_declared={row['ncaa_declared']} -> {rel(path)}")
    write_manifest(records)
    return 0


# -------------------------------------------------------- Wikidata (2026)


def acquire(years, wikidata=False):
    """Rebuild the population and target CSVs for `years`, updating the manifest.

    Population and targets are written to SEPARATE directories — the firewall
    that keeps a feature build from reaching an outcome by accident.
    """
    from data.acquire import (load_manifest,
                                                     manifest_record,
                                                     sha256_file, utcnow,
                                                     write_manifest)
    from data.wikidata import WD_DIR, enrich_wikidata
    from paths import rel

    records = load_manifest()
    report, all_pop = [], {}
    print(f"{'year':<6}{'picks':>6}{'ncaaDr':>8}{'ncaaEE':>8}{'pop':>6}"
          f"{'drft':>6}{'undr':>6}{'drft%':>7}  flags")
    for y in years:
        pop, tgt, row = build_year(y, report)
        all_pop[y] = pop
        write_csv(POP_DIR / f"draft_population_{y}.csv", POP_FIELDS, pop)
        write_csv(TGT_DIR / f"draft_targets_{y}.csv", TGT_FIELDS, tgt)
        for path, ds in ((POP_DIR / f"draft_population_{y}.csv", "draft_population"),
                         (TGT_DIR / f"draft_targets_{y}.csv", "draft_targets")):
            records[rel(path)] = manifest_record(
                source_family="wikipedia", dataset=ds, season_or_year=y,
                canonical_url=f"https://en.wikipedia.org/wiki/{y}_NBA_draft",
                local_path=rel(path), downloaded_at_utc=utcnow(),
                file_size_bytes=path.stat().st_size, sha256=sha256_file(path),
                row_count=len(pop if ds == "draft_population" else tgt),
                license="CC BY-SA 4.0 (English Wikipedia) — attribution required",
                notes="derived table; feature/target firewall enforced")
        print(f"{row['draft_year']:<6}{row['total_picks']:>6}{row['ncaa_drafted']:>8}"
              f"{row['ncaa_early_entrants']:>8}{row['population']:>6}"
              f"{row['drafted']:>6}{row['undrafted']:>6}"
              f"{row['drafted_pct']:>6.1f}%  {row['flags']}")

    write_csv(POP_DIR / "population_report.csv",
              ["draft_year", "total_picks", "ncaa_drafted", "ncaa_early_entrants",
               "population", "drafted", "undrafted", "drafted_pct", "flags"],
              report)

    if wikidata:
        y = years[-1]
        print(f"\nWikidata DOB enrichment for {y} (display-only; DEC-044)...")
        rows = enrich_wikidata(all_pop[y], y)
        p = WD_DIR / f"wikidata_dob_{y}.csv"
        write_csv(p, ["draft_year", "normalized_name", "player_name",
                      "wikipedia_title", "wikidata_qid", "date_of_birth",
                      "dob_precision", "match_method", "match_confidence"], rows)
        got = sum(1 for r in rows if r["date_of_birth"])
        print(f"  {got}/{len(rows)} DOB ({100 * got / len(rows):.1f}%) -> {rel(p)}")
        records[rel(p)] = manifest_record(
            source_family="wikidata", dataset="dob", season_or_year=y,
            canonical_url="https://www.wikidata.org/wiki/Property:P569",
            local_path=rel(p), downloaded_at_utc=utcnow(),
            file_size_bytes=p.stat().st_size, sha256=sha256_file(p),
            row_count=len(rows),
            license="CC0 1.0 (Wikidata structured data)",
            notes="P569 only; display-only, excluded from board features (DEC-044)")

    write_manifest(records)
    bad = [r for r in report if r["flags"]]
    print(f"\nyears processed: {len(report)} | years with flags: {len(bad)}")
    for r in bad:
        print(f"  {r['draft_year']}: {r['flags']}")
    return 0
