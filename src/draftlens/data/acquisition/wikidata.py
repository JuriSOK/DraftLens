"""Wikidata enrichment for prospect biography fields.

Wikidata is CC0. Queried through the public Action API only — no account, no
authentication, no bulk export, and a deliberate throttle.

Date of birth acquired here is for DISPLAY and audit only. It is prohibited as a
model feature: coverage is 100% for drafted and 69% for undrafted prospects, so
its availability is a function of the outcome (ML_SPEC 8.2, DEC-044).
"""

import csv
import json
import re
import urllib.parse

from draftlens.data.acquisition.http import http_get, http_json
from draftlens.paths import RAW

WP_API = "https://en.wikipedia.org/w/api.php"   # resolves titles -> Q-ids
WD_API = "https://www.wikidata.org/w/api.php"
WD_DIR = RAW / "wikidata"
THROTTLE = 3.0


def enrich_wikidata(pop_rows, year):
    """Q-ID + P569 only. No other property is requested or stored."""
    titles = [r["wikipedia_title"] for r in pop_rows if r.get("wikipedia_title")]
    qmap, alias = {}, {}
    for i in range(0, len(titles), 50):
        q = (f"{WP_API}?action=query&prop=pageprops&ppprop=wikibase_item"
             "&redirects=1&format=json&titles="
             + urllib.parse.quote("|".join(titles[i:i + 50])))
        d = http_json(q, throttle=THROTTLE).get("query", {})
        for r in d.get("normalized", []) + d.get("redirects", []):
            alias[r["from"]] = r["to"]
        for _, pg in d.get("pages", {}).items():
            qmap[pg["title"]] = pg.get("pageprops", {}).get("wikibase_item")

    def resolve(t):
        cur = t
        for _ in range(3):
            cur = alias.get(cur, cur)
        return qmap.get(cur)

    qids = sorted({q for q in (resolve(t) for t in titles) if q})
    dob = {}
    for i in range(0, len(qids), 50):
        q = (f"{WD_API}?action=wbgetentities&props=claims&languages=en&format=json"
             "&ids=" + "|".join(qids[i:i + 50]))
        for qid, ent in http_json(q, throttle=THROTTLE).get("entities", {}).items():
            claims = (ent.get("claims") or {}).get("P569")
            best = None
            for c in claims or []:
                dv = (c.get("mainsnak", {}).get("datavalue") or {}).get("value")
                if dv and (best is None or c.get("rank") == "preferred"):
                    best = dv
            dob[qid] = (best.get("time"), best.get("precision")) if best else (None, None)

    out = []
    for r in pop_rows:
        qid = resolve(r["wikipedia_title"]) if r.get("wikipedia_title") else None
        d, p = dob.get(qid, (None, None))
        out.append(dict(draft_year=year, normalized_name=r["normalized_name"],
                        player_name=r["player_name"], wikipedia_title=r["wikipedia_title"],
                        wikidata_qid=qid or "",
                        date_of_birth=(str(d)[1:11] if d else ""),
                        dob_precision=p if p else "",
                        match_method="wikipedia_link" if qid else "none",
                        match_confidence=("EXACT_LINK" if qid and d else
                                          "NO_DOB" if qid else "NO_ENTITY")))
    return out
