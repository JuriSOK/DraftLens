# DraftLens — ML-1 Report: exploratory analysis, leakage and stability audit

**Status:** Complete. **No model was trained.**
**Date:** 2026-08-08 · **Phase:** ML-1 ([ML_SPEC.md](ML_SPEC.md) §27)
**Reproduce:** `./.venv/bin/python scripts/run_ml1_eda.py` → `data/interim/ml1/`

Companion documents: [ML_SPEC.md](ML_SPEC.md), [ML0_REPORT.md](ML0_REPORT.md), [DATA.md](DATA.md), [DECISIONS.md](DECISIONS.md).

---

## 1. Executive summary

The corrected ML-0.1 population is confirmed and structurally sound: **887 / 431 / 456** development, **125 / 85 / 40** robustness, **26** holdout. Fourteen basketball-identity checks found **zero impossible values**, target association is unremarkable (max rank-AUC **0.687**), and pick association is weak (max |ρ| **0.216**) — no primitive behaves like a hidden outcome.

**Three findings change what ML-2 may do.**

🔴 **1. A severe leakage channel was found and removed.** `position_from_population` resolves to a five-position label for **100% of drafted (431/431)** but only **7.7% of undrafted (35/456)**. The cause is structural: ML-0 built the population from draft picks first, taking position from the **draft results table** (fine `PG`/`SG`/`SF`/`PF`/`C` labels), then added remaining early entrants from the **early-entrant list** (broad `G`/`F`). The *granularity of the label* therefore encodes the outcome. `class_from_population` shares the defect (**26.5 pp** availability gap plus an outcome-specific vocabulary — `graduate`, `redshirt` appear only for undrafted). Both, plus `match_method`/`match_confidence`, are now on the ML-0 deny list and removed from feature files (DEC-065). A model trained before this fix would have looked excellent for entirely spurious reasons.

🔴 **2. The five-position product scheme has no leakage-safe source.** The only fine-grained pre-draft label is the contaminated one. hoopR's `hoopr_position` is clean and balanced but coarse — **G / F / C at 98.0% coverage**. **DEC-009's PG/SG/SF/PF/C requirement cannot currently be met.** Canonical mapping is implemented for the coarse scheme and *deferred* for the five-position scheme.

🔴 **3. The shot-type vocabulary is not stable across the window.** `Three Point Jump Shot` is a distinct `type_text` category through 2020 and is folded into `JumpShot` from 2021. Consequently `jump_shot_attempts`/`jump_shot_makes` are **not comparable across the 2020/2021 boundary** — median jump-shot attempts jump 81 → 235. `three_point_shot_*` is unaffected because it derives from `score_value`, not `type_text`.

**Verdict: ML-2 may proceed**, provided it respects these three findings. Nothing here blocks feature engineering; two things constrain it.

## 2. Population and class balance

Gates re-confirmed: development **887 (431 drafted / 456 undrafted)**, robustness **125 (85 / 40)**.

| Year | Prospects | Drafted | Undrafted | Drafted % | Matched | Med. games | Med. minutes |
| --- | --: | --: | --: | --: | --: | --: | --: |
| 2014 | 41 | 28 | 13 | 68.3 | 41 | 35 | 1092 |
| 2015 | 44 | 27 | 17 | 61.4 | 44 | 35 | 1057 |
| 2016 | 52 | 27 | 25 | 51.9 | 51 | 33 | 960 |
| 2017 | 61 | 37 | 24 | 60.7 | 61 | 34 | 1008 |
| 2018 | 72 | 39 | 33 | 54.2 | 70 | 33 | 995 |
| 2019 | 76 | 40 | 36 | 52.6 | 76 | 34 | 1063 |
| 2020 | 65 | 40 | 25 | 61.5 | 65 | 31 | 963 |
| **2021** | **188** | 50 | **138** | **26.6** | 186 | **25** | **762** |
| **2022** | 132 | 43 | 89 | **32.6** | 131 | 33 | 1008 |
| 2023 | 79 | 41 | 38 | 51.9 | 79 | 34 | 1026 |
| 2024 | 49 | 33 | 16 | 67.3 | 47 | 34 | 1022 |
| **2025** | 28 | 26 | **2** | **92.9** | 28 | 33 | 969 |

