# DraftLens — ML-0 Report: model-ready dataset construction and leakage audit

**Status:** Complete — all gates passed. **No model was trained.**
**Date:** 2026-08-08 · **Phase:** ML-0, corrected by ML-0.1 ([ML_SPEC.md](../ML_SPEC.md) §27)

> ## ⚠️ ML-0.1 correction — the original ML-0 counts were NOT authoritative
>
> ML-0 reported **829 / 403 / 426** for the development window. **Those numbers were produced by a defective NCAA classifier and are superseded.** The parser decided NCAA membership by testing for the phrase `men's basketball` in a Wikipedia link target, which failed in three ways:
>
> 1. **False positives.** Foreign clubs and even a *league* are titled with that phrase as a parenthetical disambiguator — `Beşiktaş J.K. (men's basketball)`, `CSM Constanța (men's basketball)`, `Galatasaray S.K. (men's basketball)`, `Liga Națională (men's basketball)`.
> 2. **False negatives — much larger.** Many NCAA programs canonicalise *without* the "men's" infix (`Georgia Bulldogs basketball`) or are reached by redirect (`LSU Tigers basketball` → `LSU Tigers men's basketball`). **67 NCAA early entrants were silently missing**, including Ben Simmons, Anthony Edwards, Cade Cunningham, Marcus Smart, Tobias Harris and Jarrett Culver.
> 3. **Target mislabelling.** Because a drafted player's *draft-row* school link was also classified this way, drafted early entrants whose school went unrecognised were recorded as **undrafted**. **11 targets were wrong**, including **Anthony Bennett — the No. 1 overall pick of 2013.**
>
> Correctness takes priority over a previously published count. The corrected figures below are authoritative. Section 8 of this report retains the original ML-0 audit results for transparency where they are unchanged.

Companion documents: [ML_SPEC.md](../ML_SPEC.md) (methodology), [DATA.md](../DATA.md) (sources and raw-data audits), [DECISIONS.md](../DECISIONS.md). This report does not repeat them.

---

## 1. Purpose

Build a clean, reproducible, temporally correct analytical dataset from the approved raw sources: one row per NCAA early-entry prospect per draft year, with features and targets kept in physically separate files, plus a leakage audit.

**ML-0 computes primitives only.** No percentages, rates, per-40, per-100, scaling, normalisation, imputation, or scores — those belong to ML-2 and later (ML_SPEC §26, §27).

## 2. Population definition

**Final NCAA early entrants only** (DEC-049). Automatically-eligible players — principally seniors — are excluded because they are identifiable only once drafted, so their population membership would carry post-draft information ([DATA.md](../DATA.md) §24.5 measured 212 of 212 such players as drafted).

The raw union population remains intact in `data/raw/draft_population/`; ML-0 reads a subset of it.

## 3. Development window and partitions

| Partition | Draft years | Rows | Drafted | Undrafted | Role |
| --- | --- | --: | --: | --: | --- |
| **`2014_2025`** | 2014–2025 | **887** | **431** | **456** | Main development |
| `2011_2013` | 2011–2013 | **125** | 85 | 40 | Robustness only — not default training |
| **`2026`** | 2026 | **26** | 25 | 1 | **Final holdout** |

All three partition counts are **hard gates** in the build and are re-asserted by the validator and the test suite. All passed.

## 4. Holdout policy

2026 is written to separate files (`features_2026.parquet`, `targets_2026.parquet`) so loading it is an intentional act, never an accident of a `split` column filter.

ML-0 verified only row count, schema, feature availability, and identity matching for 2026. **No relationship between 2026 features and 2026 outcomes was inspected**, and no methodological choice in this phase used 2026 in any way.

## 5. Identity matching

Prospects come from the Wikipedia early-entrant population; statistics come from hoopR. The join is deterministic name + school, never name alone where ambiguity exists.

