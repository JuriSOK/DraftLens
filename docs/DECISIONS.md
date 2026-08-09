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

## DEC-056 — ML analytical dataset is physically built from early entrants only
**Status:** Accepted
**Decision:** The ML-0 pipeline materialises the analytical dataset from **final NCAA early entrants only**. Seniors and other automatically-eligible players remain in the raw layer for descriptive use but are never written into the ML feature or target files.
**Note:** Implements DEC-049/DEC-050. Population counts are enforced as hard build gates — **corrected in ML-0.1 (DEC-063) to 2014–2025: 887/431/456; 2011–2013: 125/85/40; 2026: 26**. The original 829/403/426 and 119/79/40 came from a defective NCAA classifier and are not authoritative and re-asserted by `scripts/experiments/validate_ml0_dataset.py` and the test suite. See [ML0_DATASET.md](experiments/ML0_DATASET.md).

## DEC-057 — Development, robustness and holdout partitions are stored separately
**Status:** Accepted
**Decision:** ML-0 writes three physically separate partitions — `2014_2025` (development), `2011_2013` (robustness only), `2026` (final holdout) — as distinct files rather than one dataset with a `split` column.
**Rationale:** Loading the 2026 holdout must be an intentional act. A shared file with a filter column makes accidental holdout access a one-line mistake; separate files make it a deliberate one.

## DEC-058 — Draft-year NCAA representation is the season ending in the draft year
**Status:** Accepted
**Decision:** A prospect entering draft year *Y* is represented by hoopR NCAA season *Y* — the season ending in that draft year — and never by a later season.
**Note:** Implements DEC-010 concretely. Asserted on every row by the build and the validator; 0 violations observed across all 974 rows.

## DEC-059 — Same-season transfers aggregate into one prospect-season record
**Status:** Accepted
**Decision:** A prospect's draft-year NCAA record is their **total production across all NCAA teams played for during that season**. A mid-season team change never duplicates the prospect. `n_teams` is retained as metadata and `primary_school` (last team by game date) is retained for identity.
**Note:** Affects 3 prospects across 2011–2026. Exact duplicate `(athlete_id, game_id)` rows are dropped before aggregation so statistics are never double-counted (3 rows removed, all 2017). Both behaviours are unit-tested.

## DEC-060 — Feature and target datasets remain physically separated
**Status:** Accepted
**Decision:** ML-0 never writes a combined dataset containing both features and outcomes. Targets contain only `canonical_prospect_id`, `draft_year`, `drafted`, `pick`, `round`; `drafting_team`, `population_source` and `early_entrant` are excluded from the analytical target table. Validation fails hard if any prohibited column appears in a feature file.
**Rationale:** Leakage prevention should be structural rather than a convention someone must remember.

## DEC-061 — Matching-only name key is separate from the canonical identity
**Status:** Accepted
**Decision:** Cross-source matching uses a dedicated `match_key` (leading-initial collapse, end-only suffix stripping, transliteration of non-decomposable Latin letters). The canonical `normalized_name` produced by the acquisition scripts is **not** changed, so `canonical_prospect_id` remains stable and previously acquired raw files stay valid.
**Note:** Raised the 2014–2025 match rate from 95.66% to 99.03%. `dlcommon.normalize_name` retains a known defect — it strips `v` as a Roman-numeral suffix anywhere in a name — which `match_key` compensates for; it is not corrected in place because that would invalidate existing canonical identifiers.

## DEC-062 — Identity exceptions live in a version-controlled override file
**Status:** Accepted
**Decision:** Where deterministic matching cannot resolve a genuine name variant, the mapping is recorded in [`config/data/identity_overrides.csv`](../config/data/identity_overrides.csv) with prospect, year, expected school, selected `athlete_id`, and a written reason. Overrides must never be hidden in Python conditionals, and a match must never be invented.
**Note:** Three entries at ML-0, all legal-name/nickname mismatches verified by unique surname+school in the relevant season.

## DEC-063 — NCAA membership is decided by canonical article title, not phrase matching
**Status:** Accepted
**Decision:** A prospect's school counts as NCAA if and only if the linked Wikipedia article, **after redirect resolution to its canonical title**, ends with `basketball` and carries **no parenthetical disambiguator**. Classification is structural — no player-name or school-name exceptions are permitted.
**Rationale:** ML-0 tested for the phrase `men's basketball` anywhere in the raw link target. That failed three ways:
- **False positives** — foreign clubs and a league use the phrase as a disambiguator: `Beşiktaş J.K. (men's basketball)`, `CSM Constanța (men's basketball)`, `Galatasaray S.K. (men's basketball)`, `Liga Națională (men's basketball)`.
- **False negatives** — Wikipedia canonicalises many NCAA programs without the "men's" infix (`Georgia Bulldogs basketball`) or behind a redirect (`LSU Tigers basketball` → `LSU Tigers men's basketball`). **67 NCAA early entrants were silently absent**, including Ben Simmons, Anthony Edwards, Cade Cunningham and Marcus Smart.
- **Target mislabelling** — the same rule classified the school on a *draft* row, so drafted early entrants whose school went unrecognised were recorded as undrafted. **11 targets were wrong, including Anthony Bennett, the 2013 No. 1 overall pick.**

The parenthesis is the reliable discriminator: college programs are titled `<Team> [men's] basketball`, while clubs, leagues and player articles disambiguate with `(...)`. It also prevents a player link such as `Anthony Edwards (basketball)` being mistaken for a school.
**Consequence:** three non-NCAA records were removed (Alperen Şengün 2021, Cezar Unitu 2024, Jacob Ledoux 2019 — a D-II athletics page). Corrected populations: **2014–2025 887/431/456**, **2011–2013 125/85/40**, **2026 26 (25 drafted / 1 undrafted)**. These supersede the counts in DEC-056.
**Note:** Correctness took priority over the previously published 829 gate, per the ML-0.1 instruction. Regression-tested in `tests/test_population_parser.py`.

## DEC-064 — Prospects without a Wikipedia article are named from list text, not the school link
**Status:** Accepted
**Decision:** In an early-entrant bullet, the first wikilink is treated as the prospect **only if it is not the school link**. Where a prospect has no article, the name is taken from the plain text preceding the position dash and `wikipedia_title` is left empty.
**Rationale:** The parser previously took `links[0]` unconditionally, so a prospect with no article was named after their school — `Casdon Jardine` (2021, Hawaiʻi) became a phantom prospect literally named `Hawai{{okina}}i`. One occurrence across 2011–2026, but the failure mode is structural. Link labels are also markup-stripped, so template artefacts no longer reach the `college` field.

## DEC-065 — Population-derived position and class metadata are prohibited as features
**Status:** Accepted
**Decision:** `position_from_population`, `class_from_population`, `match_method` and `match_confidence` are prohibited as model features, are on the ML-0 deny list, and are **removed from the feature files**. They remain available in `data/raw/draft_population/` and in `identity_crosswalk.parquet` for identity and audit work.
**Rationale (measured, 2014–2025):** the fields are dual-sourced by outcome. ML-0 builds the population from draft picks first, taking position and class from the **draft results table** (fine `PG`/`SG`/`SF`/`PF`/`C` labels), then adds remaining early entrants from the **early-entrant list** (broad `G`/`F`). The label's granularity therefore encodes the target:
- `position_from_population` resolves to a five-position label for **100% of drafted (431/431)** versus **7.7% of undrafted (35/456)**;
- `class_from_population` shows a **26.5 pp** availability gap plus an outcome-specific vocabulary (`graduate`, `redshirt`, `redshirt sophomore` occur only for undrafted; `sophomore year` only for drafted);
- every `UNMATCHED` prospect is undrafted, so `match_method` correlates with the target.

**Note:** This is the leakage channel ML-1 was chartered to find. A model trained before the fix would have scored well for entirely spurious reasons. `hoopr_position` is unaffected — its vocabulary and availability are near-identical across classes (2.4 pp gap) — and remains the approved position source.

