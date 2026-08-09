# DraftLens — Data Specification

**Status:** Historical acquisition complete and validated (pass 7) — **no source or population is approved.**
**Pass 1 (source survey):** 2026-08-07 · **Pass 2 (targeted feasibility audit):** 2026-08-07 · **Pass 3 (Sportradar-centered strategy audit, §20):** 2026-08-07 · **Pass 4 (open data consolidation audit, §21):** 2026-08-07 · **Pass 5 (hoopR small-sample verification, §22):** 2026-08-07 · **Pass 6 (Wikidata DOB feasibility audit, §23):** 2026-08-07 · **Pass 7 (historical acquisition + validation, §24):** 2026-08-08
All "date accessed" values are 2026-08-07 unless stated otherwise.

This document records evidence-based findings on candidate data sources and on the historical prospect population. It ends with a **provisional** strategy (§16), an acquisition plan (§17), and a **GO/NO-GO assessment (§18)**. Nothing here is an approved dataset or population decision — those are the project owner's, and would be recorded in [DECISIONS.md](DECISIONS.md).

**Evidence labels:**

| Label | Meaning |
| --- | --- |
| **VERIFIED** | Directly observed by fetching the source, schema, or documentation |
| **PROVISIONAL** | Reasoned recommendation from verified evidence; owner approval required |
| **REPORTED** | Stated by a secondary source; not independently confirmed |
| **UNKNOWN** | Could not be determined |
| **BLOCKING** | Must be resolved before acquisition begins |

No dataset was bulk-downloaded. Pass 2 inspected documentation, schemas, robots.txt files, terms pages, archived snapshots, one unauthenticated API error response, and ~25 metadata calls to the public MediaWiki API (which returned HTTP 429 mid-scan — see §4.2; the scan was throttled and resumed, and the rate limit was respected, not circumvented).

---

## 1. What DraftLens needs the data to support

| # | Capability | Data required |
| --- | --- | --- |
| 1 | General Draft Board ranking | Pre-draft NCAA + physical features, draft outcomes as labels |
| 2 | Team Need ranking | Shooting / playmaking / defense / rebounding / physical measures |
| 3 | Position-aware sub-scores | Position labels + per-position distributions |
| 4 | Prospect detail pages | Raw box score, advanced stats, measurements, bio |
| 5 | Three NCAA→NBA comparables | NBA player statistical profiles |
| 6 | Python backtesting | Multi-year features + labels with clean time ordering |
| 7 | 2026 replay | Pre-draft-only 2026 snapshot + result held separately |
| 8 | Future draft classes | Repeatable acquisition for a class with no result yet |

MVP scope is NCAA prospects only ([MVP.md](MVP.md) §15). International players appear throughout the official and Wikipedia population sources and **must be filtered out deliberately**, never assumed absent.

---

## 2. The 2026 draft calendar — VERIFIED anchor dates

| Event | Date | Evidence |
| --- | --- | --- |
| Early entry declaration deadline | **Apr 24, 2026**, 11:59 pm ET | VERIFIED |
| NBA announces initial early entry list | **Apr 27, 2026** — 71 filed (60 college, 11 international) | VERIFIED — nba.com, with name/school/height/class table |
| NBA G League Combine | **May 8–10, 2026**, Chicago | VERIFIED |
| NBA Draft Lottery | **May 10, 2026** | VERIFIED |
| **AWS NBA Draft Combine** | **May 10–17, 2026**, Chicago; 73 invited | VERIFIED (dates); REPORTED (invitees) |
| Combine measurements published | **May 13, 2026** | VERIFIED via multiple outlets (§8.4) |
| NCAA early entry withdrawal deadline | **May 27, 2026**, 11:59 pm ET | VERIFIED |
| NBA early entry withdrawal deadline | **Jun 13, 2026**, 5:00 pm ET | VERIFIED |
| NBA announces **final** early entrant list | **Jun 15, 2026** — 31 remained (26 college, 5 international) | VERIFIED |
| **2026 NBA Draft R1** | **Jun 23, 2026**, 8:00 pm ET, Barclays Center | VERIFIED |
| **2026 NBA Draft R2** | **Jun 24, 2026** | VERIFIED |
| Picks | 60 selections, 2 rounds | VERIFIED |

**Minor open discrepancy:** the NBA announcement says **71** filed; Hoops Rumors' final-list article says **72** declared. Wikipedia's 2026 early-entrant list contains **31** bullets, exactly matching the official final count. UNKNOWN, low impact.

