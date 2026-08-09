# ML-7 — Team Need analytical scoring

**Phase:** ML-7 · the second DraftLens product mode
**Scope:** historical development window **2014–2025 only**
**Status:** complete — dimensions, profiles and Fit Score frozen
**Reproduce:** `python scripts/build_team_need_reference.py` then `python scripts/experiments/ml7_team_need.py`

> **2026 firewall.** No 2026 prospect was scored, ranked or inspected. The NCAA peer reference is built from development seasons only, and both the reference builder and the CLI refuse the holdout year outright. Enforced by [`validate_ml7_team_need.py`](../../scripts/experiments/validate_ml7_team_need.py) check 10.
>
> **The General Draft Board is untouched.** Stage A, Stage B and the ML-6 board are unchanged, and no board signal enters a Fit Score.

---

## 1. Executive summary

> **General Draft Board asks who looks strongest overall. Team Need asks who best fits what a team is looking for.**

Team Need ranks prospects by how well their pre-draft statistical profile matches a requested set of basketball traits. It is a deterministic multi-criteria system, not a model.

Six factual dimensions on an NCAA peer-percentile scale, six predefined archetypes, and a custom weighted mode. Athleticism is **not scored** — there is no honest way to measure it without Combine data.

**It works as intended, and the proof is that it disagrees with the board.** Across the seven development classes, Team Need rankings correlate with the Overall Score at only **ρ = 0.18–0.62**, and each archetype surfaces a different prospect at the top. In the 2024 class, Adem Bona (Overall 58) tops the Slasher board while Reed Sheppard (Overall 99) tops 3&D. A mode that merely re-sorted the board would be useless.

Face validity is strong and was obtained with **zero outcome optimisation**: the top historical 3&D wings are Reed Sheppard, Tyrese Haliburton and Mikal Bridges; the top stretch bigs are Lauri Markkanen and Jaren Jackson Jr.; the top rim protectors are James Wiseman, Zach Edey and Karl-Anthony Towns.

---

## 2. Team Need product semantics

| | General Draft Board | Team Need |
| --- | --- | --- |
| Question | how strong is this prospect? | how well does this prospect fit what we want? |
| Nature | historically validated prediction | transparent preference ranking |
| Target | actual draft outcome | **none — no ground truth exists** |
| Output | Overall Score 0–100, class-relative | Fit Score 0–100, peer-relative |
| Weights | fitted coefficients | user/basketball preferences |

The two are never blended. A Team Need ranking **must** be able to place a lower-Overall prospect above a higher-Overall one — that is the entire purpose of the mode, and §20 shows it happening.

## 3. Why Team Need is not a predictive model

There is no historical label recording which prospect "correctly fitted" which team. Nothing to predict means nothing to fit, so **no formula here is optimised against anything**: not drafted/undrafted, not draft pick, not Stage A probability, not the Overall Score, not NBA outcomes, not mock drafts (DEC-101).

Optimising against draft outcomes would silently convert Team Need into a second, worse copy of the General Board — answering the question the board already answers, while claiming to answer a different one.

What is validated instead: internal consistency, temporal stability, position behaviour, redundancy, missingness handling and sensitivity to methodological choices.

---

## 4. NCAA peer-reference methodology

Every statistic is converted to a **percentile against the full NCAA player population of the same season**.

| Property | Value |
| --- | --- |
| Population | all NCAA players in that season |
| Filter | ≥ 200 minutes and ≥ 10 games |
| Retained | **2,941–3,417 players per season** (of 6,854–9,860) |
| Storage | 101-point quantile grid per season × group × metric |
| Groups | `GLOBAL`, `G`, `F`, `C` |
| Metrics | 26 |
| Reads draft outcome | **never** |

**Why the minutes filter.** A percentile against a population full of eight-minute walk-ons is not a meaningful basketball statement — the median would sit far below any rotation player. The prospect being *scored* is never filtered; only the peer group is.

