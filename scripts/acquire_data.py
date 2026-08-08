"""Acquire hoopR static Parquet source data for DraftLens.

Downloads only the datasets the MVP needs (DATA.md §16). Raw files are
immutable: an existing file is never overwritten unless --force is given.

  python scripts/acquire_data.py --source mbb --years 2011-2026
  python scripts/acquire_data.py --source nba --years 2011-2026
  python scripts/acquire_data.py --source all --years 2011-2026

Source: sportsdataverse/hoopR-mbb-data and hoopR-nba-data, CC BY 4.0
(LICENSE.md in each repository explicitly covers data). Upstream: ESPN.
Raw files stay local and git-ignored; reproduce by re-running this script.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dlcommon import (RAW, http_get, load_manifest, manifest_record, rel,  # noqa: E402
                      sha256_file, utcnow, write_manifest)

BASE = "https://raw.githubusercontent.com/sportsdataverse"

# dataset -> (repo, repo_path, filename_stem)
PLAN = {
    "mbb": {
        "player_core": ("hoopR-mbb-data", "mbb/player_core/parquet", "player_core"),
        "player_box": ("hoopR-mbb-data", "mbb/player_box/parquet", "player_box"),
        "shots": ("hoopR-mbb-data", "mbb/shots/parquet", "shots"),
    },
    "nba": {
        "player_season_stats": ("hoopR-nba-data", "nba/player_season_stats/parquet",
                                "player_season_stats"),
    },
}

DEST = {"mbb": RAW / "hoopr_mbb", "nba": RAW / "hoopr_nba"}
LICENSE = "CC BY 4.0 (sportsdataverse; LICENSE.md covers data). Upstream: ESPN."


def parse_years(spec):
    out = set()
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-")
            out.update(range(int(a), int(b) + 1))
        elif part:
            out.add(int(part))
    return sorted(out)


def acquire(source, years, force=False):
    records = load_manifest()
    n_new = n_skip = 0
    total_bytes = 0
    for dataset, (repo, repo_path, stem) in PLAN[source].items():
        outdir = DEST[source] / dataset
        outdir.mkdir(parents=True, exist_ok=True)
        for year in years:
            fname = f"{stem}_{year}.parquet"
            url = f"{BASE}/{repo}/main/{repo_path}/{fname}"
            dest = outdir / fname
            if dest.exists() and not force:
                n_skip += 1
                total_bytes += dest.stat().st_size
                continue
            try:
                blob = http_get(url, throttle=0.3)
            except Exception as e:
                print(f"  FAIL {dataset} {year}: {e}")
                continue
            dest.write_bytes(blob)
            size = dest.stat().st_size
            total_bytes += size
            n_new += 1
            records[rel(dest)] = manifest_record(
                source_family=f"hoopR-{source}", dataset=dataset, season_or_year=year,
                canonical_url=url, local_path=rel(dest), downloaded_at_utc=utcnow(),
                file_size_bytes=size, sha256=sha256_file(dest), license=LICENSE,
                notes="raw; immutable; git-ignored")
            print(f"  got  {dataset:<20} {year}  {size/1024/1024:7.2f} MB")
    write_manifest(records)
    print(f"\n{source}: {n_new} downloaded, {n_skip} already present, "
          f"{total_bytes/1024/1024:.1f} MB on disk")
    return n_new, n_skip


def main():
    ap = argparse.ArgumentParser(description="Acquire hoopR source data.")
    ap.add_argument("--source", choices=["mbb", "nba", "all"], required=True)
    ap.add_argument("--years", default="2011-2026",
                    help="e.g. 2011-2026 or 2011,2015,2020")
    ap.add_argument("--force", action="store_true",
                    help="re-download and overwrite existing raw files")
    a = ap.parse_args()

    years = parse_years(a.years)
    sources = ["mbb", "nba"] if a.source == "all" else [a.source]
    print(f"years {years[0]}-{years[-1]} ({len(years)}) | sources {sources}")
    for s in sources:
        print(f"\n== {s} ==")
        acquire(s, years, force=a.force)


if __name__ == "__main__":
    main()
