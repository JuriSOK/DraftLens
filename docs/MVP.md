# DraftLens — MVP Scope

**Status:** Approved
**Scope of this document:** What the hackathon MVP must deliver, in what order, and what it explicitly excludes.

This document is the authoritative MVP scope for DraftLens. It operates inside [PRODUCT.md](PRODUCT.md), which remains the source of truth for product behavior — where this document is silent, PRODUCT.md governs. Items marked **TBD** must not be resolved by assumption; they require an explicit decision recorded in [DECISIONS.md](DECISIONS.md).

Nothing here selects a dataset, a methodology, an algorithm, or a technology stack. Those remain open by design.

---

## 1. Purpose

To define the minimum product that demonstrates DraftLens can support a real scouting decision using objective basketball data — and to fix the order in which that product gets built if hackathon time runs short.

## 2. MVP Goal

The MVP must demonstrate that DraftLens can support a real scouting decision using objective basketball data.

The core user question it answers:

> Among the prospects in this draft class, who should I prioritize overall, or who best fits the type of player I am looking for?

## 3. User Journey

The MVP delivers one continuous path:

```
Landing page
  → General Draft Board  → browse / search / filter → prospect detail page
  → Team Need mode       → pick a profile OR set weighted criteria
                         → ranked recommendations with fit scores
                         → understand why #1 ranks above #2
```

Supporting this, and documented outside the application: Python backtesting that validates the General Draft Board methodology on historical drafts.

## 4. Landing Experience

The application begins with a lightweight DraftLens landing / home experience that introduces the product briefly and provides access to the two core modes:

1. General Draft Board
2. Team Need

The landing page must remain **minimal**. It is not a marketing-heavy website. The analytics product is the priority.

## 5. General Draft Board — REQUIRED

A core MVP feature. It must display **all prospects in the approved in-scope prospect population for the selected board** — never a filtered or truncated subset of it.

For the historical ML methodology and the 2026 replay, that in-scope population is **final NCAA early entrants** ([ML_SPEC.md](ML_SPEC.md) §3), so the 2026 board ranks **26 prospects**. The board must **not** be expanded with seniors known to have been drafted only after the fact — that would let post-draft information decide who appears on a pre-draft board. Broader players could later be shown as clearly-labelled *unranked contextual* records; that is not implemented and is not in MVP scope.

Required capabilities:

- rank all prospects
- display an **Overall Score out of 100**
- search prospects by name
- filter by position: PG, SG, SF, PF, C
- open the detail page of a prospect

It answers: *"Who are the strongest prospects overall according to DraftLens?"*

**Score methodology: TBD.** It must be selected through data analysis and historical validation, and specified in [ML_SPEC.md](ML_SPEC.md). No formula is defined in this document.

## 6. Team Need Mode — REQUIRED

The second core MVP mode. It ranks prospects according to a specific scouting need.

The MVP supports **both** entry paths:

- **A. Predefined player profiles** (§7)
- **B. Custom weighted criteria** (§8)

### Output — REQUIRED

Team Need mode produces an explicit recommendation ranking. Conceptual form:

```
#1 Recommended Prospect
Fit Score: 92/100

#2 Prospect B
Fit Score: 88/100

#3 Prospect C
Fit Score: 84/100
```

The user must be able to understand why the first prospect ranks above the alternatives — see §11.

## 7. Predefined Profiles

The MVP targets these six profiles:

- Shooter
- Slasher / Rim Attacker
- Playmaker
- 3&D Wing
- Rim Protector
- Stretch Big

These are MVP targets **only if they can be defined using reliable and measurable data**. They must never be manually assigned labels; each must be derived from factual basketball metrics.

The exact statistics, transformations, weights, and formulas are **TBD** and must be justified in [DATA.md](DATA.md) and/or [ML_SPEC.md](ML_SPEC.md).

**Constraint:** the MVP supports **one selected predefined profile at a time**. Combinations of multiple predefined profiles are not implemented in the MVP; they may be reconsidered after the hackathon if useful.

> Note: [PRODUCT.md](PRODUCT.md) §7.1 lists eight potential profiles. The MVP targets six of them. Point-of-Attack Defender and Rim Runner / Interior Finisher remain valid product concepts but are not MVP targets.

