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
**Note:** Implements DEC-049/DEC-050. Population counts are enforced as hard build gates — **corrected in ML-0.1 (DEC-063) to 2014–2025: 887/431/456; 2011–2013: 125/85/40; 2026: 26**. The original 829/403/426 and 119/79/40 came from a defective NCAA classifier and are not authoritative and re-asserted by `scripts/validate_model_dataset.py` and the test suite. See [ML0_REPORT.md](ML0_REPORT.md).

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
**Decision:** Where deterministic matching cannot resolve a genuine name variant, the mapping is recorded in [`config/identity_overrides.csv`](../config/identity_overrides.csv) with prospect, year, expected school, selected `athlete_id`, and a written reason. Overrides must never be hidden in Python conditionals, and a match must never be invented.
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
**Decision:** The canonical analytical position is the **coarse G / F / C scheme**, derived deterministically from `hoopr_position` by [`scripts/positions.py`](../scripts/positions.py) using [`config/position_map.csv`](../config/position_map.csv). Measured coverage: **98.0%** development, **100%** for the 2026 holdout. Unresolvable labels (`ATH`, `NA`, missing) stay `UNKNOWN` and are never guessed.

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
**Decision:** No feature may be derived from the generic `jump_shot_*` primitives — specifically `jump_shot_share`, `jump_shot_pct` and `jump_shots_per_40` are prohibited. The rejection is recorded in [`config/ml2_feature_dictionary.csv`](../config/ml2_feature_dictionary.csv) with status `REJECTED`, and a test fails if any column containing `jump_shot` reaches the feature layer.
**Rationale:** DEC-068 — hoopR's `type_text` folds `Three Point Jump Shot` into `JumpShot` from 2021, so the category silently changes meaning mid-window. Shot profile is built instead from `layup`, `dunk`, `tip` and three-point attempts identified via `score_value`, all of which are stable across 2014–2026.
**Note:** The raw ML-0 columns remain for source and audit purposes.

## DEC-071 — Unresolved prospects are retained, never outcome-selectively dropped
**Status:** Accepted
**Decision:** Prospects without matched hoopR statistics remain in every analytical partition with NULL feature values. They must not be dropped, zero-filled, or flagged with a `has_stats`-style predictive feature, and no missingness indicator may be derived from their absence.
**Rationale:** All 8 unresolved development prospects are undrafted (ML1_REPORT §11). Dropping rows without statistics would remove only negatives and inflate downstream performance. Validation hard-fails if the retained count falls below 8 or if the ML-2 prospect set differs from ML-0.

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
**Decision:** Where ML-2 features are near-duplicates (|r| ≥ 0.95), one representative per group is retained using a fixed rule recorded in [`config/ml3_baselines.json`](../config/ml3_baselines.json): prefer the **per-40 rate** for counting statistics; keep the **unassisted** direction of algebraic complements; keep **`three_point_attempt_rate`** for attempt mix; keep a possession percentage only where it has no per-40 twin (`usage_pct`, `tov_pct`).
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
