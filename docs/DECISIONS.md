# DraftLens — Decision Log

A record of meaningful product and technical decisions. Each entry states what was decided and why, so that later sessions do not silently reverse or re-litigate it.

**Rules**

- Record only meaningful decisions — not routine repository housekeeping.
- Never modify or remove an accepted decision to fit new work. Supersede it with a new entry instead, and update the original's status to `Superseded by DEC-XXX`.
- Statuses: `Accepted`, `Deferred`, `Superseded by DEC-XXX`, `Rejected`.
- Anything not decided is **TBD** and belongs in the relevant specification document, not here.

---

## DEC-001 — Product name: DraftLens
**Status:** Accepted
**Decision:** The project is named DraftLens.

## DEC-002 — Product purpose: NBA Draft decision support
**Status:** Accepted
**Decision:** DraftLens is a data-driven NBA Draft decision-support tool for NBA scouting departments, analytics teams, and front-office decision makers. It answers: among the prospects in an upcoming draft class, which players are the strongest prospects overall, and which best match a specific scouting need.
**Rationale:** DraftLens is explicitly not a mock draft generator, lottery simulator, video-game-style rating system, career predictor, or generative-AI scouting chatbot. It must remain analytical, explainable, fact-based, and reproducible where possible.

## DEC-003 — Hackathon context: AQX Sports Analytics Data Bowl 3.0
**Status:** Accepted
**Decision:** DraftLens is built for the AQX Sports Analytics Data Bowl 3.0.

## DEC-004 — MVP prospect scope: NCAA only
**Status:** Accepted
**Decision:** The MVP covers NCAA prospects only.

## DEC-005 — International prospects deferred
**Status:** Deferred
**Decision:** International prospects are out of scope for the MVP. They may be added in a future version through an explicit decision.

## DEC-006 — Two distinct ranking modes, not blended
**Status:** Accepted
**Decision:** DraftLens has two distinct ranking modes — General Draft Board (overall pre-draft quality) and Team Need (fit to a requested profile or custom criteria). They are not blended through a general "overall vs fit" slider.
**Rationale:** The two questions are different. Merging them into one continuum would obscure which question is being answered.

## DEC-007 — Team Need is expressed by profile or custom criteria
**Status:** Accepted
**Decision:** Team Need mode accepts the user's need in two ways: profile-based ranking (from a defined set of modern basketball profiles) and custom criteria ranking (a simple mode over broad dimensions and an advanced mode over specific statistics).
**Note:** Profile definitions, dimensions, statistics, and weights are TBD — see [ML_SPEC.md](ML_SPEC.md).

## DEC-008 — Profiles must be measurable, not labels
**Status:** Accepted
**Decision:** Each player profile must correspond to a transparent combination of measurable basketball statistics and physical characteristics. Manually assigned profile labels are not acceptable.

## DEC-009 — Traditional positions PG / SG / SF / PF / C
**Status:** Accepted
**Decision:** DraftLens uses the five traditional positions: PG, SG, SF, PF, C. Where statistically appropriate, measurements and performance are interpreted relative to position.
**Note:** The position-normalization methodology is TBD.

## DEC-010 — Latest NCAA season is the primary college representation
**Status:** Accepted
**Decision:** A prospect's main NCAA performance representation is their latest NCAA season. Full collegiate career aggregates are not used as the primary representation.

## DEC-011 — Actual NBA Draft order is the primary historical ground truth
**Status:** Accepted
**Decision:** For the General Draft Board, the primary historical target is the actual NBA Draft order. Undrafted players must also be considered where the methodology requires them.
**Rationale:** Draft order is not treated as a perfect measure of future NBA player quality. It is used because it is an objective, observable historical outcome.

## DEC-012 — Temporal validation is required; no future-information leakage
**Status:** Accepted
**Decision:** Historical evaluation must train on older drafts and evaluate on a later unseen draft, rolling the cutoff forward. Information that occurred after the draft being evaluated must never be used.
**Note:** The exact validation strategy — cutoff years, folds, metrics — is TBD.

## DEC-013 — External analyst and mock rankings are not model features
**Status:** Accepted
**Decision:** ESPN rankings, The Athletic rankings, public mock drafts, consensus draft boards, and analyst rankings must not be used as primary model input features. They may be used only as external benchmarks for comparison.
**Rationale:** DraftLens must produce an independent, data-driven evaluation rather than reproducing public consensus.