| Tier | Rule |
| --- | --- |
| `OVERRIDE` | Version-controlled exception in [`config/data/identity_overrides.csv`](../../config/data/identity_overrides.csv) |
| `NORMALIZED_EXACT` | `match_key` unique within the season |
| `DISAMBIGUATED` | Multiple name candidates, resolved uniquely by school |
| `SURNAME_SCHOOL_PREFIX` | Same surname + same school + one first name a prefix of the other, unique |
| `AMBIGUOUS` / `UNMATCHED` | **Never forced** — left null and reported |

### Match results

| Partition | Matched | Rate | Unmatched | Ambiguous |
| --- | --: | --: | --: | --: |
| 2014–2025 | 879 / 887 | **99.10%** | 7 | 1 |
| 2011–2013 | 118 / 125 | 94.40% | 6 | 1 |
| **2026** | **26 / 26** | **100.00%** | 0 | 0 |

Per year (2014–2025): 2014 41/41 · 2015 44/44 · 2016 51/52 · 2017 61/61 · 2018 70/72 · 2019 76/76 · 2020 65/65 · 2021 186/188 · 2022 131/132 · 2023 79/79 · 2024 47/49 · 2025 28/28.

### Two general normalisation fixes (not player-specific hacks)

Both were found by inspecting unmatched cases and both raised the match rate materially:

1. **Spaced initials.** Wikipedia writes `T. J. Warren`; ESPN writes `TJ Warren`. `match_key` merges leading single-letter tokens. This alone took 2014–2025 from 95.66% to 98.43% (pre-correction basis).
2. **Suffix stripping was too greedy.** `dlcommon.normalize_name` strips `jr|sr|ii|iii|iv|v` *anywhere*, so the leading initial in `V. J. Edgecombe` was consumed as the Roman numeral V. `match_key` strips suffixes only at the end.

Also added: transliteration of letters NFKD does not decompose (`ø æ å ß ł đ ð þ ı`), which recovered `Asbjørn Midtgaard`.

`match_key` is **matching-only**. The canonical `normalized_name` written by the acquisition script is untouched, so `canonical_prospect_id` stays stable and raw files remain valid.

### Manual overrides — 3 entries

Stored transparently in [`config/data/identity_overrides.csv`](../../config/data/identity_overrides.csv) with school evidence and a reason, never hidden in code:

| Year | Wikipedia | hoopR | Reason |
| --- | --- | --- | --- |
| 2022 | Adrian Griffin Jr. | AJ Griffin | Legal name vs nickname; surname+school unique at Duke |
| 2022 | Nate Williams | Jeenathan Williams | Nickname vs legal name; surname+school unique at Buffalo |
| 2024 | Bub Carrington | Carlton Carrington | Nickname vs legal name; surname+school unique at Pittsburgh |

### The 8 unresolved in 2014–2025 — diagnosed, not guessed

| Diagnosis | Players |
| --- | --- |
| School outside hoopR D-I coverage | Trevor Hudgins (2022, Northwest Missouri State — D-II) |
| No surname match at that school — most plausibly did not play that season | Jordan Hare (2016), Marquez Letcher-Ellis (2018), **Mitchell Robinson** (2018, enrolled at Western Kentucky but never played a college game), Sam Cunliffe (2021), Brandon Williams (2021), Deshawndre Washington (2024) |
| Ambiguous — multiple candidates, not forced | Isaiah Crawford (2024, Louisiana Tech) |

No match was invented. These 8 rows exist in the dataset with null statistics and are visible via `match_method`. The three foreign/non-D-I records that previously appeared here are gone: they are no longer in the population at all (ML-0.1).

## 6. Aggregation rules

**Season alignment.** A prospect entering draft year *Y* uses hoopR NCAA season *Y* (the season ending in *Y*). Enforced by assertion; **0 mismatches** across all 1,038 rows. Never *Y+1*.

**Transfers.** A prospect's draft-year record is their **total production across every NCAA team played for that season** — one row per prospect, never duplicated by a mid-season team change. `n_teams` is retained as metadata and `primary_school` (last team by game date) is kept for identity. **4 multi-team prospects** across 2011–2026; the policy is unit-tested.

