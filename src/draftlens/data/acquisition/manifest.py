"""The source manifest — provenance for every acquired raw file.

Records where a file came from, when, how large it was and its SHA-256, so a
reviewer can confirm the raw corpus was not silently edited. Raw data is
immutable (CLAUDE.md rule 12); the manifest is how that is checked.
"""

import csv
import hashlib
from datetime import datetime, timezone

from draftlens.paths import MANIFEST, rel  # noqa: F401  (rel re-exported)

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
