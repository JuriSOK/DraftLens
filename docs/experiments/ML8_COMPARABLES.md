# ML-8 — NBA statistical comparables

**Phase:** ML-8 · descriptive NCAA↔NBA similarity
**Scope:** development NCAA prospects (2014–2025) against a frozen NBA reference (2021–2025)
**Status:** complete — common space, similarity metric and score frozen
**Reproduce:** `python scripts/build_comparable_references.py` then `python scripts/experiments/ml8_comparables.py`

> **2026 firewall.** No 2026 prospect was scored or inspected. The NBA reference window ends at 2025 and the NCAA peer reference covers development years only. Both the reference builder and the CLI **refuse** the holdout year. Enforced by [`validate_ml8_comparables.py`](../../scripts/experiments/validate_ml8_comparables.py) check 6.
>
> **Every frozen system is untouched.** Stage A, Stage B, the General Draft Board and Team Need are unchanged, and none of their outputs can reach a similarity vector.

---

## 1. Executive summary

For an NCAA prospect, DraftLens returns **exactly three unique NBA players** whose statistical and role profiles most resemble his.

```
common space   6 role dimensions, 12 metrics, each side percentile-ranked
               within its OWN league
distance       coverage-normalised Euclidean
score          percentile against a frozen distribution of prospect-to-NBA
               distances
```

Face validity is strong and was obtained with **zero outcome optimisation** — nothing here knows who any prospect became:

| Prospect | Comparables |
| --- | --- |
| Mikal Bridges (2018) | Paul George · Kawhi Leonard · Trey Murphy III |
| Tyrese Haliburton (2020) | Jrue Holiday · Derrick White · Lonzo Ball |
| Zach Edey (2024) | Karl-Anthony Towns · Joel Embiid · Kristaps Porziņģis |
| Trae Young (2018) | Jamal Murray · Donovan Mitchell · Tyrese Haliburton |
| Walker Kessler (2022) | Tari Eason · Brandon Clarke · Mark Williams |

**Three honest findings shape how this must be read**, and all three point the same way:

1. **The third comparable is often nearly arbitrary.** The median 3rd-vs-4th distance margin is 0.43 — **4.0% of the distance to the third neighbour**, with a minimum of 0.00.
2. **Individual names are sensitive.** Removing any one dimension retains only 1.4–1.7 of 3 names.
3. **The score compresses at the top.** Real comparables land in a 97–100 band.

Together these mean the output is a **neighbourhood, not three uniquely correct names**. That is stated in the limitations and should be stated in the product.

---

## 2. Product semantics

> "Based on his relative statistical profile, this prospect most closely resembles these NBA player profiles."

**Never:** "he will become this player."

| Prohibited | Approved |
| --- | --- |
| "Projected NBA comp" · "expected career" · "ceiling" · "floor" · "will become" | "Statistical NBA Comparables" · "Similar NBA statistical profiles" |

There is **no ground-truth "correct comparable" dataset**. Nothing here is fitted, and no draft outcome, board signal, Team Need score or NBA career result (awards, All-Star selections, BPM, RAPTOR, VORP) may influence the methodology. Method selection rested on semantic validity, cross-league comparability, stability, coverage and interpretability.

## 3. NBA data audit

Source: **hoopR NBA `player_season_stats`** (sportsdataverse, CC BY 4.0; upstream ESPN). Seasons 2011–2026 acquired; 2021–2025 used.

**Format is LONG** — one row per player × season × category × stat; 24,491 rows for 2024 across 572 players (≈43 rows each). Categories: `totals`, `averages`, `miscellaneous`.

| Available | Not available |
| --- | --- |
| points, assists, turnovers, OREB, DREB, TREB, steals, blocks, fouls (totals) | **team totals and opponent totals** |
| FGM–FGA, 3PM–3PA, FTM–FTA (combined strings) | **shot-level events** |
| FG%, 3P%, FT%, games played, games started, minutes/game | **height and weight** |
| position abbreviation (PG/SG/G/SF/PF/F/C) | **any athleticism or physical testing** |