**Duplicate game rows.** Exact duplicate `(athlete_id, game_id)` rows are dropped before summing so statistics are never double-counted. **4 rows removed** (3 in 2017, 1 in 2021). Reported per year in `quality_report.json`.

**Did-not-play rows** are excluded from `games_played` and from all stat sums. `games_started` comes from the `starter` flag and is asserted ≤ `games_played`.

## 7. Primitive feature schema — 58 columns

**Identity / context (11):** `canonical_prospect_id`, `draft_year`, `player_name`, `normalized_name`, `college`, `position_from_population`, `class_from_population`, `wikipedia_title`, `hoopr_athlete_id`, `match_method`, `match_confidence`

**Box-score primitives (18):** `games_played`, `games_started`, `minutes`, `points`, `field_goals_made/attempted`, `three_points_made/attempted`, `free_throws_made/attempted`, `offensive_rebounds`, `defensive_rebounds`, `total_rebounds`, `assists`, `turnovers`, `steals`, `blocks`, `personal_fouls`

**Derived arithmetic primitives (2):** `two_points_made` = FGM − 3PM, `two_points_attempted` = FGA − 3PA. Identity-preserving only; validated for `made ≤ attempted` and non-negativity.

**Shot-style primitives (20):** `shot_records`, `fg_attempts_shotfile`, `fg_makes_shotfile`, `three_point_shot_attempts/makes`, `assisted_made_field_goals`, `unassisted_made_field_goals`, and attempts/makes for `jump_shot`, `layup`, `dunk`, `tip`, plus `assisted_/unassisted_` splits for layups and dunks.

**Physical / context (4):** `hoopr_position`, `height`, `weight`, `experience_years`
**Aggregation metadata (3):** `n_teams`, `primary_school`, `ncaa_season`
**Temporal metadata (1):** `covid_era_flag` — metadata for 2021/2022, **not** intended as a model feature (ML_SPEC §4.4)

### Two shot-file hazards respected

- **Free throws are never taken from `shots`.** The file contains only *made* free throws ([DATA.md](../DATA.md) §22.3), so FT comes exclusively from `player_box`. Unit-tested.
- **Coordinates are never used.** They carry ±2.1×10⁸ int32 sentinels. Three-pointers are identified by `score_value == 3`, which is populated for makes *and* misses, so shot style is derived without touching coordinates. Unit-tested.

### Position labels — a discrepancy worth noting

hoopR `position_abbreviation` is coarse: **G / F / C / ATH / NA** — not the five DraftLens positions (DEC-009). The Wikipedia population field `position_from_population` does carry finer labels (`SG`, `SF/PF`, …). Both are retained raw; **no mapping was chosen** (ML_SPEC §9.1 leaves it open). ML-1 must decide, and should note that a PG/SG/SF/PF/C split cannot come from hoopR alone.

## 8. Leakage audit

### Column deny-list — **PASS, zero violations in all three partitions**

Asserted absent from every feature file: `drafted`, `pick`, `round`, `drafting_team`, `early_entrant`, `population_source`, `date_of_birth`, `age`, `current_age`, DOB-missingness indicators, NBA identifiers or statistics, mock/consensus/analyst ranks, green-room invitations, and any post-draft derived value. Substring rules cover `nba_`, `mock`, `consensus`, `analyst`, `outcome`, `post_draft`.

Suspicious-name scan (`draft`, `nba`, `pick`, `round`, `rank`, `future`, `outcome`, `target`) flagged **0 columns** for review beyond the reviewed-and-allowed `draft_year`.

### Sampling-frame leakage — **removed**

Every row is a final NCAA early entrant, so the union-population leak is gone by construction. `early_entrant` is constant within the population and is deliberately **not** written to the feature file.

### Temporal audit — **PASS**

`ncaa_season == draft_year` on every row with statistics; **0 mismatches**; no partition contains draft years outside its range; no future season is reachable.

### Feature / target separation — **PASS**

Physically separate files. Targets contain exactly `canonical_prospect_id`, `draft_year`, `drafted`, `pick`, `round` — `drafting_team`, `population_source` and `early_entrant` are excluded. Keys align exactly in both directions for all partitions. Development and holdout key sets are disjoint.

