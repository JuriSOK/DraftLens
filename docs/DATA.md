# DraftLens — Data

What DraftLens is built on, where it comes from, and where it is known to be
weak. This is the current, final state of the data layer — the exploratory
source evaluation that preceded it lives in git history, not here.

## 1. Sources

| Source | What it provides | License |
| --- | --- | --- |
| [hoopR-mbb-data](https://github.com/sportsdataverse/hoopR-mbb-data) (sportsdataverse, upstream ESPN) | NCAA men's basketball box scores and shot events, 2011–2026 | CC BY 4.0 |
| [hoopR-nba-data](https://github.com/sportsdataverse/hoopR-nba-data) (sportsdataverse, upstream ESPN) | NBA player season statistics, 2011–2026 | CC BY 4.0 |
| English Wikipedia "`<year>` NBA draft" articles | Declared early entrants, draft results, college affiliation | CC BY-SA 4.0 (attribution required) |
| Wikidata | Date of birth, display-only | CC0 1.0 |

All four are public, unauthenticated, and fetched by `scripts/acquire.py`
(`src/data/hoopr.py`, `src/data/wikipedia.py`, `src/data/wikidata.py`). Every
acquired file is recorded in `data/source_manifest.csv` with its URL,
timestamp, size and SHA-256, and raw data is never edited in place — a
changed checksum means the record no longer rests on what was downloaded
(`src/data/acquire.py:validate_raw`).

## 2. Seasons

2011–2026. **2014–2025 is the development window; 2011–2013 is a robustness
check only, never used for a selection decision; 2026 is a sealed holdout.**

## 3. The NCAA prospect population

The population is **final NCAA early entrants only** — never "every drafted
NCAA player." Automatically-eligible players (mainly seniors) appear on no
pre-draft list, so they become identifiable only once drafted; including them
would let post-draft information decide who is even in the sample. Under an
earlier, superseded population rule, 212 of 212 non-early-entrants were
drafted — 100%, which is exactly the leak this rule closes. Declared early
entrants are published roughly a week before the draft, so membership is
genuinely pre-draft information.

Population counts (final NCAA early entrants, matched against `hoopr_position`
etc.):

| Partition | Rows | Drafted | Undrafted |
| --- | --- | --- | --- |
| Development (2014–2025) | 887 | 431 | 456 |
| Robustness (2011–2013) | 125 | 85 | 40 |
| 2026 holdout | 26 | sealed — never opened | — |

8 development prospects have no matched hoopR statistics (all undrafted) and
are retained with null features rather than dropped — dropping them would
selectively remove negatives and inflate every downstream metric.

**Declared vs final entrants (2026 product only).** The ML sampling frame
above (`data.population.load_population`) is always the FINAL population —
after the withdrawal deadline. For the 2026 product's All Declared board,
`data.population.load_declared`/`population_status` additionally read the
ORIGINAL declared pool (before withdrawal), acquired separately via
`scripts/acquire.py declared` from one fixed Wikipedia revision capturing the
NBA's official initial early-entry announcement — never a mock draft,
recruiting ranking, or "live" scrape. This is product/display metadata only;
it never changes the ML sampling frame or feeds a model. See
`docs/VALIDATION.md` §"2026 all-declared product board".

## 4. NCAA statistics available

Per-season box score totals (points, rebounds, assists, steals, blocks,
turnovers, fouls, shooting splits, minutes, games played/started), aggregated
over every team a prospect played for that season with `n_teams` retained as
metadata. Team and opponent context (for usage%, assist%, rebound%, steal%,
block%) is reconstructed from `player_box` by game, summed over only the
prospect's **played** games — never a whole-season team total, so a
mid-season transfer or an injury-shortened season doesn't inherit context from
games the prospect wasn't part of. Reconstructed team minutes measure 201.4
per game against a theoretical 200, confirming the reconstruction is sound.

Shot style comes from the play-by-play shot file, categorized into
`layup` / `dunk` / `tip` / `three_point` via `type_text` and `score_value` —
never from shot coordinates, which carry ±2.1×10⁸ int32 sentinel
contamination. The shot file holds **made** free throws only, so every
free-throw metric is sourced from `player_box` instead.

## 5. NBA statistics available

`player_season_stats` in **long format** (one row per stat per player-season):
`averages` / `miscellaneous` / `totals` categories, with made–attempted pairs
(e.g. `fieldGoalsMade-fieldGoalsAttempted`) carrying a null numeric `value`
that must be parsed from the `display_value` string (`"247-538"`). Verified
100% parseable across the audited season. No shot-location data. Reference
window for the NBA comparables system is 2021–2025, rotation-filtered
(≥750 minutes, ≥30 games); 2026 is excluded from the reference exactly as it
is from every other reference.

## 6. Identity resolution

There is no shared identifier between Wikipedia (population, draft results)
and hoopR (statistics) — prospects are matched on normalized name plus school.
Three distinct name keys exist and are not interchangeable:

- **`normalize_name`** — the canonical identity key, written once into the raw
  population CSVs. Frozen: changing it would invalidate every
  `canonical_prospect_id` already on disk.
- **`match_key`** — matching-only, with two general corrections over
  `normalize_name` (suffixes stripped only at the end so a leading initial
  like "V." survives; leading single-letter tokens merged so "T. J. Warren"
  matches "TJ Warren"). Never persisted as identity.
- **`norm_school`** — disambiguates same-name players by program.

An ambiguous match is left `UNMATCHED` rather than forced — a wrong match
would silently attach one player's statistics to another, and match failures
concentrate in the undrafted class, so a forced match would be a leakage risk
as much as an accuracy one. Every exception is either a general rule in code
or an explicitly reviewed row in `config/identity_overrides.csv` — no
player-specific branches in code. Unmatched prospects stay in the population
with null statistics; they are never dropped.

## 7. Major source hazards

- **Date of birth is outcome-correlated in its availability, not its values.**
  Measured coverage: 100% for drafted prospects, 69% for undrafted. A
  missingness indicator for DOB would be close to the single most
  target-predictive column in the dataset while carrying zero basketball
  information. DOB is excluded entirely from modelling and used only for
  Wikidata display enrichment.
- **The Wikipedia position/class label is dual-sourced by outcome.** The
  population is built from draft picks first (fine `PG`/`SG`/`SF`/`PF`/`C`
  labels, from the draft results table), then remaining early entrants are
  added from the early-entrant list (broad `G`/`F` labels only). Measured:
  `position_from_population` resolves to a five-position label for 100% of
  drafted prospects (431/431) versus 7.7% of undrafted (35/456);
  `class_from_population` shows a 26.5-point coverage gap and an
  outcome-specific vocabulary. Both fields, plus `match_method` and
  `match_confidence` (every `UNMATCHED` prospect is undrafted), are on the
  model deny list.
- **The hoopR shot-type vocabulary breaks at the 2020/21 season boundary.**
  `Three Point Jump Shot` is its own category through 2020 and folds into
  `JumpShot` from 2021 on, roughly doubling `JumpShot` share mid-window.
  Generic `jump_shot_*` features are permanently excluded; shot profile is
  built from the stable `layup` / `dunk` / `tip` / `three_point` categories
  only.
- **`athlete_id` dtype differs by hoopR file** — `player_core` stores int64,
  `player_box` and `shots` store float64. Casting straight to string produces
  `"5142718"` vs `"5142718.0"` and a silent 0% join; every join goes through
  a shared `to_int_id` helper instead.

## 8. Leakage-critical exclusions

Enforced centrally in `src/validation.py` (`DENY_EXACT`, `DENY_SUBSTRING` for
the feature-file policy; `DENIED`, `DENIED_SUBSTR` for the model-input
policy), asserted on every dataset build and covered by dedicated tests:

- No draft outcome (`drafted`, `pick`, `round`, `drafting_team`) in the
  feature file at all.
- No age, date of birth, or age-derived field.
- No `position_from_population` / `class_from_population` / `match_method` /
  `match_confidence` (§7).
- No external analyst input — mock drafts, consensus boards, analyst ranks —
  as a feature; they may only ever be an external benchmark.
- No generic `jump_shot_*` feature (§7).
- No NBA statistic reaches a pre-draft feature (the NBA corpus is read only
  by the comparables system, on the output side, never joined into
  prospect features).

## 9. Reproducibility

```bash
pip install -e .
python scripts/acquire.py mbb --years 2011-2026
python scripts/acquire.py nba --years 2011-2026
python scripts/acquire.py population --years 2011-2026 --wikidata
python scripts/build.py
python scripts/validate.py
```

Raw data (~200 MB) is git-ignored but fully reproducible from the commands
above; every published number is regenerated and checked against tight
tolerances by `tests/integration/test_frozen_anchors.py`.

## 10. Data limitations

- **No athleticism measurement exists in any source.** DraftLens does not
  score athleticism and refuses a request for it rather than substituting a
  box-score proxy like dunk rate.
- **No leakage-safe fine-grained (PG/SG/SF/PF/C) position source exists
  pre-draft.** The only fine label available is the outcome-contaminated
  Wikipedia one (§7); the analytical position is the coarse `G`/`F`/`C`
  scheme derived from hoopR's `hoopr_position`, covering 98.0% of the
  development population.
- **No shot-location data is usable** — coordinates are contaminated, so
  DraftLens has no rim-distance or shot-chart signal, only made/attempted
  style categories.
- **No Combine measurement data (height/weight beyond hoopR's box roster
  figures, wingspan, vertical, sprint/agility times) is used.** It was never
  integrated; a future phase could add it as a clearly-labelled, separately
  sourced enrichment.
- **NBA comparables have no shot-location or NBA size data either** —
  resemblance is statistical role/style only, from `player_season_stats`.
