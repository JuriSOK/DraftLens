# DraftLens — Product Definition

**Status:** Approved product definition (pre-development)
**Scope of this document:** Product behavior and product decisions only. No technical, data-source, or modeling decisions are made here.

This document is the authoritative source of truth for DraftLens product behavior. Anything not stated here is undecided. Items marked **TBD** must not be resolved by assumption — they require an explicit product decision recorded in [DECISIONS.md](DECISIONS.md).

---

## 1. Product Summary

DraftLens is a data-driven NBA Draft decision-support tool.

It evaluates NBA Draft prospects using objective pre-draft information and presents two distinct rankings: an overall draft board, and a ranking tailored to a specific scouting need. Every score it produces must be explainable and traceable back to the factual statistics it was derived from.

DraftLens is built for future NBA Draft classes. Historical drafts can be replayed for demonstration and validation, using only information that would have been available before the relevant draft.

This project is being built for the **AQX Sports Analytics Data Bowl 3.0**.

---

## 2. Problem

Draft evaluation depends heavily on subjective judgment and on public consensus boards that are difficult to audit. Scouting departments need a way to interrogate pre-draft data directly: to see which prospects the objective record supports, to rank prospects against a specific need rather than a generic consensus, and to see exactly which measurements and statistics drive a given evaluation.

## 3. Target Users

- NBA scouting departments
- NBA analytics / data teams
- NBA front-office decision makers

## 4. Core Decision

DraftLens exists to answer one question:

> Among the prospects in an upcoming NBA Draft class, which players are the strongest prospects overall, and which players best match a specific scouting need?

### What DraftLens is not

DraftLens is explicitly **not**:

- a mock draft generator
- a draft lottery simulator
- a video-game-style player rating system
- a system claiming to predict exact NBA careers
- a generative-AI scouting chatbot

The product must remain analytical, explainable, fact-based, reproducible where possible, and useful for scouting decisions.

---

## 5. Scope

### Prospect scope (MVP)

- DraftLens focuses on **NCAA prospects**.
- International prospects are **out of scope for the MVP**. They may be added in a future version.

### Eligibility for future draft classes

- Before an official NBA Draft candidate list exists for a given class, DraftLens may maintain its own tracked prospect list.
- Once an official NBA Draft candidate list exists, **that list becomes the authoritative eligibility list**.

### Time orientation

- DraftLens is designed for **future** NBA Draft classes.
- Historical drafts may be replayed for demonstration and validation, strictly using pre-draft information (see §15).
- The **2026 NBA Draft** is the proposed primary demonstration / backtesting case.

---

## 6. General Draft Board (Mode A)

**Purpose:** rank all prospects by overall pre-draft quality, using objective data available before the draft.

Conceptual output:

```
1. Prospect A — 91/100
2. Prospect B — 88/100
3. Prospect C — 86/100
```

The user should eventually be able to:

- view all prospects available in the selected dataset
- filter by position (PG, SG, SF, PF, C)
- search for a prospect by name
- open a prospect detail page

### Methodology

**TBD.** The methodology that produces the General Draft Board score is **not decided**. No formula is to be invented. The final methodology must be selected on the basis of historical validation / backtesting (see §14, §15) and specified in [ML_SPEC.md](ML_SPEC.md).

---

## 7. Team Need Mode (Mode B)

**Purpose:** rank prospects according to the type of player or statistical profile a scouting team is specifically looking for.

DraftLens has **two distinct ranking modes**. Mode A and Mode B are **not blended through a general "overall vs fit" slider**.

Team Need mode accepts the user's need in two ways: a **profile-based** ranking and a **custom criteria** ranking.

### 7.1 Profile-based team need

Potential modern basketball profiles:

- Shooter
- Slasher / Rim Attacker
- Playmaker
- 3&D Wing
- Point-of-Attack Defender
- Rim Protector
- Stretch Big
- Rim Runner / Interior Finisher

These must **not** be arbitrary labels. Each profile must correspond to a transparent combination of measurable basketball statistics and physical characteristics. For example, a "Shooter" profile should depend on several factual shooting indicators rather than a manually assigned tag.

The metrics, formulas, normalization methods, and weights behind each profile are **TBD**. They must be researched and justified before implementation.

If the implementation remains simple and understandable, the user may eventually combine a **maximum of two** player profiles. This is not to be implemented yet.

### 7.2 Custom team need

Custom ranking should eventually support two levels.

**Simple mode** — the user adjusts the relative importance of broad dimensions:

- Shooting
- Playmaking
- Defense
- Rebounding
- Athleticism
- Size

**Advanced mode** — the user may inspect or adjust more specific measurable statistics. Potential examples (**not a final list**): 3P%, 3-point volume, FT%, TS%, AST%, TOV%, STL%, BLK%, height, wingspan, vertical jump, agility.

