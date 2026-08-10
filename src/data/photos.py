"""Prospect portrait resolution from Wikimedia, with licence and identity
verification.

TWO THINGS CAN GO WRONG HERE, and both are guarded rather than hoped away:

  WRONG PERSON. Assigning a photo by name alone is how a college freshman ends
  up illustrated by a retired player who shares his name. Identity is
  therefore taken from an ALREADY-VERIFIED link wherever one exists — the 2026
  population carries `wikipedia_title` from its own acquisition — and where it
  does not, a name search must additionally be CONFIRMED by the article
  mentioning the player's school. A page that fails confirmation, or is a
  disambiguation page, yields NO photo and is reported as ambiguous.

  WRONG LICENCE. A photo is only shipped when its reuse terms are read from
  the file's own Wikimedia metadata and match an allow-list of free licences.
  Anything non-free, unknown, or unstated is rejected. There is no "probably
  fine" path: an unverifiable licence is treated exactly like a missing photo.

The output is small and purely descriptive — a thumbnail URL, the source page,
attribution text, and the licence with its URL. No photo influences any
analytical value; this module is display metadata only and is never read by a
model, a board, or a score.
"""

import csv
import json
import re
import urllib.parse

from data.acquire import http_get
from paths import RAW

PHOTO_DIR = RAW / "prospect_photos"
PHOTOS_FILE = PHOTO_DIR / "prospect_photos.csv"

WP_API = "https://en.wikipedia.org/w/api.php"
THROTTLE = 0.4
THUMB_SIZE = 400

FIELDS = ["prospect_id", "player_name", "school", "wikipedia_title",
          "identity_method", "status", "thumbnail_url", "source_url",
          "attribution", "license", "license_url", "reject_reason"]

# Licences whose terms permit reuse with attribution. A file whose
# LicenseShortName is not matched here is rejected — including "fair use",
# "non-free", and anything blank or unrecognised.
FREE_LICENSE_PATTERNS = (
    re.compile(r"^cc0", re.I),
    re.compile(r"^cc[ -]by([ -]sa)?([ -][\d.]+)?", re.I),
    re.compile(r"^public domain", re.I),
    re.compile(r"^pd([ -]|$)", re.I),
)

STATUS_OK = "OK"
STATUS_NO_IMAGE = "NO_IMAGE"
STATUS_AMBIGUOUS = "AMBIGUOUS_IDENTITY"
STATUS_LICENSE_REJECTED = "LICENSE_REJECTED"
STATUS_NOT_FOUND = "PAGE_NOT_FOUND"


def _api(params):
    params = dict(params)
    params.setdefault("format", "json")
    url = f"{WP_API}?{urllib.parse.urlencode(params)}"
    return json.loads(http_get(url, throttle=THROTTLE).decode("utf-8"))


def is_free_license(license_short_name):
    """True only for an explicitly recognised free licence."""
    if not license_short_name:
        return False
    name = str(license_short_name).strip()
    return any(p.match(name) for p in FREE_LICENSE_PATTERNS)


def _strip_html(text):
    return re.sub(r"<[^>]+>", "", str(text or "")).strip()


def search_title(player_name, school, throttle=THROTTLE):
    """Find a Wikipedia article for a player WITHOUT a pre-verified link.

    Returns (title, method) or (None, reason). The candidate must mention the
    player's school in its extract, which is what separates the right
    "Cameron Williams" from every other one. A disambiguation page is never
    accepted.
    """
    data = _api({"action": "query", "list": "search",
                 "srsearch": f"{player_name} basketball", "srlimit": 5})
    hits = (data.get("query") or {}).get("search") or []
    if not hits:
        return None, STATUS_NOT_FOUND

    school_key = str(school or "").lower().split("(")[0].strip()
    for hit in hits:
        title = hit["title"]
        page = _api({"action": "query", "titles": title,
                     "prop": "extracts|pageprops", "exintro": 1,
                     "explaintext": 1, "redirects": 1})
        pages = ((page.get("query") or {}).get("pages") or {})
        for _, p in pages.items():
            if "disambiguation" in (p.get("pageprops") or {}):
                continue
            extract = (p.get("extract") or "").lower()
            if not extract:
                continue
            if school_key and school_key in extract:
                return p.get("title", title), "SEARCH_CONFIRMED_BY_SCHOOL"
    return None, STATUS_AMBIGUOUS