## DEC-014 — Exactly three NBA statistical comparables
**Status:** Accepted
**Decision:** Each prospect has exactly three NBA statistical / style comparables.

## DEC-015 — NCAA-to-NBA comparison requires normalization
**Status:** Accepted
**Decision:** Comparables compare a prospect's current NCAA statistical profile against actual NBA players' NBA statistical profiles. Raw NCAA and NBA statistics must not be treated as if they came from the same statistical environment. A statistically defensible transformation is required.
**Note:** The transformation and similarity methodology are TBD. The output must be communicated as descriptive style/statistical similarity, never as a career-outcome prediction.

## DEC-016 — Missing Combine data must not exclude a prospect
**Status:** Accepted
**Decision:** A prospect must not be automatically excluded for not participating in the NBA Draft Combine or for having unavailable measurements. Prospects with incomplete data remain eligible for analysis whenever statistically reasonable, and data completeness should be displayed.
**Note:** Missing-value handling and imputation methodology are TBD.

## DEC-017 — No fabricated data
**Status:** Accepted
**Decision:** Unknown data remains unknown. Missing values may only be filled by an explicitly documented statistical method, never invented.

## DEC-018 — Raw statistics remain visible behind derived scores
**Status:** Accepted
**Decision:** Every derived score must be reproducible, explainable, and linked to documented metrics. The interface must expose the raw statistics a score is built from. Scores must never exist only for visual appeal.

## DEC-019 — No required generative AI dependency
**Status:** Accepted
**Decision:** The MVP must not require a paid generative AI API. Ranking explanations should preferably be generated deterministically from underlying statistics, normalized dimensions, and scoring logic.

## DEC-020 — Official candidate list is authoritative once it exists
**Status:** Accepted
**Decision:** DraftLens may maintain its own tracked prospect list before an official NBA Draft candidate list exists for a class. Once the official list exists, it becomes the authoritative eligibility list.

## DEC-021 — Designed for future drafts; historical replay for validation
**Status:** Accepted
**Decision:** DraftLens is designed for future NBA Draft classes. Historical drafts may be replayed for demonstration and validation using only information available before the relevant draft. The 2026 NBA Draft is the proposed primary demonstration / backtesting case.
**Note:** The exact train/test years are TBD.

## DEC-022 — Architecture decisions deferred
**Status:** Deferred
**Decision:** No frontend, backend, database, hosting, ML-serving, or visualization technology is selected. Architecture will be chosen only after MVP, data, and ML requirements are sufficiently defined. No dependencies are installed until then.
**Note (added with DEC-033):** DEC-033 fixes Python for backtesting and historical validation only. It is a constraint on the offline analysis work, not an application architecture decision. Everything listed above remains deferred.

## DEC-023 — MVP scope deferred
**Status:** Superseded by DEC-024
**Decision:** MVP scope is not yet defined and will be established in a dedicated product-design step, recorded in [MVP.md](MVP.md).

## DEC-024 — MVP scope approved
**Status:** Accepted
**Decision:** The hackathon MVP scope is defined and approved in [MVP.md](MVP.md), which becomes the authoritative MVP scope document. The MVP must demonstrate that DraftLens can support a real scouting decision using objective basketball data. Success criteria are enumerated in MVP.md §17.
**Supersedes:** DEC-023.

## DEC-025 — Lightweight landing page precedes the two modes
**Status:** Accepted
**Decision:** The application opens on a minimal DraftLens landing / home experience that briefly introduces the product and routes to the two core modes (General Draft Board, Team Need).
**Rationale:** The landing page is an entry point, not a marketing site. The analytics product is the priority and receives the effort.

## DEC-026 — General Draft Board required MVP capabilities
**Status:** Accepted
**Decision:** The General Draft Board is a required MVP feature and must: display all prospects in the selected draft dataset, rank them, show an Overall Score out of 100, support search by name, support filtering by PG / SG / SF / PF / C, and open a prospect detail page.
**Note:** The scoring methodology remains TBD and must be selected through data analysis and historical validation — see [ML_SPEC.md](ML_SPEC.md). Extends DEC-006.