## 9. Missingness

No imputation was performed and **no missingness indicators were created**.

| Field group | Missing (2014–2025) | % |
| --- | --: | --: |
| All box-score primitives, shot primitives, `two_points_*` | 19 / 887 | **2.14** |
| `experience_years` | 33 / 887 | 3.72 |
| `height`, `weight` | 14 / 887 | 1.58 |
| `hoopr_position` | 13 / 887 | 1.47 |

Missingness is dominated by the 8 unresolved prospects plus a small number matched to hoopR but with no box rows that season.

### Drafted-vs-undrafted coverage — the second leakage channel checked

| Field group | Drafted | Undrafted | Gap |
| --- | --: | --: | --: |
| All box-score and shot primitives | 99.30% | 96.49% | **+2.8 pp** |
| `height`, `weight` | 99.53% | 97.15% | +2.4 pp |
| `experience_years` | 97.45% | 94.96% | +2.5 pp |

**The maximum gap is 2.8 pp.** For contrast, the DOB gap that caused age to be excluded was **31 pp** ([DATA.md](../DATA.md) §23.4). The direction is expected and benign — undrafted early entrants are somewhat likelier to be non-D-I or not to have played — and the magnitude is an order of magnitude smaller. **No field is excluded on this basis**, but ML-1 should re-check after any feature filtering.

2026 missingness was profiled by field only; **it was not analysed by outcome**.

## 10. Year-level quality (2014–2025)

Per-year prospects / matched / duplicate rows removed / multi-team, plus drafted-undrafted counts, box and shot coverage, position/height/weight coverage, and median games and minutes, are written to `data/interim/ml0/quality_report.json`.

Notable: **2021 (188 prospects) and 2022 (132)** are the COVID cohorts and together are 36% of the development window; **2025 has 28 prospects with only 2 undrafted**, and the **2026 holdout now has just 1 undrafted prospect**. Both are flagged in ML_SPEC §4.3–§4.4 and are retained, not removed.

## 11. Known limitations

1. **8 unresolved prospects (0.90%) in the development window** (7 unmatched + 1 ambiguous), diagnosed in §5. They carry null statistics.
2. ~~Two non-NCAA players in the population~~ — **fixed in ML-0.1**. Three records were removed: Alperen Şengün (Beşiktaş, 2021), Cezar Unitu (CSM Constanța, 2024) and Jacob Ledoux (UT Permian Basin, 2019 — a D-II athletics page, not an NCAA D-I basketball program). See the correction notice above.
3. **The 2026 holdout has only 1 undrafted prospect** (25 drafted of 26). This is a genuine population fact, not a defect, but it means the replay can demonstrate almost nothing about undrafted discrimination. Flagged for ML-1.
4. **hoopR positions are G/F/C only**, not the five DraftLens positions (§7).
5. Shot coordinates remain unusable; only `type_text` and `score_value` are used.
6. `experience_years` is retained as a context candidate and has **not** been leakage-cleared for modelling use.
7. 2011–2013 match rate (94.40%) is lower than 2014–2025, consistent with the thinner ESPN coverage before the 2014 break.

## 12. ML-1 readiness

**Ready.** All population gates, leakage assertions, temporal assertions, validation checks (0 failures, 0 warnings) and 30 unit tests pass.

Open items ML-1 must address:

- Decide the position mapping given hoopR's G/F/C limitation (§7).
- Re-run the leakage audit on the engineered feature set, not just primitives.
- Decide whether `covid_era_flag`, `n_teams`, and `experience_years` are metadata or candidate features.
- Decide how to present the 2026 holdout given its single undrafted prospect (§11.3).

**Reproduce with:**

```bash
./.venv/bin/python scripts/build_dataset.py       # writes data/interim/ml0/
./.venv/bin/python scripts/experiments/validate_ml0_dataset.py
./.venv/bin/python -m unittest discover -s tests
```

Generated outputs total ~416 KB and are git-ignored; the scripts and the override file are committed.