**Parsing note.** The made–attempted pairs carry a null numeric `value`; they arrive as combined strings (`"247-538"`) in `display_value` and parse cleanly for **100%** of rows.

**Identity is clean.** Over 2021–2025: 2,817 player-seasons, 986 unique players, **0 athlete_ids carrying more than one name and 0 names mapping to more than one id**. Players are therefore collapsed on `athlete_id`, never on name.

Metric coverage across the window: 94.7–100% for every accepted metric.

## 4. Common NCAA/NBA metric audit

| Metric | NCAA source | NBA source | Semantics | Verdict |
| --- | --- | --- | --- | --- |
| `three_point_pct` | 3PM/3PA | 3PM/3PA | identical ratio | **ACCEPTED** |
| `ft_pct` | FTM/FTA | FTM/FTA | identical ratio | **ACCEPTED** |
| `efg_pct` | (FGM+0.5·3PM)/FGA | same formula, shared code | identical | **ACCEPTED** |
| `three_point_attempt_rate` | 3PA/FGA | 3PA/FGA | identical shot-mix ratio | **ACCEPTED** |
| `free_throw_rate` | FTA/FGA | FTA/FGA | identical | **ACCEPTED** |
| `points_per_40` | 40·PTS/MP | 40·PTS/MP | identical rate | **ACCEPTED** |
| `fga_per_40` | 40·FGA/MP | 40·FGA/MP | identical | **ACCEPTED** |
| `assists_per_40` | 40·AST/MP | 40·AST/MP | identical | **ACCEPTED** |
| `oreb_per_40`, `dreb_per_40` | 40·REB/MP | 40·REB/MP | identical | **ACCEPTED** |
| `steals_per_40`, `blocks_per_40` | 40·(STL,BLK)/MP | same | identical | **ACCEPTED** |

`efg_pct`, `ts_pct`, `per_40` and `safe_div` are **imported from `draftlens.features`**, not reimplemented — a divergent second copy would silently break the comparison this module exists to support.

**Why per-40 rates are legitimate across leagues.** A per-40 rate is never compared to a per-40 rate directly. Each side is percentile-ranked within its **own** league first, so the 40-vs-48-minute game length, pace, spacing and competition differences cancel completely. The question asked of both populations is identical: *where does this player sit among his own league's peers?*

## 5. Rejected cross-league metrics

| Rejected | Reason |
| --- | --- |
| `ast_pct`, `usage_pct` | Need team FGM and team minutes. NBA team totals **are** reconstructable by summing players (verified: team minutes sum to 1.008× the expected 19,680, the excess being overtime) — but ESPN attributes a traded player's whole season to one team, which would silently corrupt the denominator. |
| `orb_pct`, `drb_pct`, `trb_pct` | Need **opponent** rebound totals. There is no game-level NBA data here to derive them. |
| `stl_pct`, `blk_pct` | Need opponent possessions and opponent FGA. Not derivable from season-level NBA data. |
| `rim_attempt_share`, `rim_make_pct`, unassisted shares, dunk/layup shares | Require shot-level events. **There is no NBA shot file.** The entire NCAA rim-pressure family is unavailable. |
| `height`, `weight` (Size) | The NBA source carries no physical measurements. **Never fabricated.** |
| Athleticism | No athleticism measurement exists in any acquired source. No proxy permitted (ML_SPEC §18.2). |
| `jump_shot_*` | NCAA-side schema break at 2020/21 (DEC-068). |
| Raw per-game production | 19 NCAA PPG and 19 NBA PPG are not the same event. Rejected outright and asserted by validator check 3. |

Recreating a possession percentage from a materially different denominator would produce two metrics sharing a name and not a meaning. They are excluded rather than approximated.

## 6. NBA reference-player eligibility

**≥ 750 minutes and ≥ 30 games** in a season — roughly 25 minutes over 30 games, or 9 minutes across a full season. Set from the minutes distribution, never from how any prospect's comparables look.

| Threshold | Eligible players/season |
| --- | --- |
| 500 min / 20 gp | 359–375 |
| **750 min / 30 gp** | **306–323** |
| 1000 min / 40 gp | 243–266 |
| 1500 min / 40 gp | 138–190 |