## DEC-027 — Both Team Need paths are required in the MVP
**Status:** Accepted
**Decision:** The MVP must ship both Team Need entry paths: predefined player profiles and custom weighted criteria. Within custom criteria, the simple weighted mode over broad dimensions (Shooting, Playmaking, Defense, Rebounding, Athleticism, Size) is required and is the priority; the advanced view exposing specific underlying statistics is optional for the MVP and ships only if it does not make the product unnecessarily complex. Team Need must output an explicit recommendation ranking with fit scores.
**Note:** Extends DEC-007, which established the two paths as product behavior. This record makes both required MVP scope and marks the advanced view optional. The mapping from user weights to a fit score is TBD.

## DEC-028 — One predefined profile at a time in the MVP
**Status:** Accepted
**Decision:** The MVP supports exactly one selected predefined profile at a time. Combining multiple predefined profiles is out of scope for the MVP and may be reconsidered after the hackathon.
**Rationale:** [PRODUCT.md](PRODUCT.md) §7.1 allows a future maximum of two combined profiles only if the implementation stays simple and understandable. The MVP does not attempt it.

## DEC-029 — Six target profile families for the MVP
**Status:** Accepted
**Decision:** The MVP targets six profiles: Shooter, Slasher / Rim Attacker, Playmaker, 3&D Wing, Rim Protector, Stretch Big. Each is an MVP target only if it can be defined from reliable, measurable data.
**Note:** [PRODUCT.md](PRODUCT.md) §7.1 lists eight potential profiles. Point-of-Attack Defender and Rim Runner / Interior Finisher remain valid product concepts but are not MVP targets. Profile definitions, statistics, transformations, and weights are TBD. Manually assigned labels remain prohibited under DEC-008.

## DEC-030 — Prospect detail page required MVP information
**Status:** Accepted
**Decision:** Every prospect must have an analytical profile page presenting, where data is available: name, college, age, position, physical measurements, latest NCAA season statistics, advanced NCAA statistics, NBA Draft Combine data, Overall Score, useful sub-scores, data coverage / completeness, three NBA statistical comparables, the raw statistics supporting derived scores, strengths, and weaknesses. Strengths and weaknesses must be derived from factual metrics or score components; subjective scouting claims without supporting data must not be produced.
**Note:** Sub-scores are included only where statistically justifiable. Formulas remain TBD. Reinforces DEC-018.

## DEC-031 — Three NBA comparables are mandatory MVP functionality
**Status:** Accepted
**Decision:** NBA statistical comparables are required MVP functionality, not an optional bonus. Each prospect displays exactly three, and the application must state clearly that similarity is descriptive and does not predict the same NBA career.
**Note:** Extends DEC-014 (count) and DEC-015 (normalization requirement) by fixing the feature as required MVP scope. The transformation and similarity methodology remain TBD.

## DEC-032 — 2026 NBA Draft replay is the primary hackathon demonstration
**Status:** Accepted
**Decision:** The primary hackathon demonstration is a historical replay of the 2026 NBA Draft: use only data available before that draft, apply a methodology developed on earlier historical data, generate DraftLens 2026 rankings, and compare them against the actual 2026 draft order. Product positioning remains future-facing.
**Rationale:** The next future draft class does not yet have complete pre-draft data during the hackathon period. The 2026 replay proves the methodology.
**Note:** Confirms DEC-021, where the 2026 draft was recorded as the *proposed* demonstration case. Train/test cutoff years remain TBD.

## DEC-033 — Backtesting and historical validation must be implemented in Python
**Status:** Accepted
**Decision:** All backtesting and historical model validation must be performed in Python. This is an approved project constraint.
**Note:** Specific Python libraries are not chosen. This constrains the offline validation work only and does not decide the application stack — DEC-022 still stands for everything else. Validation must respect time ordering with no future-information leakage (DEC-012).

## DEC-034 — Backtest results are documented, not a product page
**Status:** Accepted
**Decision:** Historical validation results do not require a dedicated page inside the application for the MVP. They are documented in README.md, the Devpost submission, and supporting charts / figures.
**Rationale:** The application should prioritize the scouting workflow. Validation is mandatory as work, but its presentation surface is documentation.

## DEC-035 — MVP implementation priority order
**Status:** Accepted
**Decision:** If hackathon time becomes constrained, work is prioritized in this order: (1) General Draft Board, (2) Team Need mode, (3) prospect detail page, (4) explainability, (5) NBA statistical comparables, (6) backtesting / validation presentation, (7) visual polish.
**Note:** This is a sequencing guide, not an optionality ranking. Later items are not optional by default; NBA comparables and historical validation remain part of the intended MVP.