**Why this is leakage-safe**, the same three-part argument as the Stage A season-relative representation: the reference is the broad NCAA population and **not** the prospect sampling frame, so it cannot reintroduce the ML-1 sampling-frame leak; no draft outcome is read; and season Y prospects are compared to season Y peers, whose games conclude before the draft.

Peer values are computed by **the same `build_features` code** the prospect layer uses. A percentile is meaningless if the two sides are calculated differently.

## 5. Position-reference policy

`position_3` (G/F/C/UNKNOWN) is the only leakage-safe position source (DEC-067). `position_from_population` is prohibited — its granularity encodes the outcome. UNKNOWN falls back to the GLOBAL reference.

Decided **per dimension**, not blindly:

| Dimension | Reference | Why |
| --- | --- | --- |
| Shooting | **GLOBAL** | Shooting means the same at every position. A big who shoots like a guard is valuable *because* of that; position-relative would erase exactly the signal Stretch Big needs. |
| Playmaking | **GLOBAL** | A team asking for a playmaker wants absolute creation, not "good for a centre". |
| Box-score defence | **POSITION** | Blocks and steals are strongly position-dependent. Position-relative asks the answerable question: does this prospect generate defensive events at a high rate *for their position*? |
| Rebounding | **POSITION** | Six rebounds means different things for a guard and a centre — the canonical PRODUCT.md §8 example. |
| Size | **GLOBAL** | Absolute size is what "size" means. §19 shows position-relative size is actively misleading here. |
| Rim pressure | **GLOBAL** | A rim-oriented style is absolute, not position-relative. |

---

## 6. Dimension definitions

Six dimensions, **16 components, and no metric appears in two dimensions** — verified, so a user weighting two dimensions never double-counts one statistic.

| Dimension | Components | Reference | Combination |
| --- | --- | --- | --- |
| **Shooting** | `three_point_pct`, `three_point_attempt_rate`, `ft_pct`, `efg_pct` | GLOBAL | arithmetic mean |
| **Playmaking** | `ast_pct`, `tov_pct` *(inverted)* | GLOBAL | arithmetic mean |
| **Box-score defensive production** | `stl_pct`, `blk_pct` | POSITION | arithmetic mean |
| **Rebounding** | `orb_pct`, `drb_pct` | POSITION | arithmetic mean |
| **Size** | `height`, `weight` | GLOBAL | arithmetic mean |
| **Rim pressure** | `rim_attempt_share`, `free_throw_rate`, `rim_make_pct`, `unassisted_made_fg_share` | GLOBAL | arithmetic mean |

Equal weights throughout. Components within a dimension are substitutable evidence for one trait, so arithmetic mean is the right rule; there is no basketball reason to prefer 37%/22% splits and no target to derive them from.

## 7. Shooting

`mean(3P% pct, 3PA-rate pct, FT% pct, eFG% pct)`

Efficiency **and** volume **and** touch. 3P% alone crowns a low-volume specialist; volume alone crowns an inefficient chucker.

**Excluded:** `ts_pct` — |r| = 0.939 with `efg_pct` (ML-4 §6) and it includes free throws, which would double-count `ft_pct`. Generic `jump_shot_*` — schema breaks at 2020/21 (DEC-068).

## 8. Playmaking

`mean(AST% pct, 100 − TOV% pct)`

Creation volume and ball security. Turnover rate is inverted so higher always means better.

**Excluded:** `assist_to_turnover_ratio` — literally the ratio of the two components already present, pure double counting. `assists_per_40` — the same signal as AST% on a different denominator. `usage_pct` — measures role, not playmaking.

Volume is inherent in AST%, so no extreme low-usage assist ratio can manufacture an elite score.

## 9. Box-score defensive production

`mean(STL% pct, BLK% pct)`, position-relative.

> **This measures box-score defensive production, never defensive quality.** There is no matchup data, no opponent shooting when defended, no on/off context and no deterrence measure (ML_SPEC §18.3). The label is mandatory wherever it appears.