The exact feature set is **TBD** and depends on which reliable data is available. The experience must remain understandable and must not become unnecessarily complex.

### 7.3 Recommendation output

Team Need mode should explicitly recommend the best-fitting prospects, e.g.:

```
#1 Recommended Prospect
Fit Score: 92/100
```

The ranking must remain data-driven. See §16 for the explainability requirement attached to this mode.

---

## 8. Position Handling

DraftLens uses traditional positions:

- PG
- SG
- SF
- PF
- C

Where statistically appropriate, measurements and performance should be interpreted **relative to position**. For example:

- 6 rebounds per game does not mean the same thing for a PG and a C.
- A given height may be excellent for a PG and poor for a PF.
- Wingspan expectations differ by position.

Position-aware normalization should therefore be investigated. The exact methodology is **TBD**.

---

## 9. Prospect Scoring

Each prospect should eventually have:

- an **Overall Score out of 100** in General Draft Board mode
- useful analytical **sub-scores**, where those sub-scores can be grounded in factual data

Potential sub-score families (conceptual categories, not final definitions):

- Shooting
- Playmaking
- Defense
- Rebounding
- Athleticism
- Physical Profile / Size

Final formulas and weights are **TBD**.

Scores must never exist only for visual appeal. Every score must eventually be:

- reproducible
- explainable
- linked to documented metrics
- statistically justified where possible

---

## 10. Prospect Detail Page

The prospect detail page should behave like a professional scouting / analytics page. It must **not** look like a video-game player card.

Potential content:

- name
- college
- age
- position
- physical measurements
- latest NCAA season statistics
- advanced NCAA statistics
- NBA Draft Combine data when available
- overall score
- relevant sub-scores
- player-profile fit
- strengths
- weaknesses
- data coverage
- NBA statistical comparables
- raw statistics supporting derived scores

**Raw statistics must remain visible.** A scout should be able to understand what a score is based on, rather than only seeing proprietary-looking numbers.

Layout, visual design, and the final field list are **TBD**.

---

## 11. Data Principles

### NCAA representation

A prospect's main NCAA performance representation is the **latest NCAA season**. Full collegiate career aggregates must not be used as the primary representation.

### Potential factual inputs

As much reliable data as is reasonably available, potentially including:

- traditional box-score statistics
- advanced statistics
- age
- position
- height
- weight
- wingspan
- physical measurements
- NBA Draft Combine measurements
- NBA Draft Combine drills
- other objective pre-draft information

The exact datasets and feature list are **not selected**. No particular data source is assumed. Missing information must not be fabricated. See [DATA.md](DATA.md).

### Age

Age is an objective pre-draft feature and should be considered as potentially useful. Its influence must **not** be manually assumed; its relevance is to be evaluated using historical data.

### External scout rankings

The following must **not** be used as primary model input features:

- ESPN rankings
- The Athletic rankings
- public mock drafts
- consensus draft boards
- analyst rankings

DraftLens produces an independent, data-driven evaluation. Public rankings may later be used **only** as external benchmarks for comparison.

---

## 12. Missing Data

A prospect must **not** be automatically excluded because they did not participate in the NBA Draft Combine, or because some measurements are unavailable. Players with incomplete data remain eligible for analysis whenever statistically reasonable.

DraftLens should eventually display data completeness clearly. Conceptual example:

```
Data Coverage: 82%

Available:
- NCAA statistics
- advanced statistics
- height
- weight

Missing:
- vertical jump
- lane agility
```

The method for missing-value handling, imputation, and model behavior with incomplete records is **TBD**.

---

## 13. NBA Statistical Comparables

Each prospect should eventually have **exactly three** NBA statistical / style comparables.

The intended question:

> Which current or historical NBA players have a statistical profile most similar to this NCAA prospect?

The comparison is between the prospect's **current NCAA statistical profile** and the **NBA statistical profiles of actual NBA players**. This is not primarily a pre-draft-to-pre-draft historical comparison.

Raw NCAA and NBA statistics must **not** be treated as if they came from the same statistical environment — 19 PPG in NCAA is not equivalent to 19 PPG in the NBA. The methodology should investigate statistically defensible transformations such as percentiles, standardized values, position-relative values, usage-adjusted dimensions, efficiency dimensions, role/style dimensions, pace/context adjustments, or other normalized representations. The exact methodology is **TBD**.

Conceptual output:

```
NBA Statistical Comparables

1. NBA Player A — 89% statistical similarity
2. NBA Player B — 85%
3. NBA Player C — 81%
```

The application must clearly communicate that **statistical / style similarity does not mean the prospect is predicted to have the same NBA career**. The comparison is descriptive, not a career-outcome guarantee.