The 2024 median NBA player-season is 879 minutes, so a lower bar admits genuinely noisy profiles (a 40-minute season can show a 100% three-point rate); a higher one prunes exactly the role players a comparison should be able to surface.

**Reference window: 2021–2025**, five completed seasons ending before the holdout year. Chosen for modern role relevance and pool diversity, never because particular players appear in it. **542 unique players** after collapsing.

## 7. NBA player representation

Each player has several seasons; the pool must hold **one row per player**, or the top three could return as "Player A 2023, Player A 2024, Player B 2024" — three rows, two people.

| Representation | Definition | Top-3 overlap vs selected |
| --- | --- | --- |
| `LATEST_SEASON` | most recent qualifying season | **1.27 / 3 (42%)** |
| **`RECENT_MULTI_SEASON`** | **minutes-weighted mean of the last 3 qualifying seasons** | **selected** |
| `CAREER` (diagnostic) | minutes-weighted mean over all 5 | 2.25 / 3 (75%) |

**Selected: `RECENT_MULTI_SEASON`.** The latest-season variant agrees with it on only 42% of names — that gap *is* the single-season noise the multi-season profile exists to remove. Minutes weighting is the honest aggregator: a 2,400-minute season describes a role better than a 780-minute one, and every metric is already a rate, so weighting by the exposure that produced it is the same operation the rates perform.

`CAREER` is retained as a **diagnostic only**: averaging a whole career mixes career stages and roles and can manufacture a player who never existed in any single season.

## 8. Common statistical space

Six dimensions, 12 metrics, **equal weight per dimension** — so shooting's three metrics do not outvote creation's one.

| Dimension | Kind | Metrics |
| --- | --- | --- |
| `SHOOTING_EFFICIENCY` | **QUALITY** | `three_point_pct`, `ft_pct`, `efg_pct` |
| `SCORING_ROLE` | ROLE | `points_per_40`, `fga_per_40` |
| `CREATION` | ROLE | `assists_per_40` |
| `REBOUNDING` | ROLE | `oreb_per_40`, `dreb_per_40` |
| `DEFENSIVE_ACTIVITY` | ROLE | `steals_per_40`, `blocks_per_40` |
| `PERIMETER_ORIENTATION` | **STYLE** | `three_point_attempt_rate`, `free_throw_rate` *(inverted)* |

**Style vs quality is the central design choice.** Only one dimension is "higher is better". The rest are role/volume axes (a high-usage scorer is not *better* than a low-usage specialist — he is different) or a pure style axis where neither end is preferable: a stretch shooter and a rim-attacking big sit at opposite ends of `PERIMETER_ORIENTATION` and both are valid NBA roles.

If every dimension were higher-is-better, an elite prospect would simply match elite NBA players regardless of role — a goodness ranking wearing a similarity costume.

**Redundancy audit — and a notable result.** No metric appears in two dimensions. Dimension correlations are nearly **identical in both leagues**:

| Pair | NCAA | NBA |
| --- | --- | --- |
| REBOUNDING ~ PERIMETER_ORIENTATION | −0.55 | −0.55 |
| REBOUNDING ~ DEFENSIVE_ACTIVITY | +0.40 | +0.42 |
| SHOOTING_EFFICIENCY ~ PERIMETER_ORIENTATION | +0.35 | +0.34 |

That the correlation structure reproduces across two independent leagues is meaningful evidence the space measures the same constructs on both sides. Every strong pair is an expected basketball fact (bigs rebound and do not shoot threes), not double counting.

## 9. League-relative normalisation

- **NCAA prospects** are ranked against the full NCAA population **of their own draft season** — 2,941–3,417 rotation players per season (≥ 200 minutes, ≥ 10 games), 39,410 player-seasons total.
- **NBA players** are ranked against the NBA reference pool.

The NCAA peer frame is built by the **same `_season_frame`** the Team Need reference uses, so a prospect's value and its peer group are produced by identical code. That import is the only Team Need dependency and carries no Team Need score.