**Excluded:** `drb_pct` — belongs to Rebounding; including it in both would double-count it whenever a user weights Defence and Rebounding together. `personal_fouls_per_40` — not defensibly directional: a high foul rate can mean aggression or poor discipline, and nothing in the data separates them.

## 10. Rebounding

`mean(ORB% pct, DRB% pct)`, position-relative.

**Excluded:** `trb_pct` — a deterministic composite of the two components already present; including it would triple-count the same rebounds.

## 11. Size

`mean(height pct, weight pct)`, global.

**Never fabricated:** wingspan and standing reach are not in the data and are not invented. Age is prohibited (ML_SPEC §8.2).

## 12. Rim pressure

`mean(rim-attempt-share pct, FT-rate pct, rim-FG% pct, unassisted-made-FG-share pct)`

Shot diet at the rim, drawing contact, finishing, self-creation.

> **This is a shot-diet and finishing profile. It is NOT an athleticism measure and must never be presented as one.**

**Excluded:** layup/dunk/tip attempt shares — they sum to `rim_attempt_share` exactly (ML-4 verified max deviation 0.0000000000). `dunk_make_pct`, `tip_make_pct` — sparse rare-event ratios whose definedness is target-correlated (DEC-073).

## 13. Athleticism limitation

**Status: UNAVAILABLE. Not scored. No proxy.**

There is no athleticism measurement in the acquired data — no Combine testing, no vertical leap, no lane agility, no wingspan.

Dunk frequency is explicitly **not** a substitute: it is a style signal confounded by position, role and team system, not a vertical leap (ML_SPEC §18.2). The same applies to steals, blocks, height and rim-attempt share.

**Engine behaviour:** a custom request with `ATHLETICISM > 0` is **rejected** with an explicit unsupported status. The weight is never silently dropped and never redistributed across the other dimensions — silent redistribution would answer a different question than the one asked. A weight of exactly 0 is permitted.

This unblocks only when an approved Combine or physical-testing source is added to DATA.md.

---

## 14. Predefined profiles

| Profile | Formula | Eligibility |
| --- | --- | --- |
| **Shooter** | `geomean(mean(3P%, FT%, eFG%), 3PA-rate)` | — |
| **Slasher** | `RIM_PRESSURE` | — |
| **Playmaker** | `PLAYMAKING` | — |
| **3&D Wing** | `geomean(SHOOTING, DEFENCE)` | `position_3 ∈ {G, F}` |
| **Rim Protector** | `geomean(BLK% global, REBOUNDING, SIZE)` | `position_3 ∈ {F, C}` |
| **Stretch Big** | `geomean(SHOOTING, SIZE)` | `position_3 ∈ {F, C}` |

**Why geometric means.** Arithmetic mean allows full compensation — a huge score on one pillar rescues a poor one. That is wrong for archetypes that *require* all their pillars: a prospect who shoots brilliantly and defends poorly is not a 3&D wing, and a guard who shoots well is not a stretch big. The geometric mean cannot compensate.

**Rim Protector uses the GLOBAL block reference**, not the position-relative one used by the Defence dimension. Otherwise a 6-foot guard with a good-for-guards block rate would read as elite rim protection.

**Eligibility statuses:** `ELIGIBLE`, `OUT_OF_POSITION`, `UNKNOWN_POSITION`. Everyone is scored; out-of-position prospects rank behind eligible ones so the exclusion is visible rather than silent. **UNKNOWN counts as eligible** — excluding it would penalise missing data, which historically correlates with going undrafted. "3&D Wing" is an archetype name, not evidence of a true NBA wing position; only the coarse G/F distinction is leakage-safe.

## 15. Custom weighting

```
fit_raw = Σ(wᵢ · dᵢ) / Σ(wᵢ)     over REQUESTED and AVAILABLE dimensions
```