**Drafted rate ranges 26.6% → 92.9% — a 66.3 pp spread**, median 57.5%. The window is nearly balanced in aggregate (48.6%) but no single year resembles the aggregate.

**Weakest evaluation years:** **2025 (2 undrafted)** makes fold-7 Stage A metrics statistically meaningless. 2024 (16 undrafted) is thin. 2021 (138 undrafted of 188) dominates any pooled fit. No year was removed and no weights were created — ML-3/ML-4 must handle this.

## 3. Position audit

### hoopR labels (leakage-safe)

`G` 444 · `F` 352 · `C` 64 · missing 13 · `NA` 4 · `SG` 4 · `PF` 3 · `PG` 1 · `SF` 1 · `ATH` 1

Coverage of the canonical coarse scheme: **98.0%**. Distribution by outcome is balanced — G 238 undrafted / 206 drafted, F 173 / 179, C 31 / 33 — with a 2.4 pp availability gap in line with the general match gap. **No target association.**

Drafted rate by canonical position (descriptive only, not a quality claim): **C 51.6% · F 51.4% · G 46.8%**.

### The contaminated alternative

| | Five-position resolvable |
| --- | --: |
| Drafted | **431 / 431 = 100.0%** |
| Undrafted | **35 / 456 = 7.7%** |

Every `G`, `F`, `G/F`, `F/C` and missing label belongs to an undrafted prospect; every `PG`, `SG`, `SF`, `PF`, `PG/SG`… belongs to a drafted one. The only overlap is `C` (35 undrafted / 41 drafted), which is why 7.7% is not zero.

### Decision

**Implemented:** `position_3` (G/F/C) from `hoopr_position`, in [`scripts/positions.py`](../scripts/positions.py) with the table in [`config/position_map.csv`](../config/position_map.csv), unit-tested.

**Deferred:** `position_5`. The deterministic parser (explicit label → itself; composite → first listed; broad → `UNKNOWN`) is written and tested but **applied to nothing**, because its only available input is contaminated. Options for ML-2 or a product decision: accept G/F/C for position-relative normalisation; source five-position labels from a genuinely pre-draft feed; or relax DEC-009. **No position was inferred from statistics.**

## 4. Primitive distributions

41 numeric primitives profiled (`data/interim/ml1/primitive_summary_2014_2025.csv`).

- **Uniform 2.14% missingness** across every box and shot primitive — a single structural cause, not per-field gaps (§7).
- **No impossible values.** All 14 identity checks pass: made ≤ attempted for FG/2P/3P/FT and every shot type; no negatives; `games_started ≤ games_played`; no duplicate prospect-years; assisted makes never exceed made FGs; shot-file FGA never exceeds box FGA by >20%.
- **Structural zeros are meaningful, not errors:** `tip_makes` 40.7% zero, `tip_attempts` 35.0%, `unassisted_dunk_makes` 16.2%, `dunk_makes` 9.1%, `three_points_made` 10.6%. These are real basketball facts (guards do not tip in, non-shooters take no threes) and must not be imputed away.
- Ranges are plausible throughout: minutes 16–1374, points 5–983, height 68–90 in, weight 150–360 lb.

## 5. Temporal drift

Median-by-year relative range (`(max−min)/median`):

| Field | Relative range | Reading |
| --- | --: | --- |
| **`jump_shot_attempts`** | **1.126** | ⚠️ artefact of the schema break (§8), not real drift |
| `dunk_attempts` | 1.017 | Genuine style drift |
| `blocks` | 0.765 | Genuine |
| `free_throws_attempted` | 0.735 | Genuine — reflects rule and style change |
| `three_points_attempted` | 0.637 | Genuine — the three-point revolution |
| `assists` | 0.504 | Genuine |
| `total_rebounds` | 0.477 | Genuine |
| `minutes` | 0.327 | Partly COVID |
| `games_played` | 0.299 | Partly COVID |
| **`weight`** | **0.071** | Stable |
| **`height`** | **0.038** | Stable |