## DEC-066 — 2026 holdout is a ranking showcase, not Stage A classification evidence
**Status:** Accepted
**Decision:** Because **25 of the 26** final 2026 NCAA early entrants were drafted:
- **historical expanding-window folds are the primary evidence for Stage A**;
- ROC-AUC, PR-AUC and calibration metrics computed on 2026 are statistically uninformative or unstable and must not be treated as primary evidence;
- 2026 remains the final board / ranking replay showcase and the single post-freeze evaluation;
- if Stage A metrics are computed on 2026 after the freeze, they must be reported **with an explicit instability warning** and must not be overinterpreted.

**The population must not be artificially expanded to improve class balance** — in particular, seniors known after the fact to have been drafted must never be added (DEC-050, DEC-051).
**Note:** This does not permit any use of 2026 for methodology selection (DEC-051 stands).

## DEC-067 — Canonical position is coarse (G/F/C); five-position mapping deferred
**Status:** Accepted
**Decision:** The canonical analytical position is the **coarse G / F / C scheme**, derived deterministically from `hoopr_position` by [`src/draftlens/features/positions.py`](../src/draftlens/features/positions.py) using [`config/features/position_map.csv`](../config/features/position_map.csv). Measured coverage: **98.0%** development, **100%** for the 2026 holdout. Unresolvable labels (`ATH`, `NA`, missing) stay `UNKNOWN` and are never guessed.

**The PG/SG/SF/PF/C scheme required by DEC-009 is deferred**: the only fine-grained pre-draft label available is outcome-contaminated (DEC-065), so no leakage-safe source exists. The deterministic five-position parser is implemented and unit-tested but **applied to nothing**, ready for a clean source.
**Owner decision required:** accept G/F/C for position-relative work, obtain a genuinely pre-draft five-position feed, or relax DEC-009. **Position must never be inferred from statistics or from draft outcome.**

## DEC-068 — Shot-type vocabulary breaks at 2020/2021; jump-shot fields are not comparable
**Status:** Accepted
**Decision:** `jump_shot_attempts` and `jump_shot_makes` must not be used across the 2020/2021 boundary without correction. ML-2 must either subtract `three_point_shot_*` to reconstruct a comparable two-point-jumper quantity, or build shot profile from the stable categories only.
**Rationale:** the hoopR `type_text` vocabulary is not stable. `Three Point Jump Shot` is a distinct category through 2020 and is folded into `JumpShot` from 2021, so `JumpShot` share roughly doubles (≈21% → ≈50%) and median jump-shot attempts jump 81 → 235. ML-0's category map counts only `JumpShot`/`LayUpShot`/`DunkShot`/`TipShot`, so the field silently changes meaning mid-window.
**Note:** `LayUpShot`, `DunkShot`, `TipShot` and `three_point_shot_*` (derived from `score_value`, not `type_text`) are unaffected. Assist linkage is stable at 50.8–52.9% across all 12 years.

## DEC-069 — Undefined ratios are NULL, never zero and never infinity
**Status:** Accepted
**Decision:** All derived ratios use one shared `safe_div` utility. A ratio is **NULL** whenever its denominator is missing, zero or negative, or its numerator is missing. No epsilon is ever added, infinity is never produced, and an undefined statistic is never silently rendered as 0.
**Rationale:** 0 made from 0 attempts is UNKNOWN, not 0%. Substituting zero would fabricate a factual claim about a player (DEC-017) and would systematically penalise low-volume prospects. Unit-tested in `tests/test_ml2_features.py`.

## DEC-070 — Generic jump-shot metrics are permanently rejected for cross-year modelling
**Status:** Accepted
**Decision:** No feature may be derived from the generic `jump_shot_*` primitives — specifically `jump_shot_share`, `jump_shot_pct` and `jump_shots_per_40` are prohibited. The rejection is recorded in [`config/features/feature_dictionary.csv`](../config/features/feature_dictionary.csv) with status `REJECTED`, and a test fails if any column containing `jump_shot` reaches the feature layer.
**Rationale:** DEC-068 — hoopR's `type_text` folds `Three Point Jump Shot` into `JumpShot` from 2021, so the category silently changes meaning mid-window. Shot profile is built instead from `layup`, `dunk`, `tip` and three-point attempts identified via `score_value`, all of which are stable across 2014–2026.
**Note:** The raw ML-0 columns remain for source and audit purposes.

## DEC-071 — Unresolved prospects are retained, never outcome-selectively dropped
**Status:** Accepted
**Decision:** Prospects without matched hoopR statistics remain in every analytical partition with NULL feature values. They must not be dropped, zero-filled, or flagged with a `has_stats`-style predictive feature, and no missingness indicator may be derived from their absence.
**Rationale:** All 8 unresolved development prospects are undrafted (ML1_EDA §11). Dropping rows without statistics would remove only negatives and inflate downstream performance. Validation hard-fails if the retained count falls below 8 or if the ML-2 prospect set differs from ML-0.

## DEC-072 — Team context is reconstructed from the prospect's played games only
**Status:** Accepted
**Decision:** Team and opponent totals used by usage%, AST%, ORB%/DRB%/TRB%, STL%, BLK% and the per-100 rates are summed over **only the games the prospect actually played**, reconstructed from `player_box` by game with opponents obtained via a same-game self-join. Whole-season team totals are never used.
**Rationale:** A prospect who played 12 of 33 games, or who transferred mid-season, must not inherit context from games they did not play. Validated: reconstructed team minutes come to **201.4 per game** against a theoretical 200, and possessions to ≈68 per game. This confirms `team_box` is unnecessary (DATA.md §22.2).
**Note:** The conventional free-throw possession coefficient **0.44** is exposed as the named constant `FT_POSSESSION_COEF` and documented in the feature dictionary rather than embedded as a literal.

## DEC-073 — Rare-event ratio undefinedness is target-correlated and must not be imputed naively
**Status:** Accepted
**Decision:** `tip_make_pct`, `dunk_make_pct`, `assisted_dunk_make_share` and `unassisted_dunk_make_share` are marked **CAUTION**. Neither constant imputation nor a missingness indicator may be applied to them without an explicit leakage review.
**Rationale:** Measured on 2014–2025, `tip_make_pct` is defined for **77.5% of drafted versus 50.4% of undrafted** prospects — a **27.1 pp** gap; the dunk ratios show 11.9–13.3 pp. The cause is structural rather than contamination: attempting zero tip-ins or dunks is itself informative. But it means a constant fill or an indicator column would encode a partial target proxy — the same failure mode that excluded age (DEC-044).
**Note:** All other engineered features sit at a ≈2.8 pp gap, consistent with the general match gap and benign.

## DEC-074 — scikit-learn approved for the analytical ML pipeline
**Status:** Accepted
**Decision:** `scikit-learn` (1.9.0, with transitive `scipy`, `joblib`, `threadpoolctl`) is approved for the analytical ML pipeline. Still prohibited without a separate decision: xgboost, lightgbm, catboost, optuna, shap, mlflow, torch, tensorflow.
**Note:** Extends DEC-037. This is not an application-architecture decision — DEC-022 stands.

## DEC-075 — Temporal aggregation is reported year-macro AND pooled, never one alone
**Status:** Accepted
**Decision:** Every Stage A result must report **both** the year-macro aggregate (each validation year weighted equally) and the pooled aggregate (all out-of-fold predictions together), plus the standard deviation across folds and the worst-year value. A bare pooled metric is prohibited.
**Rationale:** Validation fold sizes range 28–188 and base rates 0.266–0.929, so pooled metrics are dominated by 2021 (21% of the window). ML-3 observed the two orderings genuinely disagree: the selected configuration ranks 6th on macro but 3rd on pooled. Model selection on either alone would be arbitrary.
**Note:** Folds where the minority class has fewer than 5 members are flagged **LOW NEGATIVE SUPPORT** and must not drive selection. 2025 (2 undrafted) is such a fold.