**Supported:** Shooting, Playmaking, Box-score defensive production, Rebounding, Size. **Unavailable:** Athleticism. **Optional (engine-ready, not a product slider yet):** Rim pressure — adding it to the custom UI requires a product decision.

Constraints: weights ≥ 0, at least one > 0, deterministic, no hidden General Board contribution. Weights need not sum to 1. Every rejection is explicit rather than silent.

Engine correctness checks (these test the engine, they are not candidate profiles):

| Request | scored | median | supported weight |
| --- | --- | --- | --- |
| 100% Shooting | 868 | 56 | 0.979 |
| 100% Playmaking | 868 | 63 | 0.979 |
| 50/50 Shooting + Defence | 868 | 58.5 | 0.979 |
| 70/30 Rebounding + Size | 868 | 61 | 0.980 |

## 16. Missingness and coverage

**A missing component is never a zero and never a 50.** Filling with either would make missingness a signal, and missing-data rows were disproportionately undrafted historically (DEC-071) — that is precisely how the outcome would sneak back in.

- **Component available** if non-null *and* its reliability minimum is met.
- **Reliability minimums:** 3P% needs ≥ 20 3PA, FT% ≥ 20 FTA, rim FG% ≥ 20 shot records. This blanks 3P% for **98 of 887** prospects — 2-for-4 from three is not evidence.
- **Dimension scored** when at least half its components are available, renormalising over what remains. Otherwise UNAVAILABLE.
- **Custom Fit Score** returned only when ≥ 50% of the requested weight lands on scorable dimensions. Otherwise UNAVAILABLE rather than a number built from a fraction of the request.

**Data coverage is reported alongside the score and never inside it.** Overall mean coverage is **97.2%**; 715 of 887 prospects have complete coverage and 9 have none at all (the unresolved prospects, retained rather than dropped).

There is a +0.30 correlation between coverage and Fit Score for a shooting-only request. That is **not** coverage leaking into the formula — it is a real basketball relationship: prospects who attempt too few threes to be judged tend to be non-shooters. A prospect is never rewarded for having more data.

## 17. Score scale

**Fit Score = the direct combined peer percentile, rounded to an integer 0–100.**

This is a **deliberate departure from the Overall Score**, which is class-relative. Dimension scores are already NCAA peer percentiles, so their combination already carries absolute trait meaning: "72" means "around the 72nd percentile of NCAA peers on the traits you asked for". Re-ranking within the draft class would destroy exactly that — "92nd percentile three-point volume" would collapse into "4th of 49 in this class".

The board goes the other way because a board *rank* is what that mode means. Neither is a probability.

**Prohibited labels:** "probability of fit", "probability of success", "NBA readiness probability".

**Ties** are genuine ties. Ranking orders by the continuous `fit_raw` before rounding; ties are never broken by player name, draft outcome, actual pick or any NBA information.

---

## 18. Temporal stability

Median dimension score by season, 2014–2025 — season-to-season drift (max − min):

| Dimension | Drift | Reading |
| --- | --- | --- |
| Playmaking | 5.6 | stable |
| Rim pressure | 7.1 | stable |
| Shooting | 9.2 | stable |
| Box-score defence | 11.3 | mild |
| Rebounding | 15.6 | population composition |
| **Size** | **17.7** | population composition |

Size drifts from a median of 73.0 (2014) to 58.8 (2021) and back to 64.5 (2025). This is **not** a normalisation defect: it tracks the composition of the declared early-entrant pool, which swung from 41 declarations in 2014 to 188 in 2021 (the COVID eligibility cohort, heavy with smaller guards) and back to 28 in 2025. The percentile scale is stable; the population being scored changed.

No dimension inflates without a population or data explanation.

## 19. Position stability

Median dimension score by coarse position:

| | Shooting | Playmaking | Defence | Rebounding | Size | Rim pressure |
| --- | --- | --- | --- | --- | --- | --- |
| **G** | **61.0** | **69.3** | 61.0 | 61.6 | 43.5 | 55.9 |
| **F** | 52.4 | 56.9 | 60.2 | 60.7 | 80.9 | 63.1 |
| **C** | 47.1 | 50.9 | 63.2 | **64.9** | **95.0** | **69.1** |