## 10. Position handling

ESPN mixes coarse and fine labels (`PG SG G SF PF F C`), all deterministically mappable: `PG/SG/G → G`, `SF/PF/F → F`, `C → C`. Purely lexical — **no position is inferred from statistics**, and no external roster source is consulted.

Position-relative normalisation was therefore genuinely testable, and was **tested and rejected**: it retains only **0.86 of 3 names (29%)** versus the global baseline — a completely different system.

**GLOBAL normalisation is selected** because position-relative would erase exactly the cross-position resemblance the product exists to surface. A stretch big whose profile resembles a wing is a finding, not an error; normalising within position would define that finding out of existence.

## 11. Candidate distance metrics

All coverage-normalised — computed over dimensions available for **both** players and divided by the count, so a prospect missing dimensions is not mechanically closer to everyone.

| Metric | Top-3 overlap vs Euclidean | Note |
| --- | --- | --- |
| **EUCLIDEAN** | 3.00 / 3 (self-check) | **selected** |
| MANHATTAN | 2.31 / 3 (77%) | broadly agrees; no advantage |
| COSINE | 2.21 / 3 (74%) | requires centring, and has a real failure mode |

**Cosine needed care and still failed.** Percentile vectors are all-positive, so raw cosine calls almost every pair similar; centring on the 50th percentile first turns each axis into "above or below a typical peer" and makes the angle meaningful. But the centred version is **undefined for a prospect sitting at exactly the 50th percentile on every dimension** — a zero-length vector has no direction. Euclidean handles that prospect fine. Given no accuracy advantage and a genuine degenerate case, **Euclidean is selected**: it is also the most explainable ("average gap across six dimensions, in percentile points").

## 12. Similarity score semantics

**Selected: `GLOBAL_DISTANCE_PERCENTILE`.**

```
similarity = 100 × share of the FROZEN reference distribution of
             prospect-to-NBA distances that is FARTHER than this pairing
```

> A score of 95 means: **this pairing is closer than roughly 95% of all prospect-to-NBA pairings** in the development reference (155,554 pairings, median distance 35.1). It is **not** a probability and **not** a percentage of shared traits.

**`WITHIN_POOL_PERCENTILE` was implemented, measured and rejected.** It is structurally degenerate for the top three: with a pool of 542, the three closest are always the top 0.55%, so it returns **100.00 / 99.82 / 99.63 for every prospect** — identical numbers whether the nearest match is excellent (distance 8.9) or poor (15.6). It conveys nothing.

The global reference does discriminate:

| Prospect | Scores | Distances |
| --- | --- | --- |
| Zach Edey | 100, 98, 98 | 8.9, 14.1, 14.3 |
| Mikal Bridges | 97, 97, 96 | 15.6, 15.8, 17.1 |
| Trae Young | 100, 100, 100 | 7.2, 8.2, 9.1 |

`100 - 10 × distance` was rejected outright: an arbitrary constant wearing a percentage sign.

**Honest limitation:** real comparables occupy a **97–100 band**. A top-3 match out of 542 genuinely *is* closer than nearly every pairing, so the compression is truthful — but it means the score separates a good match from a mediocre one only weakly, and the rank plus raw distance carry the finer information.

## 13. Exactly-three selection

Uniqueness is **structural**: the pool holds one row per player, so three rows are three people. Verified on 120 sampled prospects — every one returned exactly 3 unique players, 0 unavailable.

Ordering is closest-first. **Ties break deterministically** on exact distance then the stable `athlete_id` — never on fame, awards, draft position, salary or manual preference. If fewer than three players satisfy every rule the result is **UNAVAILABLE**; guards are never relaxed to force three names.

## 14. Missingness and coverage

- Distance uses dimensions available for **both** players, divided by the count — so a prospect missing three dimensions is not mechanically closer to everyone, which would give the *least*-measured prospects the most confident comparables.
- **Minimum shared coverage: 75%** (5 of 6 dimensions). Below it the result is UNAVAILABLE. Three names produced from two dimensions are not a comparison.
- A missing dimension is **dropped, never filled** with 0, 50 or a league average.