## DEC-076 — Sparse rare-event ratios are excluded from Stage A feature sets
**Status:** Accepted
**Decision:** `tip_make_pct`, `dunk_make_pct` and `unassisted_dunk_make_share` are excluded from Stage A modelling feature sets rather than imputed. They remain in the ML-2 feature layer for display and later analysis.
**Rationale:** DEC-073 measured their definedness as target-correlated (up to 27.1 pp). ML-3 tested exclusion against train-fold median imputation on the broadest feature set: exclusion scored **macro ROC-AUC 0.6979 vs 0.6915** with an equal Brier, so removing the leakage risk costs nothing. `SET_2_BOX_SHOT_PROFILE` excludes them by construction.
**Note:** No missingness indicator, sentinel value, or zero-fill may substitute for them (DEC-069, DEC-073).

## DEC-077 — Redundancy representatives chosen by basketball logic, not validation AUC
**Status:** Accepted
**Decision:** Where ML-2 features are near-duplicates (|r| ≥ 0.95), one representative per group is retained using a fixed rule recorded in [`config/ml/ml3_baselines.json`](../config/ml/ml3_baselines.json): prefer the **per-40 rate** for counting statistics; keep the **unassisted** direction of algebraic complements; keep **`three_point_attempt_rate`** for attempt mix; keep a possession percentage only where it has no per-40 twin (`usage_pct`, `tov_pct`).
**Rationale:** Choosing between mathematically equivalent representations by validation score would be fitting noise. 23 correlated pairs resolved into 14 groups; 12 carry an explicit representative, enforced by test.

## DEC-078 — Stage A baseline configuration carried into ML-4
**Status:** Accepted
**Decision:** ML-4 begins from **`LR | SET_2_BOX_SHOT_PROFILE | B_TRAIN_MEDIAN | STANDARD | ONEHOT | class_weight=balanced | C=1.0`**, with all preprocessing fitted inside each fold. `class_weight="balanced"` is retained.
**Rationale:** Selected on the multi-criterion rule, not peak AUC — it ranks 6th on year-macro ROC-AUC (0.6809 vs 0.6979) but is best or joint-best on **Brier (0.2262)**, **calibration (max gap 0.140)**, **temporal stability (SD 0.0339)** and **worst-year ROC-AUC (0.6458)** among logistic models, uses 25 features rather than 38, and excludes the DEC-076 sparse ratios by construction. The macro spread across all 15 logistic configurations is 0.029 — inside noise at 28–188 validation rows per fold — so the tie-break favours the simpler, better-calibrated, more stable option.
**Note:** `class_weight="balanced"` is kept for calibration and stability, not accuracy: it costs ~0.003 macro AUC and improves Brier from 0.2340 to 0.2262, which matters because the 2026 holdout base rate (0.96) sits far outside the training range (ML_SPEC §4.3).

## DEC-079 — The position-percentile composite is the benchmark ML-4 must beat
**Status:** Accepted
**Decision:** `B4_POSITION_PERCENTILE_COMPOSITE` — an equal-weight composite of within-position percentile ranks, fitted on training folds only — is retained as the **standing benchmark** for Stage A. A more complex model must beat **macro ROC-AUC 0.6943** and **macro NDCG@drafted 0.7171** on the same folds to justify its complexity.
**Rationale:** It matched or beat every logistic configuration on ranking (0.6943 macro) with the best stability of anything tested (SD 0.0219) and the best worst-year (0.6727). It is **not** the carry-forward because it produces rank quantiles rather than probabilities — its calibration gap reaches 0.22 and Brier 0.2530 — and DEC-053 requires Stage A to output a calibrated `P(drafted)`.
**Note:** This makes the complexity bar explicit before nonlinear models are attempted, per PRODUCT.md §20 ("Honest evaluation") and ML_SPEC §16.