Median profile score by position:

| | Shooter | Slasher | Playmaker | 3&D | Rim Protector | Stretch Big |
| --- | --- | --- | --- | --- | --- | --- |
| **G** | **57.3** | 55.9 | **69.3** | 58.7 | 45.9 | 49.6 |
| **F** | 43.0 | 63.1 | 56.9 | 55.0 | 73.0 | 63.9 |
| **C** | 29.4 | **69.1** | 50.9 | 55.1 | **82.6** | 65.8 |

Everything behaves as the definitions imply: guards lead Shooting and Playmaking, centres lead Size, Rebounding and Rim Protector, and guards are correctly *low* on Rim Protector (45.9). **Defence is near-flat across positions (60.2–63.2)** — exactly what position-relative normalisation is for.

**One pattern worth naming:** centres median **95.0** on Size. The brief flagged "every C scoring 90+ on size" as a possible normalisation pathology. Here it is not a bug — it is the correct reading of a real physical fact under a deliberately GLOBAL reference, and it is what makes Stretch Big and Rim Protector work. A user who wants "big for a guard" should use the position-relative variant, which is computed but not shipped (§20).

## 20. Profile sensitivity

**Arithmetic vs geometric for conjunctive profiles.** Aggregate agreement is high — rank correlation 0.979–0.993, top-20 overlap 18–20 of 20:

| Profile | rank corr | top-20 overlap | geo median | arith median |
| --- | --- | --- | --- | --- |
| Shooter | 0.979 | 20 | 49.5 | 51.8 |
| 3&D Wing | 0.979 | 19 | 57.0 | 58.5 |
| Rim Protector | 0.993 | 20 | 58.5 | 60.6 |
| Stretch Big | 0.982 | 18 | 58.1 | 60.4 |

**Honest reading: the choice barely moves the aggregate ranking.** But the disagreement is concentrated exactly where the archetype definition matters — on unbalanced prospects:

| Profile | Prospect | Pillars | Geometric | Arithmetic |
| --- | --- | --- | --- | --- |
| 3&D | Joey Hauser | shooting 88, defence 8 | **26.5** | 47.9 |
| 3&D | Goodluck Okonoboh | shooting 9, defence 96 | **28.9** | 52.5 |
| Stretch Big | Derek Culver | shooting 22, size 97 | **45.6** | 59.1 |

Arithmetic mean would rate an elite shooter who cannot defend as a mid-tier 3&D wing. **Geometric is retained** — not because it measurably improves an aggregate, but because it is the correct definition and costs nothing.

**Global vs position-relative size.** Rank correlation +0.496 — a large difference. Position-relative medians: G **70.0**, F 62.0, C 60.0 — guards would score *higher* on "size" than centres, because tall guards are rarer within guards. That is actively misleading for a Size slider. **GLOBAL is retained.**

## 21. Historical face-validity examples

Development classes only, and a qualitative check of whether the NCAA statistics match the profile **definition**. Formulas were **not** changed because a name looked wrong, and no later NBA outcome was consulted. Names illustrate the historical NCAA profile, nothing more.

| Profile | Top historical scorers |
| --- | --- |
| **Shooter** | Spencer Littleson (2021, 97), Brannen Greene (2016, 96), Drake Jeffries (2022, 94) |
| **Slasher** | Elfrid Payton (2014, 86), Ben Simmons (2016, 86), Bruno Fernando (2019, 85) |
| **Playmaker** | Malachi Flynn (2020, 94), Shamorie Ponds (2019, 94), Tyger Campbell (2023, 93) |
| **3&D Wing** | **Reed Sheppard** (2024, 93), **Tyrese Haliburton** (2020, 90), **Mikal Bridges** (2018, 89) |
| **Rim Protector** | James Wiseman (2020, 98), Karl-Anthony Towns (2015, 97), Zach Edey (2024, 97) |
| **Stretch Big** | **Lauri Markkanen** (2017, 89), Jay Huff (2021, 86), **Jaren Jackson Jr.** (2018, 85) |