## 8. Custom Criteria — REQUIRED

Custom Team Need ranking is required.

### Simple mode — the priority

The user adjusts the relative importance of broad dimensions:

- Shooting
- Playmaking
- Defense
- Rebounding
- Athleticism
- Size

The user must be able to change how much each dimension matters. **This simple weighted experience is the priority of §8.**

### Advanced view — optional for the MVP

A more detailed view may expose the underlying factual statistics, *if* it can be implemented without making the MVP unnecessarily complex. Possible examples: 3P%, 3-point volume, FT%, TS%, AST%, TOV%, STL%, BLK%, height, wingspan, vertical jump, agility.

The advanced feature list is **TBD** and depends on actual data availability.

## 9. Prospect Detail Page — REQUIRED

Every prospect must have a useful analytical profile page. It must look like a professional scouting / data page, **not** a video-game card.

Required MVP information, **where data is available**:

- player name
- college
- age
- position
- physical measurements
- latest NCAA season statistics
- advanced NCAA statistics
- NBA Draft Combine data when available
- Overall Score
- useful sub-scores
- data coverage / completeness
- three NBA statistical comparables
- raw factual statistics supporting derived scores
- strengths
- weaknesses

**Strengths and weaknesses must be derived from factual metrics or score components.** Subjective scouting claims without supporting data must not be produced.

### Sub-scores

Useful sub-scores are part of the MVP **if they can be statistically justified**. Potential dimensions: Shooting, Playmaking, Defense, Rebounding, Athleticism, Physical Profile / Size.

Every displayed score must correspond to measurable inputs. No arbitrary game-like ratings. The exact formulas remain **TBD**.

## 10. NBA Statistical Comparables — REQUIRED

A required MVP feature, not an optional bonus.

Each prospect displays **exactly three** NBA statistical / style comparables.

The comparison concept: the prospect's **current NCAA statistical profile** against **actual NBA players' statistical profiles**. Raw NCAA and NBA statistics must not simply be compared directly — a normalization or transformation methodology must be defined later. Potential future approaches include percentiles, z-scores, position-relative values, role/style dimensions, usage-adjusted metrics, and efficiency dimensions. **The final methodology is TBD and is not selected in this document.**

The feature answers: *"Which NBA players does this prospect's current statistical style/profile most resemble?"*

The application must clearly state that similarity is **descriptive** and does **not** predict the same NBA career.

## 11. Explainability

The user must be able to understand why one recommended prospect ranks above another. DraftLens should support deterministic explanations of this form:

```
Why Prospect A over Prospect B?

+ stronger three-point volume
+ better defensive profile for position
+ greater wingspan
- Prospect B provides stronger playmaking
```

Explanations must come from the underlying factual data and scoring logic. **Generative AI must not be required for this feature.**

## 12. Data Coverage — REQUIRED

Prospects with incomplete Combine or physical data must **not** automatically disappear from the product.

The prospect page must visibly communicate data completeness. Conceptual form:

```
Data Coverage: 82%

Available:
- NCAA stats
- advanced stats
- height
- weight

Missing:
- vertical jump
- lane agility
```

The exact data coverage formula is **TBD**.

## 13. Demonstration Draft

DraftLens is designed for **future** NBA Draft classes. However, as of the hackathon period, the future draft class does not yet have complete pre-draft data.

The primary hackathon demonstration therefore uses the **2026 NBA Draft as a historical replay**:

1. Use only data that would have been available before the 2026 NBA Draft.
2. Apply a methodology developed using earlier historical data.
3. Generate the DraftLens 2026 rankings.
4. Compare the generated ranking against the actual 2026 NBA Draft order.

**Product positioning remains future-facing.** The 2026 draft is used to prove and demonstrate the methodology, not to reposition DraftLens as a historical tool.

## 14. Backtesting Requirement — REQUIRED

Historical validation is mandatory.

**Implementation constraint (approved):** all backtesting and historical model validation **must be performed in Python**. Specific Python libraries are **not** chosen yet.

The validation methodology is **TBD**, but it must respect time ordering:

```
Train on older drafts
→ test on a later unseen draft
→ move the cutoff forward
→ repeat
```

**No future-information leakage is allowed** — see [PRODUCT.md](PRODUCT.md) §15 and [CLAUDE.md](../CLAUDE.md) rules 8–9.