---

## 14. Historical Ground Truth

For the General Draft Board, the primary historical target is the **actual NBA Draft order**.

This does not imply that actual draft order is a perfect measure of future NBA player quality. It is used because it is an objective, observable historical outcome.

The analytical question is roughly:

> Using only information available before each historical draft, how well can pre-draft data explain or reproduce where prospects were selected?

Undrafted players must also be considered where the methodology requires them.

---

## 15. Temporal Validation

Historical evaluation must strictly avoid future-information leakage.

Principle:

```
Train on older drafts
→ evaluate on a later unseen draft
→ move the cutoff forward
→ evaluate again
```

For example: train through year N, test on draft N+1; then train through N+1, test on N+2.

**Information that occurred after the draft being evaluated must never be used.**

The exact validation strategy is **TBD**.

### Backtesting / demonstration

For hackathon demonstration, DraftLens should be capable of replaying a historical draft as though it had not yet happened:

1. Train / design using information from earlier drafts.
2. Freeze the methodology.
3. Provide only pre-draft information for the target class.
4. Generate the DraftLens ranking.
5. Compare it against the actual draft outcome.

The 2026 NBA Draft is the proposed primary demonstration case. The exact train/test years and methodology are **TBD**.

---

## 16. Explainability

DraftLens should eventually explain **why one prospect ranks above another**. Conceptual example:

```
Why Prospect A over Prospect B?

+ stronger three-point volume
+ higher defensive score for position
+ greater wingspan
- Prospect B provides stronger playmaking
```

This explanation should preferably be generated **deterministically** from the underlying statistics, normalized dimensions, and scoring logic.

A paid generative AI API must **not** be required for the MVP. Generative AI is not currently required by any part of the product.

---

## 17. Search and Filtering

The General Draft Board should eventually contain all prospects available in the selected dataset. Users should be able to:

- search prospects by name
- view all prospects
- filter by PG, SG, SF, PF, C

---

## 18. MVP Boundaries

MVP scope is **NOT YET DEFINED**. It will be established in a dedicated product-design step and recorded in [MVP.md](MVP.md).

What is already fixed about the MVP:

- NCAA prospects only; international prospects deferred.
- Two distinct ranking modes, not blended by a single slider.
- No required generative AI dependency.

---

## 19. Out of Scope

For the initial MVP, do not assume support for:

- international prospects
- exact mock draft prediction from pick #1 to #60
- team-specific roster analysis
- automatic NBA team need detection
- trades
- lottery simulation
- scouting video analysis
- computer vision
- career outcome prediction
- injury prediction
- live NBA integration
- autonomous AI agents
- paid generative AI APIs
- generative scouting reports

These can only be reconsidered later through an explicit product decision recorded in [DECISIONS.md](DECISIONS.md).

---

## 20. Product Principles

**Data before AI.** The quality of the data and analysis matters more than AI branding.

**Explainability.** Users should understand why players rank where they do.

**No fabricated data.** Unknown data remains unknown unless handled by an explicitly documented statistical method.

**Decision support.** DraftLens supports scouts and analysts. It does not claim certainty.

**Reproducibility.** Data processing and model evaluation should be reproducible wherever licensing allows.

**Honest evaluation.** Do not select models or results simply because they look impressive in a demo.

**Professional interface.** The product should look like a professional analytics / scouting tool, not a game.

**Raw data visibility.** Derived scores must not hide the factual statistics they originate from.

**Keep complexity justified.** Do not add features unless they materially improve scouting usefulness, analytical credibility, explainability, or hackathon presentation.

---

## 21. Open Questions

All of the following are **TBD** and must not be resolved by assumption:

**Product**
- MVP scope and feature cut ([MVP.md](MVP.md))
- Whether combining two player profiles is included, and how combination behaves
- Final field list and layout of the prospect detail page
- How strengths / weaknesses are derived and presented
- How data coverage is computed and displayed
- How the tracked prospect list is maintained before an official candidate list exists

**Data** ([DATA.md](DATA.md))
- Which datasets and sources are used, and under what licensing
- Final feature list
- Historical coverage window
- Entity matching between NCAA, Combine, draft, and NBA records

**ML / methodology** ([ML_SPEC.md](ML_SPEC.md))
- General Draft Board scoring methodology
- Definition of each player profile in measurable terms
- Sub-score definitions and weights
- Position normalization method
- NCAA→NBA normalization and similarity methodology
- Missing-value handling and imputation
- Temporal validation strategy, evaluation metrics, and baselines
- Whether and how age contributes

**Architecture** ([ARCHITECTURE.md](ARCHITECTURE.md))
- All technical stack decisions