**Season normalisation is justified for volume and rate statistics and unnecessary for physical measurements.** This supports ML_SPEC §9.2's proposed experiments. Nothing was normalised here.

## 6. COVID-era findings

| Block | Prospects | Drafted % | Med. games | Med. minutes | Med. points | Med. FGA | Shots coverage |
| --- | --: | --: | --: | --: | --: | --: | --: |
| 2019–2020 | 141 | 56.7 | 32.0 | 1010 | 478 | 364 | 98.6% |
| **2021–2022** | **320** | **29.1** | **28.0** | **861** | **384** | **288** | 97.8% |
| 2023–2025 | 156 | 64.1 | 33.5 | 1019 | 473 | 353 | 98.7% |

**The anomaly is multi-factor, not a single cause:**
1. **Population** — 320 prospects vs 141 and 156, driven by blanket COVID eligibility inflating declarations, halving the drafted rate to 29.1%.
2. **Playing schedule** — median games 28 vs 32–33.5 and minutes 861 vs ~1010, so raw totals are genuinely depressed.
3. **Source coverage is NOT implicated** — shot coverage is 97.8% vs 98.6/98.7%.

So 2021–2022 differ in *who declared* and *how much they played*, not in data quality. Both years are retained.

## 7. Missingness

**Uniform 2.14%** (19/887) across all box and shot primitives; `height`/`weight` 1.58%; `hoopr_position` 1.47%; `experience_years` 3.72%. **No imputation, no missingness indicators.**

### Co-occurrence — five patterns, not scattered gaps

| Pattern | Prospects |
| --- | --: |
| Complete | **863** |
| Matched but no box/shot rows | 10 |
| Fully unmatched (no hoopR record at all) | **8** |
| Only height/weight absent | 5 |
| Matched, no box/shots, no physicals | 1 |

Missingness is essentially "the whole prospect is absent" or "physicals absent", which is what ML-2's handling must address — not per-field noise.

### Target-linked missingness

**Maximum drafted-vs-undrafted coverage gap: +2.81 pp** (99.30% vs 96.49%), uniform across every box and shot primitive.

For scale, the DOB gap that got age excluded was **31 pp**, and the position gap found in §3 is effectively **92 pp**. At 2.81 pp this is benign and consistent with undrafted prospects being marginally likelier to fall outside hoopR D-I coverage. **No numeric primitive is excluded on this basis.** ML-2 should re-check after engineering.

## 8. Shot coverage and schema

**Coverage is strong:** 94.2–100% of prospects have shot records in every year; the median ratio of shot-file FGA to box FGA runs **0.940–1.000**, so the two sources agree closely. Coordinates were not touched and free throws were not taken from the shot file.

### 🔴 The vocabulary is not stable

`type_text` share by season (%):

| Category | 2014 | 2017 | 2020 | **2021** | 2023 | 2025 |
| --- | --: | --: | --: | --: | --: | --: |
| JumpShot | 22.1 | 21.1 | **30.2** | **50.0** | 48.9 | 49.4 |
| **Three Point Jump Shot** | 23.6 | 27.1 | **19.2** | **—** | — | — |
| LayUpShot | 22.5 | 22.7 | 23.7 | 23.6 | 24.5 | 23.6 |
| MadeFreeThrow | 28.6 | 25.9 | 24.3 | 23.8 | 23.8 | 23.5 |
| DunkShot | 2.3 | 2.3 | 2.5 | 2.4 | 2.7 | 2.6 |
| TipShot | 1.0 | 0.9 | 0.24 | 0.22 | 0.13 | 0.98 |

**`Three Point Jump Shot` disappears after 2020 and `JumpShot` roughly doubles.** ML-0's aggregation maps only `JumpShot`/`LayUpShot`/`DunkShot`/`TipShot`, so `jump_shot_attempts` **excludes** three-point jumpers through 2020 and **includes** them from 2021.