### Where results live

Backtest results do **not** need a dedicated application page in the MVP. For the hackathon, validation results are documented primarily in:

- README.md
- the Devpost submission
- supporting charts / figures where appropriate

The application itself prioritizes the scouting workflow.

## 15. MVP Data Scope

- The MVP focuses on **NCAA prospects**. International prospect support is not required for the hackathon MVP.
- The **latest NCAA season** is the primary college performance representation.
- The project should eventually use as much reliable objective pre-draft information as is reasonably available. Potential categories: box-score statistics, advanced NCAA statistics, age, position, height, weight, wingspan, Combine measurements, Combine drills, and other reliable objective pre-draft information.

**No dataset has been approved.** Dataset research and selection happen in the next project phase (§19). No source is named as selected in this document.

## 16. Priority Order

If hackathon time becomes constrained, prioritize in this order:

1. General Draft Board
2. Team Need mode
3. Prospect detail page
4. Explainability
5. NBA statistical comparables
6. Backtesting / validation presentation
7. Visual polish

**This is an implementation priority guide, not an optionality ranking.** Later items are not optional by default — NBA comparables and historical validation remain part of the intended MVP.

## 17. Definition of Success

The MVP is successful if a user can:

1. enter DraftLens through a lightweight landing page;
2. open the General Draft Board;
3. browse / search / filter the draft class;
4. see an overall ranking supported by documented methodology;
5. open a prospect profile and inspect both raw and derived data;
6. see exactly three NBA statistical comparables;
7. switch to Team Need mode;
8. select a player profile **or** configure weighted needs;
9. receive a ranked list of recommended prospects;
10. understand why one recommended prospect ranks above another;
11. trust that missing data is clearly disclosed;
12. review documented Python backtesting showing historical validation of the General Draft Board methodology.

## 18. Out of Scope

Not included in the hackathon MVP unless an explicit later decision changes scope:

- international prospects
- automatic team roster analysis
- team-specific need detection
- mock draft pick-by-pick simulation
- lottery simulation
- trades
- scouting video analysis
- computer vision
- injury prediction
- NBA career prediction
- autonomous AI agents
- generative scouting reports
- paid generative AI APIs
- combining multiple predefined player profiles
- a dedicated backtest / validation page inside the application

This list is **additive to** [PRODUCT.md](PRODUCT.md) §19 — everything excluded there remains excluded here.

## 19. Dependencies / Next Phase

**The next mandatory project phase is dataset research and validation.** It must investigate reliable sources for:

- NCAA player statistics
- advanced NCAA statistics
- NBA Draft historical outcomes
- NBA Draft Combine data
- NBA player statistics for statistical comparables
- age / physical measurements where available

The resulting [DATA.md](DATA.md) work must evaluate each candidate source on:

- reliability
- historical coverage
- availability for the 2026 replay
- update frequency
- licensing / terms of use
- accessibility
- entity matching feasibility
- missing-data coverage
- reproducibility

**No model implementation may begin until the minimum viable data sources are known.**

## 20. Remaining TBDs

Everything below is unresolved. None of it may be filled in by assumption.

**Data** ([DATA.md](DATA.md)) — all of it: sources, licensing, final feature list, historical coverage window, entity matching, availability of 2026 pre-draft data.

**Methodology** ([ML_SPEC.md](ML_SPEC.md))
- General Draft Board Overall Score methodology
- measurable definition of each of the six MVP profiles
- sub-score definitions, inputs, and weights
- custom-criteria weighting mechanics (how user weights map to a fit score)
- position normalization method
- NCAA→NBA transformation and similarity metric for comparables
- missing-value handling and imputation
- data coverage formula
- how strengths / weaknesses are derived from score components
- how deterministic pairwise explanations are generated
- temporal validation strategy: cutoff years, folds, metrics, baselines
- specific Python libraries for backtesting

**Product**
- whether the advanced custom-criteria view ships in the MVP
- final field list and layout of the prospect detail page
- how the 2026 prospect list is assembled and frozen as a pre-draft snapshot

**Architecture** ([ARCHITECTURE.md](ARCHITECTURE.md)) — the entire application stack. Python is fixed for backtesting only; it implies nothing about the application.