## DEC-080 — Stage A model family remains regularised logistic regression
**Status:** Accepted
**Decision:** Stage A stays a **regularised logistic regression**. Random forest, HistGradientBoosting and classic gradient boosting were each evaluated in three or two predeclared configurations across the same seven temporal folds and are **rejected** for Stage A.
**Rationale:** The nonlinear advantage was not real. `RF_dNone_leaf30` posted the highest year-macro ROC-AUC in the study (0.7090) but scored **0.8654 on the 2025 fold, which has exactly two undrafted prospects**. Removing that fold drops it from **rank 1 to rank 12** (0.6830) — the largest negative shift of any candidate. All three random forests and both gradient-boosting configurations show the same pattern, and the tree ensembles carry the worst fold SDs in the study (0.065–0.076 against the incumbent's 0.034). The entire field spans only 0.681–0.709 macro ROC-AUC across four families, so no family separates on evidence.
**Note:** Applies to Stage A only. Stage B is undecided and DEC-053 is unaffected. Prohibited libraries (xgboost, lightgbm, catboost, optuna, shap, mlflow, torch, tensorflow) remain prohibited — DEC-074 stands.

## DEC-081 — Stage A uses season-relative feature normalisation
**Status:** Accepted
**Decision:** Ten Stage A metrics — `points_per_40`, `reb_per_40`, `assists_per_40`, `steals_per_40`, `blocks_per_40`, `ts_pct`, `efg_pct`, `three_point_attempt_rate`, `free_throw_rate`, `minutes_per_game` — are represented as **z-scores against the NCAA reference distribution for the same season and same coarse position** (`position_3`), built in ML-2 from the full hoopR NCAA player population. The remaining features keep the ML-3 standard representation, and the train-fold `StandardScaler` still runs afterwards. This resolves the ML_SPEC §9.2 season-normalisation open question for Stage A.
**Rationale:** This was the only change in ML-4 that improved Stage A on evidence. Against DEC-078 it improves **11 of 12** reported measures: macro ROC-AUC 0.6986 vs 0.6809, macro excluding the low-support fold 0.6997 vs 0.6758, pooled 0.6953 vs 0.6865 (the highest pooled figure of any configuration tested), Brier 0.2238 vs 0.2262, ECE 0.0590 vs 0.0701, NDCG 0.7061 vs 0.6974, fold SD 0.0281 vs 0.0339 and worst-year 0.6742 vs 0.6458. It is one of only four candidates whose ranking **improves** when the low-support fold is removed. The corroborating evidence is mechanistic: B4 — a 6-metric heuristic with no fitted coefficients — is the other top performer, and peer-relative normalisation is the only thing the two share.
**Leakage:** The reference contains no draft outcome and is not the prospect sampling frame — it is the full NCAA player population of that season, so it cannot reintroduce the ML-1 sampling-frame channel. Season Y prospects are normalised against season Y, whose games conclude before the June draft, satisfying ML_SPEC §9.2. The same formula is applied to every draft year.
**Note:** The improvement is **not statistically decisive** — mean paired gain +0.0177 against a fold SD of 0.0256 on 7 folds. It is accepted on directional consistency (5 of 7 folds, worst fold −0.019, best worst-year of any candidate), not significance.

## DEC-082 — Stage A regularisation strength is C = 0.25
**Status:** Accepted
**Decision:** Stage A uses **L2 at C = 0.25** on the season-relative representation. L1 is rejected.
**Rationale:** On the raw representation, stronger regularisation improves discrimination and Brier monotonically across C ∈ {1.0, 0.5, 0.25, 0.1, 0.05}, and `LR_C0.05` achieves the best ECE (0.0409) and max calibration gap (0.0908) in the entire study. The season-relative representation prefers a weaker penalty (0.25 rather than 0.05), consistent with z-scored inputs already carrying part of the regularising effect. `LR_C0.05` was not selected because its worst-year (0.6297) and low-support-robust macro (0.6899) fall materially below the season-relative model's (0.6742 / 0.6997), and worst-year robustness is the criterion this project has prioritised throughout. L1 at C ∈ {0.1, 1.0} ranks below the incumbent on the low-support-robust ranking (0.6694 and 0.6788); with 25 correlated features its arbitrary within-group selection is a liability.
**Note:** No season-relative configuration below C = 0.25 was predeclared, so stronger regularisation on that representation is **untested, not rejected**. Adding one after seeing results would be post-hoc selection; it must be predeclared in a future phase (ML4_STAGE_A §22).

## DEC-083 — Stage A ships uncalibrated; isotonic calibration is rejected
**Status:** Accepted
**Decision:** Stage A emits the model's **uncalibrated** probability. **Isotonic calibration is rejected.** Sigmoid (Platt) calibration under `TEMPORAL_HOLDOUT` is **not adopted but not ruled out** for later phases.
**Rationale:** The selected model is already the best-calibrated logistic model in the study on support-weighted calibration error — **ECE 0.0590**, better than its own sigmoid variant (0.0714) and better than the incumbent (0.0701). Its higher max gap (0.1965) comes from a single decile (0.7127 predicted vs 0.5161 observed) whose neighbours sit at 0.0015 and 0.0789; max gap alone was misleading, which is why ECE was added as a reported metric. Sigmoid additionally compresses the usable probability range from 0.98 to 0.62, capping the board's top at p = 0.752 — a draft tool must be able to express near-certainty. Isotonic degrades log loss to 0.84–0.88 and roughly doubles ECE on every finalist: a nonparametric calibrator fitted on one year of 49–188 rows overfits.
**Method note:** Where calibration is used, the design is **`TEMPORAL_HOLDOUT`** — base model fitted on all training years except the last, calibrator on that last training year only, both strictly earlier than the outer validation year (56 fits verified). sklearn's `CalibratedClassifierCV` default is random K-fold, which mixes draft years, and is **prohibited**. A `+none_reduced` control is mandatory alongside any calibration comparison: sigmoid is monotone and cannot reorder the board, so an AUC change under calibration is the cost of the surrendered training year, never the calibration itself.

## DEC-084 — Folds with low negative support must be re-ranked out, not merely flagged
**Status:** Accepted
**Decision:** Every Stage A model comparison must report the ranking **twice** — over all folds, and with folds flagged LOW NEGATIVE SUPPORT removed. A candidate whose ranking depends on such a fold has not been shown to be better. The sensitivity table is a required artifact.
**Rationale:** DEC-075 flagged these folds but still allowed them into the year-macro average, where 2025 carries a full 1/7 weight on an ROC-AUC computed against two negatives. ML-4 showed this was silently deciding the leaderboard: the four largest negative shifts under re-ranking all belong to tree ensembles, and the naive protocol would have selected a model that is 12th once the fold is removed and reported a fictitious +0.028 improvement.
**Note:** Strengthens DEC-075 rather than replacing it. Both aggregations are still reported. `scripts/experiments/validate_ml4_stage_a.py` requires the sensitivity artifact to exist.

## DEC-085 — Stage A class weighting stays `balanced`
**Status:** Accepted
**Decision:** `class_weight="balanced"` is retained for Stage A. Re-confirms DEC-078 against fresh evidence at a second regularisation strength.
**Rationale:** Unweighted fitting is marginally better on ranking (+0.001 macro ROC-AUC) and clearly worse on probability quality at both C values tested — Brier 0.2305 vs 0.2224 and ECE 0.0988 vs 0.0722 at C = 0.25; Brier 0.2340 vs 0.2262 and ECE 0.0957 vs 0.0701 at C = 1.0. Stage A's product obligation under DEC-053 is a calibrated probability, so the trade favours `balanced`. ML_SPEC §4.3 records that the eventual holdout base rate sits far outside the training range, making probability quality under imbalance a live concern rather than an academic one.

## DEC-086 — Stage B target representation is the raw pick
**Status:** Accepted
**Decision:** Stage B regresses on **`RAW_PICK`** — the pick number itself, untransformed. `LOG_PICK`, `PICK_PERCENTILE` and `DRAFT_VALUE` are **rejected as the production target**. This resolves the ML_SPEC §6.3 target question for Stage B.
**Rationale:** The four candidate targets are statistically indistinguishable — macro Spearman **0.2596–0.2624** averaged across 12 models, a range of 0.003 against a fold SD of 0.13. More fundamentally, `RAW_PICK`, `PICK_PERCENTILE` and `DRAFT_VALUE` are **affine images of one another within a draft year**, so for a linear model they cannot induce different rankings: measured rank correlation between their out-of-fold rankings is **0.998**, and the residual 0.002 is entirely draft size varying 58–60 across years. At fixed α their per-fold Spearman is identical to four decimals on all seven folds. Choosing among them is choosing among labels, not methods. `LOG_PICK` is the only genuinely non-affine transform and is worse on NDCG (0.8948 vs 0.9024), MAE (+0.6 picks), RMSE (+1.5) and worst-year (−0.101) for a Spearman edge of 0.003.
**Tiebreak:** Among rank-equivalent options, `RAW_PICK` is the most directly interpretable and the **only one with no dependency on an externally maintained draft-size constant** — a dependency that was already wrong for 2014 the first time it was checked (see DEC-088).
**Note:** All four transformations remain declared, monotonic, exactly invertible and tested. Nothing prevents a later phase reopening this if the model class changes — the affine-equivalence argument holds for linear models specifically.

## DEC-087 — Stage B model is Ridge(alpha=10) on the frozen Stage A representation
**Status:** Accepted
**Decision:** Stage B uses **`Ridge(alpha=10)`** on `SET_2_BOX_SHOT_PROFILE` + `SEASON_RELATIVE` + train-fold median imputation + `position_3` one-hot + train-fold `StandardScaler`, with the target z-scored on train-fold statistics (exactly invertible, rank-preserving). Random forest, HistGradientBoosting, gradient boosting and ElasticNet are **rejected** for Stage B.
**Rationale:** **Every ridge configuration outranks every nonlinear configuration** on rank quality — ridge 0.282–0.307 macro Spearman versus best nonlinear 0.275 (GB depth 2), 0.266 (RF), 0.250 (HGB). Unlike ML-4 this required no low-support argument; the ordering is direct. ElasticNet is the worst linear family (0.193–0.265): with 25 correlated basketball features, L1's arbitrary within-group selection is a liability, exactly as in ML-4 §17. Within the ridge path, α = 1 leads on macro Spearman by 0.0104 — **a quarter of that difference's own fold SD (0.0428)**, i.e. noise — while nearly doubling coefficient volatility (mean coefficient fold SD 0.0747 vs 0.0388; 20/29 vs 22/29 sign-consistent). α = 10 is the only configuration never worst on any criterion: best fold SD of the grid (0.1242), second on worst-year, second on coefficient stability, inside noise of the best macro Spearman, and best-of-grid pooled Spearman among stable options (0.3252 vs α=50's 0.2996).
**Evidence:** macro Spearman **0.2968**, pooled 0.3252, Kendall τ 0.2089, NDCG 0.9043, NDCG@14 0.7555, MAE 13.21, fold SD 0.1242, worst year 0.1381, Spearman positive in all 7 folds. Beats the B5C percentile-composite ranking baseline (0.2320) by +0.065 and the position baseline (**−0.1235**, negative) decisively.
**Note:** Stage A remains frozen (DEC-080…085). ML-5 inherited its representation unchanged and reopened nothing. The reduced `SET_2R` variant was tested and is slightly worse (0.2910); the full set is retained.

## DEC-088 — Stage B ranking metrics outrank numeric error, and RMSE-only selection is prohibited
**Status:** Accepted
**Decision:** Stage B model selection is decided by, in order: **(1) macro Spearman · (2) NDCG · (3) temporal stability · (4) worst-year ranking · (5) MAE as supporting evidence only · (6) simplicity · (7) interpretability · (8) consistency with product claims.** Selection by lowest RMSE or MAE alone is **prohibited**.
**Rationale:** Numeric error carries almost no discriminating information on this problem. The entire field of 60 configurations spans **13.1–14.4 MAE**, and the B5A baseline — predicting the training-fold mean pick for every prospect — scores **14.02**. The best model beats a constant by 0.8 picks. Selecting on RMSE would have been selecting on approximately nothing, and would have preferred a gradient-boosting model whose rank quality is 0.028 worse. Rank quality is also what the product actually outputs (PRODUCT.md §4, ML_SPEC §13).
**Method notes:** (a) Full-list NDCG discriminates poorly at 26–50 drafted prospects per year — every configuration scores 0.85–0.92 and even the perverse position baseline reaches 0.848 — so **NDCG@14 is the informative variant** and Spearman is primary. (b) A **constant predictor must report null rank metrics, never 1.0**; `stage_b_metrics` detects zero prediction variance, guarding against the ML-3 NDCG tie-break defect. (c) One **canonical orientation** exists project-wide: every prediction is inverse-transformed to the pick scale before `strength = −pick` is applied, so higher strength always means an earlier pick. Tested in both directions, including that a reversed board scores −1.
**Draft-size provenance:** Draft sizes (60 for 2014–2021, 58 for 2022–2024, 59 for 2025) are version-controlled in `config/ml/stage_b.json`, sourced from DATA.md §24.5 with **one correction**: DATA.md recorded 59 picks for 2014, but pick 60 exists in the raw data. Every observed pick is validated against its declared draft size.

## DEC-089 — Exact numeric pick prediction is NOT display-safe
**Status:** Accepted
**Decision:** DraftLens must **not** display a numeric predicted pick (e.g. "Predicted Pick: 17.3"). Stage B's output is an **ordering signal**. Permitted display concepts — final UI choice deferred to a later phase — are relative draft order, Expected Draft Tier, a draft range, or a normalised position signal. Language implying DraftLens forecasts the real NBA draft board is prohibited: Stage B sees only NCAA early entrants, never seniors or international prospects.
**Rationale:** Four independent facts, each sufficient alone. **(1)** MAE is **13.28 picks** on a 60-pick draft — more than a full round, and only 0.8 picks better than predicting the mean. **(2)** Only **20.9%** of predictions land within 5 picks; 38.1% within 10. **(3)** The model emits **illegal picks** — its minimum prediction is **−5.1**, a number that cannot exist. **(4)** Predictions collapse toward the middle: actual lottery picks (mean pick 7.8) are predicted at **23.0** and actual second-rounders (mean 44.1) at **28.8**, so the two groups' mean predictions differ by under 6 picks while their actual means differ by 36. A numeric display would systematically understate elite prospects and overstate marginal ones.
**Note:** This satisfies PRODUCT.md §20 ("No fabricated data", "does not claim certainty") and ML_SPEC §17.2 ("No false precision"). No uncertainty intervals were built — ridge provides none without distributional assumptions the data does not support — and none are needed to settle the question. Board-level figures must always carry the qualifier **"among in-scope NCAA early entrants"**: lottery recall@14 is 54.5% and first-round recall@30 is 86.0% within that population only.

## DEC-090 — The three-tier draft representation is retained for display
**Status:** Accepted
**Decision:** The tier scheme **lottery (1–14) / rest of first round (15–30) / second round (31–60)** is retained as an interpretable **display and explanation** representation. It is **not** the Stage B ranking model. The traditional four-tier scheme (1–14 / 15–30 / 31–45 / 46–60) is **rejected**.
**Rationale:** ML_SPEC §6.3 required boundaries to be justified against observed density rather than adopted because they are traditional. The four-tier scheme produces **8 of 48 year × tier cells with fewer than 5 members** (late second: 1 in 2025, 2 in 2014, 2 in 2015, 3 in 2016/2017/2024). Merging the two second-round tiers gives **1 of 36 cells below 5**. The 1–14 and 15–30 boundaries are kept because they are structural — lottery size and first-round size — not merely conventional. Boundaries are fixed from development history and never refitted per fold. Tier totals: 130 / 133 / 168.
**Evidence:** A multinomial logistic tier model reaches **42.0% exact** and **79.3% adjacent-tier** accuracy, ordered distance error 0.787. As a ranker it is competitive (macro Spearman 0.3036) but is not selected: worst-year Spearman 0.0529 against the selected model's 0.1381, lower pooled Spearman, and it cannot produce a pick-scale error.
**Limitation — must be stated wherever used:** scikit-learn provides **no native ordinal-regression estimator**. This is multinomial classification; **the estimator does not know the tiers are ordered** — only the evaluation does. It must never be described as ordinal regression.

## DEC-091 — Learning-to-rank is an evaluation objective, not a Stage B model
**Status:** Accepted
**Decision:** ML_SPEC §6.3 candidate D (learning-to-rank) is addressed by treating **ranking as the evaluation objective** rather than by fitting a dedicated ranker. No ranking library is installed. A regression output inducing a ranking is the approved mechanism.
**Rationale:** scikit-learn provides no scientifically clean learning-to-rank estimator for this setup — no LambdaMART, no RankNet, no pairwise or listwise objective. Installing a library solely to satisfy the candidate would breach DEC-074 and add a dependency for one experiment at a sample size (158–405 training rows) where the literature for these methods is thin. Every continuous target induces a ranking, and rank quality is the primary selection criterion (DEC-088).
**Note:** Recorded as a documented limitation, not a silent omission. `test_no_ranking_library_was_installed` asserts that xgboost, lightgbm, catboost, allrank, pyltr and similar remain absent. `scipy` (Spearman, Kendall τ) was already an approved transitive dependency under DEC-074 — no new dependency was added in ML-5.

## DEC-092 — Reusable analytical logic lives in `src/draftlens`; scripts stay thin
**Status:** Accepted
**Decision:** All reusable domain logic lives in the installable package `src/draftlens/` (data · features · ml). `scripts/` contains only thin entry points that parse arguments, call library functions, print results and return an exit code. A formula may have exactly **one** implementation, in the package; duplicating it in a script is a defect. Library modules are named for what they do (`stage_a.py`), not when they were written (`ml4_common.py`); experiment scripts and phase reports keep phase names because there the chronology is the evidence.
**Rationale:** The phase-by-phase layout had reached the point where `run_ml5_stage_b.py` was imported by its own validator, by the test suite, and by another phase's runner — a 621-line "script" that was really the Stage B library. That coupling makes any change to Stage B a change to five files, and it makes the analytical core unusable by a future application layer without importing experiment CLIs. Packaging under a `src/` layout with a minimal `pyproject.toml` (setuptools, five direct dependencies, no publishing configuration) makes `import draftlens` work identically for scripts, tests and any later consumer.
**Verified non-breaking:** the refactor moved code without changing behaviour. ML-2 features reproduced **bit-identically** (SHA-256 match on 887 × 81), and all ML-3, ML-4 and ML-5 artifacts reproduced with `atol=0`. Full suite 247 tests passing; all five phase validators pass.

## DEC-093 — Experiment reports are historical evidence and live in `docs/experiments/`
**Status:** Accepted
**Decision:** Frozen phase reports live in `docs/experiments/` under descriptive names (`ML4_STAGE_A.md`, not `ML4_REPORT.md`). Their selection experiments remain runnable under `scripts/experiments/`. Neither may be used to change a frozen selection: that requires a new phase and a new decision. `docs/` itself holds only the living specifications — PRODUCT, MVP, DATA, ML_SPEC, ARCHITECTURE, DECISIONS.
**Rationale:** Six phase reports at the top level made the specifications hard to find and implied the reports were still open for revision. They are not — they are the record of what was measured, and their numbers are pinned by `tests/integration/test_frozen_anchors.py`.

## DEC-094 — Stage A and Stage B are frozen in code, and the anchors are tested
**Status:** Accepted
**Decision:** The frozen selections are declared as data in `draftlens.ml.stage_a.STAGE_A` and `draftlens.ml.stage_b.STAGE_B`, and the published metrics are asserted end-to-end in `tests/integration/test_frozen_anchors.py` at a tolerance of **1e-4** — the precision the reports publish. A failing anchor must be investigated, never accommodated by loosening the tolerance.
**Rationale:** "Frozen" written only in prose is not enforceable. Declaring the configuration as inspectable data means a change is visible in a diff, and pinning the anchors means a change is visible in CI. The anchors covered: population 887/431/456; Stage A macro ROC-AUC 0.6986, pooled 0.6953, Brier 0.2238, NDCG 0.7061, SD 0.0281, worst year 0.6742, ECE 0.0590; Stage B macro Spearman 0.2968, Kendall 0.2089, NDCG 0.9043, NDCG@14 0.7555, MAE 13.2141, RMSE 15.5641.

## DEC-095 — Stage B's frozen representation is STANDARD, not SEASON_RELATIVE
**Status:** Accepted (corrects a documentation error in ML-5)
**Decision:** Stage B's frozen feature representation is **`STANDARD`**. `draftlens.ml.stage_b.STAGE_B` and `config/ml/stage_b.json` record `STANDARD`, and a correction notice has been added to [ML5_STAGE_B.md](experiments/ML5_STAGE_B.md).
**Rationale:** ML-5 declared it would inherit Stage A's `SEASON_RELATIVE` representation, and both the config and the report said so — but the experiment script imported `season_relative` without ever calling it. Discovered during the R-1 refactor when a rebuilt Stage B entry point produced macro Spearman 0.2999 instead of the published 0.2968. **Every published ML-5 number is correct and exactly reproducible**; only the *description* of the representation was wrong. The evidence supports `STANDARD`, so `STANDARD` is what is frozen.
**Not silently repaired:** running Stage B with `SEASON_RELATIVE` moves macro Spearman from 0.2968 to 0.2999 (+0.0031, well inside the fold SD of 0.124). Adopting it would be a scientific change and requires its own evaluation phase, not a refactor. Recorded as open architectural debt.
**Note:** this is exactly the failure mode the R-1 brief's "compare BEFORE and AFTER outputs, do not accept close enough" rule exists to catch.

## DEC-096 — Stage B enters the General Draft Board
**Status:** Accepted
**Decision:** The General Draft Board combines **both** frozen stages. Stage A-only was evaluated as the reference board and is **beaten**, so Stage B enters the Overall Score.
**Rationale:** Against the Stage A-only board the selected combination improves every headline measure — binary macro ROC-AUC 0.6986 → **0.7123**, graded board NDCG 0.8159 → **0.8283**, drafted-only Spearman 0.2461 → **0.2781** — and improves the joint objective in **5 of 6 non-degenerate folds** (every alternative combination is a coin flip at 3/6). The largest gain is in robustness: Stage A alone is the least stable board tested (graded NDCG fold SD 0.0869, worst year 0.6590); the combination cuts the SD by a third (0.0594) and lifts the worst year to 0.7281. Stage B's contribution is largest exactly where Stage A struggles most — 2021, the COVID cohort, gains +0.0691.
**Why this was not automatic:** the two-stage architecture existing is not a reason to combine. **Stage B alone is NOT a board** — it is worse than Stage A on the joint objective (graded NDCG 0.8095, improving in only 2 of 7 folds) and much worse at separating drafted from undrafted (macro AUC 0.6911 vs 0.6986, −0.041 excluding the degenerate fold), because it was trained solely among drafted players and models no draft likelihood. The combination works because the stages are only moderately correlated (pooled Spearman 0.509) and each is better at a different job.
**Note:** the incremental value is **modest** — +0.012 graded NDCG. The case rests on consistency and stability, not effect size. Stage A-only remains a defensible board and is retained as a permanent candidate in `config/ml/ml6_board.json`.

## DEC-097 — The board signal is a multiplicative expected draft value
**Status:** Accepted
**Decision:** The final board signal is
`final_board_signal = P(drafted) × draft_slot_utility(Stage B predicted pick)`
where `draft_slot_utility = (draft_size + 1 − clip(pick, 1, draft_size)) / draft_size`. Rank fusion, lexicographic banding, Stage-B-only and the equal-weight sum are **rejected**.
**Rationale:** The product is a real expectation — likelihood of entering the draft times the conditional quality of the slot the profile resembles — so it has a meaning a scout can be told in one sentence. It has **no free constants**: no weight, no band width, no curvature; the clipping bound is the basketball-valid slot range and touches 1 of 617 development rows. It is the only candidate positive on all three axes with consistent fold support (graded 5/6, AUC 4/6, Spearman 5/6) and has the smallest graded downside of any combination (−0.0118 against −0.041 for the alternatives).
**Rejections, with the specific reason each lost:** `C | WITHIN_BOARD_PERCENTILE` posted the best raw AUC (0.7244) but **−0.0203 of it disappears when the 2-negative 2025 fold is removed** — the largest such shift of any candidate — and multiplying a probability by a *rank* forfeits the expected-value reading. `D_RANK_FUSION` is strong (best pooled AUC, largest Spearman gain) but is a coin flip on the joint objective (3/6, worst −0.041) and is an avowed heuristic. `E_LEXICOGRAPHIC` scored the **highest graded NDCG (0.8395)** yet improves binary AUC by only +0.0034, and its output depends on a band-width constant nothing in the data selects — deciles, quintiles and 20-tiles would give different boards. Rejected as too arbitrary. `F_EQUAL_WEIGHT_SUM` is a weighted sum of two differently-scaled quantities and has no interpretation.
**Prohibited and not performed:** any blend-weight search. No 0.1/0.9 … 0.9/0.1 grid was evaluated; the single 0.5/0.5 point exists only as a labelled heuristic reference.

## DEC-098 — Overall Score is a class-relative integer 0–100 ranking score
**Status:** Accepted
**Decision:** `overall_score = round(100 × within-class percentile of final_board_signal)` — an **integer 0–100**. The historical-empirical (cross-class absolute) alternative was implemented, measured and **rejected**.
**Rationale:** Both transforms are exactly order-preserving, so the choice turns on what the absolute scale would mean. The historical variant produced a genuine 25-point spread in class medians — its intended advantage — but its absolute meaning rests on the board signal distribution transferring across classes, and that signal is built from Stage A's probability scale. ML_SPEC §4.3 and DEC-066 establish Stage A is **badly miscalibrated** when a class's base rate departs from the 48.6% training window, and declared-entrant composition varies by a factor of six across development alone. An absolute score would silently inherit that miscalibration while presenting cross-class comparability it does not possess. The class-relative score depends only on **ordering within a class**, which is exactly what both stages were validated on.
**Binding properties, all enforced by test and validator:** integer only (`92.738` implies precision the model lacks); order-preserving — if A outranks B on the board signal then `score(A) ≥ score(B)`, verified in all 7 development classes; equal signals receive equal scores, and ties are **never** broken by player name, draft outcome or any NBA information.
**Accepted limitation:** scores are **not comparable across draft classes** — every class necessarily contains a ~100 and a ~0. This is disclosed, not engineered away.

## DEC-099 — Three product signals, never collapsed into one label
**Status:** Accepted
**Decision:** DraftLens exposes three distinct signals and must never merge their labels:
**Overall Draft Score** (0–100 ranking score) · **Draft Probability** (Stage A `P(drafted)`, the only genuine probability) · **Draft Position Signal** (Stage B conditional draft-order signal).
**Rationale:** The Overall Score uses Stage B, so calling it a probability would be false. Stage A is the only output on a probability scale. Stage B's numeric pick is **not display-safe** (DEC-089: MAE 13.21, 21% within 5 picks) and remains prohibited as a "Predicted Pick" claim.
**Prohibited language:** labelling the Overall Score *Draft Probability* or *chance of being drafted*; "92/100 means a 92% chance"; presenting Stage B as *Predicted Pick*. **Approved framing:** "a 0–100 ranking score derived from historical pre-draft models — not a probability and not a predicted pick", read as *"top X% of this draft class on the pre-draft evidence"*.
**Note:** the ML-5 three-tier scheme (42% exact / 79% adjacent) is available as a **secondary explanation** of the Draft Position Signal. It is never used to construct the Overall Score.

## DEC-100 — Applying Stage B to every prospect is a conditional signal, and missing Stage B is neutral
**Status:** Accepted
**Decision:** Stage B — trained on drafted prospects only — is applied to **every** board prospect. Its meaning for a prospect who is not drafted is strictly conditional: *"if this basketball profile were draftable, which part of the draft does it resemble?"* It is never a pick assignment. When Stage B cannot produce a signal, the prospect receives the **neutral** quality value so the board degenerates to a monotone function of Stage A alone for them; they are never dropped and never penalised.
**Rationale:** The extrapolation was audited before anything was built on it and is well behaved — **1 of 617** development out-of-fold predictions falls outside the legal slot range and none exceeds the draft size, with undrafted profiles landing 4.7 picks later on average. Targets are untouched throughout: every undrafted prospect keeps `drafted = 0` and `pick = NULL`, and the graded relevance used to evaluate boards assigns them exactly 0. That relevance is an **evaluation quantity only** — never a training target and never a synthetic pick.
**Why neutral rather than low:** unresolved and missing-data rows were disproportionately undrafted historically (all 8 unresolved development prospects are undrafted, DEC-071), so penalising a missing Stage B signal would turn missingness into a hidden outcome proxy — the same failure mode that excluded date of birth (ML_SPEC §8.2).
**Honest note:** 0 of 617 development prospects have a missing Stage B signal, so this policy is enforced by test rather than selected by measurement.

## DEC-101 — Team Need is a preference system and is never fitted to an outcome
**Status:** Accepted
**Decision:** Team Need is a **deterministic multi-criteria preference ranking**, not a predictive model. No dimension, profile, weight, threshold or reference choice may be optimised against `drafted`, `pick`, Stage A probability, the Overall Score, the General Board signal, NBA career outcomes or mock drafts. Team Need must never import the board pipeline, and the board's output never enters a Fit Score.
**Rationale:** There is no historical label recording which prospect "correctly fitted" which team, so there is nothing to fit against. Optimising on draft outcomes would silently turn Team Need into a second, worse copy of the General Board — answering the question the board already answers while claiming to answer a different one. The mode's entire purpose is that it **can** rank a lower-Overall prospect first: measured across the seven development classes, Team Need rankings correlate with the Overall Score at only **ρ = 0.18–0.62**, and each archetype surfaces a different prospect at the top (2024: Adem Bona, Overall 58, tops Slasher; Reed Sheppard, Overall 99, tops 3&D).
**Validated instead of accuracy:** internal consistency, temporal stability, position behaviour, redundancy, missingness handling and sensitivity. Enforced by `validate_ml7_team_need.py` check 3, which also confirms that adding a board column to the input frame cannot change a Fit Score.

## DEC-102 — Six factual dimensions on an NCAA peer-percentile scale
**Status:** Accepted
**Decision:** Team Need scores six dimensions — **Shooting · Playmaking · Box-score defensive production · Rebounding · Size · Rim pressure** — each an equal-weight mean of a small non-redundant metric set, expressed as a percentile against the **full NCAA player population of the same season** (filtered to ≥ 200 minutes and ≥ 10 games, retaining 2,941–3,417 players per season). Reference group is decided per dimension: **GLOBAL** for Shooting, Playmaking, Size and Rim pressure; **POSITION** (`position_3`) for Box-score defence and Rebounding.
**Rationale:** Equal weights because the components of a dimension are substitutable evidence for one trait and there is no target from which to derive a split. The per-dimension reference choice is a basketball judgement: shooting means the same at every position (position-relative would erase the signal Stretch Big depends on), while six rebounds means different things for a guard and a centre (PRODUCT.md §8). **No metric appears in two dimensions**, so a user weighting two dimensions never double-counts one statistic — verified by test and by the redundancy audit.
**Documented exclusions:** `ts_pct` (|r| = 0.939 with `efg_pct`, and double-counts free throws), `assist_to_turnover_ratio` (literally the ratio of two components already present), `trb_pct` (a deterministic composite of ORB% and DRB%), `drb_pct` in Defence (belongs to Rebounding; would double-count under custom weighting), `personal_fouls_per_40` (not defensibly directional), layup/dunk/tip attempt shares (they sum to `rim_attempt_share` exactly), and all generic `jump_shot_*` metrics (DEC-068).
**Note:** `position_from_population` remains prohibited; only `position_3` is leakage-safe (DEC-067).

## DEC-103 — Athleticism is UNAVAILABLE and is never proxied
**Status:** Accepted
**Decision:** Athleticism is **not scored**. It is not a dimension, has no proxy, and a custom request with `ATHLETICISM > 0` is **rejected** with an explicit unsupported status — the weight is never silently dropped and never redistributed across the other dimensions. A weight of exactly 0 is permitted. This unblocks only when an approved Combine or physical-testing source is added to DATA.md.
**Rationale:** There is no athleticism measurement in the acquired data — no Combine testing, no vertical leap, no lane agility, no wingspan. Dunk frequency is a **style** signal confounded by position, role and team system, not a vertical leap (ML_SPEC §18.2); the same applies to steals, blocks, height and rim-attempt share. Manufacturing a score from unrelated box-score statistics would be exactly the fabricated rating this project has refused since PRODUCT.md §20. Silent redistribution is rejected separately: it would answer a different question than the one the user asked, without telling them.
**Note:** wingspan and standing reach are likewise never fabricated; Size is height and weight only.

## DEC-104 — Conjunctive archetypes use a geometric mean; eligibility uses coarse position only
**Status:** Accepted
**Decision:** Profiles that **require** all their pillars — 3&D Wing, Rim Protector, Stretch Big, and Shooter (efficiency × volume) — combine them with a **geometric mean**. Single-dimension profiles (Slasher, Playmaker) pass the dimension through. Position eligibility uses `position_3` only: 3&D `∈ {G, F}`, Rim Protector and Stretch Big `∈ {F, C}`. Everyone is scored; out-of-position prospects rank behind eligible ones, and **UNKNOWN counts as eligible**.
**Rationale:** An arithmetic mean allows full compensation — an elite shooter who cannot defend would score as a mid-tier 3&D wing. The geometric mean cannot compensate, which is the correct definition. **Honest sensitivity result:** the choice barely moves the aggregate (rank correlation 0.979–0.993, top-20 overlap 18–20/20), but the disagreement lands exactly where the definition matters — Joey Hauser (shooting 88 / defence 8) scores 26.5 geometric against 47.9 arithmetic. Geometric is retained because it is the correct definition and costs nothing, not because it improved an aggregate. Rim Protector uses the **GLOBAL** block reference rather than the position-relative one, otherwise a 6-foot guard with a good-for-guards block rate would read as elite rim protection.
**UNKNOWN is eligible** because excluding it would penalise missing data, which historically correlates with going undrafted (DEC-071). "3&D Wing" is an archetype name, not evidence of a true NBA wing position — SG vs SF is not inferable from any leakage-safe source.

## DEC-105 — Fit Score is a peer-relative integer 0–100, and missing evidence is never a zero
**Status:** Accepted
**Decision:** Fit Score is the **direct combined peer percentile**, rounded to an integer 0–100 — deliberately **not** re-ranked within the draft class. Custom mode uses `fit_raw = Σ(wᵢ·dᵢ)/Σ(wᵢ)` over requested **and available** dimensions. A missing component is dropped and its dimension renormalises; a dimension is scored only when at least half its components are available; a custom Fit Score is returned only when at least half the requested weight lands on scorable dimensions, and is otherwise **UNAVAILABLE** rather than manufactured.
**Rationale for the scale:** dimension scores are already NCAA peer percentiles, so their combination already carries absolute trait meaning — "72" means "around the 72nd percentile of NCAA peers on the traits you asked for". A second within-class percentile would destroy exactly that, collapsing "92nd percentile three-point volume" into "4th of 49 in this class". This is a deliberate divergence from the Overall Score (DEC-098), which **is** class-relative because a board rank is what that mode means. Neither is a probability; labelling Fit Score a "probability of fit" or "probability of success" is prohibited.
**Rationale for missingness:** filling a missing component with 0 or 50 would make missingness a signal, and missing-data rows were disproportionately undrafted historically (DEC-071) — that is precisely how the outcome would sneak back in. **Reliability minimums** (3P% needs ≥ 20 3PA, FT% ≥ 20 FTA, rim FG% ≥ 20 shot records) treat a thin denominator as MISSING rather than as a real low value; this blanks 3P% for 98 of 887 prospects, because 2-for-4 from three is not evidence.
**Data coverage is reported alongside the score and never inside it** — a prospect is never rewarded or penalised for how much data exists about them. Ties are genuine ties, ordered by the continuous signal before rounding, and are never broken by player name, draft outcome, actual pick or any NBA information.

## DEC-106 — NBA comparables are descriptive resemblance and are never fitted
**Status:** Accepted
**Decision:** NBA comparables state a **statistical resemblance** and nothing more: *"based on his relative statistical profile, this prospect most closely resembles these NBA player profiles."* The claim *"he will become this player"* is prohibited, as are the words **projected · expected career · ceiling · floor · will become**. Approved framing: "Statistical NBA Comparables" / "Similar NBA statistical profiles". No draft outcome, Stage A/B signal, Overall Score, Team Need Fit Score or NBA career result (awards, All-Star selections, BPM, RAPTOR, VORP) may enter the similarity vector or influence the methodology.
**Rationale:** There is no ground-truth "correct comparable" dataset, so there is nothing to fit against; optimising against draft outcomes or later NBA success would answer a different question while claiming to answer this one. Method selection therefore rested on semantic validity, cross-league comparability, stability, coverage and interpretability. `draftlens.comparables` never imports the board, the stages or the Team Need scoring modules, and validator check 4 confirms that adding a board column to the input frame cannot change a comparable.
**Note:** the sole `team_need` dependency is `reference._season_frame`, the shared NCAA season-population builder — it carries no Team Need score, and exists so both sides of a percentile are produced by identical code.

## DEC-107 — The common space is six league-relative role dimensions
**Status:** Accepted
**Decision:** NCAA and NBA profiles are compared in a **six-dimension space** — `SHOOTING_EFFICIENCY` (quality) · `SCORING_ROLE` · `CREATION` · `REBOUNDING` · `DEFENSIVE_ACTIVITY` (role) · `PERIMETER_ORIENTATION` (style) — built from 12 metrics, **equal weight per dimension**, with each side percentile-ranked **within its own league and season** on the **GLOBAL** (not position-relative) reference.
**Rationale:** Raw production is never comparable across leagues — 19 NCAA PPG and 19 NBA PPG are not the same event. Percentile-ranking within each league first is also what makes per-40 rates valid: the 40-vs-48-minute game length, pace and competition differences cancel, because the question asked of both populations is identical. Equal weight **per dimension** prevents shooting's three metrics outvoting creation's one. Only one dimension is higher-is-better: if all six were, an elite prospect would simply match elite NBA players regardless of role — a goodness ranking wearing a similarity costume.
**Cross-league evidence:** the dimension correlation structure reproduces almost exactly in both leagues (REBOUNDING~PERIMETER −0.55/−0.55, REBOUNDING~DEFENSIVE +0.40/+0.42, SHOOTING~PERIMETER +0.35/+0.34), which is real evidence the space measures the same constructs on both sides. No metric appears in two dimensions.
**Position:** ESPN's mixed labels map deterministically and lexically to G/F/C, so position-relative normalisation was genuinely testable — and was **tested and rejected** (retains only 0.86 of 3 names, 29%). It would erase the cross-position resemblance the product exists to surface: a stretch big resembling a wing is a finding, not an error.

## DEC-108 — Rejected cross-league metrics, and why each is unavailable
**Status:** Accepted
**Decision:** The following are **excluded** from the common space rather than approximated: `ast_pct` and `usage_pct` (team-context denominators); `orb_pct`/`drb_pct`/`trb_pct`, `stl_pct`, `blk_pct` (opponent-context denominators); the entire rim-pressure family (`rim_attempt_share`, `rim_make_pct`, unassisted and dunk/layup shares); `height`/`weight`; athleticism; `jump_shot_*`; and all raw per-game production.
**Rationale:** The hoopR NBA source carries player totals and per-game averages only — no team totals, no opponent totals, no shot-level events, no physical measurements. NBA team totals **are** reconstructable by summing players (verified: team minutes sum to 1.008× the expected 19,680, the excess being overtime), but ESPN attributes a traded player's entire season to a single team, which would silently corrupt any team-context denominator. Opponent totals cannot be derived at all without game-level data. Recreating these would produce two metrics sharing a name and not a meaning — the exact failure this project has refused since ML-2.
**Never fabricated:** wingspan, standing reach, height, weight and athleticism have no NBA source and are not invented (ML_SPEC §18.2). Raw per-game production is rejected outright and asserted by a validator check.

## DEC-109 — NBA reference pool: one row per player, recent multi-season, rotation-filtered
**Status:** Accepted
**Decision:** The comparable pool is **exactly one row per unique NBA player**, collapsed on `athlete_id`, built as the **minutes-weighted mean of the player's last 3 qualifying seasons** within a frozen **2021–2025** window, where a qualifying season requires **≥ 750 minutes and ≥ 30 games**. 542 unique players.
**Rationale:** Uniqueness is structural, so the top three can never come back as "Player A 2023, Player A 2024, Player B 2024" — three rows, two people. Collapsing on id rather than name is safe and correct here: audited over 2021–2025, **0 athlete_ids carry more than one name and 0 names map to more than one id**. The latest-season alternative agrees with the selected representation on only **42%** of names — that gap is the single-season noise the multi-season profile removes. Minutes weighting is the honest aggregator: a 2,400-minute season describes a role better than a 780-minute one, and every metric is already a rate. The `CAREER` variant is retained as a **diagnostic only** — averaging a whole career mixes career stages and can manufacture a player who never existed in any single season.
**Eligibility rationale:** 750 minutes ≈ 25 minutes over 30 games. Measured alternatives retain 359–375 (500 min), 306–323 (750 min), 243–266 (1000 min) and 138–190 (1500 min) players per season; the lower bar admits genuinely noisy profiles and the higher one prunes exactly the role players a comparison should surface. Set from the minutes distribution, never from how any prospect's comparables look. **2026 is excluded** from the window.

## DEC-110 — Coverage-normalised Euclidean distance, global-reference similarity score, exactly three unique players
**Status:** Accepted
**Decision:** Similarity is **coverage-normalised Euclidean distance** over dimensions available for both players, requiring **≥ 75% shared coverage** (5 of 6). The product score is `GLOBAL_DISTANCE_PERCENTILE` — the share of a **frozen** reference distribution of prospect-to-NBA distances that is farther than this pairing. Exactly **3 unique** players are returned, closest first, ties broken on exact distance then `athlete_id`.
**Rationale:** Coverage normalisation prevents a prospect missing dimensions from appearing mechanically closer to everyone, which would hand the *least*-measured prospects the most confident comparables. Below the coverage minimum the result is **UNAVAILABLE**; guards are never relaxed to force three names, and a missing dimension is dropped rather than filled with 0, 50 or a league average. **Euclidean** was selected over Manhattan (77% agreement, no advantage) and Cosine (74%): cosine needs centring on the 50th percentile to be meaningful on all-positive percentile vectors, and even centred it is **undefined for a prospect at exactly the 50th percentile on every dimension**, where Euclidean is fine.
**Score rationale:** `WITHIN_POOL_PERCENTILE` was implemented, measured and **rejected as structurally degenerate** — with a pool of 542 the three closest are always the top 0.55%, so it returns 100.00 / 99.82 / 99.63 for *every* prospect, identical whether the nearest match is excellent (distance 8.9) or poor (15.6). The global reference discriminates (Edey 100/98/98 against Mikal Bridges 97/97/96). `100 − 10 × distance` was rejected as an arbitrary constant wearing a percentage sign. The score is **not a probability and not a percentage of shared traits**.
**Self-match:** 283 development prospects also appear in the NBA pool; each is excluded from his own candidate set on the canonical normalised name. Verified 0 self-matches.
**Binding honesty caveat:** the median 3rd-vs-4th margin is **4.0%** of the third distance (minimum 0.00), and dropping any single dimension changes about half the names. **The output is a neighbourhood, not three uniquely correct names**, and the product must present it that way.