Coverage is 97.9% on the NCAA side (the 2.1% are the unresolved prospects) and 100% on the NBA side.

## 15. Historical self-match prevention

**283 development prospects also appear in the NBA reference pool.** A prospect must not return himself, so identity is excluded deterministically on the canonical normalised name — the same key used for cross-source joins throughout the project. Verified: **0 self-matches** across all 283.

No draft or career field is read to do this; only the name key.

## 16. Representation stability

See §7. `LATEST_SEASON` retains 42% of names, `CAREER` 75%. The representation choice materially changes the output, which is why the multi-season profile was chosen on stated reasoning rather than by default.

## 17. Leave-one-dimension-out stability

| Dropped | Kind | Top-3 overlap retained |
| --- | --- | --- |
| CREATION | ROLE | 1.36 / 3 (45.5%) |
| SCORING_ROLE | ROLE | 1.38 / 3 (46.0%) |
| SHOOTING_EFFICIENCY | QUALITY | 1.59 / 3 (53.2%) |
| REBOUNDING | ROLE | 1.67 / 3 (55.7%) |
| PERIMETER_ORIENTATION | STYLE | 1.67 / 3 (55.7%) |
| DEFENSIVE_ACTIVITY | ROLE | 1.69 / 3 (56.3%) |

**Two readings, and both matter.**

*The good news:* the range is narrow — 45.5% to 56.3%. **No single dimension carries the result.** If one did, dropping it would collapse overlap toward 0 while dropping others left it near 3. The space is genuinely six-dimensional.

*The honest news:* removing any one dimension still changes about half the names. With 542 densely packed candidates, small changes reshuffle near-ties. **Individual comparable identity is not robust**; the neighbourhood is.

## 18. Neighbour-margin analysis

| Statistic | Value |
| --- | --- |
| Median 3rd-vs-4th distance margin | **0.43** |
| Margin as a share of the 3rd distance | **4.0%** |
| p25 / p75 | 0.20 / 1.03 |
| Minimum | **0.00** |
| Median distance to #1 / #3 | 8.76 / 11.00 |

**The third comparable is frequently near-arbitrary.** A 4% median margin means the 4th-closest player is usually almost as close as the 3rd, and sometimes exactly as close. The product requirement is exactly three, so three are returned — but the third name should be read as "one of several equally close profiles", never as a uniquely correct answer.

This is the single most important caveat in the phase and is repeated in §22.

## 19. Historical face-validity examples

Development prospects only. A sanity audit of whether neighbours are close **in the dimensions** — formulas were **not** changed because a name looked wrong, and no NBA career outcome was consulted.

| Prospect | Comparables (similarity) |
| --- | --- |
| Trae Young (2018) | Jamal Murray (100) · Donovan Mitchell (100) · Tyrese Haliburton (100) |
| Zach Edey (2024) | Karl-Anthony Towns (100) · Joel Embiid (98) · Kristaps Porziņģis (98) |
| Mikal Bridges (2018) | Paul George (97) · Kawhi Leonard (97) · Trey Murphy III (96) |
| Tyrese Haliburton (2020) | Jrue Holiday (98) · Derrick White (97) · Lonzo Ball (96) |
| Jalen Williams (2022) | Donovan Mitchell (100) · Jamal Murray (100) · Kyrie Irving (100) |
| Walker Kessler (2022) | Tari Eason (100) · Brandon Clarke (99) · Mark Williams (99) |

Worked example — Zach Edey's NCAA profile: scoring role 98, rebounding 99, perimeter orientation 4 (an almost entirely interior shot diet), creation 61. The three returned players are high-usage scoring bigs with interior-tilted diets. The match is explainable directly from the dimensions, which is the only claim being made.

That Mikal Bridges returns Paul George and Kawhi Leonard — and that the archetype's namesake lands on two canonical 3&D wings — is meaningful **precisely because nothing in the construction knows who he became**.

## 20. Deterministic explanation logic

Structured fields only. No generative model, no scouting prose.

