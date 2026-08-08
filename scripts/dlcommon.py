"""Shared helpers for DraftLens data acquisition and validation.

Intentionally small: name normalisation, a throttled HTTP fetch, and the
source manifest. Not a framework.
"""

import csv
import hashlib
import json
import re
import time
import unicodedata
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW = DATA / "raw"
MANIFEST = DATA / "source_manifest.csv"

USER_AGENT = "DraftLens/0.1 (research project; contact: project owner)"

MANIFEST_FIELDS = [
    "source_family", "dataset", "season_or_year", "canonical_url", "local_path",
    "downloaded_at_utc", "file_size_bytes", "sha256", "row_count", "license", "notes",
]


def utcnow():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def normalize_name(s):
    """Casefold, strip accents/suffixes/punctuation. Used for cross-source joins."""
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b\.?", "", s)
    return re.sub(r"\s+", " ", re.sub(r"[^a-z ]", "", s)).strip()


def http_get(url, throttle=0.0, retries=3, timeout=120):
    """Fetch bytes with a descriptive UA, polite backoff on 429/5xx."""
    last = None
    for attempt in range(retries):
        if throttle:
            time.sleep(throttle)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            last = e
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(20 * (attempt + 1))
                continue
            raise
        except Exception as e:  # transient network
            last = e
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"GET failed after {retries} attempts: {url} ({last})")


def http_json(url, throttle=0.0):
    return json.loads(http_get(url, throttle=throttle).decode("utf-8"))


# --------------------------------------------------------------- manifest
def load_manifest():
    if not MANIFEST.exists():
        return {}
    with open(MANIFEST, newline="", encoding="utf-8") as f:
        return {r["local_path"]: r for r in csv.DictReader(f)}


def write_manifest(records):
    """records: {local_path: dict}. Sorted, deterministic output."""
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    rows = sorted(records.values(),
                  key=lambda r: (r["source_family"], r["dataset"],
                                 str(r["season_or_year"])))
    with open(MANIFEST, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=MANIFEST_FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in MANIFEST_FIELDS})


def manifest_record(**kw):
    rec = {k: "" for k in MANIFEST_FIELDS}
    rec.update(kw)
    return rec


def rel(path):
    return str(Path(path).resolve().relative_to(ROOT))
