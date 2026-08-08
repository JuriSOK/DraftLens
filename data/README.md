# DraftLens — Data Directory

Source data is **acquired locally, never committed**. Reproducibility comes from the acquisition scripts plus [`source_manifest.csv`](source_manifest.csv), not from redistributing source files (DEC-047).

## Acquiring the data

```bash
# one-time environment (DEC-037: pandas + pyarrow only)
python3 -m venv .venv && ./.venv/bin/python -m pip install pandas pyarrow

# NCAA (hoopR MBB) and NBA (hoopR NBA) Parquet, 2011-2026  — ~192 MB
./.venv/bin/python scripts/acquire_data.py --source all --years 2011-2026

# Wikipedia prospect population + draft targets, and 2026 Wikidata DOB
./.venv/bin/python scripts/acquire_draft_population.py --years 2011-2026 --wikidata

# verify everything (structure, coverage, checksums, firewall, ID stability)
./.venv/bin/python scripts/validate_raw_data.py
```

Acquisition is idempotent: an existing raw file is **never overwritten** unless `--force` is passed.

## Directory convention

### `raw/` — immutable source data

```
raw/
├── hoopr_mbb/            NCAA — sportsdataverse/hoopR-mbb-data (CC BY 4.0, upstream ESPN)
│   ├── player_core/      player_core_YYYY.parquet    2011-2026  bios, position, height, weight
│   ├── player_box/       player_box_YYYY.parquet     2011-2026  game-level box scores
│   └── shots/            shots_YYYY.parquet          2011-2026  shot-level records
├── hoopr_nba/            NBA — sportsdataverse/hoopR-nba-data (CC BY 4.0, upstream ESPN)
│   └── player_season_stats/  player_season_stats_YYYY.parquet  2011-2026  (long format)
├── draft_population/     PRE-DRAFT identity — Wikipedia (CC BY-SA 4.0)
├── draft_targets/        DRAFT OUTCOMES — Wikipedia (CC BY-SA 4.0)
└── wikidata/             P569 date of birth, 2026 only (CC0 1.0)
```

Files here are **never modified in place**. If a source file is wrong or needs cleaning, the fix belongs in a transformation script writing to `interim/` — not in an edit to the raw file. `validate_raw_data.py` compares every file's SHA-256 against the manifest and fails if a raw file changed after acquisition.

### `interim/`
Intermediate transformed data: cleaned, parsed, joined, or reshaped steps along the way.

### `processed/`
Model-ready or application-ready derived datasets.

## ⚠️ Feature / target firewall

`draft_population/` and `draft_targets/` are **deliberately separate directories** and must never be merged into one convenient file before the feature-generation boundary (DATA.md §11, §24.8).

- **`draft_population/`** — pre-draft identity only: name, college, position, class, `early_entrant`, `population_source`, `wikipedia_title`.
- **`draft_targets/`** — outcomes only: `drafted`, `pick`, `round`, `drafting_team`.

`validate_raw_data.py` asserts that no outcome column ever appears in a population file.

**Two population fields are prohibited as model features** (DEC-041): `early_entrant` and `population_source`. Across 2011–2026, 212 of 212 non-early-entrants were drafted, so `early_entrant = False` predicts the target with certainty. They are provenance metadata, not inputs.

**Date of birth is display-only** (DEC-044). It lives in `wikidata/`, never in a feature file, and must not enter General Draft Board historical features — including as a missingness indicator.

## Source manifest

[`source_manifest.csv`](source_manifest.csv) is the one data file that **is** committed. One row per acquired file:

`source_family, dataset, season_or_year, canonical_url, local_path, downloaded_at_utc, file_size_bytes, sha256, row_count, license, notes`

It is the reproducibility contract: it records exactly what was downloaded, from where, when, and under which licence.

## Rules

- **Do not commit raw data.** `.gitignore` excludes `data/**` except this README, the manifest, and `.gitkeep` markers. Verify with `git check-ignore` before committing.
- **Do not modify raw source data.** Treat `raw/` as read-only.
- **Do not commit licensed or restricted datasets.** Licensing must be checked before any data enters version control.
- **Transformations must be reproducible** from `raw/` by a script in [`../scripts/`](../scripts/).
- **Do not fabricate missing data.** Missing values may only be filled by an explicitly documented and approved method (DEC-017).

## Licences and attribution

| Source | Licence | Obligation |
| --- | --- | --- |
| sportsdataverse hoopR (MBB, NBA) | CC BY 4.0 — `LICENSE.md` explicitly covers data | Attribution; upstream ESPN rights not independently reviewed |
| English Wikipedia | CC BY-SA 4.0 | Attribution **and** share-alike on any published derived table |
| Wikidata structured data | CC0 1.0 | None required; attribution as good practice |

## Current coverage

2011–2026 acquired and validated: 168,461 NCAA player-season rows, 2,857,536 player-game rows, 12,724,485 shots, 8,342 NBA player-seasons, and 1,186 reconstructed draft prospects. See [DATA.md](../docs/DATA.md) §24 for the full quality profile.