Each comparable exposes `dimension_delta` (every shared dimension, with both percentiles and the gap), `closest_dimensions` (gaps ≤ 15 percentile points), `largest_differences` (gaps ≥ 25) and `unavailable_dimensions`. A distance is a sum over dimensions, so it can always be reported dimension by dimension — that is the honest decomposition.

**A dimension missing for either side is reported as unavailable and never counted as a difference** — absence of evidence is not evidence of divergence.

```
 2. Joel Embiid              similarity  98   (NBA 2022-2024, distance 14.1)
      ~ scoring role: 98 vs 100
      ~ perimeter vs interior shot diet: 4 vs 8
      ! box-score defensive activity: 49 vs 74
```

## 21. Final methodology

```
NBA pool          2021-2025, >= 750 min and >= 30 games per season
                  minutes-weighted mean of the last 3 qualifying seasons
                  542 unique players, collapsed on athlete_id

common space      6 dimensions / 12 metrics, equal weight per dimension
                  each side percentile-ranked within its OWN league and season
                  GLOBAL reference group (not position-relative)

distance          coverage-normalised Euclidean, >= 75% shared dimensions

score             percentile against the frozen distribution of
                  prospect-to-NBA distances

output            exactly 3 unique players, closest first,
                  ties broken on distance then athlete_id,
                  self-match excluded
```

Selected on semantic validity, cross-league comparability, stability, coverage, interpretability and simplicity — never on famous-name appeal, and never against any outcome.

## 22. Limitations

1. **The third comparable is often near-arbitrary** — 4% median margin, minimum 0.00 (§18). Read the output as a neighbourhood.
2. **Individual names are sensitive** — dropping any dimension changes about half the top three (§17). No dimension dominates, but no name is robust either.
3. **The score compresses into 97–100** for real comparables (§12). Truthful, but weakly discriminating.
4. **No shot-level NBA data**, so the entire rim-pressure family is absent. Interior orientation is proxied only by free-throw rate.
5. **No NBA height or weight**, so size — a real component of resemblance — is not in the space at all. A 6'0" and a 7'0" player with identical rates are indistinguishable here.
6. **No possession-based percentages** (AST%, usage%, rebound rates), because their NBA denominators do not exist or would be corrupted by traded-player attribution.
7. **Defensive activity is box-score events only** — steals and blocks, not defensive quality.
8. **The NBA pool is recent and rotation-filtered** (542 players, 2021–2025). A prospect resembling a 2005 role, or a player below 750 minutes, has no candidate.
9. **NCAA and NBA percentile scales are not equally spaced.** Equal percentiles mean equal *relative standing*, not equal difficulty.
10. **There is no ground truth**, so no accuracy claim is possible. Everything here is descriptive resemblance.

## 23. 2026 firewall

No 2026 prospect was scored, ranked or inspected. The NBA reference window is 2021–2025 and the NCAA peer reference covers 2014–2025. `scripts/build_comparable_references.py` and `scripts/run_comparables.py` both **refuse** the holdout year rather than merely omitting it, and `eligible_seasons` raises if 2026 is requested.

No metric, threshold, representation, distance metric or score transform was chosen by looking at how any 2026 prospect's comparables appear.

## 24. Application readiness

All four analytical systems are complete and frozen:

| System | Output |
| --- | --- |
| General Draft Board | Overall Score 0–100 (class-relative ranking) |
| Stage A | Draft Probability — the only genuine probability |
| Stage B | Draft Position Signal — never a literal pick |
| Team Need | Fit Score 0–100 (peer-relative trait match) |
| **NBA comparables** | **exactly 3 statistical resemblances + per-dimension explanation** |

Every one is deterministic, reproducible from committed code and config, and importable as `draftlens.*` without touching an experiment script. A future application would consume the library; it would never reimplement it.

## 25. Next phase

**2026 product replay and application integration.**

The holdout may be opened for the first time: generate the 2026 board, Overall Scores, Team Need rankings and NBA comparables, then compare against the actual draft **once**, reporting the result as-is. No methodology may change after the holdout is opened.

The 2026 holdout remains sealed until that phase begins.