## DEC-036 — Dataset research is mandatory before ML implementation
**Status:** Accepted
**Decision:** The next mandatory project phase is dataset research and validation, covering NCAA player statistics, advanced NCAA statistics, NBA Draft historical outcomes, NBA Draft Combine data, NBA player statistics for comparables, and age / physical measurements. Candidate sources must be evaluated on reliability, historical coverage, availability for the 2026 replay, update frequency, licensing / terms of use, accessibility, entity matching feasibility, missing-data coverage, and reproducibility. No model implementation may begin until the minimum viable data sources are known.
**Note:** No dataset has been approved. See [DATA.md](DATA.md).

## DEC-037 — Minimal Python data-analysis environment approved
**Status:** Accepted
**Decision:** A minimal Python environment is approved for **data inspection, data preprocessing, and the mandatory historical backtesting**. For the current verification step the permitted dependencies are Python, `pandas`, and `pyarrow`, installed in a local project virtual environment (`.venv/`).

**This decision explicitly does NOT:**
- select the application stack — no frontend, backend, database, hosting, or ML-serving technology is chosen (DEC-022 stands);
- approve any ML algorithm, library, model, scoring formula, or similarity method (DEC-033's note and [ML_SPEC.md](ML_SPEC.md) stand);
- approve bulk data acquisition — only the small verification pass described in [DATA.md](DATA.md) §22 is authorised.

**Scope:** Python is approved for the **analytical / data pipeline** only. Adding modelling libraries (scikit-learn, xgboost, lightgbm), web frameworks, databases, notebook servers, or visualization libraries requires a separate decision.
**Rationale:** DEC-033 already requires backtesting to be performed in Python. Inspecting Parquet source data is a prerequisite to any dataset decision, and cannot be done without a reader.

## DEC-038 — hoopR MBB approved as the primary NCAA source
**Status:** Accepted
**Decision:** `sportsdataverse/hoopR-mbb-data` is the primary NCAA source for the MVP — player identity, player game/season statistics, shot-level data, position, height, and weight. `athlete_id` is the canonical NCAA source identifier.
**Note:** `athlete_id` dtype differs across files (`player_core` int64; `player_box` and `shots` float64) and must be normalised numerically on load. Naive string comparison silently yields 0% overlap. Licence: CC BY 4.0 explicitly covering data; upstream ESPN. Verified stable across 2011–2026 ([DATA.md](DATA.md) §24.6).

## DEC-039 — Historical prospect population rule (raw reconstruction)
**Status:** Superseded by DEC-049 for ML use; retained for the raw data layer
**Decision:** For each draft year the reconstructed NCAA prospect population is **final NCAA early entrants UNION all NCAA players actually drafted**, deduplicated per player.
**Rationale:** A pragmatic reconstruction of serious NCAA draft prospects — the only population recoverable at name level for 2011–2026.
**Superseded (DEC-049):** this union remains the definition of the acquired **raw** `draft_population/` layer, but it must NOT be used as the ML population — membership itself carries post-draft information. See DEC-049.

## DEC-040 — Known population limitation: undrafted seniors
**Status:** Accepted
**Decision:** Undrafted automatically-eligible seniors are not systematically recoverable and are therefore absent from the population. This limitation must remain documented and must not be presented as full eligibility coverage.
**Note:** No name-level list of automatically-eligible players exists for any year ([DATA.md](DATA.md) §3.1). Relates to the open ground-truth wording question (§3.7).

## DEC-041 — `early_entrant` and `population_source` are prohibited as model features
**Status:** Accepted
**Decision:** The `early_entrant` and `population_source` fields must never be used as General Draft Board model features.
**Rationale:** DEC-039's population rule makes membership informative: measured across 2011–2026, **212 of 212 non-early-entrants were drafted (100.0%)**, and all 469 undrafted players are early entrants. `early_entrant = False` therefore predicts the target with certainty. The fields are retained as pre-draft provenance metadata only ([DATA.md](DATA.md) §24.5).

## DEC-042 — Wikipedia / MediaWiki approved for population and draft targets
**Status:** Accepted
**Decision:** English Wikipedia via the MediaWiki Action API is approved for the reconstructed prospect population and historical draft outcomes. Licence CC BY-SA 4.0; attribution is required for any derived table that is published.
**Note:** Article markup varies by year — `{{sortname}}`, plain wikilinks, inline `||` cells, and `!scope=row` header cells all occur. Parsers must handle all four and assert per-year counts.

## DEC-043 — hoopR NBA approved for statistical comparables
**Status:** Accepted
**Decision:** `sportsdataverse/hoopR-nba-data` `player_season_stats` is approved as the source of NBA player-season statistics for the three NBA statistical comparables. Acquired 2011–2026: 8,342 player-seasons, 40 stat dimensions, no schema drift.
**Note:** Long/tidy format requiring a pivot; made/attempted pairs are combined strings. The similarity method remains undefined — see [ML_SPEC.md](ML_SPEC.md). Extends DEC-031.

## DEC-044 — Age / DOB excluded from historical General Draft Board features
**Status:** Accepted
**Decision:** Date of birth and derived age must **not** be used as General Draft Board historical model inputs. Also prohibited: a missing-DOB indicator, any sentinel exposing missingness, and imputation intended to reintroduce the feature.
**Approved uses:** prospect biography and display, the 2026 prospect profile, exploratory analysis, and later controlled ablation research.
**Rationale:** DOB availability is target-dependent. The audit found 100% coverage for drafted players versus 69% for undrafted, with every missing historical value belonging to an undrafted prospect ([DATA.md](DATA.md) §23.4), and full acquisition showed fill declining monotonically from 71.9% (2011) to 1.6% (2026), consistent with retrospective backfill for players who turned professional (§24.7). Availability itself is therefore a leakage channel.
**Note:** This fulfils the [PRODUCT.md](PRODUCT.md) §11 requirement that age be evaluated empirically. It was evaluated and is excluded from ranking inputs on leakage grounds, not removed from the product.

## DEC-045 — Wikidata approved for biographical DOB enrichment
**Status:** Accepted
**Decision:** Wikidata is approved as a biographical enrichment source, restricted to the Q-ID and **P569 (date of birth)** reached via the Wikipedia-title → Q-ID path. Structured Wikidata data is CC0 1.0; no attribution required.
**Note:** No other property may be ingested — in particular not draft position, career statistics, current team, awards, or current age. Stored separately in `data/raw/wikidata/`, never merged into feature files. Use is bounded by DEC-044.

## DEC-046 — Combine data is optional enrichment
**Status:** Accepted
**Decision:** NBA Draft Combine data is not required for the MVP and was not acquired. The core product must remain functional without it. Combine fields remain classified Desirable/Optional, never Essential.

## DEC-047 — Raw data stays local; reproducibility via scripts and manifest
**Status:** Accepted
**Decision:** Raw source datasets are stored locally and git-ignored. Public reproducibility is provided by committing acquisition scripts, source URLs, transformations, schema documentation, and `data/source_manifest.csv` (with per-file SHA-256, size, timestamp, and licence) — **not** by redistributing source data.
**Rationale:** Respects upstream terms across all families without relying on a new legal assumption. Raw files are immutable: acquisition never overwrites an existing file unless `--force` is passed, and validation verifies checksums against the manifest.

## DEC-048 — Acquisition window 2011–2026
**Status:** Accepted
**Decision:** The approved data acquisition window is **2011–2026 inclusive**: 2011–2025 for historical development and backtesting, with **2026 reserved as the final holdout candidate**. The 2026 feature snapshot cutoff is **2026-06-22 23:59:59 ET**.
**Note:** The final ML training window remains subject to data-quality analysis and is not selected here. A coverage regime change at 2014 (ESPN roughly doubled D-I coverage) means 2011–2013 are not directly comparable for per-season normalisation ([DATA.md](DATA.md) §24.3).

## DEC-049 — Primary ML population: final NCAA early entrants only
**Status:** Accepted
**Decision:** The primary General Draft Board historical ML population is **final NCAA early entrants only**, containing both drafted and undrafted early entrants. The union rule of DEC-039 must not be used as the ML population.
**Rationale:** Under the union, a senior or automatically-eligible player could enter the population *only because we already knew they were drafted*. Measured across 2011–2026, **212 of 212 non-early-entrants were drafted (100.0%)** ([DATA.md](DATA.md) §24.5). The leak was in the sampling frame, not in any column, so no feature engineering could remove it. The declared early-entrant list is published before the draft, so membership is genuinely pre-draft information.
**The historical question becomes:** among NCAA players who officially declared as final early entrants, which prospects were selected, and how highly?
**Supersedes:** DEC-039 for ML use. DEC-039 still defines the raw `draft_population/` layer.

## DEC-050 — Seniors / automatically eligible players excluded from the ML dataset
**Status:** Accepted
**Decision:** NCAA seniors and other automatically-eligible players known only because they were ultimately drafted remain in the raw data for descriptive analysis and display, but are **excluded from the primary General Draft Board ML training and backtesting dataset**. They must never be silently mixed into the positive or negative class.
**Note:** Reconsider only if a defensible **pre-draft** historical population of automatically-eligible players is obtained. DATA.md §3.1 established that no name-level list exists for any year, so this is not expected. Relates to DEC-040.

## DEC-051 — 2026 holdout population: final NCAA early entrants only
**Status:** Accepted
**Decision:** The final hackathon holdout population is the **26 final 2026 NCAA early entrants**. Seniors must not be added merely because we now know after the fact that they were drafted. 2026 remains completely unseen during methodology development; the actual outcome is used only after the methodology is frozen, in exactly one evaluation.
**Note:** The 2026 base rate (88.5% drafted) differs sharply from the 2014–2025 training window (48.6%), so calibration is expected to degrade on the holdout. The holdout tests **ranking quality**, not calibration ([ML_SPEC.md](ML_SPEC.md) §4.3).

## DEC-052 — Primary ML window 2014–2025; 2011–2013 for robustness only
**Status:** Accepted
**Decision:** The primary ML development and temporal-validation window is **2014–2025** (829 early entrants; 403 drafted; 48.6% drafted). **2011–2013** are reserved for sensitivity and robustness analysis and are not in the default training set unless later evidence supports inclusion. **2026** remains the untouched final holdout.
**Rationale:** DATA.md §24.3 verified a hoopR/ESPN coverage regime change at 2014 — core rows jump 5,740 → 10,587 and teams 542 → 628 — making per-season normalisation baselines incomparable across the break.
**Note:** Refines DEC-048, which set the *acquisition* window at 2011–2026 and deferred the ML window.

## DEC-053 — General Draft Board uses a two-stage analytical structure
**Status:** Accepted
**Decision:** The General Draft Board's primary methodology to evaluate is a **two-stage design**: Stage A estimates P(drafted) over all early entrants; Stage B estimates conditional draft position among drafted early entrants. The two signals are combined into the Overall Score.
**Rationale:** "Will this player be drafted?" and "how high will a drafted player go?" are different questions over different populations. A single regression would force undrafted players to receive an invented pick number, violating DEC-017.
**Note:** No algorithm, target encoding, metric, or combination formula is approved. A single-stage ordinal model over {undrafted, late second, early second, rest of R1, lottery} remains a legitimate secondary structure to compare. See [ML_SPEC.md](ML_SPEC.md) §6.

## DEC-054 — Team Need remains separate from the General Draft Board
**Status:** Accepted
**Decision:** Team Need is a **deterministic multi-criteria preference ranking**, not a predictive model, and does not reuse the General Draft Board's predictive output. User weights are preferences and must never be fitted to draft outcomes. Team Need does not include the Overall Score unless a later explicit product decision adds it.
**Note:** Reinforces DEC-006 and DEC-007 at the methodology level. Fitting profile weights to draft outcomes would silently turn Team Need into a second draft board.

## DEC-055 — Athleticism sub-score must not be fabricated
**Status:** Accepted
**Decision:** No Athleticism sub-score may be manufactured from box-score statistics. Without Combine data the dimension is **unavailable or incomplete** and must be omitted or displayed as explicitly missing. The Defense sub-score must be named and described as **box-score defensive production**, not defensive quality.
**Rationale:** The acquired data contains no athleticism measurement; dunk frequency is a style signal confounded by position, role, and system. Defensive data is limited to steals, blocks, rebounds and fouls — no matchup, opponent-shooting, on/off, or deterrence measure exists. DEC-008 requires profiles be measurable rather than asserted, and DEC-016 requires missing data be disclosed rather than hidden.