def resolve_photo(wikipedia_title, throttle=THROTTLE):
    """Thumbnail + licence for an article's lead image.

    Returns a dict with `status`. Only STATUS_OK carries a usable photo, and
    only when the licence was read from the file's own metadata and matched
    the free-licence allow-list.
    """
    page = _api({"action": "query", "titles": wikipedia_title,
                 "prop": "pageimages", "piprop": "name|original",
                 "redirects": 1})
    pages = ((page.get("query") or {}).get("pages") or {})
    if not pages or "-1" in pages:
        return {"status": STATUS_NOT_FOUND}

    entry = next(iter(pages.values()))
    resolved_title = entry.get("title", wikipedia_title)
    filename = entry.get("pageimage")
    if not filename:
        return {"status": STATUS_NO_IMAGE, "wikipedia_title": resolved_title}

    info = _api({"action": "query", "titles": f"File:{filename}",
                 "prop": "imageinfo",
                 "iiprop": "url|extmetadata", "iiurlwidth": THUMB_SIZE})
    fpages = ((info.get("query") or {}).get("pages") or {})
    if not fpages:
        return {"status": STATUS_NO_IMAGE, "wikipedia_title": resolved_title}
    fentry = next(iter(fpages.values()))
    infos = fentry.get("imageinfo") or []
    if not infos:
        return {"status": STATUS_NO_IMAGE, "wikipedia_title": resolved_title}

    ii = infos[0]
    meta = ii.get("extmetadata") or {}
    license_name = (meta.get("LicenseShortName") or {}).get("value")
    license_url = (meta.get("LicenseUrl") or {}).get("value") or ""
    artist = _strip_html((meta.get("Artist") or {}).get("value"))
    credit = _strip_html((meta.get("Credit") or {}).get("value"))

    if not is_free_license(license_name):
        return {"status": STATUS_LICENSE_REJECTED,
                "wikipedia_title": resolved_title,
                "reject_reason": f"licence not on the free allow-list: "
                                f"{license_name!r}"}

    thumb = ii.get("thumburl") or ii.get("url")
    if not thumb:
        return {"status": STATUS_NO_IMAGE, "wikipedia_title": resolved_title}

    return {
        "status": STATUS_OK,
        "wikipedia_title": resolved_title,
        "thumbnail_url": thumb,
        "source_url": ii.get("descriptionurl")
                      or f"https://commons.wikimedia.org/wiki/File:{filename}",
        "attribution": artist or credit or "Wikimedia Commons",
        "license": str(license_name).strip(),
        "license_url": license_url,
    }


def _resolve_one(prospect_id, player_name, school, wikipedia_title):
    """Identity first, then licence. Either failing yields no photo."""
    method = "VERIFIED_POPULATION_LINK"
    title = (wikipedia_title or "").strip()
    if not title:
        title, method = search_title(player_name, school)
        if not title:
            return dict(prospect_id=prospect_id, player_name=player_name,
                       school=school, wikipedia_title="",
                       identity_method="SEARCH", status=method,
                       reject_reason="no confidently identified article")

    photo = resolve_photo(title)
    row = dict(prospect_id=prospect_id, player_name=player_name, school=school,
              wikipedia_title=photo.get("wikipedia_title", title),
              identity_method=method, status=photo["status"],
              thumbnail_url=photo.get("thumbnail_url", ""),
              source_url=photo.get("source_url", ""),
              attribution=photo.get("attribution", ""),
              license=photo.get("license", ""),
              license_url=photo.get("license_url", ""),
              reject_reason=photo.get("reject_reason", ""))
    return row


def acquire_photos(log=print):
    """Resolve portraits for the 2026 pool and the 2027 watchlist.

    Writes one row per prospect — including failures — so the coverage audit
    can distinguish "no free image exists" from "identity was ambiguous" from
    "licence rejected".
    """
    import pandas as pd

    from data.acquire import (load_manifest, manifest_record, sha256_file,
                              utcnow, write_manifest)
    from paths import rel

    targets = []

    declared = pd.read_csv(RAW / "draft_population" / "draft_declared_2026.csv")
    for r in declared.itertuples():
        pid = f"2026-{str(r.normalized_name).replace(' ', '_')}"
        title = "" if pd.isna(r.wikipedia_title) else str(r.wikipedia_title)
        targets.append((pid, r.player_name, r.college, title))

    watch_path = RAW / "draft_watchlist" / "draft_watchlist_sources_2027.csv"
    if watch_path.exists():
        from data.matching import normalize_name
        w = pd.read_csv(watch_path)
        w = w[w.is_ncaa.astype(str) == "True"]
        seen = set()
        for r in w.itertuples():
            key = normalize_name(r.player_name)
            if key in seen:
                continue
            seen.add(key)
            # 2027 identities come from media boards, not a Wikipedia parse,
            # so there is no pre-verified link — search + school confirmation.
            targets.append((f"2027-{key.replace(' ', '_')}",
                           r.player_name, r.school, ""))

    rows = []
    for i, (pid, name, school, title) in enumerate(targets, start=1):
        try:
            rows.append(_resolve_one(pid, name, school, title))
        except Exception as exc:
            rows.append(dict(prospect_id=pid, player_name=name, school=school,
                            wikipedia_title=title, identity_method="",
                            status="ERROR", reject_reason=repr(exc)))
        if i % 20 == 0:
            log(f"  {i}/{len(targets)} resolved")

    PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    with open(PHOTOS_FILE, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in sorted(rows, key=lambda r: r["prospect_id"]):
            w.writerow({k: r.get(k, "") or "" for k in FIELDS})

    by_status = {}
    for r in rows:
        by_status[r["status"]] = by_status.get(r["status"], 0) + 1
    log(f"\n  resolved {len(rows)} prospects")
    for k, v in sorted(by_status.items()):
        log(f"    {k:<22} {v}")

    records = load_manifest()
    records[rel(PHOTOS_FILE)] = manifest_record(
        source_family="wikimedia", dataset="prospect_photos", season_or_year="",
        canonical_url="https://en.wikipedia.org/w/api.php",
        local_path=rel(PHOTOS_FILE), downloaded_at_utc=utcnow(),
        file_size_bytes=PHOTOS_FILE.stat().st_size,
        sha256=sha256_file(PHOTOS_FILE), row_count=len(rows),
        license="per-file; only free licences are accepted and each row "
               "records its own licence + attribution",
        notes="display-only prospect portraits; identity verified via the "
             "population's Wikipedia link or a school-confirmed search; "
             "non-free or unverifiable licences are rejected")
    write_manifest(records)
    return by_status


def load_photos(path=PHOTOS_FILE):
    """prospect_id -> verified photo metadata, OK rows only. None if not
    acquired."""
    import pandas as pd

    if not path.exists():
        return None
    df = pd.read_csv(path).fillna("")
    return df