**Consequence for ML-2:** `jump_shot_attempts` / `jump_shot_makes` must not be used across the boundary as-is. Two safe routes: reconstruct a comparable "two-point jumper" quantity by subtracting `three_point_shot_*`, or drop the raw jump-shot fields and build shot profile from `layup`/`dunk`/`tip`/`three_point_shot_*`, which are stable. `LayUpShot`, `DunkShot` and `TipShot` shares are stable throughout; `TipShot` declines steadily (1.0% → 0.1%) then rebounds in 2025, worth a glance but not blocking. Minor junk categories (`Not Available` 2.98% in 2018; a handful of rebound/timeout rows in 2015) are already excluded by the category map.

## 9. Assist linkage

**Exceptionally stable — the most reliable signal found.**

| Season | 2014 | 2016 | 2018 | 2020 | 2021 | 2023 | 2025 |
| --- | --: | --: | --: | --: | --: | --: | --: |
| Assisted rate % | 51.54 | 52.24 | 52.04 | 51.60 | 51.96 | 51.38 | 51.81 |

Range across all 12 years: **50.84 – 52.92%** — a 2.1 pp band with no regime change, including across the shot-type break. Assisted/unassisted splits are safe for ML-2.

## 10. Leakage sanity audit

| Check | Result |
| --- | --- |
| Strongest target separation | `unassisted_dunk_makes`, rank-AUC **0.687** |
| Next | `dunk_makes` 0.671 · `tip_attempts` 0.668 · `dunk_attempts` 0.667 · `games_played` 0.653 |
| Strongest pick association (drafted only) | `unassisted_dunk_makes` ρ = **−0.216** |
| Impossible-value checks | 14 run, **0 findings** |
| Prohibited columns in feature files | **0** in all three partitions |

**No primitive behaves like a hidden outcome.** A rank-AUC near 0.687 is a plausible basketball signal (rim finishing correlates with draft stock), not contamination. The negative pick correlations are the correct direction — better production, lower pick number.

The leakage that *did* exist was in metadata, not statistics, and is documented in §1 and DEC-065.

## 11. Unresolved prospects and selection bias

Eight unresolved (7 UNMATCHED + 1 AMBIGUOUS):

| Year | Player | College | Category |
| --- | --- | --- | --- |
| 2016 | Jordan Hare | Rhode Island | Did not play that season |
| 2018 | Marquez Letcher-Ellis | Nevada | Did not play that season |
| 2018 | Mitchell Robinson | Western Kentucky | Enrolled, never played a college game |
| 2021 | Sam Cunliffe | Evansville | Did not play that season |
| 2021 | Brandon Williams | Arizona | Did not play that season |
| 2022 | Trevor Hudgins | Northwest Missouri State | D-II, outside hoopR D-I scope |
| 2024 | Deshawndre Washington | New Mexico State | Did not play that season |
| 2024 | Isaiah Crawford | Louisiana Tech | True ambiguity — not forced |

> ⚠️ **All 8 are undrafted. Zero are drafted.**

Against a 48.6% base rate this is not chance. **Dropping rows without statistics would remove only negatives and inflate apparent model performance.** ML-2 must either retain them with explicit missing handling or document the exclusion as a measured, one-sided sample restriction. They are retained here.

## 12. Robustness period 2011–2013

| Year | Prospects | Drafted % | Matched | Box coverage | Shots coverage | position_3 | Height |
| --- | --: | --: | --: | --: | --: | --: | --: |
| 2011 | 39 | 69.2 | 34 | 87.2% | 87.2% | 82.1% | 87.2% |
| 2012 | 43 | 69.8 | 43 | 100.0% | 100.0% | 95.3% | 100.0% |
| 2013 | 43 | 65.1 | 41 | 95.3% | 95.3% | 86.0% | 95.3% |

Overall 125 prospects, 68.0% drafted, 94.4% matched. Coverage is **consistently worse** than 2014–2025 (98.0–99.3%) and 2011 is materially weaker on every axis, consistent with the DATA.md §24.3 coverage break at 2014. **Keeping 2011–2013 robustness-only remains justified.** They were not used to alter any development conclusion.