The 3&D list returning Mikal Bridges — the archetype's namesake in NBA discourse — and Stretch Big returning Markkanen and Jackson Jr. is meaningful precisely because **nothing in the construction knows who they became**.

## 22. Explanation logic

Deterministic and structured. **No generative model, no subjective scouting prose.**

Each score exposes up to 2 strengths (components ≥ 60th percentile), up to 2 limiting components (≤ 40th percentile), and separately the missing components.

Two rules keep explanations honest:

- **A missing component is never a weakness.** Too few three-point attempts to judge shooting is an absence of evidence, not evidence of poor shooting. Missing components are listed separately with reason "insufficient evidence".
- **The statistic is quoted in its natural direction.** An inverted component reads "29.7th percentile turnover rate (lower is better)" — the number a scout recognises — never its inversion.

Example output for a Stretch Big:

```
  3. Kel'el Ware              C     fit 75
       + height: 99th percentile
       + weight: 96th percentile
       - three-point volume: 19th percentile
       - free-throw touch: 26th percentile
```

Only components that actually feed the requested score can appear. The UI renders these later; this module decides *what* is said, never how it reads.

---

## 23. Limitations

1. **Defence is box-score production only.** No matchup data, no opponent shooting when defended, no on/off context, no deterrence. Steals and blocks are noisy and position-confounded.
2. **Athleticism does not exist in this system.** A team that genuinely needs athletic testing cannot get it here, and no proxy is offered.
3. **No wingspan, no standing reach.** Size is height and weight only — a real limitation for evaluating bigs.
4. **Position is coarse.** Only G/F/C is leakage-safe. "3&D Wing" cannot verify wing-ness; SG vs SF is not inferable.
5. **There is no ground truth**, so no accuracy claim can be made. The system can only be checked for consistency and transparency — nothing here says a high Fit Score leads to NBA success.
6. **Percentiles inherit the reference filter.** The ≥ 200-minute rule is a documented judgement, not an optimum.
7. **Low-volume shooters lose their 3P% component** (98 of 887). Their Shooting score rests on three components instead of four — better than trusting 2-for-4, but still less evidence.
8. **The conjunctive choice is justified by definition, not by measured aggregate impact** (§20). It matters for individuals, not for rank correlation.
9. **Size drift across seasons is population composition, not a stable trait scale** (§18).
10. **9 prospects have no dimension scores at all** — the unresolved rows, retained rather than dropped.

## 24. 2026 firewall

No 2026 prospect was scored, ranked, inspected or used to choose any formula. The NCAA percentile reference contains development seasons only; `scripts/build_team_need_reference.py` and `scripts/run_team_need.py` both **refuse** the holdout year outright rather than merely omitting it.

No profile weight, threshold, reference choice or combination rule was selected by looking at how any 2026 prospect scores.

## 25. NBA-comparable readiness

ML-8 (NBA statistical comparables) inherits two directly reusable pieces:

- **The peer-percentile machinery** — `PercentileReference` generalises to any population, including NBA seasons, which is exactly the normalised representation ML_SPEC §21 requires for comparing NCAA and NBA profiles.
- **The dimension vocabulary** — six factual dimensions provide a shared, interpretable space, which is the "shared representation space" that section lists as TBD.

Two constraints carry over unchanged: NCAA and NBA statistics must never be treated as one environment (19 PPG in the NCAA is not 19 PPG in the NBA), and the comparables engine must never read board features or targets.

## 26. Next phase

**ML-8 — NBA statistical comparables.**

Still open after that: the application layer, and the ML-9 holdout replay, which is the only phase permitted to open 2026.

The 2026 holdout remains sealed.