Sources: [nba.com early entry](https://www.nba.com/news/2026-nba-draft-early-entry-candidates) · [Hoops Rumors dates](https://www.hoopsrumors.com/2026/04/2026-nba-draft-dates-deadlines-to-watch.html) · [Hoops Rumors final list](https://www.hoopsrumors.com/2026/06/nba-announces-final-list-of-2026-draft-early-entrants.html) · [Wikipedia 2026 NBA draft](https://en.wikipedia.org/wiki/2026_NBA_draft) · [NCAA pre-draft key dates (PDF)](https://ncaaorg.s3.amazonaws.com/compliance/cbreform/CBR_NBADraftCombineDates.pdf)

---

## 3. Blocker 1 — the historical prospect population

This was the highest-priority question. Pass 2 resolved it substantially, and the answer is **partly negative in a way that constrains the product**.

### 3.1 The decisive finding

**VERIFIED:** Wikipedia's NBA draft articles carry a highly consistent structure across 2000–2026, obtained via the documented MediaWiki `action=parse` API:

| Section | 2000 | 2005 | 2011 | 2015 | 2020 | 2024 | 2026 | What it actually contains |
| --- | :-: | :-: | :-: | :-: | :-: | :-: | :-: | --- |
| Draft selections | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | Full pick table: pick, player, position, nationality, team, school |
| Notable undrafted players | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | **Outcome-selected** — see §3.3 |
| Early entrants | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **Name-level list** — see §3.2 |
| Automatically eligible entrants | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | **Rules text only — NO NAMES** |
| Invited attendees | ✅ | ✅ | ✅ | — | ✅ | ✅ | ✅ | **Green-room invitees (~13–24), NOT the Combine** |

**The single most important result of this audit — VERIFIED:** the "Automatically eligible entrants" section is a **statement of CBA eligibility rules, not a list of players**. Confirmed by reading the raw wikitext for 2015 and 2026, and by structural check across every year 2011–2026. Example (2026):

> *Players who do not meet the criteria for "international" players are automatically eligible if they meet any of the following criteria: They have no remaining college eligibility. If they graduated from high school in the U.S., but did not enroll in a U.S. college or university, four years have passed since their high school class graduated. They have signed a contract with a professional basketball team not in the NBA…*

**There is no published, name-level list of automatically-eligible (senior / exhausted-eligibility) players — for any year, from any source found.** This is not a gap in our search; it is a structural fact about how draft eligibility is published. Early entrants must *declare* and are therefore listed. Seniors become eligible *automatically* and are announced nowhere.

### 3.2 What IS recoverable — early entrants, name-level

**VERIFIED.** Wikipedia's "Early entrants" sections contain the **final** (post-withdrawal) list in a consistent bullet format:

```
* {{flagicon|USA}} [[Cameron Boozer]] – F, [[Duke Blue Devils men's basketball|Duke]] (freshman)
* {{flagicon|USA}} [[Nate Ament]] – F, [[Tennessee Volunteers men's basketball|Tennessee]] (freshman)
```

Name · nationality · position · school · class. The 2026 section contains **exactly 31 bullets**, matching the officially announced final count of 31 — a precise cross-validation of Wikipedia against the NBA's own announcement.

**VERIFIED counts** (`ncaaEE` = bullets linking a `men's basketball` program, i.e. the NCAA subset):

| Draft | Early entrants | NCAA subset | Undrafted-table rows |
| --- | --: | --: | --: |
| 2011 | 49 | 38 | not measured |
| 2012 | 50 | 41 | not measured |
| 2013 | 60 | 44 | not measured |
| 2014 | (list format differs — parser returned 0) | — | 33 |
| 2015 | 59 | 42 | not measured |
| 2016 | 72 | 48 | not measured |
| 2017 | 75 | 64 | not measured |
| 2018 | 88 | 70 | not measured |
| 2019 | 97 | 75 | not measured |
| 2020 | 84 | 66 | not measured |
| 2021 | not measured (rate-limited) | — | — |
| 2022 | 150 | 125 | 45 |
| 2023 | 99 | 78 | 35 |
| 2024 | 77 | 49 | 37 |
| 2025 | 46 | 27 | 33 |
| 2026 | 31 | 26 | **none (section absent)** |

Two years (2014, 2021) were not measured and must be re-checked; 2014 uses a different list markup. The trend is real and material: **NCAA early entrants ranged from ~26 to ~125 per year**, peaking in the COVID-eligibility era (2022) and collapsing sharply by 2025–26.

**Licensing — VERIFIED as clean:** Wikipedia content is CC BY-SA, accessible through the documented MediaWiki API. This is the **only** population candidate in this document with unambiguous redistribution rights. Attribution and share-alike obligations apply and must be honored.

**Rate limits — VERIFIED and respected:** an unthrottled scan received HTTP 429 after ~13 rapid requests. Any acquisition must throttle, set a descriptive User-Agent, and cache locally.

### 3.3 Why "Notable undrafted players" cannot be the undrafted class

**VERIFIED, and this is a trap worth stating plainly.** The section is populated with undrafted players *"who later appeared in NBA games."* Two disqualifying consequences:

1. **Outcome selection.** Membership is determined by post-draft NBA employment — the definition of a leakage-contaminated label. Training on it would teach the model to identify undrafted players who *succeeded*, not undrafted players generally.
2. **It does not exist for the replay year.** The 2026 article has **no** such section (VERIFIED) because no 2026 undrafted player has played yet. A feature that cannot be constructed for the target class is unusable by construction.

It has exactly one legitimate use: qualitative sanity-checking of historical output.

### 3.4 Option-by-option verdict

**Option A — full eligible NCAA population: REJECT.**
Requires a name-level roster of every automatically-eligible player. §3.1 verified no such list exists anywhere, for any year. Reconstructing it would mean inferring "no remaining college eligibility" per player from roster class, redshirt status, transfers, medical hardships, and the COVID blanket-eligibility waiver — an inference chain with no ground truth to validate against. False inclusions and exclusions would be large and unmeasurable. Not realistically constructable.

**Option B — final early entrants + NCAA seniors: PARTIALLY FEASIBLE, and the practical basis for the recommendation.**
The early-entrant half is **verified recoverable, name-level, 2011–2026** (§3.2). The senior half is **not recoverable** (§3.1). Two further concerns were assessed:
- *Does "senior" reliably mean automatically eligible?* **No.** The CBA criterion is "no remaining college eligibility," which decouples from nominal class year via redshirts, graduate transfers, medical waivers, and the COVID cohort. Class year is a proxy, not the criterion.
- *Would including all seniors add noise?* **Yes, heavily.** D-I fields several thousand seniors annually against ≤60 total picks. Most were never realistic NBA prospects, so the negative class would be dominated by players no scouting department ever evaluated — which is not the question DraftLens asks.

So Option B in full is both infeasible *and*, if it were feasible, statistically noisy. **Option B′ (below) is the usable form.**

**Option C — Combine participants: FEASIBLE ONLY IF NBA ACCESS CLEARS; genuine but narrower.**
The participant list is recoverable per year from the NBA Stats combine endpoints (§8), reportedly back to 2000-01, at roughly 60–75 players/year. It includes players who went undrafted, and it is the only long-history population with a truly *official* basis. Three serious caveats:
- It depends entirely on the unresolved NBA terms question (§5) — **BLOCKING**.
- **Wikipedia does NOT provide it.** The "Invited attendees" sections are green-room invitations (~13–24 players), a different and much smaller thing. This correction matters: pass 1's population options must not be read as Wikipedia-satisfiable.
- **The 2024 mandatory-participation rule is a regime change** (VERIFIED). Before 2024, being invited was itself a selection signal; from 2024, invited players are required to attend under the CBA subject to exceptions. A model trained pre-2024 and tested on 2026 crosses that boundary.

*Can a Combine-only model still be defended?* **Yes, but only under restated framing:** "ranking serious NBA Draft prospects **within the league-selected Combine pool**." That is a narrower and more selected question than ranking every eligible player — the negative examples become near-misses rather than the general field, so the model learns to order players the league had already identified. It is defensible and honest, provided the product says so.

**Option D — external historical prospect dataset: REJECT.**
Every candidate examined derives from sources this project has already verified as blocked or robots-disallowed. Specifically: `JasonG7234/NBA-Draft-Model` states its data comes from **RealGM, Basketball-Reference, Barttorvik, 247Sports, and HoopMath**; `mathgonzaga/NBADraftModel` uses **Barttorvik**; others use Basketball-Reference. Consuming these would **launder** data we determined we may not collect ourselves — the restriction attaches to the data, not to who fetched it. Additionally, 247Sports is a recruiting-ranking service, which DEC-013 prohibits as a model feature. No academic or DOI-citable dataset with drafted + undrafted + NCAA statistics was found. Reject on provenance, not on quality.

**Option E — NCAA performance threshold pool: VIABLE AS A SUPPLEMENT, NOT AS THE DEFINITION.**
Objectively derivable from CBBD, fully reproducible, and it does capture the intuition that "serious prospect" correlates with role and production. But making it the *definition* of the population replaces a factual eligibility question with a modeling assumption, and every threshold silently encodes a prior about who counts. That redefines the product: DraftLens would no longer rank draft prospects but rank "players meeting our criteria." **No thresholds are invented here.** Its legitimate role is as a *filter applied to* a factually-defined population, and any threshold must be an explicit, recorded decision.

### 3.5 Population comparison

| Strategy | Historical coverage | Includes undrafted | Reproducible | Bias | Noise | Entity matching | Product fidelity | Recommendation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **A** — Full eligible NCAA | None (no source) | Yes in principle | ❌ | Unmeasurable | Extreme | N/A | Highest | **Reject — not constructable** |
| **B** — Early entrants + seniors | Early entrants 2011–26 ✅; seniors ❌ | Yes | ❌ (senior half) | Inference-driven | Very high | Hard | High | **Reject as stated** |
| **B′** — Final NCAA early entrants ∪ drafted NCAA players | **2011–2026 VERIFIED** | **Yes — declared-and-undrafted** | ✅ CC BY-SA | Excludes undrafted seniors | Moderate | Name+school, medium | Good, with caveat | **Preferred (provisional)** |
| **C** — Combine participants | 2000-01+ if NBA clears | Yes | ⚠️ terms BLOCKING | League pre-selection | Low | Weakest join (§9.3) | Narrower framing | **Best fallback / complement** |
| **D** — External datasets | Varies | Yes | ❌ | Inherited | Unknown | Unknown | Unknown | **Reject — provenance laundering** |
| **E** — Threshold pool | Full CBBD range | Yes | ✅ | Assumption-encoded | Tunable | Easy (single source) | Redefines product | **Supplement only** |

### 3.6 Recommendations — PROVISIONAL, owner approval required

1. **Preferred: Option B′** — the union of (a) final NCAA early entrants per draft year, from Wikipedia, and (b) all NCAA players actually drafted that year. Recoverable, name-level, 2011–2026, under a clean CC BY-SA license, with the class-year and school fields needed for matching. It yields real undrafted examples: an academic source notes 30 early entrants went undrafted in 2016 alone, and 2022's 125 NCAA early entrants against 60 total picks implies a large declared-and-undrafted class.
2. **Best fallback: Option C** — Combine participants, if and only if the NBA terms question clears. Also valuable as a *complement* to B′: the union of both covers declared underclassmen and league-identified prospects including seniors who attended the Combine.
3. **Reject: A, D.** **Supplement only: E.**

### 3.7 Ground-truth wording — a product question for the owner

**This audit does require a wording change, and the owner must decide it.**

[PRODUCT.md](PRODUCT.md) §14 currently frames the analytical question as:

> *"Using only information available before each historical draft, how well can pre-draft data explain or reproduce where prospects were selected?"*

Under Option B′ the honest framing is narrower — approximately:

> *"Among NCAA players who entered a given draft as declared early entrants, plus those actually selected, how well can pre-draft data explain or reproduce where they were selected and who went undrafted?"*

Under Option C it is narrower still: *"…within the league-selected Combine pool…"*

Neither is a weaker product — both are precise about what was actually measured. But the difference is real and must be stated in the product UI, not buried. **[PRODUCT.md](PRODUCT.md) was not edited.** This is flagged for owner decision (§19).

---

## 4. NCAA / college performance data

### 4.1 CollegeBasketballData.com (CBBD) — see §6 for the deep audit

Strongest programmatic NCAA candidate. Schema verified, terms unverified.

### 4.2 Wikipedia / MediaWiki API — population and draft outcomes

- **Access — VERIFIED:** documented public API (`action=parse`), no key required, JSON, section-level or full wikitext.
- **License — VERIFIED:** CC BY-SA. Redistribution permitted with attribution and share-alike. **The only source in this document with unambiguous redistribution rights.**
- **Rate limits — VERIFIED:** HTTP 429 after ~13 rapid requests. Must throttle.
- **Limitations:** wikitext parsing is brittle (2014's early-entrant list uses different markup); community-maintained, so per-year completeness varies; no player statistics.

### 4.3 Sources rejected or reference-only (pass 1, re-confirmed in pass 2)

| Source | Status | Evidence |
| --- | --- | --- |
| **Sports-Reference CBB** | **Reference only** | VERIFIED 403 on four separate paths, including the `player-seasons-coverage-summary` page, which returned a Cloudflare *"Just a moment… Enable JavaScript and cookies"* challenge. Their own coverage documentation is unreadable to us. BPM available from 2010-11 (REPORTED via their blog) |
| **Basketball-Reference** | **Reference only** | Same operator, same restrictions |
| **Barttorvik** | **Reject for ingestion** | VERIFIED `robots.txt`: `Disallow: /playerstat.php`, `Disallow: /*.json` — precisely the player-stats and JSON paths |
| **stats.ncaa.org** | **Reject** | VERIFIED 403 Akamai on both the site and its `robots.txt` |
| **KenPom** | **Reject** | Paid; redistribution barred |
| **SportsDataIO / Sportradar** | **Reject** | Commercial licensing and cost |
| **hoopR / SportsDataverse** | **Investigate further** | R-first; Python parity unverified against DEC-033 |

---

## 5. Blocker 3 — NBA data access

### 5.1 There IS an official NBA API, and it is closed to us

**VERIFIED — the decisive new finding.** <https://developerportal.nba.com/> states:

> *"The NBA Developer Portal is only available for NBA Teams and Official NBA Business Partners, please do not reach out without the proper affiliation."*

It also notes *"No payment is required to sign up, generate API credentials, and use the APIs"* — the barrier is affiliation, not cost. DraftLens is neither an NBA team nor an official business partner.

**Consequence:** the `stats.nba.com` endpoints are not an undocumented corner of an otherwise-open platform. They sit **outside** the channel the NBA created for programmatic access and explicitly gated. That materially weakens any argument that automated use is implicitly permitted.

### 5.2 The Terms of Use remain unreadable — BLOCKING

**VERIFIED across four attempts:**
- Live <https://www.nba.com/termsofuse> returns HTTP 200 but is client-rendered; the ~470 KB of served HTML contains **zero** occurrences of "data mining", "robots", "spiders", "scrape", "harvest", or "extract".
- Two Wayback snapshots (2017 and 2023 `id_` raw captures) are also SPA shells with the same zero-hit result.
- A 2023 legal survey of 43 sites' terms ([Zuva](https://zuva.ai/blog/llm-breach-of-terms-of-use/)) does **not** cover NBA.com.

`www.nba.com/robots.txt` disallows `/api/*` and `/stats/events/` but not `/stats/` broadly; `stats.nba.com/robots.txt` returns a 301 with an empty body. **robots.txt is not a license, and the absence of a disallow is not permission.**

The widely used [`swar/nba_api`](https://github.com/swar/nba_api) client (MIT — *software* license) points users to NBA.com's Terms without reproducing them, and warns that NBA.com publishes no information about endpoint changes, i.e. these endpoints are undocumented and unstable by design.

**Status: BLOCKING.** A human must open the Terms of Use in a browser and record the verdict. This single question gates Combine data, draft outcomes, and the comparables pool simultaneously.

### 5.3 NBA fallbacks by family

**A. Draft outcomes — STRONG fallback exists.**
**Wikipedia draft articles** (§4.2) carry the complete 60-pick table for every year: pick, player, position, nationality, team, school. CC BY-SA, documented API. This fully removes NBA Stats from the critical path for draft targets. The cost is losing NBA `PERSON_ID`, which weakens the join to NBA player statistics.
Secondary: CBBD `GET /draft/picks`, which carries `athlete_id` linking straight to CBBD NCAA stats.

**B. Combine measurements — WEAK fallback only.**
- Kaggle "NBA Anthropometric" (REPORTED 2000–2023, "acquired using NBA Stats API"): a self-declared derivative of the official data, license UNKNOWN, **ends 2023 so it cannot serve the 2026 replay**.
- Secondary press (NBADraft.net, On3, NBC Sports, Bleacher Report) published 2026 Combine measurements on **May 13, 2026** — VERIFIED to exist, but these are article-formatted reprints, not a reproducible dataset, and are themselves derivatives of official data.
- **There is no clean, complete, reproducible non-NBA source for Combine data.** If §5.2 fails, Combine measurements are effectively lost, and with them most of the Athleticism and Physical Profile sub-scores.

**C. NBA player statistics — MEDIOCRE fallback.**
[balldontlie.io](https://www.balldontlie.io/) — REPORTED: free tier 5 requests/minute covering Teams, Players, Games; terms *prohibit reselling, redistributing, or sublicensing the data* and building competing products; it explicitly disclaims ownership of underlying sports data and warns that league/team IP may attach. So: usable to compute with, **not** to redistribute — and the free tier lacks the advanced/usage dimensions the comparables engine needs. Depth and terms both fall short.
Community Kaggle NBA datasets exist but generally derive from Basketball-Reference or NBA Stats — the same laundering objection as §3.4 Option D.

---

## 6. Blocker 2 — CollegeBasketballData deep audit

### 6.1 Access and authentication — VERIFIED

An unauthenticated request to `https://api.collegebasketballdata.com/teams` returned **HTTP 401** with a documented message:

> `{"message":"Unauthorized. Did you forget to add \"Bearer \" before your key? Go to CollegeBasketballData.com to register for your free API key. See the CFBD Blog for examples on usage..."}`

Bearer-token auth, free key by registration. No authentication was bypassed and no key was registered — **account creation is an outward-facing action requiring owner approval** (§19).

### 6.2 Software license vs. data rights — the distinction the project must not blur

**VERIFIED:**
- `cbbd` on PyPI is **MIT licensed** — this covers the **Python client library** only.
- The `cbbd-python` repo has **no LICENSE file at its root** (checked directly).
- `cbbd-r`'s LICENSE file is an unfilled template stub (`YEAR: 2025 / COPYRIGHT HOLDER: cbbdr authors`).
- Any "MIT" appearing on an OpenAPI/Swagger page describes the **API specification or generator**, never the basketball data served through it.

**Therefore: MIT says nothing whatsoever about rights in the underlying basketball data.** These are separate legal objects and must be tracked separately in this document and in any attribution we publish.

### 6.3 Data rights — UNKNOWN, and the available evidence is restrictive

**VERIFIED:** <https://collegebasketballdata.com/terms> and its sibling <https://collegefootballdata.com/terms> are **both client-rendered Vue applications**. The CFBD terms page returned 956 KB of HTML containing **23 characters** of extractable text. Wayback attempts did not yield readable text either. The operative terms cannot be read by automated means.

**REPORTED** (search-engine excerpt of the CFBD terms — same operator, Bill Radjewski / `BlueSCar`):
- *"Reselling or redistributing data obtained from the API without explicit permission is prohibited."*
- Attribution is *"appreciated where appropriate"*; users are asked to act in good faith.
- Free tier: **1,000 API calls per calendar month**; higher tiers via Patreon.

**If that redistribution clause is accurate, it has a direct product consequence:** DraftLens could compute with CBBD data but **could not commit CBBD-derived processed datasets to a public repository or attach them to a Devpost submission** without explicit permission. Since [PRODUCT.md](PRODUCT.md) §20 makes reproducibility a principle — qualified as "wherever licensing allows" — this would force the pipeline to be reproducible *by re-running acquisition with the user's own key*, not by shipping data. That is a legitimate and common pattern, but it must be a deliberate choice.

**Status: BLOCKING.** A human must read both terms pages in a browser.

**Upstream provenance: UNKNOWN.** The `athlete_source_id` string field implies a third-party upstream (ESPN is the pattern in the sibling CFBD project) but this was not confirmed. If an upstream provider's terms flow through, they may bind us regardless of CBBD's own terms.

### 6.4 Rate/quota feasibility — PROVISIONAL

1,000 calls/month (REPORTED) against a per-season, per-team-or-conference query signature (§6.5). At roughly one call per conference per season, ~32 D-I conferences × 15 seasons ≈ 480 calls for one full pass of player season stats, plus a similar order for shooting stats. **A full historical pull plausibly fits within one or two months of free tier if carefully batched and cached — but it leaves no room for iteration.** Verify actual pagination behaviour before relying on this.

### 6.5 Endpoint surface — VERIFIED

`StatsApi`: `GET /stats/player/season`, `GET /stats/player/shooting/season`, `GET /stats/team/season`, `GET /stats/team/shooting/season`.
`DraftApi`: `GET /draft/picks`, `/draft/positions`, `/draft/teams`.
`TeamsApi`: rosters. Also Games, Plays, Lineups, Ratings, Rankings, Recruiting, Lines, Venues, Conferences.

**Query signature — VERIFIED:** `season` is **required**; `team` or `conference` is **required for shooting stats** (either/or), optional for season stats; optional `season_type` and date-range filters. This shapes the acquisition plan: shooting stats must be pulled per team or per conference, never league-wide in one call.

**Historical coverage — UNKNOWN, BLOCKING.** REPORTED "games from 2003+". The earliest season with complete **player season stats**, **player advanced stats**, and **player shooting-profile stats** could not be determined without a key. The shooting-profile endpoint is play-by-play-derived and is expected to start later than the box-score endpoints. **2025-26 availability also unverified.** These three dates set the real training window (§7).

### 6.6 CBBD schema audit — VERIFIED fields

**Legend:** ✔ = present and directly useful · ➜ = derivable · ✖ = absent

#### `PlayerSeasonStats` (`GET /stats/player/season`)

| Field | Meaning | DraftLens use | Leakage risk |
| --- | --- | --- | --- |
| `season`, `season_label` | Season | Temporal key — **essential for cutoffs** | None |
| `team_id`, `team`, `conference` | Program | Context, strength-of-competition | None |
| `athlete_id` | CBBD player ID | **Primary join key**; matches `DraftPick.athlete_id` | None |
| `athlete_source_id` | Upstream ID (provenance UNKNOWN) | Secondary join | None |
| `name`, `position` | Identity, position | Matching; position normalization | Low — verify it is the pre-draft label |
| `games`, `starts`, `minutes` | Role volume | Role weight, eligibility filters | None |
| `points` | Scoring | Scoring dimension | None |
| `assists`, `turnovers`, `assists_turnover_ratio` | Playmaking | **Playmaking sub-score** | None |
| `steals`, `blocks` | Defensive events | **Defense sub-score** | None |
| `fouls` | Fouls | Context | None |
| `usage` | Usage rate | **Role/usage dimension** | None |
| `offensive_rating`, `defensive_rating`, `net_rating` | Per-possession efficiency | **Efficiency sub-scores** | None |
| `porpag` | Points over replacement per adjusted game | Value metric | None |
| `effective_field_goal_pct`, `true_shooting_pct` | Shooting efficiency | **Shooting sub-score** | None |
| `free_throw_rate` | FTA/FGA | Rim pressure proxy → **Slasher profile** | None |
| `offensive_rebound_pct` | ORB% | **Rebounding sub-score** | None |
| `field_goals` {made, attempted, pct} | FG / FG% | Shooting | None |
| `two_point_field_goals` {…} | 2P / 2P% | Shooting, interior scoring | None |
| `three_point_field_goals` {…} | **3PM, 3PA, 3P%** | **Shooter / Stretch Big / 3&D profiles** | None |
| `free_throws` {…} | FT / FT% | Shooting touch indicator | None |
| `rebounds` {total, offensive, defensive} | Rebound counts | Rebounding | None |
| `win_shares` {total, offensive, defensive, total_per40} | Value | Overall value dimension | None |

#### `PlayerSeasonShootingStats` (`GET /stats/player/shooting/season`)

| Field | Meaning | DraftLens use | Leakage risk |
| --- | --- | --- | --- |
| `tracked_shots` | Shots with type data | **Coverage/reliability gate** | None |
| `assisted_pct` | Share of makes assisted | **Self-creation vs. play-finishing** — separates Slasher from Rim Runner | None |
| `dunks`, `layups`, `tip_ins`, `two_point_jumpers`, `three_point_jumpers` | Each with made / attempted / pct / assisted / assisted_pct | **The core of profile definitions** | None |
| `attempts_breakdown` | Share of attempts by shot type | **Shot-diet / style vector** | None |
| `free_throw_rate` | FTA/FGA | Rim pressure | None |
| `athlete_id`, `athlete_name` | Identity | Join | None |

This endpoint is the strongest single argument for CBBD: shot-type mix with assisted rates makes Shooter, Slasher/Rim Attacker, Stretch Big, and Rim Runner **measurable** rather than asserted, satisfying DEC-008.

#### `TeamRosterPlayer` (`TeamsApi`)

| Field | DraftLens use | Leakage risk |
| --- | --- | --- |
| `id`, `source_id`, `name`, `first_name`, `last_name` | Identity, matching | None |
| `position` | Position normalization | Low |
| `height`, `weight` | **Listed** (not measured) size — must stay separate from Combine values | Low — must be the pre-draft-season roster |
| `hometown` | Disambiguation | None |
| **`date_of_birth`** | **Age at draft** — the approved age feature | None if from pre-draft roster |
| `start_season`, `end_season` | Class inference | ⚠️ `end_season` may be updated post-hoc — do not use to infer eligibility |
| `jersey` | — | None |

#### `DraftPick` (`GET /draft/picks`)

| Field | DraftLens use | Leakage risk |
| --- | --- | --- |
| `athlete_id` | **Deterministic join to NCAA stats** | None (the key itself) |
| `year`, `round`, `pick`, `overall` | **THE TARGET** | 🚫 **TARGET ONLY — never a feature** |
| `overall_rank`, `position_rank` | Derived rankings | 🚫 Target-derived |
| `draft_team_id`, `draft_team` | Drafting team | 🚫 Post-draft |
| `source_team_*`, `source_team_college_id` | College | Matching | None |
| `name` | Identity | Matching | None |
| `height`, `weight` | Size at draft | ⚠️ Provenance UNKNOWN — if measured at the Combine it is pre-draft; if a later NBA bio value it is post-draft. **Must verify before use** |

**Contains drafted players only** — no undrafted representation. Confirms §3.

#### Requested-metric coverage

| Family | Metric | CBBD |
| --- | --- | --- |
| Shooting | FG%, 2P%, 3P%, 3PA, FT%, TS%, eFG% | ✔ all present |
| Shooting | Shot-type breakdown | ✔ **exceptionally strong** |
| Playmaking | Assists, turnovers, AST/TO | ✔ |
| Playmaking | AST%, TOV% | ✖ — ➜ derivable from minutes + team possessions |
| Defense | Steals, blocks, defensive rating | ✔ |
| Defense | STL%, BLK% | ✖ — ➜ derivable |
| Rebounding | Rebounds (O/D/T), ORB% | ✔ |
| Rebounding | DRB%, TRB% | ✖ — ➜ derivable |
| Role | Minutes, usage | ✔ |
| Role | Possessions | ✖ — ➜ derivable from team season stats |
| Efficiency | ORtg, DRtg, net rating, win shares, PORPAG | ✔ |
| Efficiency | BPM | ✖ — not derivable from these primitives |

Only **BPM** is genuinely unavailable. The four missing rate stats are derivable given team-level possession data, which CBBD also serves — a **modeling task**, recorded here as a constraint on [ML_SPEC.md](ML_SPEC.md), not a data gap.

---

## 7. Research window validation

### 7.1 Year-coverage matrix

| Data family | Earliest reliable year | Basis | Label |
| --- | --- | --- | --- |
| NCAA basic stats (CBBD) | 2003? | REPORTED "games from 2003+"; player-stat start unconfirmed | **UNKNOWN — BLOCKING** |
| NCAA advanced stats (CBBD) | Unknown | Requires API key to test | **UNKNOWN — BLOCKING** |
| NCAA shooting profiles (CBBD) | Unknown, expected latest | Play-by-play-derived | **UNKNOWN — BLOCKING** |
| NCAA advanced (SR, reference) | 2010-11 | BPM added at 2010-11 | REPORTED |
| **Prospect population — early entrants** | **2000; name-level verified 2011–2026** | Wikipedia scan | **VERIFIED** |
| **Prospect population — "automatically eligible"** | **Never** | Rules text only, all years | **VERIFIED (negative)** |
| Draft outcomes (Wikipedia) | Effectively unlimited | Consistent structure 2000–2026 | **VERIFIED** |
| Draft outcomes (NBA Stats) | Unlimited | Official | Gated by §5.2 |
| Combine | 2000-01 | Two partly independent reports | REPORTED; gated by §5.2 |
| NBA comparable stats | Long | NBA Stats / fallbacks | Gated by §5.2 |
| Age / DOB | Unknown fill rate | CBBD roster field verified present | **UNKNOWN** |

### 7.2 Window assessment

| Window | Drafts | Assessment |
| --- | --- | --- |
| 2000–2025 | ~26 | Combine reaches back this far, but "Automatically eligible entrants" sections don't appear until 2011 and NCAA advanced/PBP data almost certainly doesn't reach it. Largest era-comparability problems |
| 2005–2025 | ~21 | Same shooting-profile problem |
| **2011–2025** | **15** | Aligns with three independent boundaries: Wikipedia's eligibility-section structure stabilizes at 2011; SR added college BPM at 2010-11 (proxy for broad advanced-stat reliability); early-entrant name lists verified continuously from 2011. Verified NCAA early-entrant volume across it: ~26–125/year |
| 2015–2025 | 11 | Safest data quality; fewer folds; small undrafted pool in low years (2025: only 27 NCAA early entrants) |

### 7.3 Recommendation — **2011–2025 confirmed as the DATA RESEARCH WINDOW (PROVISIONAL)**

The proposal survives the audit, and pass 2 strengthened rather than weakened it: 2011 is now supported by a **directly verified** structural boundary (Wikipedia's eligibility sections) in addition to the pass-1 BPM proxy.

**Two caveats stand:**
1. The binding constraint is still CBBD's own advanced and shooting coverage, which remains **UNKNOWN pending API access**. If shooting profiles start after 2011, the window must move forward.
2. The **2024 mandatory-Combine regime change** sits inside the window (§8.3).

**This is a research window, not the ML training window** — that remains for [ML_SPEC.md](ML_SPEC.md).

---

## 8. Combine data

### 8.1 Official endpoints — VERIFIED schemas (via `nba_api` docs)

`draftcombineplayeranthro`: `HEIGHT_WO_SHOES, HEIGHT_W_SHOES, WEIGHT, WINGSPAN, STANDING_REACH, BODY_FAT_PCT, HAND_LENGTH, HAND_WIDTH` + identity fields.
`draftcombinedrillresults`: `STANDING_VERTICAL_LEAP, MAX_VERTICAL_LEAP, LANE_AGILITY_TIME, MODIFIED_LANE_AGILITY_TIME, THREE_QUARTER_SPRINT, BENCH_PRESS`.
`draftcombinespotshooting`: made/attempted/pct at 15 ft, college 3, NBA 3 across five locations.
`draftcombinestats`: the combined table — **`SeasonYear` accepts the literal `All Time`** (pattern `^(\d{4}-\d{2})|(All Time)$`), so the full history is one request.

### 8.2 Coverage
REPORTED from 2000-01 (Kaggle card + AWS "more than 25 years"). Per-year completeness UNKNOWN.

### 8.3 Missingness and the 2024 regime change
- Only ~60–75 invited per year against a much larger pool — **most prospects have no Combine record at all**.
- Attending ≠ testing: anthropometrics are well populated; drills less so; shooting drills sparsest.
- **VERIFIED:** *"Beginning in 2024, participation in the combine became mandatory for a player to be eligible for the draft."* Combine *presence* therefore means something different before and after 2024 — a regime break inside the research window that behaves like leakage across a train/test boundary.

### 8.4 2026 availability
Combine ran May 10–17, 2026; measurements were published **May 13, 2026** and are VERIFIED to exist in public reporting. Whether the 2026 season is present in the NBA Stats table is unverified (gated by §5.2).

---

## 9. Entity matching

### 9.1 Confidence tiers

| Tier | Join | Basis |
| --- | --- | --- |
| **Exact** | CBBD stats ↔ CBBD draft picks | Shared `athlete_id` |
| **Exact** | NBA drafthistory ↔ NBA player stats | Shared `PERSON_ID` (if NBA access clears) |
| **High** | Combine ↔ NBA drafthistory | `PLAYER_ID` = `PERSON_ID` for players who reached the NBA |
| **Medium** | **Wikipedia population ↔ CBBD NCAA stats** | Name + school + class year — the new critical join under Option B′ |
| **Review required** | **Combine ↔ NCAA stats** | Name + position only |

### 9.2 The two weakest links

1. **Combine ↔ NCAA** (pass 1 finding, unchanged): combine records expose `TEMP_PLAYER_ID` alongside `PLAYER_ID`, and a player who never reaches the NBA plausibly never receives a real `PERSON_ID`. **Match failure concentrates in the undrafted class** — precisely the negative examples the population depends on.
2. **Wikipedia ↔ CBBD** (new under Option B′): joins on name + school + class. Wikipedia gives clean school links (`[[Duke Blue Devils men's basketball|Duke]]`) which normalize well, and class year is a strong disambiguator — so this is more tractable than the Combine join. But it is still name-based, and §9.3's hazards apply.

### 9.3 Name hazards
Suffixes (Jr., Sr., II, III) · initial spacing (`A.J.`/`AJ`) · accents · hyphenation · apostrophes (`De'Andre`) · nicknames vs. legal names · duplicate names within a class · transfers and multi-school careers · school naming conventions differing across sources · position labels disagreeing across all sources.

### 9.4 Proposed identity architecture — conceptual only

```
canonical_player_id          DraftLens-owned surrogate key
  ├── source_ids             {cbbd_athlete_id, cbbd_source_id, nba_person_id,
  │                           combine_temp_player_id, wikipedia_page_title}
  ├── normalized_name        casefolded, unaccented, suffix-stripped
  ├── name_variants[]        every raw spelling seen, with source
  ├── date_of_birth          nullable
  ├── college                nullable; multi-valued for transfers
  ├── class_year             freshman | sophomore | junior | senior | graduate
  ├── draft_year             the class the record belongs to
  └── match_confidence       exact | high | medium | review_required
```

`wikipedia_page_title` is a genuinely useful addition — Wikipedia links are stable, unique, and disambiguated by the community, making them a serviceable natural key for the population layer.

**Non-negotiable:** unmatched and low-confidence records must be **surfaced and counted**, never silently dropped.

---

## 10. Temporal leakage audit

| Feature family | Classification | Notes |
| --- | --- | --- |
| NCAA box-score stats (final season) | ✅ **SAFE PRE-DRAFT** | Season concluded before the draft |
| NCAA advanced stats (usage, ORtg/DRtg, TS%, ORB%, win shares, PORPAG) | ✅ **SAFE PRE-DRAFT** | Derived from completed play |
| NCAA shot-type splits, assisted% | ✅ **SAFE PRE-DRAFT** | Same |
| Combine anthropometrics | ✅ **SAFE PRE-DRAFT** | Measured in May |
| Combine drills, shooting drills | ✅ **SAFE PRE-DRAFT** | Same |
| Combine *participation* flag | ⚠️ **REGIME RISK** | Meaning changed in 2024 (§8.3) |
| Age at draft date | ✅ **SAFE PRE-DRAFT** | Only if computed against that year's draft date |
| Early-entry declaration / withdrawal status | ✅ **SAFE PRE-DRAFT** | Withdrawal deadline precedes the draft |
| Class year (freshman…senior) | ✅ **SAFE PRE-DRAFT** | From the pre-draft-season roster |
| CBBD roster `end_season` | ⚠️ **LEAKAGE RISK** | May be updated after the fact; must not be used to infer eligibility |
| `DraftPick.height` / `.weight` | ⚠️ **LEAKAGE RISK** | Provenance unverified (§6.6); may be a post-draft NBA bio value |
| Position from a *current* NBA bio | ⚠️ **LEAKAGE RISK** | Reflects post-draft role |
| Listed height/weight from a current bio | ⚠️ **LEAKAGE RISK** | Bio fields are updated post-draft |
| **Wikipedia "Notable undrafted players"** | 🚫 **OUTCOME-SELECTED — PROHIBITED** | Membership requires later NBA appearance (§3.3) |
| **Draft pick number, round, drafting team** | 🚫 **TARGET ONLY** | The label |
| **Undrafted status** | 🚫 **TARGET ONLY** | Also a label |
| **NBA career / rookie statistics** | 🚫 **TARGET ONLY** | See §10.1 |
| Current NBA team / experience / current age | 🚫 **POST-DRAFT ONLY** | Present-day state |
| Existence of an NBA `PERSON_ID` | ⚠️ **LEAKAGE RISK** | Implies reaching the NBA; must not be a feature or a join filter |
| Retroactive NCAA stat corrections | ⚠️ **LEAKAGE RISK** | Low impact, non-zero |
| Analyst rankings, mock drafts, 247Sports recruiting ranks | 🚫 **PROHIBITED AS FEATURES** | DEC-013 — benchmark only |

### 10.1 The NBA-statistics firewall

NBA player statistics are **required** for one purpose and **forbidden** for another:

- ✅ **Allowed:** `nba_comparable_profiles` — actual NBA players described by actual NBA production.
- 🚫 **Forbidden:** any path by which NBA production enters `prospect_features`. Including the non-obvious: deriving normalization constants from NBA outcomes, selecting NCAA features by correlation with later NBA success, or restricting the comparable pool using knowledge of what a prospect became.

**The two datasets must never be joined on `canonical_player_id` during board training or inference.** The only legitimate meeting point is the rendered prospect page, after both are computed independently.

---

## 11. Dataset layers — conceptual

| Layer | Purpose | Contains | Readable by |
| --- | --- | --- | --- |
| `prospect_eligibility` | Who is in each class's pool | draft_year, canonical_player_id, eligibility_basis (`early_entry` \| `drafted` \| `combine_invitee`), source, as-of date | Population construction |
| `prospect_features` | Pre-draft evidence | NCAA stats, advanced stats, shot-type splits, Combine data, age, position, coverage flags | Board, Team Need, prospect page |
| `draft_targets` | Historical labels only | draft_year, canonical_player_id, round, pick, overall, team, undrafted flag | Label assembly, evaluation only |
| `nba_comparable_profiles` | NBA-side similarity pool | NBA player season profiles | Similarity engine only |
| `source_identity_map` | Cross-source identity | canonical_player_id, source IDs, name variants, DOB, college, class, match_confidence | All layers |

`prospect_eligibility` is **not optional** — it records *why* each player is in the pool, which is what §3.7's honest limitations statement is built from.

---

## 12. Missing-data analysis

| Field family | Expected coverage | Class |
| --- | --- | --- |
| NCAA box score (final season) | Very high | **Essential** |
| NCAA advanced (usage, ORtg/DRtg, TS%, eFG%, ORB%) | High | **Essential** |
| NCAA shot-type splits | Medium; earlier seasons thinner | **Desirable** |
| Position | High; cross-source disagreement is the real problem | **Essential** |
| Age / date of birth | **Low–medium — likely worst offender** | **Desirable** |
| Combine anthropometrics | **~60–75 players/year only** | **Desirable** |
| Combine athletic drills | Lower still | **Optional** |
| Combine shooting drills | Sparsest | **Optional** |
| Measured wingspan without a Combine record | Largely unavailable | **Optional** |

**Four distinct kinds of missingness — do not conflate:** (1) not invited to the Combine — informative pre-2024, structural after; (2) invited but skipped a drill — often strategic; (3) field genuinely unrecorded; (4) **entity-match failure**, which looks like missing data but is a pipeline defect biased toward undrafted players (§9.2). Type 4 must be measured and reported separately — treating a failed join as "missing data" would launder a bias into an imputation.

Imputation methodology belongs to [ML_SPEC.md](ML_SPEC.md). The data-coverage formula ([MVP.md](MVP.md) §12) must be computed from an explicit field manifest with declared tiers; the formula remains TBD.

---

## 13. Source evaluation matrix

| Source | Publisher | Category | Tier | Coverage | 2026? | Stable ID | API | License / terms | Redistribution | Reproducibility | Main limitation | **Recommendation** |
| --- | --- | --- | --- | --- | :-: | :-: | :-: | --- | --- | --- | --- | --- |
| **Wikipedia / MediaWiki API** | Wikimedia | Population + draft outcomes | Community, high-governance | 2000–2026 VERIFIED | ✅ | Page titles | ✅ documented | **CC BY-SA — VERIFIED** | ✅ **with attribution + share-alike** | High | Wikitext parsing brittle; no player stats; 429 rate limits | **Preferred — population + draft targets** |
| **CollegeBasketballData** | B. Radjewski | NCAA stats, rosters, draft picks | Community, documented | REPORTED 2003+; player-stat start **UNKNOWN** | Unverified | ✅ `athlete_id` | ✅ REST, Bearer | Client MIT; **data rights UNKNOWN — BLOCKING** | **Likely prohibited (REPORTED)** | Medium — key-dependent | Terms unreadable; 1k calls/mo; no BPM | **Preferred — NCAA features (pending terms)** |
| **NBA Stats (combine / draft / players)** | NBA | Combine, draft, NBA stats | Official but undocumented | REPORTED 2000-01+ | Likely | ✅ `PERSON_ID` | Undocumented | **UNKNOWN — BLOCKING**; official portal is **partner-only (VERIFIED)** | Unknown | High if permitted | Outside the NBA's own gated developer channel | **Must resolve terms before any use** |
| **nba.com official early-entry lists** | NBA | Population | Official | Names verified 2026; historical names not recoverable from pr.nba.com | ✅ | ❌ | ❌ | Site ToU applies | Unknown | Low (manual) | Excludes seniors | **Cross-validation of Wikipedia** |
| **developerportal.nba.com** | NBA | Official API | Official | — | — | ✅ | ✅ | **Teams and Official Business Partners only — VERIFIED** | — | — | Not available to us | **Unavailable** |
| **balldontlie.io** | BALLDONTLIE LLC | NBA stats | Community/commercial | Long | ✅ | ✅ | ✅ documented | Terms readable; **prohibits resale/redistribution (REPORTED)** | ❌ | Medium | Free tier 5 req/min; lacks advanced stats | **Weak fallback — NBA stats** |
| **Sports-Reference / Basketball-Reference** | Sports Reference LLC | NCAA + NBA | Reputable secondary | Deep | ✅ | Site IDs | ❌ | Automated access prohibited (REPORTED) | ❌ | Not reproducible | **VERIFIED 403 ×4**, incl. Cloudflare challenge | **Reference only** |
| **Barttorvik** | B. Torvik | NCAA advanced | Community | 2008+ | ✅ | ❌ | ❌ | **robots.txt disallows the needed paths — VERIFIED** | Unknown | Not permitted | Owner-disallowed | **Reject** |
| **stats.ncaa.org** | NCAA | Official NCAA stats | Official | Long | ✅ | NCAA IDs | ❌ | Unreadable | Unknown | Not accessible | **VERIFIED 403 Akamai** | **Reject** |
| **Kaggle "NBA Anthropometric"** | T. Dobrucki | Combine anthro | Community derivative | REPORTED 2000–2023 | ❌ | ❌ | ❌ | **UNKNOWN** | Unknown | Medium | Ends 2023 — no 2026 | **Cross-check only** |
| **GitHub draft-model datasets** | Individuals | Prospects | Community | Varies | Varies | ❌ | ❌ | Varies | — | Low | **Derive from RealGM / BBRef / Barttorvik / 247Sports** | **Reject — provenance laundering** |
| **RealGM early-entry pages** | RealGM | Population | Community | By-year | Likely | ❌ | ❌ | **UNKNOWN** | Unknown | Unknown | **VERIFIED 403** | **Superseded by Wikipedia** |
| **hoopR / SportsDataverse** | S. Gilani et al. | NCAA + NBA | Community | MBB PBP 2006+ | Unverified | ESPN IDs | R pkg | Package open-source; data terms unclear | Unknown | Medium | R, not Python (DEC-033) | **Investigate further** |
| **KenPom / SportsDataIO / Sportradar** | Various | NCAA + NBA | Paid | Deep | ✅ | ✅ | ✅ | Commercial | Licensed | High | Cost, redistribution barred | **Reject** |

---

## 14. 2026 snapshot cutoff validation

### 14.1 Verdict: **2026-06-22 23:59:59 ET is defensible — CONFIRMED (PROVISIONAL)**

Every constraint was verified against official and near-official sources (§2):

| Constraint | Requirement | Satisfied? |
| --- | --- | --- |
| After the final eligibility population exists | ≥ Jun 15, 2026 (final early-entrant announcement) | ✅ 7 days of margin |
| After all pre-draft measurement events | ≥ May 17, 2026 (Combine ends); measurements published May 13 | ✅ |
| After the last withdrawal | ≥ Jun 13, 2026 5:00 pm ET | ✅ |
| After the NCAA season concluded | ✅ (spring) | ✅ |
| Strictly before any pick is announced | < Jun 23, 2026 8:00 pm ET | ✅ ~20 hours of margin |

It cleanly captures *"everything a scouting model could legitimately know immediately before the draft"* — including the green-room invitation waves reported from June 9, which are pre-draft public information (though **note:** green-room invitations are a league signal about expected draft position and are close in spirit to the DEC-013 prohibition on consensus signals; they should be treated as prohibited-as-features unless the owner decides otherwise).

**Alternative considered and not preferred:** 2026-06-13 17:00 ET (the NBA withdrawal deadline) is more conservative but falls *before* the Jun 15 final-list publication, so the authoritative population would not yet exist. That makes it strictly worse for this purpose.

### 14.2 Target separation

The draft result must be stored only in `draft_targets`, physically separate from `prospect_features` (§11). **No pick information may appear in any feature record.** Physical separation is what makes the leakage guarantee auditable rather than merely asserted.

---

## 15. 2026 demonstration population

### 15.1 What can be assembled — VERIFIED

| Component | Status |
| --- | --- |
| Official final NCAA early entrants | ✅ **26 NCAA players** (31 total less 5 international) — Wikipedia list verified against the official Jun 15 announcement |
| Automatically eligible NCAA players (seniors) | ❌ **Not available** — no name-level list exists (§3.1) |
| Combine participants | ⚠️ 73 invited (REPORTED); measurements published May 13, 2026; machine-readable access gated by §5.2 |
| Drafted players | ✅ Full 60-pick Wikipedia table |
| Undrafted "serious prospects" | ⚠️ Only as *declared early entrants who went undrafted* — derivable as (final early entrants) − (drafted) |

### 15.2 Recommended 2026 demo population — PROVISIONAL

**The union of: (a) the 26 final NCAA early entrants, and (b) all NCAA players selected in the 2026 draft.**

This is **exactly Option B′ applied to 2026** — the demo population and the historical training population are constructed by the same rule, which is the consistency [MVP.md](MVP.md) and good practice both favor. No mismatch to document.

**Expected size:** on the order of 26 early entrants plus the NCAA share of 60 picks, with overlap — plausibly 50–70 players. **This is small.** Two consequences to state honestly:
- A board of ~60 players is a legitimate scouting artifact but a thin demo relative to "all prospects in the dataset" ([MVP.md](MVP.md) §5).
- If the Combine pool becomes available (§5.2), adding the ~73 invitees would materially enrich the demo **and** pull in senior prospects the early-entry list structurally omits. **This is the strongest argument for resolving the NBA terms question.**

---

## 16. Provisional source strategy

**PROVISIONAL. No source or population is approved.**

```
Prospect population (historical + 2026)
  Preferred:   Wikipedia final NCAA early entrants ∪ drafted NCAA players   [Option B′]
  Fallback:    NBA Combine participants                                     [Option C, terms-gated]
  Supplement:  NCAA performance thresholds applied to the above             [Option E]
  Rejected:    Full eligible population (A); external datasets (D)

NCAA statistics
  Primary:     CollegeBasketballData.com API        [BLOCKING: terms + coverage]
  Fallback:    hoopR / sportsdataverse-py           [Python parity unverified]
  Reference:   Sports-Reference CBB (manual only)

Draft outcomes
  Primary:     Wikipedia draft tables               [CC BY-SA — cleanest rights in the project]
  Secondary:   CBBD /draft/picks                    [bonus: athlete_id join]
  Tertiary:    NBA Stats drafthistory               [terms-gated; adds PERSON_ID]

NBA Draft Combine
  Primary:     NBA Stats combine endpoints          [BLOCKING: terms]
  Fallback:    Kaggle NBA Anthropometric (2000–2023, no 2026, license unknown)
  Reality:     No clean reproducible non-NBA source exists

NBA comparable statistics
  Primary:     NBA Stats leaguedashplayerstats      [BLOCKING: terms]
  Fallback:    balldontlie.io                       [no redistribution; lacks advanced stats]
  Status:      Weakest family in the project

Biographical / identifiers
  Primary:     CBBD rosters (DOB, height, weight, position) — fill rate UNKNOWN
  Supplement:  Wikipedia page titles as population natural keys
  Never:       NBA bio endpoints to fill prospect fields (§10)
```

---

## 17. Acquisition plan — DO NOT EXECUTE

| Dataset | Primary source | Fallback | Access method | Format | Source ID | Range | Row magnitude | Join keys | **Blocking before acquisition** |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `prospect_eligibility` | Wikipedia `action=parse` | NBA official lists (manual) | Throttled API, cached | wikitext → parsed | page title | 2011–2026 | ~10³ (≈700–900 NCAA early entrants + drafted) | name, school, class, draft_year | Confirm 2014/2021 list markup; agree the NCAA/international filter rule |
| `prospect_features` | CBBD `/stats/player/season` + `/stats/player/shooting/season` + rosters | hoopR | REST, Bearer, per season × conference | JSON | `athlete_id` | 2011–2026 | ~10⁴–10⁵ rows before filtering | `athlete_id`, name+school+class | **CBBD terms + earliest-season coverage + quota check** |
| `prospect_features` (Combine part) | NBA Stats `draftcombinestats` (`All Time`) | Kaggle anthro | Single request | JSON | `PLAYER_ID`/`TEMP_PLAYER_ID` | 2000-01–2026 | ~10³ | name + position | **NBA ToU** |
| `draft_targets` | Wikipedia draft tables | CBBD `/draft/picks` | Throttled API | wikitext table | page title / `athlete_id` | 2011–2026 | ~900 (60/yr × 15) | name, draft_year | Agree undrafted encoding |
| `nba_comparable_profiles` | NBA Stats `leaguedashplayerstats` (+Advanced) | balldontlie | Per-season requests | JSON | `PERSON_ID` | TBD by ML | ~10³–10⁴ | `PERSON_ID` | **NBA ToU**; verify Advanced column list |
| `source_identity_map` | Derived from all of the above | — | Local build | — | composite | — | ~10³–10⁴ | all | Pilot the Combine↔NCAA match on 2–3 years first |

---

## 18. GO / NO-GO assessment

### Overall: 🟡 **YELLOW**

The MVP is feasible, but **two methodological compromises are required and one legal question is unresolved**:

1. **The historical population must narrow.** Undrafted seniors cannot be represented — no name-level source exists (VERIFIED). The board will rank declared early entrants plus drafted players, which is a real and defensible question but a **narrower** one than PRODUCT.md §14 currently describes. This needs a wording decision (§3.7).
2. **The NBA terms question is unresolved** and gates Combine data, and with it most of the Athleticism and Physical Profile sub-scores, plus the entire comparables pool.

It is **not RED**: every core capability has a viable path, and the population and draft-target layers are now backed by a source with verified clean licensing (Wikipedia, CC BY-SA) — a genuine improvement over pass 1, where the population had no verified source at all.

| Capability | Rating | Reasoning |
| --- | :-: | --- |
| **General Draft Board** | 🟡 **YELLOW** | Population verified recoverable 2011–2026 and targets are clean, but the pool excludes undrafted seniors, requiring a restated ground-truth claim. Feature layer depends on unresolved CBBD terms |
| **Team Need** | 🟡 **YELLOW** | The **strongest** capability on data grounds: CBBD's shot-type splits with assisted rates make all six MVP profiles measurable, and every requested shooting/playmaking/defense/rebounding metric is present or derivable except BPM. Yellow **only** because CBBD terms are unverified. Would be GREEN on terms clearance |
| **NBA comparables** | 🟡 **YELLOW**, closest to red | Requires NBA player statistics. Official API is partner-only (VERIFIED); stats.nba.com terms unreadable; the only readable-terms fallback (balldontlie) prohibits redistribution and lacks advanced stats. **The weakest family** |
| **2026 replay** | 🟡 **YELLOW** | Calendar, cutoff, population, and targets all verified and clean. Downgraded only by the small demo population (~50–70 players) and Combine dependency |
| **Historical Python backtesting** | 🟡 **YELLOW** | 15 drafts with verified per-year population counts is enough for rolling-origin validation. Blocked on CBBD feature coverage; the 2024 Combine regime break sits inside the window |

---

## 19. Blockers requiring owner decision or action

**Legal / access — must be a human in a browser:**

1. 🔴 **Read the NBA.com Terms of Use** and record whether programmatic access to `stats.nba.com` is permitted. Gates Combine + comparables + NBA-side draft IDs. Note the official channel is partner-only (VERIFIED).
2. 🔴 **Read the CollegeBasketballData.com and CollegeFootballData.com terms** and record redistribution, attribution, and commercial-use terms. Determines whether derived datasets may be published at all.
3. 🟠 **Approve (or decline) registering a free CBBD API key.** Account creation on an external service is an outward-facing action and was not taken.

**Product decisions:**

4. 🔴 **Approve a population strategy** (§3.6) — Option B′ recommended.
5. 🔴 **Decide the ground-truth wording** (§3.7). PRODUCT.md §14 was deliberately not edited.
6. 🟠 **Accept or reject the ~50–70-player 2026 demo population**, versus waiting on Combine access to enrich it.
7. 🟠 **Decide whether green-room invitations are prohibited as features** under DEC-013 (§14.1).

**Verification (post-key, before modeling):**

8. Earliest season with complete CBBD player season / advanced / shooting-profile stats; and whether 2025-26 is populated.
9. CBBD quota sufficiency for a full historical pull (§6.4).
10. Date-of-birth fill rate in CBBD rosters.
11. `DraftPick.height`/`.weight` provenance — Combine-measured or post-draft bio? (§6.6)
12. Re-check the 2014 and 2021 Wikipedia early-entrant list markup.
13. Pilot the Combine↔NCAA match on 2–3 years, measuring failure **separately for drafted and undrafted** players.

---

## 20. Sportradar-centered strategy audit (pass 3)

Evaluated: can **Sportradar** become the primary provider for NCAA statistics, prospect population, draft outcomes, NBA statistics, identity, and NCAA↔NBA linking — with a secondary source only for Combine data?

**Headline: technically the strongest option examined; legally the most restrictive.** The blocker is not coverage or schema — both are good — it is that the Sportradar terms, as written, do not permit what a public hackathon submission does.

**No Sportradar API key was available; no API calls were made; no account was created.** All findings below come from official Sportradar documentation. Items requiring live calls are listed in §20.12.

### 21.1 Access and legal — VERIFIED, and BLOCKING

**Trial terms — VERIFIED** ([Your Account](https://developer.sportradar.com/getting-started/docs/your-account)):

| Property | Value |
| --- | --- |
| Trial duration | *"Our trials last 30 days."* |
| Quota | *"1,000 requests (quota) per rolling 30 days"* |
| Rate limit | *"1 QPS (queries per second)"* |
| Key scope | Per-**application** master key covering *"every active product within this application"* — so NBA + NCAAMB can share one key |
| Data parity | *"Trial access provides the same real-world data as production, with some rare exceptions"*; not throttled or delayed |
| Historical access on trial | **UNKNOWN** — the page does not address it |

**🔴 The blocking clause — VERIFIED** ([Terms and Conditions](https://developer.sportradar.com/sportradar-updates/page/terms-and-conditions), Free Trial, §3). Free-trial customers may:

> *"access and use the Service… solely for purposes of internally evaluating the Products"*

and are

> **"not authorized… to use the Products in connection with any commercial use or any use involving publication or display of the Data or Content."**

A hackathon submission — a public demo, a Devpost entry, a public repository — **is publication and display**. A trial key therefore permits evaluating whether to buy Sportradar. It does not permit building DraftLens's deliverable.

**Paid terms are also restrictive — VERIFIED** (§2.2, §1.19, §2.12):
- The license is to *"use, import, distribute, reproduce, display… for the purposes of providing sports information and content on the Properties"* — **"Properties" means specific websites/apps named on an Order Form** (§1.19). Anything not named is not covered.
- Perpetual rights are granted *"solely for archiving purposes."*
- Prohibited: *"copying or creating derivative works,"* reverse engineering, *"disseminating performance data,"* developing competitive products, removing copyright notices, and any use *"other than display on the Properties authorized."*
- **Mandatory attribution:** a *"powered by Sportradar"* logo must appear on the Properties (§2.12).
- Sportradar's APIs are *"a B2B service and are not intended to be called directly from a client application."*

**Consequences for DraftLens, stated plainly:**

| Question | Answer |
| --- | --- |
| May trial data be used for the hackathon build? | **No — VERIFIED.** Internal evaluation only |
| May API responses be committed to a public repo? | **No — VERIFIED.** Prohibited under both trial and paid terms |
| May derived datasets/scores be published? | **Doubtful — the paid terms prohibit "creating derivative works" and "disseminating performance data."** UNKNOWN whether DraftLens sub-scores would qualify; would need written clarification |
| May results be stored locally? | Paid: yes, archiving is expressly contemplated. Trial: only for internal evaluation |
| Is attribution required? | **Yes — VERIFIED**, "powered by Sportradar" logo |

This is **more restrictive than every other candidate**, including CBBD (whose reported clause bars *redistribution* but not publication or display) and far more so than Wikipedia (CC BY-SA).

### 21.2 NCAA field inventory — VERIFIED

From [NCAAMB Seasonal Statistics](https://developer.sportradar.com/basketball/reference/ncaamb-seasonal-statistics) and [NCAAMB Player Profile](https://developer.sportradar.com/basketball/reference/ncaamb-player-profile).
URL: `/{access_level}/v8/{lang}/seasons/{season_year}/{season_type}/teams/{team_id}/statistics.{format}` — **per team, per season**.

| Category | Field | Status |
| --- | --- | :-: |
| **Identity** | `id`, `full_name`, `first_name`, `last_name`, `abbr_name` | ✅ |
| | `position`, `primary_position` | ✅ |
| | `height` (in), `weight` (lb) | ✅ |
| | `experience` (FR/SO/JR/SR/5th/GR) | ✅ |
| | `jersey_number`, `status`, `birth_place`, team/school object, conference, division | ✅ |
| | **`birthdate`** | ❌ **ABSENT — see §20.5** |
| | `references` array (cross-league) | ✅ |
| **Playing time** | `games_played`, `games_started`, `minutes` | ✅ |
| **Scoring** | `points`; `field_goals_made/att/pct`; `two_points_made/att/pct`; `three_points_made/att/pct`; `free_throws_made/att/pct` | ✅ |
| **Playmaking** | `assists`, `turnovers`, `assists_turnover_ratio` | ✅ |
| **Rebounding** | `offensive_rebounds`, `defensive_rebounds`, `rebounds` | ✅ |
| **Defense** | `steals`, `blocks`, `blocked_att`, `personal_fouls`, `tech_fouls`, `flagrant_fouls`, `foulouts`, `ejections` | ✅ |
| **Advanced** | **`true_shooting_pct`**, `true_shooting_att` | ✅ |
| | **`usage_pct`** | ✅ |
| | `efficiency`; **PER** (nested in profile) | ✅ |
| **Shot profile** | **`field_goals_at_rim_made/att/pct`** | ✅ **strong** |
| | **`field_goals_at_midrange_made/att/pct`** | ✅ **strong** |
| **Absent** | `eFG%` (present in NBA, **not** NCAA), offensive/defensive rating, per-possession metrics, AST%/TOV%/STL%/BLK%, ORB%/DRB%/TRB%, dunks/layups/tip-ins split, **assisted %**, catch-and-shoot / pull-up, shot coordinates | ❌ |

**Averages** are also returned for most counting stats.

**Assessment vs. CBBD.** Sportradar wins on **rim/midrange shot-location splits** (a true location measure, not an inferred shot type) and on carrying TS% and usage% natively. CBBD wins on **shot-type granularity and `assisted_pct`** — dunks vs. layups vs. tip-ins vs. jumpers, each with an assisted rate, which is what separates a Slasher from a Rim Runner and a Shooter from a spot-up finisher. CBBD also has ORtg/DRtg/win shares/PORPAG/ORB%, none of which Sportradar exposes. **Neither is a superset of the other.**

### 21.3 NCAA historical coverage — VERIFIED

`season_year` valid range: **2013–2026** ("season year is always the year a season *begins*").

| Test season | Available? |
| --- | :-: |
| 2013-14 | ✅ |
| 2015-16 | ✅ |
| 2018-19 | ✅ |
| 2020-21 | ✅ |
| 2022-23 | ✅ |
| 2024-25 | ✅ |
| **2025-26** | ✅ |

All seven requested seasons are covered. NCAA data alone would support drafts **2014–2026**. **But NCAA coverage is not the binding constraint — see §20.4.**

### 21.4 Draft / prospect endpoints — VERIFIED schemas, **UNVERIFIED population**

Draft endpoints sit on a **separate v1 path** from the v8 statistics APIs:

| Endpoint | URL | Draft years |
| --- | --- | :-: |
| Draft Summary | `/nba/{access}/v1/{lang}/{draft_year}/draft.{format}` | **2019–2026** |
| Prospects | `/nba/{access}/v1/{lang}/{draft_year}/prospects.{format}` | **2019–2026** |
| Top Prospects | `/nba/{access}/v1/{lang}/{draft_year}/top_prospects.{format}` | **2019–2026** |
| Team Draft Summary, Trades, Push Draft Picks/Trades | — | 2019–2026 |

**🔴 `draft_year` is bounded at 2019 — VERIFIED.** This is the single hardest constraint in the Sportradar strategy and it is *tighter than the NCAA statistics coverage*.

**Prospect object — VERIFIED fields:** `id`, `source_id`, `league_id` (populated post-draft), `first_name`, `last_name`, `name`, `birth_place`, `height` (inches), `weight` (lbs), `position`, `experience` (FR/JR/SR), school/team object (`id`, `name`, `market`, `alias`), conference, division, `top_prospect` (boolean).

**Absent from the prospect object — VERIFIED:** `birthdate`; draft pick number or round; any drafted/undrafted status or NBA team assignment.

**Draft Summary — VERIFIED:** `rounds[] → picks[]` with pick `id`, `number` (within round), `overall`, `traded` flag, selecting `team` object, `trades[]`, and a nested **prospect object carrying both `id` (prospect id) and `league_id` (NBA player id, populated typically the next day)**. Pick-to-player linkage is therefore explicit and clean for drafted players.

**Who actually appears in `/prospects` — UNVERIFIED (A/B/C/D/E/F all remain open).** Documentation states only that *"prospects are added to the API after the NCAA Men's Basketball season ends and players declare, typically in May"* — which suggests a declaration-driven pool rather than all eligible players, but the count and whether undrafted prospects are retained after the draft **cannot be determined from documentation**. The existence of a separate Top Prospects endpoint and a `top_prospect` boolean implies `/prospects` is the broader set. **This must be measured, not inferred** (§20.12).

### 21.5 The age problem — a new, previously unrecognised gap

**VERIFIED:** neither the NCAAMB Player Profile nor the draft Prospect object exposes `birthdate` — only `birth_place`. The **NBA** Player Profile *does* carry `birthdate`.

[PRODUCT.md](PRODUCT.md) §11 approves age as a candidate pre-draft feature whose relevance must be evaluated from historical data. Under a Sportradar-only strategy, **age could only be recovered for prospects who reached the NBA** — which is a post-draft outcome determining feature availability, i.e. exactly the leakage pattern §10 prohibits.

**Consequence: a Sportradar-only strategy cannot support the age feature at all without a third source.** CBBD's roster `date_of_birth` field (fill rate still unverified) remains the only pre-draft DOB candidate identified in any pass.

### 21.6 NCAA ↔ NBA identity linking — VERIFIED mechanism, **partial coverage**

From [ID Handling](https://developer.sportradar.com/basketball/docs/nba-ig-id-handling):

- IDs are **UUIDs**, and *"all IDs remain permanent once created"* — including through team relocations. Stable identity is a genuine strength.
- NCAA player IDs **do not transfer** to the NBA API, but NCAA IDs are exposed in the NBA Player/Team Profile `references` array under `id_type: "league_profile"` (`scope`: `NBA`, `NCAAMB`, `NBDL`; `id_type`: `external`, `league_profile`, `sport_profile`).
- **The decisive sentence — VERIFIED:** *"The NBA Draft feeds contain `source_id` attributes mapping NCAA prospect IDs, facilitating profile linking for drafted players. **Undrafted free agents require bio-based matching (name, college, position).**"*

**This does not solve DraftLens's hardest matching problem — it reproduces it.** §9.2 established that match failure concentrating in the undrafted class is the most damaging possible bias, because undrafted players *are* the negative examples. Sportradar gives deterministic linking exactly where it was already easy (drafted players) and falls back to fuzzy name+college+position matching exactly where it was already hard.

It is still an improvement: fuzzy matching would be needed for one join instead of several, within one ID namespace, with clean school objects. But the claim "one provider solves entity matching" is **false as documented**.

**Rating: 🟡 YELLOW.**

### 21.7 NBA statistics for comparables — VERIFIED, strong

[NBA Seasonal Statistics](https://developer.sportradar.com/basketball/reference/nba-seasonal-statistics), same URL shape as NCAA, `season_year` **2013–2025** (2025 = 2025-26).

Totals and averages include: points; FG / 2P / 3P / FT (made, attempted, pct); offensive, defensive and total rebounds; assists; turnovers; steals; blocks; personal and technical fouls; plus/minus; minutes; games played/started; **efficiency**; **true_shooting_pct/att**; **effective_field_goal_pct**; **usage_pct**; **PER**; assist-to-turnover ratio; fast-break; second-chance; paint stats **with rim/midrange zone breakdowns**.

NBA Player Profile adds: `birthdate`, `birth_place`, `height`, `weight`, `position`, `primary_position`, `college`, `high_school`, `jersey_number`, `experience`, `rookie_year`, `draft` {`year`, `round`, `pick`, `team_id`}, and the `references` array.

**The strategic advantage: the NCAA and NBA feeds share a schema family.** Both expose TS%, usage%, and **rim/midrange shooting zones from one vendor with one definition**. Every other candidate strategy would have to reconcile differently-defined metrics across two providers before any NCAA→NBA normalization could begin. That is a real and substantial reduction in methodological risk.

**Rating: 🟢 GREEN.**

### 21.8 NBA historical coverage — VERIFIED

| Test season | Available? |
| --- | :-: |
| 2013-14 | ✅ |
| 2016-17 | ✅ |
| 2019-20 | ✅ |
| 2022-23 | ✅ |
| 2024-25 | ✅ |
| **2025-26** | ✅ (`season_year=2025`) |

Thirteen NBA seasons — ample for a comparables pool.

### 21.9 Draft outcome integration — 🟡 YELLOW

Draft Summary links each pick to a prospect `id` **and** an NBA `league_id`, with round, pick, overall, and selecting team. For **2019–2026** this would fully replace the Wikipedia draft-outcome layer and eliminate name-based matching for drafted players.

Downgraded from GREEN for three reasons: coverage starts at 2019 (Wikipedia covers every year); no drafted/undrafted flag is exposed on the prospect object, so undrafted status must be derived by set difference; and the whole layer inherits §20.1's licensing blocker, whereas Wikipedia's CC BY-SA is unambiguous.

### 21.10 Combine — **COMBINE REQUIRES A SECONDARY SOURCE**

**VERIFIED.** The complete NBA API endpoint list contains **no Combine endpoint**. No field for height without shoes, wingspan, standing reach, body fat, hand length/width, standing or max vertical, lane agility, shuttle, three-quarter sprint, bench press, or shooting drills appears anywhere in the basketball API documentation. Sportradar's separate "Insights" product is described as connecting Combine and Synergy data, but that is a team/enterprise analytics offering, **not the public basketball API**.

The Sportradar height/weight fields are *listed* values, not Combine-measured ones — they cannot substitute (§7).

### 21.11 Kaggle Combine candidates — license VERIFIED, contents UNKNOWN

| | **NBA Anthropometric** | **NBA Draft Combine** |
| --- | --- | --- |
| Author | tymoteuszdobrucki | marcusfern |
| URL | [kaggle.com/…/nba-anthropometric](https://www.kaggle.com/datasets/tymoteuszdobrucki/nba-anthropometric) | [kaggle.com/…/nba-draft-combine](https://www.kaggle.com/datasets/marcusfern/nba-draft-combine) |
| **Stated license** | **CC BY 4.0 — VERIFIED** (page metadata) | **CC BY 4.0 — VERIFIED** (page metadata) |
| Coverage | **"Draft years 2000-2023" — VERIFIED** from page description | UNKNOWN |
| 2026 included? | **No** | UNKNOWN — a search result REPORTS an update on 2026-05-16 (days after the 2026 Combine), but the dataset-card image timestamp is 2022-04-24. **Contradictory; unresolved** |
| Provenance | **REPORTED** *"acquired using NBA Stats API"* | UNKNOWN |
| Row count, field list, drafted indicator, NBA player ID, duplicate/missing handling, update date | **UNKNOWN — all require Kaggle authentication** | **UNKNOWN — same** |

**Kaggle dataset pages are client-rendered; file listings and data cards require a signed-in session. No Kaggle account was created — this is owner action (§20.14).**

**Legal analysis (Part 13) — the distinction that matters:**

A **CC BY 4.0 badge is the uploader's declaration.** An uploader cannot grant rights they do not hold. If the underlying measurements were "acquired using NBA Stats API", the upstream rights sit with the NBA — and §5.2 established that the NBA Terms of Use could not be read and remain **BLOCKING**. **A permissive license applied to a derivative does not launder restrictions attached to the source.**

| Use | Assessment |
| --- | --- |
| **A. Local analysis only** | **Lowest risk.** Private, non-published analysis. Still contingent on the upstream position |
| **B. Publish the raw CSV in GitHub** | **UNKNOWN — LEGAL REVIEW REQUIRED.** Highest risk; redistributes the upstream data wholesale under a license the uploader may not have been entitled to grant |
| **C. Publish only derived metrics** | **Lower risk, still UNKNOWN.** Aggregated/derived values are further from the source, but "derived" is not a legal safe harbour |
| **D. Ship acquisition instructions instead of data** | **Safest, and recommended.** The repo carries code and documentation; each user obtains the dataset themselves under its stated terms |

Option D is also the pattern already forced by CBBD's reported redistribution clause (§6.3), so a single reproducibility posture — *"reproducible by re-running acquisition, not by shipping data"* — would satisfy both.

### 21.12 Required API tests — DO NOT EXECUTE WITHOUT A KEY AND A LICENCE DECISION

`SPORTRADAR_API_KEY` **was not present** in the environment or in any local env file (checked by name only; no values printed). No account was created. `.env.example` was **not** modified — that awaits access approval per the task instruction.

Given §20.1, these tests should only be run once the owner has resolved whether a licence permitting the hackathon use exists. Each is small and read-only.

| # | Question | Endpoint | Record |
| --- | --- | --- | --- |
| 1 | Historical NCAA season works | `/ncaamb/{access}/v8/en/seasons/2013/REG/teams/{team_id}/statistics.json` | status, player row count, field presence |
| 2 | Current NCAA season works | same with `seasons/2025` | status, row count, whether 2025-26 is populated |
| 3 | **Prospect population, pre-2026** | `/nba/{access}/v1/en/2018/prospects.json` | **expect failure — 2018 is outside the documented 2019–2026 range.** Confirms the floor |
| 4 | **Prospect population** | `/nba/{access}/v1/en/2019/prospects.json` | **total count**; count with `league_id` present; NCAA vs international split; `top_prospect` count |
| 5 | **Prospect population** | `/nba/{access}/v1/en/2025/prospects.json` | same |
| 6 | **The critical test** | `/nba/{access}/v1/en/2026/prospects.json` | **total count vs. 60 picks.** If materially > 60, undrafted prospects are retained → answers Part 4/5 |
| 7 | 2026 draft results | `/nba/{access}/v1/en/2026/draft.json` | pick count, presence of prospect `id` and `league_id` per pick |
| 8 | NBA historical season | `/nba/{access}/v8/en/seasons/2013/REG/teams/{team_id}/statistics.json` | status, field presence |
| 9 | **ID linking** | NBA Player Profile for 3–4 known ex-NCAA players | presence and format of `references[]` entries with `scope: NCAAMB` |
| 10 | **Linking for undrafted** | NBA Player Profile for a known undrafted ex-NCAA player | whether an `NCAAMB` reference exists — tests §20.6's limitation directly |

Quota note: tests 1–10 cost ~15 calls of a 1,000-call trial.

**⚠️ Quota feasibility for a real pull — the practical killer.** NCAA Seasonal Statistics is **per team, per season**. Division I fields roughly 360 teams. One season ≈ 360 calls = **36% of the entire trial quota**. The 2013–2025 window ≈ 360 × 13 ≈ **4,700 calls — 4.7× the total trial allowance**, before any NBA, prospect, or profile calls. **A trial key cannot acquire this dataset even if the terms permitted it.** A paid tier would be required on volume grounds alone.

### 21.13 Two-source strategy assessment — 🔴 **RED as currently configured**

| Dimension | Assessment |
| --- | --- |
| Data coverage | 🟢 Strong — NCAA 2013+, NBA 2013+, drafts 2019+ |
| Schema consistency | 🟢 **Best of any option** — shared metric definitions across NCAA and NBA |
| Entity matching | 🟡 Better than fuzzy-only, but undrafted players still need bio matching |
| Historical consistency | 🟡 Draft coverage floor of 2019 gives only **7** training drafts (2019–2025) |
| 2026 support | 🟢 All components present except age |
| Age feature | 🔴 **Unavailable** without a third source |
| Combine | 🔴 Absent — secondary source mandatory |
| Legal / access risk | 🔴 **Trial forbids publication or display; paid restricts to named Properties and prohibits derivative works** |
| Public reproducibility | 🔴 API responses may not be committed |
| Hackathon practicality | 🔴 Trial quota is ~4.7× too small for the historical pull |

**The strategy fails on licensing and quota, not on data.** If the owner obtains a licence expressly permitting a public analytical demonstration — an academic, hackathon-sponsor, or evaluation licence with written scope — the rating would rise to 🟡 YELLOW (the 2019 floor, the age gap, and the Combine gap would remain).

### 21.14 Strategy comparison

| Criterion | **A — Current (CBBD + Wikipedia + NBA fallback + Combine)** | **B — Sportradar-centered (+ Combine)** |
| --- | --- | --- |
| Number of sources | 3–4 | 2 |
| NCAA richness | 🟢 ORtg/DRtg, win shares, PORPAG, ORB%, **shot-type splits + assisted %** | 🟡 TS%, usage%, PER, **rim/midrange zones**; no ratings, no assisted % |
| Prospect population | 🟡 Wikipedia early entrants, 2011–2026 verified | ❓ **Unverified composition**, 2019–2026 only |
| Drafted + undrafted | 🟡 Declared-and-undrafted derivable; seniors absent | ❓ Unverified; no drafted flag exposed |
| NBA statistics richness | 🔴 Weakest family; fallbacks poor | 🟢 **Strong** |
| Stable IDs | 🟡 CBBD `athlete_id` within source; Wikipedia page titles | 🟢 **Permanent UUIDs throughout** |
| NCAA ↔ NBA linking | 🔴 Fuzzy, manual | 🟡 Deterministic for drafted; **fuzzy for undrafted** |
| Entity-matching complexity | 🔴 High | 🟡 Moderate |
| Historical coverage | 🟢 **2011–2026** | 🔴 **2019–2026 (7 training drafts)** |
| 2026 coverage | 🟢 Verified | 🟢 Verified except age |
| Advanced stats | 🟢 Broader | 🟡 Narrower but cross-league consistent |
| **Age / date of birth** | 🟡 CBBD DOB field exists (fill rate unknown) | 🔴 **Absent pre-draft** |
| Combine | 🔴 Secondary source needed | 🔴 Secondary source needed |
| Licensing clarity | 🟡 Wikipedia CC BY-SA clean; CBBD unread; NBA unread | 🟢 **Clear** — and clearly **prohibitive** |
| Public reproducibility | 🟡 Wikipedia yes; CBBD likely no | 🔴 **No** |
| API reliability | 🟡 Community + undocumented endpoints | 🟢 **Commercial SLA-grade** |
| Trial limitations | 🟢 CBBD free tier 1,000/mo, renewable | 🔴 1,000 calls total; ~4.7× short |
| Long-term sustainability | 🟡 Depends on volunteer projects | 🟢 Commercial vendor |
| Implementation effort | 🔴 Higher — multi-source reconciliation | 🟢 **Lower — one schema family** |

**Recommendation: 🔀 HYBRID, defaulting to STRATEGY A — PROVISIONAL, owner decision required.**

Build on **Strategy A**, because it is the only configuration verified as *permitted and practical* today: Wikipedia's CC BY-SA licence is unambiguous, CBBD's free tier is renewable and adequate, and the 2011–2026 window gives 15 training drafts against Sportradar's 7.

Pursue **Sportradar as a targeted upgrade** for the two places Strategy A is weakest — **NBA comparables** (§18 rated it YELLOW-closest-to-red; Sportradar rates GREEN) and **NCAA↔NBA identity** — but **only if** the owner secures a licence that expressly permits a public analytical demonstration. Without that licence, Sportradar cannot be used for the deliverable at all, no matter how good the data is.

Do not adopt Sportradar as the *sole* provider under any licence: the 2019 draft floor halves the training history, and the missing pre-draft birthdate would silently retire an approved product feature ([PRODUCT.md](PRODUCT.md) §11).

### 21.15 Status labels

| Finding | Label |
| --- | --- |
| Trial: 30 days, 1,000 calls/rolling 30 days, 1 QPS, per-application | **VERIFIED** |
| Trial prohibits commercial use and any publication or display of Data/Content | **VERIFIED — BLOCKING** |
| Paid licence limited to named "Properties"; derivative works prohibited; attribution logo required | **VERIFIED — BLOCKING for public repo** |
| NCAA seasonal statistics field inventory | **VERIFIED** |
| NCAA coverage `season_year` 2013–2026 | **VERIFIED** |
| NBA coverage `season_year` 2013–2025 | **VERIFIED** |
| Draft endpoints bounded `draft_year` 2019–2026 | **VERIFIED** |
| Prospect object schema (no birthdate, no pick, no drafted flag) | **VERIFIED** |
| Draft Summary links picks → prospect `id` + `league_id` | **VERIFIED** |
| `references` array; NCAA↔NBA linking documented for **drafted** players; undrafted need bio matching | **VERIFIED** |
| No pre-draft birthdate anywhere in NCAA or prospect feeds | **VERIFIED** |
| No Combine data in the Sportradar basketball API | **VERIFIED — secondary source required** |
| **Who appears in `/prospects` (A–F)** | **UNKNOWN — requires live calls** |
| Whether historical endpoints are included in trial access | **UNKNOWN** |
| Kaggle combine datasets stated CC BY 4.0 | **VERIFIED** |
| Kaggle coverage/rows/fields/update date | **UNKNOWN — requires Kaggle auth (owner action)** |
| Kaggle upstream rights vs. CC BY 4.0 badge | **UNKNOWN — LEGAL REVIEW REQUIRED** |
| Sportradar as sole provider | **REJECTED** — 2019 floor + no pre-draft age |
| Sportradar trial as the hackathon data source | **REJECTED** — terms prohibit publication/display |

### 21.16 Owner actions arising from pass 3

1. 🔴 **Decide whether to pursue a Sportradar licence** that expressly permits a public analytical demonstration (academic / hackathon-sponsor / evaluation scope, in writing). Without it, Sportradar is unusable for the deliverable.
2. 🔴 **Do not build on a Sportradar trial key** — VERIFIED as internal-evaluation only.
3. 🟠 **Inspect the two Kaggle Combine datasets while signed in** and record coverage, row count, field list, 2026 inclusion, and update date.
4. 🟠 **Legal review of the Kaggle upstream-rights question** (§20.11) — this is the same NBA-terms question as §5.2 wearing a different hat.
5. 🟠 If a licence is obtained, run the ten tests in §20.12 — especially **test 6**, which determines whether undrafted prospects exist in the feed.

---

## 21. Open data consolidation audit (pass 4)

**Objective:** find the cleanest legally and reproducibly usable strategy, ideally reducing DraftLens to **three primary sources or fewer**, preferring static licensed files over fragile pipelines.

**Result: a materially better strategy exists.** A three-source bundle was found in which every component carries an **explicit licence covering the data itself** — a first for this project. It simultaneously upgrades the two weakest capabilities identified in §18 (NBA comparables and licensing clarity) and plausibly recovers the age feature that Sportradar could not supply.

**No dataset was downloaded.** Only repository metadata, directory listings, file manifests, licence files, README files, and dataset-card metadata were inspected.

### 21.1 The headline finding — the sportsdataverse `hoopR` static data repositories

Pass 2 dismissed hoopR as "R-first, Python parity unverified." **That assessment was incomplete and is corrected here.** The hoopR *R package* is one thing; the **`hoopR-*-data` GitHub repositories are language-agnostic static Parquet archives** requiring no R, no API key, no account, and no rate limit.

| Repository | Coverage | Updated | Size | Licence |
| --- | --- | --- | --- | --- |
| [`sportsdataverse/hoopR-mbb-data`](https://github.com/sportsdataverse/hoopR-mbb-data) | *"Men's College Basketball Data 2003 – Present"* | **2026-08-07** (today) | ~38 GB repo | **CC BY 4.0** |
| [`sportsdataverse/hoopR-nba-data`](https://github.com/sportsdataverse/hoopR-nba-data) | *"NBA Data 2002 – Present"* | **2026-08-07** (today) | ~21 GB repo | **CC BY 4.0** |
| [`sportsdataverse/hoopR-nba-stats-data`](https://github.com/sportsdataverse/hoopR-nba-stats-data) | NBA Stats-derived PBP/possessions/lineups | 2026-08-07 | ~2 GB | **CC BY 4.0** |

**Licence — VERIFIED** by reading `LICENSE.md` in each repository:

> *"# Creative Commons Attribution 4.0 International (CC BY 4.0) … The contents of this repository **(data, code, and documentation)** are licensed under the Creative Commons Attribution 4.0 International License… You are free to: **Share** — copy and redistribute the material in any medium or format; **Adapt** — remix, transform, and build upon the material for any purpose, **even commercially**."*

This is the first candidate in four passes whose licence text **explicitly names the data** and explicitly permits redistribution and adaptation. (GitHub's API reports `NOASSERTION` because the root `LICENSE` file is an unfilled R-package template stub — `LICENSE.md` is the operative document. VERIFIED.)

**Provenance — VERIFIED and documented:** the README states the source chain explicitly — `hoopR-mbb-raw (source: ESPN) → hoopR-mbb-data → sportsdataverse releases`. Upstream is **ESPN**. See §21.7 for what that means legally.

#### Directory inventory — VERIFIED

`hoopR-mbb-data/mbb/`: `crosswalk`, `game_rosters`, `officials`, `pbp`, **`player_box`**, **`player_core`**, `player_season_stats`, `rosters`, `schedules`, **`shots`**, `standings`, `team_box`, `team_season_stats`

`hoopR-nba-data/nba/`: `betting_lines`, `crosswalk`, **`draft`**, `game_rosters`, `officials`, `pbp`, `player_box`, **`player_season_stats`**, `player_core`, `rosters`, `schedules`, `shots`, `standings`, `team_box`, `team_season_stats`

#### Per-directory coverage — VERIFIED by listing Parquet files

| Dataset | Files | Range | Total size | Note |
| --- | --: | --- | --- | --- |
| `mbb/player_box` | 24 | **2003 → 2026** | ~75 MB | Game-level; season stats aggregate from this |
| `mbb/shots` | 22 | **2003 → 2026** | ~137 MB | **Shot-level data** |
| `mbb/player_core` | 24 | **2003 → 2026** | small | Player biographical records |
| `mbb/player_season_stats` | 2 | 2025 → 2026 only | ~2.6 MB | ⚠️ Pre-aggregated only for recent seasons |
| `mbb/rosters` | 2 | 2025 → 2026 only | ~2 MB | ⚠️ Recent only |
| `mbb/crosswalk` | 2 | 2026 only | ~230 KB | Player + team crosswalk; manifest shows **5,627 player rows for 2026** |
| `nba/player_season_stats` | **25** | **2002 → 2026** | — | ✅ **Full history, pre-aggregated** |
| `nba/player_box` | 25 | 2002 → 2026 | — | Game-level |
| `nba/draft` | 3 | 2023 → 2026 | ~48 KB | ⚠️ **Too shallow — see §21.4** |

**Note the asymmetry — VERIFIED:** NBA season stats are pre-aggregated for the full 2002–2026 history, while NCAA season stats are pre-aggregated only for 2025–2026. Historical NCAA season totals must be **aggregated from `player_box`** (24 files, ~75 MB). That is straightforward and arguably preferable — it gives DraftLens control over the aggregation and lets the "latest NCAA season" rule (DEC-010) be applied exactly.

#### `player_box` schema — VERIFIED (55 columns)

Identity: `athlete_id`, `athlete_display_name`, `athlete_jersey`, `athlete_short_name`, `athlete_headshot_href`, **`athlete_position_name`**, **`athlete_position_abbreviation`**
Context: `game_id`, `season`, `season_type`, `game_date`, `game_date_time`, full team and opponent blocks, `home_away`, `team_score`, `opponent_team_score`
Performance: `minutes`, `field_goals_made`, `field_goals_attempted`, `three_point_field_goals_made`, `three_point_field_goals_attempted`, `free_throws_made`, `free_throws_attempted`, `offensive_rebounds`, `defensive_rebounds`, `rebounds`, `assists`, `steals`, `blocks`, `turnovers`, `fouls`, `points`
Status: `starter`, `ejected`, `did_not_play`, `active`

**What this is and is not.** These are **primitives, not pre-computed advanced metrics.** There is no TS%, eFG%, usage%, ORtg, DRtg, win shares, or rate stat in the file. But every one of those is **derivable**: TS% and eFG% directly from the box line; usage%, AST%, TOV%, STL%, BLK%, ORB%/DRB%/TRB% from the player line plus `team_box` and opponent totals. Two-point splits derive as FG − 3P. `starter` supports games-started.

Compared with CBBD, which serves ORtg/DRtg/win shares/PORPAG pre-computed, this is **more derivation work in exchange for a clean licence, no API key, no monthly quota, and full transparency of every formula** — which is arguably better aligned with DEC-018's requirement that every score be reproducible and traceable.

#### `mbb/shots` — the profile engine

**VERIFIED to exist for 2003–2026 (~137 MB).** Shot-level records are the raw material from which shot-location and shot-type profiles are built. Field-level schema was **not verified** (no Parquet reader is installed and installing one was out of scope), so whether it carries coordinates, shot-type labels, and assisted flags is **UNKNOWN — one small file read resolves it** (§21.9).

If it carries coordinates, this is **stronger** than CBBD's pre-binned shot types, because DraftLens would define rim/midrange/three boundaries itself and could document them — again favouring explainability.

#### `player_core` — the possible age fix

**REPORTED** (from hoopR package documentation, not independently confirmed): the player core schema includes `date_of_birth` (YYYY-MM-DD), `age`, `height`, `weight`, and `position_id` / `position_name` / `position_abbreviation`.

If accurate, this is significant: **age was the feature Sportradar could not supply pre-draft** (§20.5), and CBBD's DOB fill rate has never been measured. `player_core` spans **2003–2026 (24 files, VERIFIED)**.

**Fill rate is UNKNOWN and is the single highest-value thing to measure** (§21.9). ESPN college rosters commonly carry class year reliably and birth date sparsely, so temper expectations until measured.

### 21.2 Best NCAA source

**`hoopR-mbb-data`.** Static Parquet, 2003–2026, CC BY 4.0 covering data, updated daily, no key, no quota, language-agnostic. It replaces CBBD's role and removes CBBD's two unresolved problems at once: unreadable terms (§6.3) and a 1,000-call monthly quota (§6.4).

**What is given up versus CBBD:** pre-computed ORtg/DRtg/win shares/PORPAG, pre-binned shot types with `assisted_pct`, and a same-source `athlete_id → draft pick` join. **What is gained:** an explicit data licence, unlimited local access, shot-level data, and full history 2003–2026.

### 21.3 Best NBA player-statistics source — the biggest single upgrade

**`hoopR-nba-data/nba/player_season_stats`** — **25 Parquet files, 2002 → 2026, pre-aggregated, CC BY 4.0 (VERIFIED).**

§18 rated NBA comparables **"YELLOW, closest to red — the weakest family in the project,"** because the official NBA API is partner-only, `stats.nba.com` terms are unreadable, and balldontlie prohibits redistribution while lacking advanced stats. This repository resolves that: a full-history, statically distributed, explicitly licensed NBA player-season dataset with no key and no quota.

Field-level schema unverified (same Parquet-reader limitation), but the NBA `player_box` schema mirrors the MBB one, so the same derivation path applies. **Comparables move from RED-adjacent to plausible GREEN.**

### 21.4 Draft outcomes and the undrafted population — Wikipedia still wins

**`hoopR-nba-data/nba/draft` is insufficient — VERIFIED.** Its manifest (`nba_draft_in_data_repo.csv`) shows only **2023–2026**, and the 2026 entry reads `season 2026, row_count 60` — exactly 60 rows, i.e. **drafted players only, with no undrafted representation.** (The 2026 file was generated 2026-05-31, *before* the June 23–24 draft, so whether those 60 rows are picks-with-players or an empty pick order is additionally **UNKNOWN**.)

Three or four draft years cannot support a 15-fold rolling validation, and 60 rows cannot supply a negative class.

**No dataset found in this pass contains a non-outcome-selected undrafted prospect population.** The Kaggle candidates that advertise a drafted flag were assessed and rejected in §21.6.

**Therefore §3.6's conclusion stands unchanged: Wikipedia remains the prospect-population and draft-outcome source** — final NCAA early entrants ∪ drafted NCAA players, name-level and verified for 2011–2026, under CC BY-SA. Pass 4 searched hard for a replacement and did not find one.

### 21.5 Best Combine source — unchanged, three candidates compared

No Combine data exists in any hoopR repository (VERIFIED by directory listing) and none in Sportradar (§20.10). **A Combine-specific source remains mandatory.**

| | **NBA Anthropometric** | **NBA Draft Combine** | **NBA Draft Combine Measurement Data** |
| --- | --- | --- | --- |
| Author | tymoteuszdobrucki | marcusfern | thedevastator |
| URL | [link](https://www.kaggle.com/datasets/tymoteuszdobrucki/nba-anthropometric) | [link](https://www.kaggle.com/datasets/marcusfern/nba-draft-combine) | [link](https://www.kaggle.com/datasets/thedevastator/nba-draft-combine-measurement-data-from-2012-201) |
| Licence | **CC BY 4.0 — VERIFIED** | **CC BY 4.0 — VERIFIED** | **CC BY 4.0 — VERIFIED** |
| Coverage | **2000–2023 — VERIFIED** | UNKNOWN | 2012–2019 (from slug) |
| 2026? | ❌ No | UNKNOWN (contradictory evidence, §20.11) | ❌ No |
| Fields | Anthropometrics only | UNKNOWN | Measurements |
| Provenance | REPORTED *"acquired using NBA Stats API"* | UNKNOWN | UNKNOWN |

Also noted: [`natelapin/nba-draft-combine-and-player-info-drafted-data`](https://www.kaggle.com/datasets/natelapin/nba-draft-combine-and-player-info-drafted-data) — *"NBA Draft Combine Results and Player Info, Includes if player was drafted or not"*, **Apache 2.0 (VERIFIED)**. Interesting because it pairs Combine data with a drafted flag, but its population definition, coverage, and provenance are **UNKNOWN** and it must be treated as outcome-suspect until its prospect pool is documented (§21.6).

**Best current candidate: `tymoteuszdobrucki/nba-anthropometric`** — only because it is the one with verified coverage (2000–2023) and a stated provenance. It does **not** cover 2026, so the 2026 demo would need Combine data from elsewhere or would proceed without it (all Combine fields are classified *Desirable/Optional*, never *Essential*, per §12 — so this degrades the demo rather than blocking it).

### 21.6 Datasets rejected in this pass

| Dataset / source | Reason |
| --- | --- |
| [`wyattowalsh/basketball` "NBA Database"](https://www.kaggle.com/datasets/wyattowalsh/basketball) | **Strong runner-up, rejected as primary.** SQLite, daily-updated, [`wyattowalsh/nbadb`](https://github.com/wyattowalsh/nbadb) pipeline MIT-licensed and actively maintained (pushed 2026-08-03, 70 stars), Kaggle licence **CC BY-SA 4.0 (VERIFIED)**, and it contains `draft_history`, `draft_combine_stats`, and `common_player_info`. **But its README and pipeline confirm extraction from `stats.nba.com` via a pinned `nba_api` runtime** — so it inherits the unresolved NBA Terms question (§5.2) wholesale. Superseded for NBA stats by hoopR (ESPN-derived, cleaner chain). **Retain as the leading fallback for Combine + draft-combine data if the NBA-terms question ever clears.** |
| [`adityak2003/college-basketball-players-20092021`](https://www.kaggle.com/datasets/adityak2003/college-basketball-players-20092021) | College stats 2009–2021 + NBA advanced 2014–2022. **No licence exposed on the page (UNKNOWN)**; provenance undocumented but strongly consistent with Barttorvik, whose `robots.txt` disallows `/playerstat.php` and `/*.json` (§4.3). Would launder a robots-disallowed source. Ends 2021 — no 2026. **Reject.** |
| [`andrewsundberg/college-basketball-dataset`](https://www.kaggle.com/datasets/andrewsundberg/college-basketball-dataset) | CC0 (VERIFIED), 2013–2025. **Team-level, not player-level** — wrong grain for a prospect board. **Reject for this purpose.** |
| [`benwieland/nba-draft-data`](https://www.kaggle.com/datasets/benwieland/nba-draft-data), [`mattop/nba-draft-basketball-player-data-19892021`](https://www.kaggle.com/datasets/mattop/nba-draft-basketball-player-data-19892021) | Both **CC0 (VERIFIED)**. Both are *drafted-players-only* pick tables (`benwieland` describes *"NBA statistics for every pick"*). No undrafted population; both end 2021. Wikipedia already covers this more completely and more currently. **Reject.** |
| GitHub draft-model repos (`JasonG7234/NBA-Draft-Model`, `mathgonzaga/NBADraftModel`, `AyushBatra01/NBADraft`, `KaanME/NBA-Draft-Model`) | Re-confirmed from pass 2: provenance is RealGM / Basketball-Reference / Barttorvik / 247Sports / HoopMath — all blocked, robots-disallowed, or analyst-ranking sources barred by DEC-013. **Reject — provenance laundering.** |
| Hugging Face NBA datasets (`Hatman/NBA-Player-Career-Stats`, `suzyanil/nba-data`, `mrblack911/NBA_DATA`, `dcayton/nba_tracking_data_15_16`) | Undocumented provenance, no schema documentation, or wrong scope (2015-16 tracking only). None approaches hoopR's coverage or licence clarity. **Reject.** |
| Zenodo / Dataverse / academic supplements | Searched; **no DOI-citable dataset combining NCAA statistics with drafted *and* undrafted prospects was found.** Papers exist (e.g. *The Determinants of Draft Position for NBA Prospects*) but without archived datasets. Confirms pass 2's Option D rejection. |

### 21.7 Licence ratings

| Source | Uploader/publisher licence | Upstream | Rating |
| --- | --- | --- | --- |
| **Wikipedia / MediaWiki API** | CC BY-SA — VERIFIED | Wikimedia community | 🟢 **GREEN** |
| **`hoopR-mbb-data`** | **CC BY 4.0 explicitly covering data — VERIFIED** | **ESPN** | 🟡 **YELLOW** (green licence, unexamined upstream) |
| **`hoopR-nba-data`** | **CC BY 4.0 explicitly covering data — VERIFIED** | **ESPN** | 🟡 **YELLOW** (same) |
| Kaggle Combine (`nba-anthropometric`) | CC BY 4.0 — VERIFIED | REPORTED NBA Stats | 🟡 **YELLOW** |
| `wyattowalsh/basketball` | CC BY-SA 4.0 — VERIFIED | **Confirmed `stats.nba.com`** | 🟡 **YELLOW**, closer to red |
| CBBD | UNKNOWN, redistribution REPORTED prohibited | UNKNOWN | 🟡/🔴 |
| Sportradar | Clear and **prohibitive** for public output | Own | 🔴 **RED** |
| Sports-Reference, Barttorvik, stats.ncaa.org, RealGM | Automated access prohibited / robots-disallowed / 403 | — | 🔴 **RED** |

**The honest caveat, stated once and applying to hoopR, Kaggle, and `wyattowalsh` alike:** a redistributor's licence declaration binds *that redistributor's* contribution. It cannot extinguish rights held upstream. hoopR is nonetheless the **strongest position available**, because (a) the licence text explicitly names *data*, not just code; (b) the source chain is documented rather than implied; (c) the project is institutional, long-running, and actively maintained rather than an anonymous one-off upload. **No source in this project reaches unambiguous GREEN on upstream rights except Wikipedia.**

### 21.8 Candidate bundles

**BUNDLE A — hoopR + Wikipedia + Kaggle Combine ⭐ RECOMMENDED**
`hoopR-mbb-data` (NCAA stats, shots, bios) + `hoopR-nba-data` (NBA comparables) · Wikipedia (population + draft outcomes) · Kaggle Combine (anthropometrics)

**BUNDLE B — CBBD + Wikipedia + Kaggle Combine** *(the current Strategy A)*

**BUNDLE C — `wyattowalsh/basketball` + hoopR-mbb + Wikipedia**
NBA side, draft history and Combine all from one SQLite database; NCAA from hoopR; population from Wikipedia.

**BUNDLE D — hoopR only (mbb + nba + nba draft)**
Single publisher, two-source-family ideal — but the draft directory covers only 2023–2026 with drafted players only.

**BUNDLE E — Sportradar + Kaggle Combine** *(pass 3)*

| Criterion | **A ⭐** | **B** (current) | **C** | **D** | **E** |
| --- | :-: | :-: | :-: | :-: | :-: |
| Product coverage | 🟢 | 🟢 | 🟢 | 🔴 | 🟡 |
| Historical depth | 🟢 2003–2026 | 🟢 | 🟢 | 🔴 draft 2023+ | 🔴 draft 2019+ |
| 2026 feasibility | 🟢 (no Combine) | 🟢 (no Combine) | 🟢 | 🟡 | 🟡 |
| Undrafted support | 🟡 Wikipedia | 🟡 Wikipedia | 🟡 Wikipedia | 🔴 none | ❓ unproven |
| Advanced NCAA stats | 🟡 derived | 🟢 pre-computed | 🟡 derived | 🟡 | 🟡 |
| NBA comparable quality | 🟢 2002–2026 | 🔴 weakest | 🟢 | 🟢 | 🟢 |
| Combine quality | 🟡 to 2023 | 🟡 to 2023 | 🟡 | 🔴 none | 🟡 |
| Entity matching | 🟡 | 🔴 | 🟡 | 🟡 | 🟡 |
| Licence clarity | 🟢 **all explicit** | 🟡 CBBD unread | 🟡 | 🟢 | 🔴 |
| Public reproducibility | 🟢 | 🟡 likely no | 🟡 | 🟢 | 🔴 |
| Implementation effort | 🟡 derivation | 🟡 | 🟡 | 🟢 | 🟢 |
| Sources | **3** | 3–4 | 3 | 1–2 | 2 |
| **Overall** | 🟢 **GREEN** | 🟡 | 🟡 | 🔴 | 🔴 |

**Bundle A is recommended (PROVISIONAL).** It reaches the "three sources maximum" target, every component's licence explicitly addresses data, it removes the two CBBD unknowns, and it converts NBA comparables from the project's weakest capability into a solved one. The cost is deriving advanced metrics from primitives rather than consuming them pre-computed — real work, but transparent work that improves explainability.

### 21.9 Entity matching under Bundle A

| Join | Basis | Determinism |
| --- | --- | --- |
| NCAA box ↔ NCAA bios/shots | `athlete_id` within hoopR-mbb | ✅ **Deterministic** |
| NBA season stats ↔ NBA bios | `athlete_id` within hoopR-nba | ✅ **Deterministic** |
| **Wikipedia population ↔ hoopR NCAA** | name + school + class year | ⚠️ **Normalization required** |
| **Wikipedia draft results ↔ hoopR NCAA** | name + school + draft year | ⚠️ **Normalization required** |
| **Kaggle Combine ↔ hoopR NCAA** | name + position | ⚠️ **Manual review likely** |
| NCAA ↔ NBA (comparables) | **Not required** — the firewall in §10.1 forbids this join for board training; comparables operate on the NBA pool independently | N/A |

**Net difficulty: comparable to Bundle B, not worse.** hoopR uses ESPN `athlete_id` consistently across MBB and NBA repositories, and the `mbb/crosswalk` directory (2026 only, 5,627 player rows — VERIFIED) suggests an ID-mapping resource whose scope should be checked. The two hard joins (Wikipedia→NCAA, Combine→NCAA) are the same two that Bundle B already faces.

### 21.10 Research window — **2011–2025 + 2026 holdout stands**

hoopR MBB coverage begins at **2003**, comfortably earlier than the 2011 floor. The binding constraints remain those identified in §7: Wikipedia's eligibility-section structure stabilises at 2011, and 2010-11 is the proxy for broad college advanced-metric reliability.

**No move to 2013 is warranted** — that was contingent on Sportradar's 2013 floor, and Sportradar is not recommended. Under Bundle A there is no data-driven reason to discard 2011 and 2012.

One new consideration: since advanced metrics would be **derived from box-score primitives** rather than consumed pre-computed, their availability is uniform back to 2003, which *strengthens* the case for keeping 2011. Whether ESPN's early-2000s NCAA coverage is complete enough is **UNKNOWN** and should be checked when the files are read.

### 21.11 2026 replay under Bundle A

| Component | Source | Status |
| --- | --- | --- |
| 2025-26 NCAA player stats | `mbb/player_box_2026.parquet` | ✅ **VERIFIED present** |
| 2025-26 NCAA shots | `mbb/shots_2026.parquet` | ✅ **VERIFIED present** |
| 2026 NCAA bios / position / height / weight | `mbb/player_core_2026.parquet`, `mbb/rosters_2026.parquet` | ✅ **VERIFIED present** |
| Age / DOB | `player_core` `date_of_birth` | 🟡 **REPORTED; fill rate UNKNOWN** |
| 2026 prospect population | Wikipedia — 26 final NCAA early entrants | ✅ VERIFIED |
| 2026 draft outcome (target) | Wikipedia — full 60-pick table | ✅ VERIFIED |
| 2026 Combine | ❌ Not in the verified-coverage Kaggle dataset | 🔴 **Gap** |
| NBA comparables pool | `nba/player_season_stats_2026.parquet` and history | ✅ **VERIFIED present** |

**Rating: 🟢 GREEN, with a Combine caveat.** Every component except Combine is verified present, and the 2026-06-22 23:59:59 ET cutoff (§14) is unaffected. Combine fields are *Desirable/Optional*, so their absence degrades the Athleticism and Physical Profile sub-scores for 2026 rather than blocking the replay.

### 21.12 Status labels

| Finding | Label |
| --- | --- |
| hoopR-mbb-data / hoopR-nba-data licensed **CC BY 4.0 explicitly covering data** | **VERIFIED** |
| hoopR MBB `player_box` 2003–2026; `shots` 2003–2026; `player_core` 2003–2026 | **VERIFIED** |
| hoopR NBA `player_season_stats` 2002–2026 pre-aggregated | **VERIFIED** |
| hoopR `player_box` 55-column schema (primitives only, no advanced metrics) | **VERIFIED** |
| hoopR provenance = ESPN, documented in README | **VERIFIED** |
| hoopR `nba/draft` covers only 2023–2026, 60 rows for 2026 (drafted only) | **VERIFIED** |
| `player_core` contains `date_of_birth`, `age`, `height`, `weight`, position | **REPORTED — fill rate UNKNOWN** |
| `mbb/shots` field schema (coordinates? assisted flags?) | **UNKNOWN — one small file read resolves it** |
| Kaggle Combine datasets CC BY 4.0 | **VERIFIED** |
| Upstream ESPN rights vs. CC BY 4.0 redistribution | **UNKNOWN — LEGAL REVIEW ADVISED** |
| Bundle A as recommended strategy | **PROVISIONAL — owner approval required** |
| `wyattowalsh/basketball` as NBA primary | **REJECTED as primary** (stats.nba.com upstream); retained as Combine/draft fallback |
| `adityak2003`, `andrewsundberg`, `benwieland`, `mattop`, GitHub draft repos, HF datasets | **REJECTED** |
| No open dataset with non-outcome-selected undrafted prospects | **VERIFIED (negative)** |

### 21.13 Owner actions arising from pass 4

1. 🔴 **OWNER APPROVAL REQUIRED FOR DOWNLOAD.** Confirming schemas and fill rates requires reading Parquet files. Minimum useful set ≈ **215 MB** (`mbb/player_box` ~75 MB + `mbb/shots` ~137 MB), plus small `player_core` files. No Parquet reader is currently installed — this would also be the first dependency installation, which DEC-022 defers.
2. 🟠 **Approve a small verification read first** — 3 files (`player_core_2026`, one `shots` file, one `player_box` file, together a few MB) would resolve the DOB fill rate, the shots schema, and the box-score aggregation path before any bulk pull.
3. 🟠 **Legal review of the ESPN-upstream question** for hoopR (§21.7). Lower risk than the NBA-terms question — the licence explicitly covers data and the chain is documented — but it is the same class of question.
4. 🟠 **Decide Bundle A vs. Bundle B**, or a staged migration (Bundle B for NCAA, Bundle A's `hoopR-nba-data` for comparables immediately, since that upgrade is unambiguous).
5. 🟠 Inspect the Kaggle Combine datasets while signed in (carried forward from §20.16).

---

## 22. hoopR small-sample verification (pass 5)

**Authorised scope:** a small verification pass only — four 2026 Parquet files, **17.22 MB total**, downloaded to `data/raw/`. No historical archive was acquired. Bundle A remains **PROVISIONAL**.

**Environment:** local `.venv/` with `pandas` 3.0.5 and `pyarrow` 25.0.0 only (DEC-037). Audit scripts: [`scripts/verify_hoopr_sample.py`](../scripts/verify_hoopr_sample.py), [`scripts/verify_hoopr_sample2.py`](../scripts/verify_hoopr_sample2.py) — read-only, they write nothing.

**Files inspected (all VERIFIED present and readable):**

| File | Size | Rows | Cols |
| --- | --: | --: | --: |
| `mbb/player_core_2026.parquet` | 0.88 MB | 12,481 | 36 |
| `mbb/player_box_2026.parquet` | 3.24 MB | 196,876 | 55 |
| `mbb/shots_2026.parquet` | 13.00 MB | 991,836 | 20 |
| `nba/player_season_stats_2026.parquet` | 0.11 MB | 25,006 | 15 |

**Headline: the data is better than pass 4 estimated in every respect except one — and that one is serious.** Shot-type labels and assist linkage are *directly present* (not merely derivable from coordinates), identity is effectively perfect, and prospect matching was flawless. But **date of birth is 1.58% populated**, which removes pre-draft age from hoopR entirely.

### 22.1 AUDIT 1 — `player_core` schema and fill rates

36 columns: `season, athlete_id, guid, uid, slug, type, first_name, last_name, full_name, display_name, short_name, height, display_height, weight, display_weight, age, date_of_birth, birth_city, birth_state, birth_country, jersey, position_id, position_name, position_abbreviation, position_display_name, college_id, current_team_id, headshot_href, experience_years, status_id, status_name, status_type, draft_year, draft_round, draft_selection, active`

12,481 rows, **12,481 unique `athlete_id`, zero duplicates** — exactly one row per player-season.

| Field | dtype | Fill (all 12,481) | **Fill (rotation: ≥200 min, n=3,486)** |
| --- | --- | --: | --: |
| `athlete_id`, `display_name`, `position_abbreviation` | int64 / str / str | **100.00%** | **100.00%** |
| `experience_years` | float64 | 97.29% | **100.00%** |
| `height` | float64 | 94.38% | **99.83%** |
| `weight` | float64 | 65.12% | **96.70%** |
| `birth_city` / `birth_country` | str | 92.70% | — |
| `birth_state` | str | 83.81% | — |
| **`date_of_birth`** | str | **1.58%** (197) | **5.45%** (190) |
| **`age`** | float64 | **1.57%** (196) | **5.45%** (190) |
| `college_id` | float64 | 0.63% | — |
| `draft_year`, `draft_round`, `draft_selection` | float64 | **0.00%** | 0.00% |

#### 🔴 CAN DRAFTLENS RELIABLY DERIVE PRE-DRAFT AGE? **NO — VERIFIED.**

Pass 4 recorded as **REPORTED** that `player_core` carries `date_of_birth` and flagged fill rate as the highest-value unknown. **The field exists; the data does not.** 197 of 12,481 players have a birth date, and restricting to rotation players — the population DraftLens actually scores — barely moves it, to **5.45%**.

This is decisive, not marginal. Consequences:

- **PRODUCT.md §11 approves age as a candidate pre-draft feature whose relevance must be evaluated from historical data.** Under hoopR alone, that evaluation cannot be run at all.
- `age` (1.57%) is additionally **unusable for historical work even where populated** — it is a current-age field that drifts with time. Per the audit instruction and DEC-012, only `date_of_birth` computed against the relevant draft date would be admissible.
- `experience_years` (100% among rotation players) and class year are **not substitutes** for age. They correlate with it but are a different quantity, and DEC-017 forbids fabricating the difference.

**This is the one respect in which CBBD may still be superior — and CBBD's own DOB fill rate has never been measured.** See §22.10.

Two further notes: `player_core` has **no team-name column** (only `current_team_id`), and the `draft_*` columns are **100% null** in the MBB feed — they exist in the ESPN athlete schema but carry no NCAA-side draft information.

### 22.2 AUDIT 2 — `player_box`

196,876 rows (game-level), 55 columns, 12,481 unique players, 727 teams.

**Present — VERIFIED (all critical fields):** `athlete_id`, `team_id`, `athlete_display_name`, `athlete_position_abbreviation`, `game_id`, `season`, `season_type`, `game_date`, `minutes`, `points`, `field_goals_made`, `field_goals_attempted`, `three_point_field_goals_made`, `three_point_field_goals_attempted`, `free_throws_made`, `free_throws_attempted`, `offensive_rebounds`, `defensive_rebounds`, `rebounds`, `assists`, `turnovers`, `steals`, `blocks`, `fouls`, `starter`, `did_not_play`, `ejected`, `team_score`, `opponent_team_id`, `opponent_team_score`, `home_away`.

**Absent as columns but arithmetically derivable:** FG%, 2PM, 2PA, 2P%, 3P%, FT%, games played, games started (from `starter` + `did_not_play`).

#### Team context — **`team_box` is NOT required — VERIFIED**

Aggregating `player_box` by `(game_id, team_id)` reconstructs team totals directly:

- 12,600 team-game rows
- **summed player points == `team_score` in 99.89%** of team-games (12,586/12,600)
- median summed team minutes/game = **200** (exactly the expected 5 × 40)
- team FGA, FTA, OREB, DREB, TOV, AST all derivable with **zero nulls**
- **opponent totals available via self-join on `game_id` for 100.00%** of team-games

So possession estimates, ORB%/DRB%/TRB%, usage%, and all rate statistics are computable from `player_box` alone. The 0.11% points mismatch is a data-quality item to quantify, not a blocker.

### 22.3 AUDIT 3 — `shots` (the strongest single finding)

991,836 rows, 20 columns: `game_id, season, period_number, clock_display_value, team_id, athlete_id_1, athlete_id_2, type_id, type_text, scoring_play, score_value, coordinate_x, coordinate_y, coordinate_x_raw, coordinate_y_raw, athlete_name_1, athlete_name_2, team_name, team_mascot, team_abbrev`

| Field | Present | Fill | Notes |
| --- | :-: | --: | --- |
| Shooter ID (`athlete_id_1`) | ✅ | 99.91% | |
| **Assister ID (`athlete_id_2`)** | ✅ | 17.21% overall | **= assist linkage** |
| Shot made/missed (`scoring_play`) | ✅ | 100% | boolean |
| Shot value (`score_value`) | ✅ | 100% | {2: 445,829 · 3: 292,418 · 1: 253,589} |
| **Shot type (`type_text`)** | ✅ | 100% | **direct labels** |
| Period, game clock | ✅ | 100% | |
| Team, game ID | ✅ | 100% | |
| x/y coordinates | ⚠️ | 100% *nominally* | **contaminated — see below** |
| Shot distance | ❌ | — | derivable only from usable coordinates |
| Explicit zone (rim/paint/midrange) | ❌ | — | derivable from `type_text` |

**Shot-type taxonomy — VERIFIED, directly labelled:**

| `type_text` | Count | Share |
| --- | --: | --: |
| JumpShot | 452,659 | 45.64% |
| MadeFreeThrow | 253,589 | 25.57% |
| LayUpShot | 237,730 | 23.97% |
| **DunkShot** | 28,375 | 2.86% |
| **TipShot** | 19,481 | 1.96% |
| Shot (unclassified) | 2 | 0.00% |

This is **materially better than pass 4 assumed**. Pass 4 expected to have to infer shot types from coordinates; instead ESPN supplies dunk / layup / tip-in / jumper labels directly — the same granularity CBBD serves pre-binned, but at shot level, so DraftLens can define its own aggregations and document them (DEC-018).

**Assist linkage — VERIFIED:** of 738,247 field-goal attempts (excluding free throws), 23.12% carry an assister; of the 330,073 **made** field goals, **51.71% are assisted** — a plausible NCAA assisted-FG rate. 99.76% of assister IDs resolve to `player_box`. **Assisted/unassisted shot rates are directly derivable, per shot type.**

#### ⚠️ Two data-quality defects found

1. **Coordinates are contaminated with sentinel values.** `coordinate_x` ranges −214,748,406.75 … 214,748,406.75 and `coordinate_y` −214,748,365 … 214,748,365 — the int32 overflow sentinel (±2³¹) standing in for missing. The columns are nominally 100% non-null but a share of values are unusable. **The true usable-coordinate rate is UNKNOWN and must be measured.** Fortunately DraftLens does not depend on coordinates: `type_text` carries the shot-style signal.
2. **Only *made* free throws appear.** `MadeFreeThrow` (253,589) exactly equals the `score_value == 1` count, so missed free throws are absent from this file. **Free-throw attempts and FT% must come from `player_box`, never from `shots`.** Any FT metric computed from `shots` would be silently wrong.

### 22.4 AUDIT 4 — metric derivability

| Metric | Status | Source columns required |
| --- | --- | --- |
| FG%, 3P%, FT% | **DERIVABLE** | `player_box`: made / attempted pairs |
| 2PM, 2PA, 2P% | **DERIVABLE** | `player_box`: `field_goals_*` − `three_point_field_goals_*` |
| eFG% | **DERIVABLE** | `player_box`: `field_goals_made`, `three_point_field_goals_made`, `field_goals_attempted` |
| TS% | **DERIVABLE** | `player_box`: `points`, `field_goals_attempted`, `free_throws_attempted` |
| AST/TO | **DERIVABLE** | `player_box`: `assists`, `turnovers` |
| AST% | **DERIVABLE** | `player_box` player + team aggregates: `assists`, `minutes`, team `field_goals_made` |
| TOV% | **DERIVABLE** | `player_box`: `turnovers`, `field_goals_attempted`, `free_throws_attempted` |
| ORB%, DRB%, TRB% | **DERIVABLE** | `player_box` player + team + **opponent** rebounds (self-join on `game_id`) |
| STL%, BLK% | **DERIVABLE** | `player_box` player + opponent possession estimate |
| usage% | **DERIVABLE** | `player_box`: player FGA/FTA/TOV/minutes + team totals |
| Points per possession | **DERIVABLE** | `player_box`: points + possession estimate |
| Per-40 statistics | **DERIVABLE** | `player_box`: any counting stat + `minutes` |
| Per-100-possession statistics | **DERIVABLE** | `player_box`: counting stats + team possession estimate |
| **Shot-at-rim frequency** | **DERIVABLE** | `shots`: `type_text` ∈ {LayUpShot, DunkShot, TipShot} |
| **Rim FG%** | **DERIVABLE** | `shots`: `type_text` + `scoring_play` |
| **Midrange frequency** | ⚠️ **DERIVABLE (approximate)** | `shots`: JumpShot with `score_value == 2`. A true midrange/three split by distance needs usable coordinates (§22.3) |
| **3PA rate** | **DERIVABLE** | `player_box` (3PA/FGA) or `shots` (`score_value == 3`) |
| **Assisted shot rate** | **DERIVABLE** | `shots`: `athlete_id_2` presence, by `type_text` |
| **Dunk frequency** | **DIRECT** | `shots`: `type_text == 'DunkShot'` |
| **Layup frequency** | **DIRECT** | `shots`: `type_text == 'LayUpShot'` |
| Offensive / defensive rating | **REQUIRES ADDITIONAL DATASET** | Not derivable from box + shots at player level with defensible attribution |
| BPM, win shares, PORPAG | **NOT AVAILABLE** | Not derivable from these primitives |
| **Age at draft** | 🔴 **NOT AVAILABLE** | `date_of_birth` 1.58% (§22.1) |

No formulas are specified here — that remains [ML_SPEC.md](ML_SPEC.md)'s job.

### 22.5 AUDIT 5 — six MVP profile feasibility

Assessed purely on verified available/derivable data. **No weights are proposed.**

**1. Shooter — 🟢 GREEN**
Candidate dimensions: 3PA volume and 3PA rate · 3P% · FT% · eFG% · TS% · jump-shot share of attempts · **unassisted three-point rate** (self-creation vs. spot-up).

**2. Slasher / Rim Attacker — 🟢 GREEN**
Rim-attempt share (LayUp + Dunk + Tip / FGA) · rim FG% · free-throw rate (FTA/FGA) · **unassisted rim-attempt share** — the metric that separates a slasher from a play-finisher · dunk frequency.

**3. Playmaker — 🟢 GREEN**
Assists · AST% · AST/TO · TOV% · usage% · **assists credited at shot level** via `athlete_id_2`, decomposable by the shot type created (e.g. assists generating threes vs. rim finishes).

**4. 3&D Wing — 🟡 YELLOW**
The shooting half is GREEN (as profile 1). The defensive half is **thin**: only steals, blocks, defensive rebounds, and fouls exist. There is **no defensive rating, no matchup data, no opponent shooting-when-defended, and no point-of-attack signal**. Steals and blocks are noisy, position-confounded proxies for perimeter defence. Height/weight (99.83%/96.70% among rotation players) and position add context but do not measure defence.

**5. Rim Protector — 🟡 YELLOW**
Blocks and BLK% are the primary signal, supported by DREB%, height (99.83%) and weight (96.70%). But **opponent field-goal percentage at the rim when this player is on the floor is not derivable** — the shots file has no defender attribution and no on/off context. Blocks alone reward one visible action and miss deterrence entirely, which is most of rim protection.

**6. Stretch Big — 🟢 GREEN**
Position (100% fill) · height/weight · 3PA rate · 3PA volume · 3P% · share of attempts that are jumpers vs. rim. The conjunction of size and perimeter shooting is exactly what the available data measures well.

**Summary: 4 GREEN, 2 YELLOW, 0 RED.** Both YELLOWs are defence-side and share one root cause — box-score defensive statistics are weak proxies. This is a limitation of the data class, not of hoopR specifically; CBBD's defensive rating would be a modelled estimate rather than a measurement.

### 22.6 AUDIT 6 — size, duplicates, transfers

| File | Rows | Cols | Unique players | Unique teams |
| --- | --: | --: | --: | --: |
| `player_core` | 12,481 | 36 | 12,481 | — |
| `player_box` | 196,876 | 55 | 12,481 | 727 |
| `shots` | 991,836 | 20 | 9,381 shooters | 723 |

- **`player_core` has exactly one row per `athlete_id` — zero duplicates.** No "TOT"-style aggregate rows exist; the grain is player-season, already deduplicated.
- **`player_box` is game-level**, one row per player-game, so multi-team seasons appear as *rows on different teams*, not as duplicate season rows.
- **Mid-season transfers are rare: 21 of 12,481 players (0.17%) appear under more than one `team_id` within 2026.** Portal transfers between seasons are the common case and appear as separate player-seasons.
- **2 duplicate `(athlete_id, game_id)` rows** — a negligible but real defect requiring a dedupe step.
- `shots` covers 9,381 of 12,481 players (75.2%); the remainder are deep-bench players who never attempted a shot.

**The aggregation policy is not resolved here** (per instruction). What is now established: DEC-010's "latest NCAA season" rule is cleanly implementable because the season grain is unambiguous, and the multi-team case affects well under 1% of players.

### 22.7 AUDIT 7 — `athlete_id` consistency

⚠️ **A first-pass check reported 0% overlap. That was an artifact of my own comparison, not a data defect** — `player_core.athlete_id` is `int64` while `player_box.athlete_id` and `shots.athlete_id_1` are `float64`, so naive string casting produced `"5142718"` vs `"5142718.0"`. Corrected with numeric coercion:

| Join | Coverage |
| --- | --: |
| `player_box` → `player_core` | **100.00%** (12,481 / 12,481) |
| `shots` shooter → `player_core` | **99.42%** (9,327 / 9,381) |
| `shots` shooter → `player_box` | **99.42%** (9,327 / 9,381) |
| `shots` **assister** → `player_box` | **99.76%** (6,988 / 7,005) |

**hoopR is confirmed as a canonical NCAA identity source within a season.** Every player with a box-score row has a bio row. **Practical note for the pipeline: `athlete_id` dtype is inconsistent across files and must be normalised to a single integer type on load** — exactly the trap that produced the false 0%.

Cross-*season* ID stability was **not tested** (only 2026 was downloaded) and remains **UNKNOWN** — see §22.11.

### 22.8 AUDIT 8 — 2026 prospect matching sample

Twelve verified 2026 NCAA early entrants (names and schools from the official nba.com early-entry table and the Wikipedia early-entrants section, both verified in §2 and §3.2), matched against `player_core` on normalised name, with school resolved by joining `player_box`.

School resolution succeeded for **12,481/12,481 (100%)** of `player_core` rows via the `player_box` team join.

| Result | Count |
| --- | --: |
| **Exact (name + school agree)** | **12 / 12** |
| Name-only (school mismatch) | 0 |
| Ambiguous | 0 |
| Unmatched | 0 |

All twelve — Dybantsa (BYU), Boozer (Duke), Brown Jr. (Louisville), Acuff Jr. (Arkansas), Ament (Tennessee), Anderson Jr. (Texas Tech), Burries (Arizona), Evans (Duke), Dawes (Utah), Dynes (USC), Bonke (Charlotte), Brumbaugh (Tulane) — resolved to a single `athlete_id` with the correct school and a position label. **No match was forced.**

**100% on a 12-player sample is encouraging but not conclusive.** The sample is biased toward well-known players with clean names; it deliberately included four suffixed names (`Jr.`) and the normalisation handled them. Two Duke players matched without collision. The full-population match rate — especially for obscure players and historical seasons — remains **UNKNOWN**.

### 22.9 Optional audit — NBA `player_season_stats` 2026

**Format finding:** the file is **LONG (tidy) format**, not wide — 25,006 rows = 582 players × ~43 stat rows each. Columns: `season, athlete_id, athlete_display_name, athlete_position_abbreviation, athlete_jersey, team_id, team_slug, team_display_name, category, stat_label, stat_name, stat_display_name, stat_description, display_value, value`. **A pivot is required before use.**

40 distinct `stat_name` values across three categories:

- **totals (15):** `points, assists, totalRebounds, offensiveRebounds, defensiveRebounds, steals, blocks, turnovers, fouls, fieldGoalsMade-fieldGoalsAttempted, threePointFieldGoalsMade-threePointFieldGoalsAttempted, freeThrowsMade-freeThrowsAttempted, fieldGoalPct, threePointFieldGoalPct, freeThrowPct`
- **averages (18):** per-game equivalents plus `gamesPlayed, gamesStarted, avgMinutes`
- **miscellaneous (10):** `assistTurnoverRatio, scoringEfficiency, shootingEfficiency, doubleDouble, tripleDouble, disqualifications, ejections, flagrantFouls, technicalFouls, stealTurnoverRatio`

| Requirement | Status |
| --- | --- |
| player ID, name, position, team | ✅ **DIRECT** |
| games, minutes | ✅ DIRECT (`gamesPlayed`, `avgMinutes`) |
| points, rebounds (O/D/T), assists, turnovers, steals, blocks | ✅ DIRECT |
| FG, 3P, FT made/attempted | ✅ DIRECT — but stored as **`"made-attempted"` combined strings** requiring parsing |
| 2P | **DERIVABLE** (FG − 3P) |
| TS%, eFG% | **DERIVABLE** from points, FGA, FTA, 3PM |
| usage% | ⚠️ **Requires NBA team totals** — not in this file; would need `nba/player_box` |
| `value` column | 13.96% null — the combined `"made-attempted"` rows have no scalar value, as expected |

**NBA comparables rating: 🟢 GREEN.** All primitives needed for a normalised NCAA↔NBA profile space are present or derivable, with the same dimensional families available on both sides. Two caveats: the long format and `"made-attempted"` strings add parsing work, and usage% needs one more file. **This confirms pass 4's central claim — the project's weakest capability is now solved.** No similarity method is proposed here.

### 22.10 Does hoopR replace CBBD?

**PARTIALLY.**

| Dimension | hoopR (verified) | CBBD (documented, unverified) |
| --- | --- | --- |
| Licence | **CC BY 4.0 naming data** | Unread; redistribution REPORTED prohibited |
| Access | Static files, no key, no quota | API key, 1,000 calls/month |
| Shot detail | **Shot-type labels + assist linkage, shot-level** | Pre-binned types + `assisted_pct` |
| Box score / rate stats | Primitives; all rates derivable (team totals confirmed derivable) | Pre-computed |
| ORtg / DRtg / win shares / PORPAG / BPM | **Not available** | Pre-computed |
| Position | **100% fill** | Present |
| Height / weight | **99.83% / 96.70%** (rotation) | Present |
| **Date of birth** | 🔴 **1.58% — unusable** | Field exists; **fill rate still unmeasured** |

hoopR wins decisively on licence, access, and shot detail — the things that were blocking. It loses on pre-computed efficiency ratings (acceptable; most are derivable, and BPM/win shares were never essential) and, critically, **on age**.

### 22.11 New risks discovered

| # | Risk | Severity |
| --- | --- | :-: |
| 1 | **`date_of_birth` 1.58% / 5.45% among rotation players** — pre-draft age unavailable from hoopR. Contradicts pass 4's REPORTED expectation | 🔴 **HIGH** |
| 2 | **`shots` coordinates contaminated with ±2.1×10⁸ int32 sentinels** — nominally 100% non-null, truly usable share UNKNOWN | 🟠 MEDIUM |
| 3 | **`shots` contains only *made* free throws** — FT metrics must come from `player_box` or they will be silently wrong | 🟠 MEDIUM |
| 4 | **`athlete_id` dtype differs across files** (int64 vs float64) — produced a false 0% match in the first check; must be normalised on load | 🟠 MEDIUM |
| 5 | Cross-*season* `athlete_id` stability untested (2026 only) | 🟠 MEDIUM |
| 6 | 2 duplicate `(athlete_id, game_id)` rows; 0.11% team-points reconciliation gap | 🟢 LOW |
| 7 | `player_core` has no team-name column; school requires a `player_box` join (100% successful) | 🟢 LOW |
| 8 | `draft_year` / `draft_round` / `draft_selection` are 100% null in the MBB feed | 🟢 LOW (Wikipedia supplies these) |
| 9 | ESPN early-season coverage for 2011–2013 untested | 🟠 MEDIUM |

### 22.12 Status labels

| Finding | Label |
| --- | --- |
| Four files readable; schemas as listed | **VERIFIED** |
| `date_of_birth` 1.58% overall / 5.45% rotation | **VERIFIED — BLOCKING for the age feature** |
| position 100%, height 99.83%, weight 96.70% (rotation) | **VERIFIED** |
| Shot type directly labelled; assist linkage present; 51.71% of made FG assisted | **VERIFIED** |
| Team totals derivable from `player_box` alone; opponent join 100% | **VERIFIED** |
| `player_box` → `player_core` ID coverage 100% | **VERIFIED** |
| 12/12 exact prospect matches | **VERIFIED (small sample)** |
| NBA comparables data sufficient | **VERIFIED — GREEN** |
| Coordinate usable-value rate | **UNKNOWN** |
| Cross-season ID stability; 2011–2013 coverage; full-population match rate | **UNKNOWN** |
| CBBD DOB fill rate | **UNKNOWN — now the deciding question** |
| Bundle A | **PROVISIONAL — pending owner review** |

### 22.13 Owner decisions arising from pass 5

1. 🔴 **Decide how age is handled.** Three options, none taken here: **(a)** measure CBBD's DOB fill rate and adopt CBBD as a bio-only third NCAA source; **(b)** find another pre-draft DOB source; **(c)** accept that DraftLens ships without age and record it as a scope reduction against PRODUCT.md §11. Option (a) requires the CBBD terms question (§6.3) to be resolved first.
2. 🟠 **Approve the next verification slice** — 2–3 historical years (e.g. 2011, 2016, 2021 `player_core` + `player_box`, ≈12 MB) to test cross-season ID stability and early-window coverage before any bulk pull.
3. 🟠 **Accept or contest the two YELLOW profiles.** 3&D Wing and Rim Protector rest on thin defensive proxies. This is a data-class limitation, and DEC-008 requires profiles to be measurable rather than asserted.
4. 🟠 **Approve bulk acquisition** of `mbb/player_box` + `mbb/shots` + `mbb/player_core` for 2011–2026 (~215 MB) once 1–2 are settled.

---

## 23. Wikidata DOB feasibility audit (pass 6)

**Scope:** can Wikidata supply the pre-draft date of birth that hoopR cannot (§22.1)? **Biographical enrichment only** — no other Wikidata property is retrieved or stored.

**Method:** [`scripts/audit_wikidata_dob.py`](../scripts/audit_wikidata_dob.py), stdlib + existing pandas, no new dependencies, no account, no authentication. **~15 API calls total**, batched 50 entities per request and throttled at 1.2 s.

**Headline: DOB is effectively free for drafted players and complete for the 2026 demo — but historical coverage is missing almost exclusively from the undrafted class.** That is the same bias signature §9.2 identified as the most damaging failure mode available, so the finding is **YELLOW, not GREEN**, despite a perfect 2026 result.

### 23.1 Licensing and property — VERIFIED

**Licence** ([Wikidata:Licensing](https://www.wikidata.org/wiki/Wikidata:Licensing)):

> *"All structured data in the main, property and lexeme namespaces is made available under the [Creative Commons CC0 License](https://creativecommons.org/publicdomain/zero/1.0/) (Public domain)"* — while *"text in other namespaces is made available under the Creative Commons Attribution-ShareAlike 4.0 License."*

**CC0 1.0 means no attribution is required for the structured data**, and contributors apply CC0 as a condition of contributing. This is the **cleanest licence position of any source in this project** — cleaner even than Wikipedia's CC BY-SA, because DraftLens would consume *structured claims* (main namespace), not article text. Attribution should still be given as good practice.

**Property** ([Property:P569](https://www.wikidata.org/wiki/Property:P569)): label *"date of birth"*, description *"date on which the subject was born"*, data type **point in time**, single-best-value constraint, subject must be an instance of human. VERIFIED.

### 23.2 Access method and matching strategy — VERIFIED working

The **linked-entity path was tested first and succeeded outright**, so name-based Wikidata search was never needed:

```
Wikipedia draft/early-entrant entry
   → [[wikilink]] / {{sortname}} → English Wikipedia page title
   → MediaWiki  action=query&prop=pageprops&ppprop=wikibase_item&redirects=1   (≤50 titles/call)
   → Wikidata   action=wbgetentities&props=claims  → P569 ONLY                 (≤50 QIDs/call)
```

Redirects and title normalisation are followed automatically. **Every prospect resolved through `EXACT_LINK`; zero fell back to search, and zero were `AMBIGUOUS`.** No ambiguous match was accepted.

⚠️ **Parser defect found and fixed.** A first run reported only 4 NCAA drafted players for 2022. The cause was in my parser, not the data: the 2022 draft table uses plain `[[wikilinks]]` while 2026 uses `{{sortname}}`, and the first implementation required a `bgcolor` attribute that only some rows carry. Rewritten to take the player from the third table cell regardless of markup, 2022 returns **43** NCAA drafted. **Any production ingestion must handle both markup styles**; per-year row counts should be asserted against the known pick count.

### 23.3 AUDIT A — 2026 NCAA prospect population

Population = final NCAA early entrants ∪ all NCAA players drafted in 2026, deduplicated on normalised name.

| | Count |
| --- | --: |
| Draft table rows parsed | 60 (NCAA: **50**) |
| Early-entrant bullets | 31 (NCAA: **26**) |
| **Unique 2026 NCAA prospects** | **53** |
| — drafted | 50 |
| — declared but undrafted | **3** |

| Cohort | n | Entity found | **DOB found** | Full date |
| --- | --: | --: | --: | --: |
| **All NCAA prospects** | 53 | **100.0%** | **100.0%** | 98.1% |
| A. Drafted | 50 | 100.0% | **100.0%** | 98.0% |
| B. Declared & undrafted | 3 | 100.0% | **100.0%** | 100.0% |

All 53 classified `EXACT_LINK`. **Zero** `NO_ENTITY`, `NO_DOB`, or `AMBIGUOUS`.

⚠️ **The undrafted cohort is n=3.** A 100% rate on three players is not evidence of anything. It also re-confirms §15's concern from a new angle: in 2026, 23 of the 26 NCAA early entrants were drafted, leaving a negative class of three. The same pattern appears in 2025 (2 declared-undrafted). The historical variance is extreme — 2022 had **83**. This is a population problem, not a Wikidata problem, but it bounds what the 2026 demo can demonstrate.

### 23.4 AUDIT B — historical sample (n=92)

Ten drafted + ten declared-undrafted per year where the population allowed, sampled at even intervals through each list rather than from the top, so the sample is **not star-biased**.

| Year | n | Entity | DOB | Full date | **Drafted DOB** | **Undrafted DOB** |
| --- | --: | --: | --: | --: | --: | --: |
| 2011 | 20 | 75.0% | 75.0% | 75.0% | **100.0%** | **50.0%** |
| 2015 | 20 | 95.0% | 95.0% | 95.0% | **100.0%** | **90.0%** |
| 2020 | 20 | 80.0% | 80.0% | 80.0% | **100.0%** | **60.0%** |
| 2022 | 20 | 90.0% | 90.0% | 90.0% | **100.0%** | **80.0%** |
| 2025 | 12 | 91.7% | 91.7% | 91.7% | **100.0%** | **50.0%** |

| Cohort | n | Entity | **DOB** | Full date |
| --- | --: | --: | --: | --: |
| ALL | 92 | 85.9% | **85.9%** | 85.9% |
| **Drafted** | 50 | 100.0% | **100.0%** | 100.0% |
| **Declared & undrafted** | 42 | 69.0% | **69.0%** | 69.0% |

Sampled NCAA populations per year: 2011 (43 drafted / 11 undrafted), 2015 (40/17), 2020 (46/25), 2022 (43/83), 2025 (45/2).

#### 🔴 Class-dependent missingness: YES, and it is total

**Every one of the 13 missing DOBs in the 92-player historical sample is an undrafted player. Not one drafted player was missing.** Drafted 100.0% vs undrafted 69.0% — a **31-point gap**, present in all five years and never smaller than 10 points.

The mechanism is obvious in hindsight: a drafted player gets an English Wikipedia article as a matter of course; a player who declared and went undrafted often does not, and `NO_ENTITY` and `NO_DOB` coincide exactly (the entity/DOB percentages are identical in every row above — where an entity exists, P569 is essentially always populated).

**Why this matters more than the raw percentage.** [DATA.md](DATA.md) §9.2 identified match failure concentrated in the undrafted class as the most damaging possible bias, because undrafted players *are* the negative examples. Here the missingness of `date_of_birth` is **almost perfectly correlated with the target label**. A model given age plus a missingness indicator could learn "DOB unknown ⇒ undrafted" and score well for entirely spurious reasons. **This is target leakage through a missingness pattern, not through a feature value** — a subtler channel than anything in the §10 leakage table, and it should be added there.

Handling is an [ML_SPEC.md](ML_SPEC.md) matter and is **not decided here**. What this audit establishes is that naïve use of age would be unsafe.

### 23.5 AUDIT D — precision distribution

| Precision | 2026 (n=53) | Historical (n=92) |
| --- | --: | --: |
| `FULL_DATE` (P569 precision 11) | 52 | 79 |
| `MONTH_PRECISION` (10) | 1 | 0 |
| `YEAR_PRECISION` (9) | 0 | 0 |
| `MISSING` | 0 | 13 |

**Where a DOB exists it is almost always a full `YYYY-MM-DD`** — 98.1% in 2026 and 100% of found values historically. Only one record (Maliq Brown, 2026) carries month precision, stored as `2003-11-00`.

**No day or month value may ever be invented for a partial date** (DEC-017). Month- and year-precision records must be treated as missing for age purposes or carried with explicit uncertainty; that choice belongs to ML_SPEC.

### 23.6 AUDIT E — cross-check (n=10)

Wikidata P569 compared against the **English Wikipedia infobox `{{birth date}}` template**, which is maintained separately from Wikidata for most biographies and therefore constitutes a genuine second record. Sample spread across the pick range, not just lottery picks.

| Outcome | n | Notes |
| --- | --: | --- |
| **Exact agreement** | **8** | Identical `YYYY-MM-DD` |
| Precision difference | 1 | Maliq Brown — Wikidata `2003-11-00` (month precision) vs infobox `2003-11-16`. **Year and month agree**; this is coarser precision, not a conflict |
| Unable to cross-check | 1 | Nick Martinelli — no `{{birth date}}` template in the article |

**Zero genuine contradictions across nine checkable records.** No Wikidata value was overwritten. The one precision gap is flagged for manual review and shows the Wikipedia infobox could serve as a precision backfill — a possibility, not a decision.

### 23.7 AUDIT F — combined readiness for the 2026 prospect pool

The 53 prospects joined to the already-downloaded hoopR 2026 files on normalised name, with school used to disambiguate:

| Measure | Result |
| --- | --: |
| Matched to a hoopR `athlete_id` | **53 / 53 (100.0%)** |
| Wikidata DOB available | **53 / 53 (100.0%)** |
| **Both NCAA statistics AND DOB** | **53 / 53 (100.0%)** |

Among the 53 matched prospects: position **100%**, height **100%**, weight **100%**, Wikidata DOB **100%**.

> **FULL FEATURE READINESS for 2026 (stats + position + physicals + DOB): 100.0%**

#### An unexpected finding — hoopR's own DOB is 98.1% *for prospects*

Among these 53 prospects, hoopR `player_core.date_of_birth` is populated for **52 (98.1%)** — against a global 2026 fill rate of **1.58%** (§22.1).

The missingness is therefore **not random and not uniform**: ESPN maintains full biographies for players it profiles heavily, which is precisely the prospect population. §22.1's conclusion that *"hoopR cannot be the primary DOB source"* stands for the general NCAA population, but should be **qualified**: for the prospects DraftLens actually scores, hoopR alone may cover most of the need, with Wikidata as the complement.

Two cautions before relying on it: this is **2026 only**, and it says nothing about the *undrafted* cohort, which numbers three players here. Testing hoopR DOB fill on historical `player_core` files — especially for declared-undrafted players — is a cheap, high-value next check (§23.10).

### 23.8 AUDIT C — leakage controls and conceptual storage

**Only three things are taken from Wikidata: the Q-ID, P569, and the Wikipedia title used to reach them.** The audit script requests `props=claims` and reads `P569` exclusively; no other property is parsed or stored.

**Explicitly excluded** — current team, NBA career statistics, draft position, awards, current league, current age, and every other post-draft property. Note that Wikidata *does* hold draft position for most drafted players; taking it would import the target label from a second source and is prohibited.

Proposed conceptual storage (not implemented):

```
source_identity_map                    prospect_bio
├── canonical_player_id                ├── canonical_player_id
├── hoopR_athlete_id                   ├── date_of_birth        (P569, full precision only)
├── wikipedia_title                    ├── dob_precision        (11 | 10 | 9)
├── wikidata_qid                       └── dob_source           (wikidata | hoopR | …)
├── normalized_name
├── college
└── match_confidence   (EXACT_LINK | EXACT_IDENTITY_MATCH |
                        HIGH_CONFIDENCE | AMBIGUOUS | NO_ENTITY | NO_DOB)
```

`pre_draft_age = draft_reference_date − date_of_birth`, computed against **that class's draft date** (2026-06-23 for the replay). Date of birth is time-invariant and therefore safe; **the current-age field must never be used** (DEC-012), including hoopR's `age` column and Wikidata-derived current age.

### 23.9 Feasibility rating — 🟡 **YELLOW**

Not GREEN, despite a flawless 2026 result, and not RED, despite a real bias.

**For GREEN** — 2026 readiness is 100% on every axis. Matching is deterministic via linked entities with zero ambiguity. Where a DOB exists it is a full date 98–100% of the time. The cross-check found no contradictions. The licence (CC0) is the cleanest in the project. Drafted players are at 100% in every year tested.

**Against GREEN** — historical undrafted coverage is **69.0%**, and **100% of the missingness sits in the undrafted class**. The gap appears in all five sampled years. Because that class is the negative label, missingness is nearly a proxy for the target. Additionally the historical sample is 92 players, and the undrafted cohorts for 2025 (n=2) and 2026 (n=3) are too small to characterise.

**Against RED** — coverage is neither too sparse nor unreliable; matching worked perfectly; the shortfall is confined, understood, measurable, and specific to one cohort.

### 23.10 Recommendation — **Option A: keep age optional and missing-aware (PROVISIONAL)**

Recommended over the alternatives:

- **Not B (remove age from MVP scoring).** [PRODUCT.md](PRODUCT.md) §11 approves age as a candidate feature whose relevance must be *evaluated from historical data*. At 100% for drafted players and 100% for the entire 2026 demo pool, there is more than enough data to run that evaluation. Discarding it now would pre-empt a decision the product says must be made empirically.
- **Not C (another targeted DOB source search) — yet.** §23.7 shows a cheaper first move exists: measure hoopR's historical `player_core` DOB fill, particularly for undrafted players. If ESPN covers declared prospects as well historically as it does in 2026, the union of hoopR and Wikidata may close most of the gap at no additional sourcing cost.
- **Option A**, with one non-negotiable condition: because DOB missingness is almost perfectly correlated with the target, **any use of age must treat missingness as a leakage channel, not merely as a gap to impute.** [ML_SPEC.md](ML_SPEC.md) must address it explicitly; nothing is decided here.

**No change to PRODUCT.md or MVP.md is proposed**, and neither was modified.

### 23.11 Status labels

| Finding | Label |
| --- | --- |
| Wikidata structured data is CC0 1.0; no attribution required | **VERIFIED** |
| P569 = "date of birth", point-in-time datatype | **VERIFIED** |
| Wikipedia→Q-ID→P569 path works with zero ambiguity | **VERIFIED** |
| 2026: 53 NCAA prospects, 100% entity, 100% DOB, 98.1% full date | **VERIFIED** |
| 2026: 100% hoopR match; 100% stats + position + physicals + DOB | **VERIFIED** |
| Historical: drafted 100% DOB, undrafted 69.0% DOB (n=92) | **VERIFIED** |
| Missingness concentrated entirely in the undrafted class | **VERIFIED — leakage risk** |
| Cross-check: 8 exact, 1 precision-only, 1 uncheckable; 0 contradictions | **VERIFIED** |
| hoopR DOB is 98.1% among 2026 prospects despite 1.58% overall | **VERIFIED (2026 only)** |
| hoopR historical DOB fill, especially for undrafted players | **UNKNOWN** |
| Undrafted DOB coverage beyond a 42-player sample | **UNKNOWN** |
| Wikidata as a DraftLens source | **PROVISIONAL — not approved** |

### 23.12 New risk for the §10 leakage table

**Missingness-as-target-proxy.** `date_of_birth` is absent for ~31% of historical undrafted prospects and 0% of drafted ones. Any age feature, missing indicator, or imputation must be designed so the *absence* of a birth date cannot inform the prediction. This is a distinct channel from every entry currently in §10, all of which concern feature *values*. It should be added when §10 is next revised.

### 23.13 Owner decisions arising from pass 6

1. 🔴 **Choose the age handling** — Option A recommended (§23.10). Options B and C remain open.
2. 🟠 **Approve the hoopR historical DOB check** — 3–4 `player_core` files (~3 MB) to test whether ESPN's prospect-biased DOB fill holds historically and extends to undrafted players. Cheapest path to closing the gap.
3. 🟠 **Note the negative-class size problem.** Declared-undrafted NCAA prospects numbered 3 in 2026 and 2 in 2025, against 83 in 2022. Whatever the DOB outcome, this bounds the 2026 demo and affects the §3.6 population choice.

---

## 24. Historical acquisition and full-data validation (pass 7)

**Status: acquisition complete and validated — 0 hard failures, 0 warnings.**

Approved window **2011–2026** acquired for all four source families. Raw files are immutable, local, and git-ignored; reproducibility is provided by the acquisition scripts and [`data/source_manifest.csv`](../data/source_manifest.csv), not by redistributing source data.

### 24.1 Scripts

| Script | Purpose |
| --- | --- |
| [`scripts/dlcommon.py`](../scripts/dlcommon.py) | Shared helpers: name normalisation, throttled HTTP with backoff, manifest I/O |
| [`scripts/acquire_data.py`](../scripts/acquire_data.py) | hoopR MBB + NBA Parquet acquisition (`--source mbb\|nba\|all --years 2011-2026`) |
| [`scripts/acquire_draft_population.py`](../scripts/acquire_draft_population.py) | Wikipedia population + targets + optional Wikidata DOB (`--years`, `--wikidata`) |
| [`scripts/validate_raw_data.py`](../scripts/validate_raw_data.py) | Structure, coverage, manifest integrity, firewall, ID stability, quality profile |
| [`scripts/audit/`](../scripts/audit/) | Archived one-off feasibility scripts behind §22 and §23 (see §24.10) |

### 24.2 Files acquired — 97 files, 201.9 MB

| Family | Dataset | Files | Bytes | Licence |
| --- | --- | --: | --: | --- |
| hoopR-mbb | `player_core` | 16 | 11.8 MB | CC BY 4.0 (upstream ESPN) |
| hoopR-mbb | `player_box` | 16 | 57.8 MB | CC BY 4.0 (upstream ESPN) |
| hoopR-mbb | `shots` | 16 | 120.9 MB | CC BY 4.0 (upstream ESPN) |
| hoopR-nba | `player_season_stats` | 16 | 1.7 MB | CC BY 4.0 (upstream ESPN) |
| wikipedia | `draft_population` | 16 | derived | CC BY-SA 4.0 — attribution required |
| wikipedia | `draft_targets` | 16 | derived | CC BY-SA 4.0 — attribution required |
| wikidata | `dob` (2026 only) | 1 | derived | CC0 1.0 |

Every record carries `canonical_url`, `downloaded_at_utc`, `file_size_bytes`, `sha256`, and licence text. No Combine data was acquired (DEC-045). No NBA play-by-play or shot data was acquired.

### 24.3 NCAA quality profile by season — VERIFIED

| Season | core rows | unique IDs | box rows | shot rows | teams | pos% | height% | weight% | **DOB%** | box→core |
| --- | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |
| 2011 | 5,440 | 5,440 | 146,552 | 523,999 | 495 | 100.0 | 99.2 | 94.2 | **71.93** | 99.73 |
| 2012 | 5,470 | 5,470 | 148,383 | 515,845 | 507 | 100.0 | 99.0 | 94.7 | **67.59** | 99.58 |
| 2013 | 5,740 | 5,740 | 152,419 | 580,497 | 542 | 100.0 | 98.5 | 94.2 | **63.87** | 98.97 |
| **2014** | **10,587** | 10,587 | 182,737 | 784,865 | **628** | 100.0 | 88.4 | 79.1 | 37.38 | 99.94 |
| 2015 | 10,844 | 10,844 | 182,657 | 803,389 | 638 | 100.0 | 92.8 | 81.0 | 27.67 | 99.97 |
| 2016 | 10,915 | 10,915 | 182,524 | 851,494 | 640 | 100.0 | 93.7 | 80.6 | 19.95 | 100.00 |
| 2017 | 10,795 | 10,795 | 182,558 | 857,941 | 641 | 100.0 | 92.0 | 79.1 | 14.80 | 99.82 |
| 2018 | 11,340 | 11,340 | 186,066 | 860,585 | 658 | 100.0 | 92.8 | 79.5 | 9.85 | 99.46 |
| 2019 | 10,788 | 10,788 | 185,819 | 839,915 | 652 | 100.0 | 95.7 | 82.5 | 8.14 | 98.69 |
| 2020 | 12,991 | 12,991 | 181,675 | 818,482 | 663 | 100.0 | 83.4 | 70.4 | 6.94 | 98.76 |
| **2021** | 8,670 | 8,670 | **134,917** | **608,140** | **493** | 100.0 | 93.0 | 83.0 | 9.53 | 98.53 |
| 2022 | 12,090 | 12,090 | 191,555 | 873,219 | 679 | 100.0 | 91.2 | 74.4 | 6.54 | 98.82 |
| 2023 | 12,529 | 12,529 | 196,589 | 920,595 | 706 | 100.0 | 92.8 | 72.4 | 5.92 | 98.68 |
| 2024 | 12,548 | 12,548 | 198,586 | 957,173 | 717 | 100.0 | 92.0 | 69.5 | 4.45 | 99.59 |
| 2025 | 15,233 | 15,233 | 207,623 | 936,510 | 701 | 100.0 | 76.7 | 57.1 | 2.92 | 99.99 |
| 2026 | 12,481 | 12,481 | 196,876 | 991,836 | 727 | 100.0 | 94.4 | 65.1 | 1.58 | 100.00 |

**Totals: 168,461 player-season core rows · 2,857,536 player-game box rows · 12,724,485 shot rows.**

- **Position is 100% populated in every season.** Height 76.7–99.2%, weight 57.1–94.7%.
- **`player_core` has exactly one row per `athlete_id` in every season** (core rows = unique IDs, all 16 years).
- **box→core ID coverage is 98.5–100.0%** in every season.

#### ⚠️ Three coverage anomalies

1. **2014 coverage regime change.** Core rows jump 5,740 → 10,587 and teams 542 → 628 between 2013 and 2014 — ESPN roughly doubled its D-I coverage. Seasons 2011–2013 cover materially fewer players than 2014+. This is a comparability break inside the research window and affects any percentile or position-relative normalisation computed per season.
2. **2021 is depressed across the board** (8,670 core rows, 134,917 box rows, 608,140 shots, 493 teams) — the COVID-affected season, with cancelled games and reduced schedules. Expected, but it is a genuine outlier season.
3. **🔴 `date_of_birth` fill declines monotonically from 71.93% (2011) to 1.58% (2026).** This is the opposite of a normal recency pattern and is the single most important new observation in this pass — see §24.7.

### 24.4 NBA quality profile — VERIFIED

| | Result |
| --- | --- |
| Seasons | **2011–2026, all 16 present** |
| Total rows (long format) | **357,801** |
| Total player-seasons | **8,342** (452–606 per season) |
| Distinct `stat_name` values | **40 in every season** — no schema drift |

Required dimensions (`points`, `assists`, `totalRebounds`, `steals`, `blocks`, `turnovers`, `gamesPlayed`, `avgMinutes`) present in all 16 seasons.

### 24.5 Reconstructed draft population — VERIFIED

Rule: **final NCAA early entrants ∪ NCAA players actually drafted** (DEC-038), deduplicated on normalised name.

| Draft year | Total picks | NCAA drafted | NCAA early entrants | **Population** | Drafted | Undrafted | Drafted % |
| --- | --: | --: | --: | --: | --: | --: | --: |
| 2011 | 60 | 43 | 37 | 54 | 43 | 11 | 79.6 |
| 2012 | 60 | 47 | 39 | 60 | 47 | 13 | 78.3 |
| 2013 | 60 | 45 | 43 | 61 | 45 | 16 | 73.8 |
| 2014 | 60 ᶜ | 39 | 35 | 49 | 39 | 10 | 79.6 |
| 2015 | 60 | 40 | 41 | 57 | 40 | 17 | 70.2 |
| 2016 | 60 | 39 | 45 | 59 | 39 | 20 | 66.1 |
| 2017 | 60 | 50 | 60 | 74 | 50 | 24 | 67.6 |
| 2018 | 60 | 50 | 66 | 79 | 50 | 29 | 63.3 |
| 2019 | 60 | 46 | 71 | 83 | 46 | 37 | 55.4 |
| 2020 | 60 | 46 | 63 | 71 | 46 | 25 | 64.8 |
| **2021** | 60 | 46 | **169** | **171** | 46 | **125** | **26.9** |
| **2022** | 58 | 43 | 125 | 126 | 43 | 83 | 34.1 |
| 2023 | 58 | 46 | 78 | 84 | 46 | 38 | 54.8 |
| 2024 | 58 | 42 | 49 | 58 | 42 | 16 | 72.4 |
| **2025** | 59 | 45 | 27 | 47 | 45 | **2** | **95.7** ⚠ |
| **2026** | 60 | 50 | 26 | 53 | 50 | **3** | **94.3** ⚠ |

**Total 1,186 prospects — 717 drafted, 469 undrafted (39.5%).**

Pick counts of 58–60 are correct: teams forfeited second-round picks in several years.

> ᶜ **CORRECTION (ML-5).** The 2014 total-picks figure originally read **59**. That is wrong: pick **60** is present in `data/raw/draft_targets/draft_targets_2014.csv` (Cory Jefferson, San Antonio Spurs). The value is corrected to **60**. The error was caught by a Stage B validator check asserting that no observed pick may exceed its year's declared draft size — a check that exists because the `PICK_PERCENTILE` target divides by that number. All other years were re-verified against observed picks and are consistent. The draft sizes are version-controlled in [`config/ml5_stage_b.json`](../config/ml5_stage_b.json); see [ML5_REPORT.md](ML5_REPORT.md) §4.

#### 🔴 Class balance varies by a factor of six

Undrafted share ranges from **2.1% (2025)** and **5.7% (2026)** to **73.1% (2021)** and **65.9% (2022)**. The COVID eligibility cohort inflated 2021–2022 early-entrant counts (169 and 125), while 2025–2026 have almost no declared-and-undrafted players. **Any temporal validation scheme must confront the fact that the positive/negative ratio is not stable across folds.** That is an ML_SPEC concern; it is recorded here as a data fact.

#### 🔴 NEW STRUCTURAL LEAKAGE FINDING — `early_entrant` is a partial target

The population rule makes membership itself informative. Measured across all 16 years:

> **Of 212 population members who were NOT early entrants, 212 were drafted — 100.0%.**
> **All 469 undrafted players are early entrants, without exception.**

This is a logical consequence of the rule (a non-early-entrant can only enter the population by being drafted), not a parser defect. Consequences:

- **`early_entrant` and `population_source` must never be model features.** `early_entrant = False` predicts `drafted = True` with certainty.
- The effective negative class exists **only within the early-entrant subset**. The real discrimination problem is "among declared early entrants, who got drafted?" — narrower than the population size suggests.
- This belongs in the §10 leakage table and reinforces §3.7: the ground-truth wording needs owner attention.

Both fields are retained in `draft_population/` as **provenance metadata**, correctly located (declaration is pre-draft public information), but they are flagged here as prohibited inputs.

### 24.6 Cross-season `athlete_id` stability — VERIFIED, excellent

The open question from §22.7 (stability tested only within 2026) is now answered across 2011–2026:

| Measure | Result |
| --- | --: |
| Distinct `athlete_id` values | 83,247 |
| Appearing in more than one season | 43,933 (52.8%) |
| **…resolving to exactly one normalised name** | **43,933 (100.00%)** |
| …with more than one name (rename or collision) | **0** |
| Normalised names appearing in >1 season | 42,849 |
| …mapping to more than one `athlete_id` | 5,522 (12.9%) |

**`athlete_id` is stable across seasons — zero exceptions in 43,933 multi-season players.** hoopR is confirmed as the canonical NCAA identity spine for the full window.

The 12.9% of names mapping to multiple IDs is the expected inverse: distinct real players sharing a common normalised name (e.g. two "Chris Johnson"s in different seasons). It is **not** evidence of ID instability, but it does quantify the ambiguity that name-based joins from Wikipedia must survive — always disambiguate with school.

**Dtype hazard confirmed and handled:** `player_core.athlete_id` is `int64` while `player_box.athlete_id` and `shots.athlete_id_1` are `float64`. All scripts coerce numerically via `dlcommon`/`ids()`; naive string comparison silently yields 0% overlap (§22.7).

### 24.7 🔴 Date-of-birth availability is itself outcome-correlated

§22.1 measured 1.58% DOB fill in 2026 and §23.4 found historical DOB missingness concentrated in the undrafted class. The full acquisition adds a third, compounding observation: **DOB fill declines monotonically with recency**, from 71.93% (2011) to 1.58% (2026).

The most plausible mechanism is that ESPN backfills birth dates for college players **who go on to professional careers**. If so, DOB availability is a function of *what happened after* the season — a post-draft outcome determining feature availability, which is precisely the pattern §10 prohibits.

This **independently corroborates the approved exclusion of age from historical General Draft Board features** (DEC-044) and strengthens it: the concern is not only the drafted/undrafted gap measured in §23.4 but a season-level recency gradient consistent with retrospective backfill. Age remains approved for **prospect display and the 2026 profile**, where 2026 coverage is 100% via Wikidata.

### 24.8 Feature / target firewall — VERIFIED enforced

| Location | Contents |
| --- | --- |
| `data/raw/draft_population/` | `draft_year, player_name, normalized_name, college, position, class, population_source, early_entrant, wikipedia_title` |
| `data/raw/draft_targets/` | `draft_year, normalized_name, player_name, wikipedia_title, drafted, pick, round, drafting_team` |
| `data/raw/wikidata/` | `wikidata_qid, date_of_birth, dob_precision, match_method, match_confidence` (2026 only) |

`validate_raw_data.py` asserts on every year that **no outcome column (`pick`, `round`, `drafting_team`, `drafted`) appears in a population file**, that population and target keys match exactly, that no `normalized_name` is duplicated within a year, that every drafted row has a non-null pick, and that DOB never appears in a population file. **All assertions pass for all 16 years.** Separation is structural — three directories, three writers, never one convenient joined table.

### 24.9 2026 readiness — VERIFIED

| Measure | Result |
| --- | --: |
| Reconstructed 2026 NCAA population | **53** (50 drafted + 3 declared-undrafted) |
| Matched to hoopR NCAA data | **53 / 53 (100.0%)** |
| Wikidata DOB (display-only) | **53 / 53 (100.0%)** |
| Position fill | 100% |
| 2026 NCAA stats, shots, bios present | Yes |

The feature snapshot cutoff remains **2026-06-22 23:59:59 ET** (§14). All 2026 outcome data sits exclusively in `draft_targets/`.

### 24.10 Script consolidation

The three one-off feasibility scripts were **archived, not deleted**, to preserve the evidence behind §22 and §23:

`scripts/verify_hoopr_sample.py`, `scripts/verify_hoopr_sample2.py`, `scripts/audit_wikidata_dob.py` → **`scripts/audit/`**, with a README recording what each produced and which maintained script supersedes it. They target the pre-consolidation raw layout and will not run unmodified against the current structure; `scripts/` now contains only maintained code.

### 24.11 Remaining data blockers and risks

| # | Item | Severity |
| --- | --- | :-: |
| 1 | **Class balance is unstable across years** (2.1% to 73.1% undrafted). Affects any fold design | 🔴 HIGH |
| 2 | **`early_entrant` / `population_source` are partial target indicators** — must be excluded from features | 🔴 HIGH |
| 3 | **Undrafted seniors remain unrepresented** (DEC-039); ground-truth wording still needs owner sign-off (§3.7) | 🔴 HIGH |
| 4 | **2014 coverage regime change** (ESPN roughly doubled D-I coverage); 2011–2013 are thinner | 🟠 MEDIUM |
| 5 | **DOB availability is outcome- and recency-correlated** — age excluded from board features | 🟠 MEDIUM (managed) |
| 6 | 2021 is a COVID outlier season across every volume metric | 🟠 MEDIUM |
| 7 | `shots` coordinate sentinel contamination (§22.3) still unquantified across history | 🟠 MEDIUM |
| 8 | Only *made* free throws appear in `shots` (§22.3) — FT metrics must come from `player_box` | 🟠 MEDIUM |
| 9 | Weight fill degrades in recent seasons (57.1% in 2025, 65.1% in 2026) | 🟢 LOW |
| 10 | ESPN upstream-rights question (§21.7) still unreviewed | 🟠 MEDIUM |
| 11 | Combine data not acquired — optional enrichment (DEC-045) | 🟢 LOW |

### 24.12 Window assessment

**2011–2025 development window: still defensible, with one caveat.** All 15 years parse cleanly, carry complete position data, and have stable identity. The caveat is the **2014 coverage break** — 2011–2013 cover roughly half as many players and teams. That does not invalidate those years (the *prospect* population is what matters, and their drafted counts are normal at 43/47/45), but per-season normalisation baselines are not comparable across the break. Whether to keep 2011–2013 is a modelling decision for [ML_SPEC.md](ML_SPEC.md), not a data decision.

**2026 as final holdout: still suitable.** 100% hoopR match, 100% position, full stats and shots, a clean cutoff, and outcomes fully quarantined. Its one weakness is the small undrafted class (n=3), which limits what the replay can demonstrate about undrafted discrimination — a presentation constraint, not a blocker.

---

## 25. Open questions carried forward

- Is the negative class "declared and undrafted", "combine attendee and undrafted", or both? ([ML_SPEC.md](ML_SPEC.md))
- How is the 2024 Combine regime change handled across a train/test boundary?
- Are AST%/TOV%/STL%/BLK% derived from CBBD primitives, or dropped?
- What match-confidence threshold admits a record, and how are rejects surfaced to the user?
- How is position reconciled across disagreeing sources?
- Are raw pulls archived as versioned snapshots, given that undocumented endpoints change without notice — and does the CBBD redistribution clause permit archiving them at all?
- Does `listed` vs `measured` height/weight become two features, or one reconciled value?