## 13. 2026 holdout limitations

**Non-target-aware checks only.** The 2026 target file is never opened by the EDA script; `dev_only()` raises if 2026 reaches a target-aware path, and both guards are unit-tested.

| Check | Result |
| --- | --- |
| Rows | 26 |
| Schema matches development | ✅ |
| hoopR matched | 100.0% |
| Box / shots coverage | 100.0% / 100.0% |
| `position_3` coverage | 100.0% |
| Height / weight coverage | 100.0% / 100.0% |
| Prohibited columns | none |

**2026 is the cleanest partition in the project** — and simultaneously the least informative for classification, with 25 drafted and 1 undrafted (DEC-066). Stage A metrics computed on it will be unstable or undefined; historical folds are the primary evidence. 2026 remains the final ranking/replay showcase.

## 14. Recommendations for ML-2

**🟢 STRONG CANDIDATES**

| Family | Justification |
| --- | --- |
| **Per-minute / per-game rates** | Minutes correlate 0.85 with points and 0.86 with FGA — raw totals largely measure opportunity |
| **Shooting efficiency** (FG%, 2P%, 3P%, FT%, eFG%, TS%) | All numerators and denominators present, zero impossible values |
| **Shot-diet shares from layup / dunk / tip / three_point_shot_*** | Stable vocabulary across the whole window |
| **Assisted / unassisted rates** | 50.8–52.9% band over 12 years — the most stable signal found |
| **Season normalisation of volume and rate stats** | Relative ranges 0.3–1.0 justify it |
| **Coarse position-relative normalisation (G/F/C)** | 98.0% coverage, leakage-free, balanced by outcome |
| **Rebounding and playmaking rates** | Team totals derivable from `player_box` (DATA.md §22.2) |

**🟡 NEEDS CAUTION**

| Family | Caution |
| --- | --- |
| **Any `jump_shot_*` feature** | Schema break at 2020/2021 — subtract `three_point_shot_*` or drop |
| **`blocks`** | Correlates only 0.07 with minutes — position-driven; needs position-relative treatment |
| **`tip_*`** | 35–41% structural zeros and a declining trend |
| **`experience_years`** | 3.72% missing, not leakage-cleared, and conceptually close to class year |
| **COVID-year handling** | Population *and* playing time both shift; a single adjustment will not fix both |
| **`height`/`weight`** | Clean and stable, but 1.58% missing with a 2.4 pp target gap |
| **Rows without statistics** | All undrafted — dropping them biases the sample |

**🔴 REJECT**

| Item | Reason |
| --- | --- |
| **`position_from_population`** | 100% vs 7.7% resolvable by outcome — target-contaminated (DEC-065) |
| **`class_from_population`** | 26.5 pp availability gap, outcome-specific vocabulary |
| **`match_method` / `match_confidence`** | Every UNMATCHED prospect is undrafted |
| **Five-position (PG/SG/SF/PF/C) features** | No leakage-safe source exists |
| **Date of birth / age / DOB indicators** | DEC-044, unchanged |
| **Raw untransformed totals as primary features** | Dominated by opportunity |

## 15. Remaining blockers

| # | Blocker | Severity | Owner action |
| --- | --- | :-: | --- |
| 1 | **No leakage-safe PG/SG/SF/PF/C source** — DEC-009 cannot be met | 🔴 | Accept G/F/C, source a pre-draft five-position feed, or relax DEC-009 |
| 2 | **Shot-type schema break at 2020/2021** — `jump_shot_*` not comparable | 🔴 | ML-2 must derive around it |
| 3 | **All 8 unresolved prospects are undrafted** | 🟠 | ML-2 must not silently drop them |
| 4 | **2025 fold has 2 undrafted; 2026 holdout has 1** | 🟠 | ML-3/ML-4 fold weighting; do not expand the population |
| 5 | **Class balance swings 26.6% → 92.9%** | 🟠 | Year-aware evaluation required |

None blocks ML-2 from starting; 1–3 constrain what it may build.
