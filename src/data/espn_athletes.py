"""NBA player height, acquired per-athlete from the ESPN athlete API.

WHY A SEPARATE SOURCE. The hoopR NBA player-season file DraftLens already
uses carries no height at all (see `comparables.nba_features` — it explicitly
refuses to fabricate one). Height is needed only for the NBA Comparables
plausibility gate, so it is acquired here as its own small, auditable raw
dataset rather than smuggled into the statistical feature layer.

WHY ESPN. hoopR's NBA data is an ESPN mirror, so ESPN's own athlete endpoint
is the SAME upstream provider and keys on the SAME `athlete_id` already stored
in the reference pool. That makes the join an exact identity join — no name
matching, therefore no name ambiguity, which is the failure mode a
biography-site scrape would introduce. No player is ever matched by name here.

WHAT IS PARSED. Only `displayHeight` (e.g. `6' 9"`), converted to integer
inches. A row whose height is missing or unparseable is written with an empty
height and is treated downstream as NO HEIGHT — never guessed, never
defaulted, and never silently allowed to bypass the gate.

This module reads no draft outcome, no NBA career result, and nothing about
the 2026 or 2027 populations.
"""

import csv
import json
import re

from data.acquire import http_get
from paths import RAW

HEIGHT_DIR = RAW / "nba_heights"
HEIGHTS_FILE = HEIGHT_DIR / "nba_player_heights.csv"

ATHLETE_API = ("https://site.web.api.espn.com/apis/common/v3/sports/"
               "basketball/nba/athletes/{athlete_id}")

FIELDS = ["athlete_id", "espn_display_name", "display_height", "height_inches"]

THROTTLE = 0.25

# "6' 9\"" / "6'9" / "6' 9" — feet and inches, apostrophe-separated.
_HEIGHT_RE = re.compile(r"^\s*(\d+)\s*'\s*(\d+(?:\.\d+)?)?\s*\"?\s*$")


def parse_display_height(display_height):
    """`6' 9"` -> 81 inches. Returns None when absent or unparseable —
    never a guess, and never a league-average default."""
    if display_height is None:
        return None
    m = _HEIGHT_RE.match(str(display_height))
    if not m:
        return None
    feet = int(m.group(1))
    inches = float(m.group(2)) if m.group(2) else 0.0
    total = feet * 12 + inches
    # Sanity band: anything outside it is a parse artifact, not a person.
    if not (60 <= total <= 96):
        return None
    return int(round(total))


def fetch_athlete(athlete_id, throttle=THROTTLE):
    """One athlete's identity + height from ESPN. Returns a dict; height
    fields are None when ESPN has no usable value."""
    url = ATHLETE_API.format(athlete_id=int(athlete_id))
    raw = http_get(url, throttle=throttle)
    payload = json.loads(raw.decode("utf-8"))
    athlete = payload.get("athlete") or {}
    display_height = athlete.get("displayHeight")
    return dict(
        athlete_id=int(athlete_id),
        espn_display_name=athlete.get("displayName") or "",
        display_height=display_height or "",
        height_inches=parse_display_height(display_height),
    )


def acquire_nba_heights(athlete_ids=None, log=print):
    """Fetch height for every athlete in the frozen NBA reference pool.

    Keyed on the pool's own `athlete_id`, so the later join is an identity
    join. Writes one row per athlete — including those with no height, so the
    audit can distinguish "not acquired" from "ESPN has no height".
    """
    from data.acquire import (load_manifest, manifest_record, sha256_file,
                              utcnow, write_manifest)
    from paths import rel

    if athlete_ids is None:
        from comparables.reference import load_pool
        athlete_ids = sorted(int(a) for a in load_pool().athlete_id.unique())

    rows, failures = [], []
    for i, aid in enumerate(athlete_ids, start=1):
        try:
            rows.append(fetch_athlete(aid))
        except Exception as exc:                      # network/HTTP/parse
            failures.append((aid, repr(exc)))
            rows.append(dict(athlete_id=int(aid), espn_display_name="",
                            display_height="", height_inches=None))
        if i % 50 == 0:
            log(f"  {i}/{len(athlete_ids)} athletes fetched")

    HEIGHT_DIR.mkdir(parents=True, exist_ok=True)
    with open(HEIGHTS_FILE, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in sorted(rows, key=lambda r: r["athlete_id"]):
            w.writerow({k: ("" if r.get(k) is None else r.get(k))
                       for k in FIELDS})

    with_height = sum(1 for r in rows if r["height_inches"] is not None)
    log(f"\n  athletes: {len(rows)}  with height: {with_height} "
        f"({100 * with_height / max(1, len(rows)):.1f}%)  "
        f"fetch failures: {len(failures)}")
    for aid, err in failures[:10]:
        log(f"    FAILED {aid}: {err}")

    records = load_manifest()
    records[rel(HEIGHTS_FILE)] = manifest_record(
        source_family="espn", dataset="nba_player_heights", season_or_year="",
        canonical_url="https://site.web.api.espn.com/apis/common/v3/sports/"
                     "basketball/nba/athletes/{athlete_id}",
        local_path=rel(HEIGHTS_FILE), downloaded_at_utc=utcnow(),
        file_size_bytes=HEIGHTS_FILE.stat().st_size,
        sha256=sha256_file(HEIGHTS_FILE), row_count=len(rows),
        license="ESPN public athlete endpoint; identity/height facts only",
        notes="height for the NBA comparables plausibility gate ONLY; keyed on "
             "the same athlete_id as hoopR (exact identity join, no name "
             "matching); missing height is never imputed")
    write_manifest(records)
    return dict(total=len(rows), with_height=with_height,
               failures=len(failures))


def load_nba_heights(path=HEIGHTS_FILE):
    """athlete_id -> height in inches, for athletes ESPN had a height for.
    Returns None if the dataset has not been acquired."""
    import pandas as pd

    if not path.exists():
        return None
    df = pd.read_csv(path)
    df["height_inches"] = pd.to_numeric(df.height_inches, errors="coerce")
    return df
