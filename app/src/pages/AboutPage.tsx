import { useEffect } from "react";
import type { ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";
import { useDraftLensData } from "../data/DataProvider";
import { LoadingState, ErrorState } from "../components/DataStates";
import { useOnboarding } from "../onboarding/OnboardingContext";
import styles from "./AboutPage.module.css";

const NAV_SECTIONS = [
  { id: "overview", label: "Overview" },
  { id: "training", label: "Training" },
  { id: "general-board", label: "General Board" },
  { id: "team-need", label: "Team Need" },
  { id: "comparables", label: "Comparables" },
  { id: "validation", label: "Validation" },
  { id: "limitations", label: "Limitations" },
];

export function AboutPage() {
  const { data, error, loading } = useDraftLensData();
  const { start } = useOnboarding();
  const location = useLocation();

  useEffect(() => {
    if (!location.hash) return;
    const el = document.getElementById(location.hash.slice(1));
    el?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [location.hash]);

  if (loading) return <LoadingState />;
  if (error || !data) return <ErrorState message={error ?? "Unknown error"} />;

  const { historical, holdout2026, note } = data.validationSummary;
  const year2026 = data.years["2026"];
  const available = year2026.status === "available" ? year2026 : null;

  return (
    <div className="container">
      <div className={styles.page}>
        <nav className={styles.sideNav} aria-label="Methodology sections">
          {NAV_SECTIONS.map((s) => (
            <Link key={s.id} to={`/methodology#${s.id}`} className={styles.sideNavLink}>
              {s.label}
            </Link>
          ))}
        </nav>

        <div className={styles.content}>
          {/* Overview */}
          <div id="overview" className={styles.intro}>
            <div className={styles.introTop}>
              <h1 className={styles.title}>Methodology</h1>
              <button type="button" className={styles.replayButton} onClick={start}>
                Replay Quick Tour
              </button>
            </div>
            <p className={styles.introKicker}>1. What DraftLens does</p>
            <p className={styles.sub}>
              DraftLens is a <strong>decision-support tool</strong>, not a
              mock-draft predictor. It ranks NCAA prospects using only their
              pre-draft statistical record — no scouting opinion, no mock
              draft, no post-draft information. This page is the complete
              explanation; the Quick Tour above is the 60-second version.
            </p>
            <p className={styles.sub}>
              Three separate questions, three separate tools:{" "}
              <strong>General Board</strong> asks who should be drafted
              highest overall. <strong>Team Need</strong> asks who best
              matches the specific traits a team wants.{" "}
              <strong>NBA Comparables</strong> asks which current NBA players
              a prospect's statistical style resembles. None of the three
              answers the others' question.
            </p>
          </div>

          {/* 2. The data */}
          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>2. The data</h2>
            <p className={styles.body}>
              Every number on this site comes from a prospect's NCAA box
              scores and shot logs — points, rebounds, assists, shooting
              splits, shot location — from public sources (hoopR/ESPN college
              basketball). Nothing is scouted, no video is watched, and no
              external analyst ranking (ESPN, mock drafts, recruiting sites)
              is ever used as an input. Physical measurements are limited to
              height and weight from the same public box-score provider;
              there is no Combine data, so DraftLens does not score
              athleticism at all.
            </p>
            <p className={styles.body}>
              The 2026 board covers the{" "}
              {available?.scoreableDeclaredCount ?? 60} NCAA players who
              initially filed for early entry into the 2026 Draft. That is
              not the same thing as "every player eligible for the 2026
              Draft" — automatically-eligible players (mainly seniors who
              don't need to declare) aren't publicly listed before the draft,
              so a leakage-safe pre-draft population can't be built for them;
              and the official list also included international-only
              players DraftLens has no comparable NCAA data for. Both are
              open limitations, not hidden ones.
            </p>
          </section>

          {/* 3. How DraftLens is trained */}
          <section id="training" className={styles.section}>
            <h2 className={styles.sectionTitle}>3. How DraftLens is trained</h2>
            <p className={styles.body}>
              "Trained" means DraftLens's two statistical models (Draft
              Probability and Draft Order) learned their statistical
              relationships from historical NCAA classes whose Draft outcome
              is already known — 2014 through 2025.
            </p>
            <div className={styles.statRow}>
              <div className={styles.statBox}>
                <span className={styles.statValue}>887</span>
                <span className={styles.statLabel}>NCAA final early entrants, 2014-2025</span>
              </div>
              <div className={styles.statBox}>
                <span className={styles.statValue}>431</span>
                <span className={styles.statLabel}>drafted</span>
              </div>
              <div className={styles.statBox}>
                <span className={styles.statValue}>456</span>
                <span className={styles.statLabel}>undrafted</span>
              </div>
            </div>
            <p className={styles.body}>
              This population is restricted to declared early entrants for a
              specific reason: it's a reproducible pre-draft sampling frame.
              Widening it to "every NCAA player" would let a prospect's
              inclusion be decided by whether they were later drafted — a
              real leak DraftLens found and closed early in development.{" "}
              <strong>This is not a claim that 887 prospects represent every
              NCAA basketball player</strong> — it's the population for whom
              draft-eligibility was knowable before the draft happened.
            </p>
            <p className={styles.body}>
              Validation never mixes future and past seasons. DraftLens uses{" "}
              <strong>forward-in-time (temporal) validation</strong>: train
              on earlier seasons, evaluate on one later, unseen Draft class,
              then move the window forward and repeat. When predicting a
              Draft class, DraftLens only learns from information that would
              have existed before that Draft — the same discipline a real
              scout is under.
            </p>
            <TechnicalDetails summary="Technical details: folds and partitions">
              <p>
                Seven expanding-window folds, each training on 2014 through
                year N-1 and validating on year N, for N = 2019 through 2025.
                No threshold, weight, or hyperparameter is ever selected using
                validation-year data — every choice is made on training years
                only, inside each fold. A separate 2011-2013 partition (125
                prospects) exists purely as a robustness check and never
                influences a selection decision.
              </p>
            </TechnicalDetails>

            <h3 className={styles.subTitle}>What the model uses</h3>
            <ul className={styles.factList}>
              <li>Scoring production (points, shooting volume)</li>
              <li>Shooting efficiency (FG%, 3P%, FT%, eFG%, TS%)</li>
              <li>Shot profile (rim attempts, assisted vs. unassisted makes)</li>
              <li>Playmaking (assist rate, turnover rate)</li>
              <li>Rebounding (offensive and defensive rate)</li>
              <li>Steals and blocks</li>
              <li>Role and playing time (minutes, starts)</li>
              <li>Physical measurements (height, weight)</li>
              <li>Coarse position (guard / forward / center)</li>
            </ul>

            <h3 className={styles.subTitle}>What the model does NOT use</h3>
            <ul className={styles.factList}>
              <li>Mock drafts or consensus big boards</li>
              <li>Scouting grades or public prospect rankings</li>
              <li>Team preferences, interviews, or workouts</li>
              <li>Medical information</li>
              <li>The actual Draft result for the class being predicted</li>
              <li>Future NBA performance of any kind</li>
            </ul>
            <TechnicalDetails summary="Technical details: full feature list">
              <p>
                The frozen feature set (<code>SET_2_BOX_SHOT_PROFILE</code>)
                is 24 engineered statistics: points/reb/ast/stl/blk/turnovers
                per-40, minutes per game, start share, FG%/TS%/eFG%/FT%/3P%,
                3PA rate, FT rate, usage%, height, weight, rim/dunk/layup
                attempt share, rim make%, layup make%, and assisted vs.
                unassisted made-field-goal share. Position enters only as a
                coarse G/F/C/UNKNOWN one-hot — the only leakage-safe position
                source, since finer position labels are available for
                drafted prospects but not undrafted ones.
              </p>
            </TechnicalDetails>
          </section>

          {/* 4. General Draft Board */}
          <section id="general-board" className={styles.section}>
            <h2 className={styles.sectionTitle}>4. General Draft Board</h2>
            <p className={styles.body}>
              The General Board answers one question: among this year's
              prospects, who does the objective pre-draft record support
              most, and how highly? It combines two independent signals:
            </p>
            <FormulaBox
              parts={["Draft Probability", "×", "Draft Order quality"]}
              result="General Board signal"
            />
            <p className={styles.body}>
              A player needs both a profile that looks draftable AND a
              profile associated with stronger Draft positioning — one
              weak ingredient pulls the combined signal down.
            </p>
          </section>

          {/* 5. Draft Probability */}
          <section id="draft-probability" className={styles.section}>
            <h2 className={styles.sectionTitle}>5. Draft Probability</h2>
            <p className={styles.qa}>
              <strong>What is this?</strong> A statistical model's estimate
              of how likely a prospect is to be drafted at all, based only on
              their NCAA production.
            </p>
            <p className={styles.qa}>
              <strong>What information does it use?</strong> Per-40-minute
              production, shooting splits, shot profile, height and weight —
              the same statistics shown on each Prospect page — fitted on 887
              NCAA early entrants from 2014-2025 whose outcome (drafted or
              not) is already known.
            </p>
            <p className={styles.qa}>
              <strong>What does 72% mean?</strong> A 72% Draft Probability
              means the frozen statistical model assigns a 0.72 probability
              of being drafted, calibrated against its validated 2014-2025
              population.
            </p>
            <p className={styles.qa}>
              <strong>What does it NOT mean?</strong> It is not a 72%
              probability of NBA success, and not a projection of career
              outcome — it describes draftability from box-score production
              only.
            </p>
            <h3 className={styles.subTitle}>Why season-relative normalization?</h3>
            <p className={styles.body}>
              NCAA environments change year to year — pace, three-point rate,
              and scoring levels have all shifted meaningfully since 2014.
              Season-relative normalization compares a prospect's statistical
              profile within their own season's environment rather than
              assuming a raw number means the same thing in every year.
            </p>
            <TechnicalDetails summary="Technical details: frozen model configuration">
              <ul className={styles.techList}>
                <li>Model: Logistic Regression</li>
                <li>Training population: 887 historical final NCAA early entrants, 2014-2025</li>
                <li>Target: drafted / not drafted</li>
                <li>Feature set: SET_2_BOX_SHOT_PROFILE</li>
                <li>Representation: season-relative</li>
                <li>Missing-value strategy: training-median imputation</li>
                <li>Position handling: G/F/C/UNKNOWN one-hot</li>
                <li>Class weighting: balanced</li>
                <li>Regularization: C = 0.25</li>
                <li>Calibration: none (uncalibrated)</li>
                <li>
                  Validated macro ROC-AUC: {historical.draftProbabilityMacroAuc.toFixed(4)}{" "}
                  across seven forward-in-time folds (2019-2025)
                </li>
              </ul>
            </TechnicalDetails>
          </section>

          {/* 6. Draft Order */}
          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>6. Draft Order</h2>
            <p className={styles.body}>
              Draft Probability answers "does this profile look draftable?"
              Draft Order asks a different question: "among historically
              drafted profiles, how high did profiles like this tend to go?"
              Two prospects can both look clearly draftable, yet their
              statistical profiles still imply different expected Draft
              positioning.
            </p>
            <p className={styles.body}>
              DraftLens deliberately never shows a literal predicted pick
              number. Historically, that number is only accurate to within
              about 13 picks on a 60-pick draft — close to useless as a
              specific number, even though the underlying ordering is
              genuinely informative.
            </p>
            <h3 className={styles.subTitle}>
              Why use it at all if the exact pick isn't reliable?
            </h3>
            <p className={styles.body}>
              A model can carry useful <em>relative ordering</em> information
              without producing a precise literal number — the same way a
              scout might confidently say "Player A profiles higher than
              Player B" without claiming to know the exact pick either will
              go. DraftLens therefore uses Draft Order only as a ranking/
              quality signal inside the General Board. It never tells a user
              "this player will be selected #17."
            </p>
            <TechnicalDetails summary="Technical details: frozen model configuration">
              <ul className={styles.techList}>
                <li>Model: Ridge Regression, alpha = 10</li>
                <li>Training population: 431 historically drafted prospects, 2014-2025</li>
                <li>Target: actual pick number, training years only</li>
                <li>Representation: standard (not season-relative)</li>
                <li>
                  Validated macro Spearman: {historical.draftOrderMacroSpearman.toFixed(4)}{" "}
                  among drafted prospects, same seven folds
                </li>
                <li>Diagnostic-only MAE: ≈13.2 picks — why the raw number is never shown</li>
              </ul>
            </TechnicalDetails>
          </section>

          {/* 7. How Rank is created */}
          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>7. How Rank is created</h2>
            <p className={styles.body}>How does DraftLens decide Rank #1, #2, #3…?</p>
            <ol className={styles.stepList}>
              <li>Calculate the General Board signal for every prospect in the current board population.</li>
              <li>Sort prospects from highest signal to lowest.</li>
              <li>That ordering becomes the DraftLens Rank — highest signal is Rank #1, second-highest is Rank #2, and so on.</li>
            </ol>
            <p className={styles.body}>
              Rank is therefore always <strong>relative to the current
              prospect pool</strong> — not a fixed, universal position.
            </p>
          </section>

          {/* 8. Overall Score */}
          <section id="overall-score" className={styles.section}>
            <h2 className={styles.sectionTitle}>8. Overall Score</h2>
            <p className={styles.body}>
              Overall Score translates the raw General Board signal into an
              easier 0-100 number, based on where a player sits within the
              current prospect pool:
            </p>
            <FormulaBox
              parts={["round(100 × within-class percentile of General Board signal)"]}
              result="Overall Score"
            />
            <p className={styles.example}>
              <strong>92 / 100</strong> means this player's General Board
              signal sits near the top of this prospect pool — it is{" "}
              <strong>not</strong> a 92% chance of being drafted, not a 92%
              chance of NBA success, and not "92/100 talent."
            </p>
            <p className={styles.body}>
              Because it's class-relative, the same underlying signal can
              produce a different Overall Score in a different-sized or
              different-quality pool — that's expected, not a bug.
            </p>
          </section>

          {/* 9. Comparison card */}
          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>
              9. Draft Probability vs. Rank vs. Overall Score vs. Team Need Fit
            </h2>
            <p className={styles.body}>
              Four different numbers appear across the product. They answer
              four different questions:
            </p>
            <div className={styles.compareGrid}>
              <div className={styles.compareCard}>
                <h3 className={styles.compareTitle}>Draft Probability</h3>
                <p>"What is the estimated probability this NCAA statistical profile gets drafted?"</p>
              </div>
              <div className={styles.compareCard}>
                <h3 className={styles.compareTitle}>General Board Rank</h3>
                <p>"Where does this player sit relative to everyone else in this DraftLens pool?"</p>
              </div>
              <div className={styles.compareCard}>
                <h3 className={styles.compareTitle}>Overall Score</h3>
                <p>"An easier 0-100 representation of that relative General Board position."</p>
              </div>
              <div className={styles.compareCard}>
                <h3 className={styles.compareTitle}>Team Need Fit</h3>
                <p>"How strongly does this profile match a particular basketball need?"</p>
              </div>
            </div>
          </section>

          {/* 10. Why differs */}
          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>
              10. Why doesn't DraftLens simply reproduce the real Draft?
            </h2>
            <p className={styles.body}>
              The NBA Draft isn't determined solely by NCAA statistics. Real
              Draft decisions involve information entirely outside
              DraftLens's data:
            </p>
            <ul className={styles.exclusionGrid}>
              <li>Scouting</li>
              <li>Interviews</li>
              <li>Private workouts</li>
              <li>Medical evaluation</li>
              <li>Team-specific needs</li>
              <li>Roster construction</li>
              <li>Measurements not consistently available</li>
              <li>Trades</li>
              <li>Risk tolerance</li>
              <li>Upside/projection</li>
              <li>International evaluation</li>
              <li>Late-breaking information</li>
            </ul>
            <p className={styles.body}>
              DraftLens deliberately does not try to reverse-engineer any of
              this. A DraftLens rank can differ substantially from the real
              Draft — that alone does not mean the system is wrong.
            </p>
            <h3 className={styles.subTitle}>What the numbers actually show</h3>
            <div className={styles.metricsGrid}>
              <Metric label="Historical Draft Probability macro ROC-AUC" value={historical.draftProbabilityMacroAuc} />
              <Metric label="Historical Draft Order Spearman" value={historical.draftOrderMacroSpearman} />
              <Metric label="Historical General Board binary AUC" value={historical.generalBoardBinaryAuc} />
              <Metric label="Historical General Board graded NDCG" value={historical.generalBoardGradedNdcg} />
            </div>
            <p className={styles.body}>
              In plain language: the model captures meaningful statistical
              signal, but only part of the information real teams use. It's
              a real signal, not a coin flip — and not a replacement for
              scouting either.
            </p>
            {holdout2026 && (
              <p className={styles.techNote}>
                2026 holdout: graded NDCG ≈{" "}
                {holdout2026.generalBoardGradedNdcg?.toFixed(3) ?? "—"}. The
                2026 class's binary classification metrics are not headlined
                here on their own — 25 of the 26 final entrants were drafted,
                leaving only one negative example, so those metrics are
                low-support and descriptive only. Full numbers are in
                Validation below.
              </p>
            )}
          </section>

          {/* 11. Why useful */}
          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>11. Why DraftLens is still useful</h2>
            <p className={styles.body}>
              Differing from consensus isn't framed here as failure — it's
              the point. DraftLens provides:
            </p>
            <ul className={styles.factList}>
              <li><strong>Independent signal</strong> — not trained to copy media consensus.</li>
              <li><strong>Transparency</strong> — every number traces to a statistic you can see.</li>
              <li><strong>Consistency</strong> — every prospect is processed with the same rules.</li>
              <li><strong>A second opinion</strong> — a scout or front office can compare their own assessment against an independent statistical view.</li>
              <li><strong>Outlier discovery</strong> — differences between DraftLens and consensus are interesting investigation targets, not just errors.</li>
              <li><strong>Team-specific exploration</strong> — a prospect ranked lower overall can rank much higher for a specific Team Need.</li>
            </ul>
            <p className={styles.example}>
              DraftLens is an <strong>independent statistical perspective</strong> and a{" "}
              <strong>pre-draft analytical signal</strong> — a decision-support tool, not a claim of objective truth or a "true player ranking."
            </p>
          </section>

          {/* 12. Team Need */}
          <section id="team-need" className={styles.section}>
            <h2 className={styles.sectionTitle}>12. Team Need</h2>
            <div className={styles.contrastGrid}>
              <div className={styles.contrastCard}>
                <h3 className={styles.contrastTitle}>General Board asks:</h3>
                <p>"Who should be drafted highest overall?"</p>
              </div>
              <div className={styles.contrastCard}>
                <h3 className={styles.contrastTitle}>Team Need asks:</h3>
                <p>"Who best matches the basketball traits my team wants?"</p>
              </div>
            </div>
            <p className={styles.body}>
              Team Need has no historical outcome to optimize against — there
              is no "correct" archetype fit to fit a model to. Instead, every
              prospect's statistics are converted into six factual dimensions
              on a 0-100 scale, each one a percentile against the full NCAA
              player population of that season (minimum 200 minutes and 10
              games played, so the comparison group excludes barely-used
              walk-ons):
            </p>
            <ul className={styles.factList}>
              <li>
                <strong>Shooting</strong> — 3P%, 3PA rate, FT%, eFG%, compared
                to the whole NCAA population regardless of position (shooting
                means the same thing everywhere on the floor).
              </li>
              <li>
                <strong>Playmaking</strong> — assist rate and turnover rate
                (turnovers count against the score), compared to the whole
                NCAA population.
              </li>
              <li>
                <strong>Defensive Production</strong> — steal rate and block
                rate, compared only to players at the same coarse position
                (guard / forward / center), since blocks and steals are
                heavily position-dependent. Box-score only — there is no
                matchup or deterrence data, so this is never presented as
                full defensive quality.
              </li>
              <li>
                <strong>Rebounding</strong> — offensive and defensive rebound
                rate, also compared within position.
              </li>
              <li>
                <strong>Size</strong> — height and weight, compared to the
                whole NCAA population (position-relative size would make
                every center look average, which defeats the point).
              </li>
              <li>
                <strong>Rim Pressure</strong> — share of shots at the rim,
                free throw rate, finishing percentage and unassisted-basket
                share, compared to the whole NCAA population. This is a
                shot-diet and finishing measure, not athleticism.
              </li>
            </ul>
            <p className={styles.body}>
              <strong>Athleticism is not one of these dimensions.</strong>{" "}
              There is no Combine data — no vertical leap, no lane agility, no
              wingspan — anywhere in DraftLens's sources, so athleticism is
              never scored, estimated, or approximated from a proxy
              statistic.
            </p>
          </section>

          {/* 13. The six archetypes */}
          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>13. The six archetypes</h2>
            <p className={styles.body}>
              Each predefined archetype combines two or more of the
              dimensions above. The combination method matters: an{" "}
              <strong>arithmetic mean</strong> lets one strong trait
              compensate for a weaker one — right when the traits are
              substitutable evidence for the same thing. A{" "}
              <strong>geometric mean</strong> does not compensate — a
              prospect needs real strength in every ingredient, so one elite
              trait can't fully hide a very weak complementary one. DraftLens
              uses geometric mean specifically where an archetype's
              basketball definition requires both halves together.
            </p>

            <ArchetypeBlock
              name="Shooter"
              meaning="Efficient AND high-volume perimeter shooting — the archetype fails if a prospect only has one half."
              metrics={["3P%", "3-point attempt rate", "FT%", "Effective FG%"]}
              formula={
                <FormulaBox
                  parts={["Efficiency (3P%, FT%, eFG%)", "×", "Volume (3PA rate)"]}
                  result="Shooter score"
                />
              }
              method="GEOMETRIC_MEAN"
              why="A geometric mean requires both: 3P% alone crowns a low-volume specialist, and volume alone crowns an inefficient high-shot-count player."
              highMeaning="A high score means real, high-volume, efficient perimeter shooting — not just a good percentage on a handful of attempts."
            />

            <ArchetypeBlock
              name="Slasher / Rim Attacker"
              meaning="Getting to the rim, drawing contact, finishing, and creating without help."
              metrics={["Rim attempt share", "Free throw rate", "Rim finishing %", "Unassisted basket share"]}
              formula={<FormulaBox parts={["Rim Pressure dimension"]} result="Slasher score" />}
              method="Direct dimension score (already an equal-weight arithmetic mean of its four metrics)"
              why="Rim Pressure already combines shot diet, contact drawing, finishing and self-creation with equal weight — no additional combination is needed."
              highMeaning="A high score means a real rim-oriented scoring style: frequent rim attempts, drawn contact, made finishes, and shots created without an assist."
            />

            <ArchetypeBlock
              name="Playmaker"
              meaning="Creating offense for teammates while taking care of the ball."
              metrics={["Assist rate", "Turnover rate (lower is better)"]}
              formula={<FormulaBox parts={["Playmaking dimension"]} result="Playmaker score" />}
              method="Direct dimension score (arithmetic mean, turnover rate inverted)"
              why="Creation volume and ball security, equally weighted — volume is already built into assist rate, so a low-usage player can't manufacture an elite score from a tiny sample of clean assists."
              highMeaning="A high score means real, high-volume creation without giving the ball away at a high rate."
            />

            <ArchetypeBlock
              name="3&D Wing"
              meaning="Perimeter shooting combined with box-score defensive production — a guard or forward, specifically."
              metrics={["Shooting dimension", "Defensive Production dimension"]}
              formula={
                <FormulaBox
                  parts={["Shooting", "×", "Defensive Production"]}
                  result="3&D score"
                />
              }
              method="GEOMETRIC_MEAN"
              why="Inherently conjunctive: a prospect elite at only one side of the ball is not a 3&D wing. An arithmetic mean would let elite shooting fully cover for weak defensive activity, or vice versa."
              highMeaning="A high score means real strength on both ends, not one elite half compensating for a weak one."
              eligibility="Guards and forwards only. (A '3&D wing' is a role name, not a claim about a prospect's true NBA position — DraftLens can only distinguish guard/forward/center.)"
            />

            <ArchetypeBlock
              name="Rim Protector"
              meaning="Shot-blocking, defensive rebounding and size together — an interior anchor, not just a shot-blocker."
              metrics={["Block rate (league-wide, not position-relative)", "Rebounding dimension", "Size dimension"]}
              formula={
                <FormulaBox
                  parts={["Shot-blocking", "×", "Rebounding", "×", "Size"]}
                  result="Rim Protector score"
                />
              }
              method="GEOMETRIC_MEAN"
              why="Conjunctive across blocking, defensive glass, and size. Shot-blocking is compared to the WHOLE NCAA population here (not just other bigs) — otherwise a 6-foot guard with a good-for-a-guard block rate would misleadingly read as elite rim protection."
              highMeaning="A high score means real interior size, real rebounding, and a real shot-blocking rate — not just one of the three."
              eligibility="Forwards and centers only."
            />

            <ArchetypeBlock
              name="Stretch Big"
              meaning="Frontcourt size combined with genuine perimeter shooting ability."
              metrics={["Shooting dimension", "Size dimension"]}
              formula={<FormulaBox parts={["Shooting", "×", "Size"]} result="Stretch Big score" />}
              method="GEOMETRIC_MEAN"
              why="Must genuinely combine big-man size AND perimeter shooting — a geometric mean stops a small, purely perimeter guard from winning on shooting alone."
              highMeaning="A high score means a big man who can really shoot, not just a tall player or just a good shooter."
              eligibility="Forwards and centers only."
            />

            <p className={styles.techNote}>
              A dimension or pillar with missing data is dropped and the
              score renormalizes over what remains — a missing component is
              never treated as zero. If more than half a conjunctive
              archetype's evidence is missing, the Fit Score is left
              unavailable rather than built from a guess.
            </p>
          </section>

          {/* 14. Custom Team Need */}
          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>14. Custom Team Need</h2>
            <p className={styles.body}>Building your own need, step by step:</p>
            <ol className={styles.stepList}>
              <li>Pick the traits your team values from five approved dimensions: Shooting, Playmaking, Defensive Production, Rebounding, Size.</li>
              <li>Give each trait a weight (0 or higher) using the sliders.</li>
              <li>DraftLens automatically normalizes the weights — you don't need them to add up to 100.</li>
              <li>Each prospect receives a weighted Fit Score from their own dimension scores.</li>
              <li>Missing dimensions for a specific prospect are dropped from THEIR calculation only, using the same coverage rule as the predefined profiles.</li>
            </ol>
            <p className={styles.body}>
              Rim Pressure and Athleticism are not offered as custom sliders
              — Rim Pressure isn't yet an approved custom-mode dimension, and
              Athleticism doesn't exist as a scored dimension at all.
            </p>

            <h3 className={styles.subTitle}>Worked example</h3>
            <p className={styles.body}>A team weights its need as:</p>
            <table className={styles.exampleTable}>
              <tbody>
                <tr><td>Shooting</td><td className={styles.exampleValue}>50</td></tr>
                <tr><td>Playmaking</td><td className={styles.exampleValue}>30</td></tr>
                <tr><td>Defense</td><td className={styles.exampleValue}>20</td></tr>
                <tr><td>Rebounding</td><td className={styles.exampleValue}>0</td></tr>
                <tr><td>Size</td><td className={styles.exampleValue}>0</td></tr>
              </tbody>
            </table>
            <p className={styles.formulaLine}>
              DraftLens computes:{" "}
              <code>(50 × Shooting + 30 × Playmaking + 20 × Defense) / 100</code>
            </p>
            <p className={styles.body}>
              Because weights are relative, <code>50 / 30 / 20</code> and{" "}
              <code>5 / 3 / 2</code> produce identical rankings — only the
              ratio between weights matters, not their absolute size.
            </p>

            <h3 className={styles.subTitle}>How to choose weights</h3>
            <p className={styles.body}>
              This is UX guidance, not a frozen formula — there is no
              analytically "correct" weighting, because weights are your
              team's preference.
            </p>
            <table className={styles.exampleTable}>
              <tbody>
                <tr><td>Primary need</td><td className={styles.exampleValue}>50</td></tr>
                <tr><td>Secondary need</td><td className={styles.exampleValue}>30</td></tr>
                <tr><td>Supporting need</td><td className={styles.exampleValue}>20</td></tr>
                <tr><td>Not important</td><td className={styles.exampleValue}>0</td></tr>
              </tbody>
            </table>
            <p className={styles.techNote}>Example starting point — adjust freely for your own priorities.</p>

            <h3 className={styles.subTitle}>What the result means</h3>
            <p className={styles.body}>
              Like the predefined profiles, a custom Fit Score is directly
              peer-relative on 0-100 — it is a weighted average of dimension
              scores that are already NCAA peer percentiles, so the result
              keeps that same absolute meaning. It is not re-ranked against
              only the prospects you're currently viewing, and it is never a
              probability of anything.
            </p>
          </section>

          {/* 15. NBA Statistical Comparables */}
          <section id="comparables" className={styles.section}>
            <h2 className={styles.sectionTitle}>15. NBA Statistical Comparables</h2>
            <p className={styles.body}>
              Comparables are found in two steps. Height decides{" "}
              <em>who is eligible</em> to be compared; statistics decide{" "}
              <em>who is closest</em>.
            </p>
            <FormulaBox
              parts={["Height plausibility filter", "→", "Six-dimension statistical similarity"]}
              result="Top 3 NBA comparables"
            />
            <p className={styles.body}>
              <strong>Step 1 — height plausibility.</strong> DraftLens first
              restricts the NBA pool to players within a reasonable height
              range of the prospect. The rule is adaptive and fixed in
              advance: start at <strong>±2 inches</strong>; if that leaves
              fewer than three eligible players, widen to ±3 inches, then ±4
              inches; if three still cannot be found, the comparison is
              reported unavailable rather than filled with implausible names.
              An NBA player with no recorded height is never an eligible
              candidate, and a prospect with no recorded height gets no
              comparables — a missing measurement never silently bypasses the
              filter.
            </p>
            <p className={styles.techNote}>
              The ±2-inch starting window was chosen from a coverage audit
              over every scoreable 2026 and 2027 prospect: it already gives
              all 75 at least three candidates (median pool 249 of 542
              players), while ±1 inch leaves the tallest prospect with a
              single candidate. No window was picked by looking at which NBA
              names it produced.
            </p>
            <p className={styles.body}>
              <strong>Step 2 — statistical similarity.</strong> Within that
              physically plausible pool, DraftLens finds the three closest
              profiles using the <em>unchanged</em> six-dimension normalized
              comparison space shared between NCAA and NBA box scores. The
              NBA reference pool is recent, meaningfully-used players
              (2021-2025 seasons, minimum minutes and games).
            </p>
            <p className={styles.body}>
              <strong>Height is a filter, not a similarity dimension.</strong>{" "}
              It never enters the distance calculation, so two candidates who
              both pass the filter are ranked purely on statistical
              resemblance. Sharing a height band does <strong>not</strong>{" "}
              mean two players share a body type, athleticism, or future
              outcome — it only means comparing them is not physically
              absurd.
            </p>
            <p className={styles.body}>
              This is <strong>purely descriptive resemblance</strong>,
              generated without the system ever seeing what a historical
              prospect became — never a projection of a prospect's NBA
              outcome or ceiling. A comparable means "these players occupy a
              similar statistical neighborhood," not "this prospect will
              become this NBA player."
            </p>
            <p className={styles.body}>
              The similarity score is deliberately de-emphasized in the
              product because it compresses toward the 97-100 range by
              construction, so a "97" and a "100" are closer in practice than
              the raw numbers suggest — the ranked order (#1/#2/#3 closest)
              is the meaningful part, not the score.
            </p>
          </section>

          {/* 16. Analyze your own dataset */}
          <section id="analyze-your-own" className={styles.section}>
            <h2 className={styles.sectionTitle}>16. Analyze your own dataset</h2>
            <p className={styles.paragraph}>
              <Link to="/analyze">Analyze Data</Link> runs this same frozen
              methodology on a dataset you supply. Nothing about the models
              changes: the browser loads the fitted Draft Probability, Draft
              Order, Team Need and NBA Comparables parameters exported from
              the Python system and applies them exactly as the built-in board
              does.
            </p>
            <ul className={styles.factList}>
              <li>
                <strong>Formats.</strong> Excel (.xlsx, .xls) or JSON (.json),
                in the strict DraftLens Dataset Format — a two-sheet workbook
                or the equivalent JSON object. The full column reference and
                both templates are on the Analyze Data page.
              </li>
              <li>
                <strong>Counts, never rates.</strong> Every input is a season
                total or a physical measurement. DraftLens computes each
                percentage itself, which is why there is no question of
                whether 41.2 means 41.2% or 0.412.
              </li>
              <li>
                <strong>Your data stays in your browser.</strong> The file is
                parsed and analysed locally. There is no upload, no server and
                no storage — reloading the page discards the session.
              </li>
              <li>
                <strong>Analysis is limited to what the data supports.</strong>{" "}
                Stats work from the totals alone. Basketball Profile, Team
                Need and NBA Comparables need a season DraftLens holds NCAA
                peer references for. Missing optional columns remove specific
                components rather than being filled in.
              </li>
              <li>
                <strong>A General Board requires a compatible population.</strong>{" "}
                Draft Probability and Draft Order were validated on final NCAA
                early entrants. A file declaring any other population gets no
                Draft Probability and no Overall Score, because those numbers
                would not mean what they say — DraftLens says so rather than
                producing a plausible substitute. A draft size is required too,
                since the board converts a predicted slot into utility against
                the size of the draft being entered.
              </li>
              <li>
                <strong>Supported seasons only.</strong> Season-relative
                normalisation and peer percentiles need that season's NCAA
                reference distribution. An unsupported season loses those
                analyses; no neighbouring season is substituted for it.
              </li>
              <li>
                <strong>Pre-draft only.</strong> A column recording a draft
                outcome is rejected outright, not ignored.
              </li>
              <li>
                <strong>Verified against Python.</strong> Before this feature
                shipped, the frozen 2026 inputs were run through the browser
                runtime and compared against the Python system for every
                prospect. Draft Probability, Draft Order, board signal, Team
                Need dimensions and profile scores agree to within 1e-13, and
                board rank, Overall Score, Fit Score, eligibility and the top
                three NBA comparables are identical.
              </li>
            </ul>
          </section>

          {/* 17. Validation */}
          <section id="validation" className={styles.section}>
            <h2 className={styles.sectionTitle}>17. Validation</h2>
            <ul className={styles.factList}>
              <li>Methodology was frozen before the final 2026 replay.</li>
              <li>
                2026 predictions were generated and cryptographically hashed
                before any 2026 prospect-level outcome was opened.
              </li>
              <li>No analytical change was made after the holdout was unsealed.</li>
              <li>
                All validation uses forward-in-time folds — training on
                earlier draft classes and evaluating on a later, unseen one.
                Random splitting is never used, because it would leak future
                information into training.
              </li>
            </ul>
            <p className={styles.disclosure}>
              One aggregate, non-matching 2026 diagnostic figure was briefly
              and incidentally observed while sourcing a structural
              (non-outcome) input during preparation, used nowhere, and is
              recorded in full in the project's validation report.
            </p>

            <div className={styles.metricsGrid}>
              <div className={styles.metricGroup}>
                <h3 className={styles.metricGroupTitle}>Historical (2019–2025)</h3>
                <Metric label="Draft Probability macro ROC-AUC" value={historical.draftProbabilityMacroAuc} />
                <Metric label="Draft Order macro Spearman" value={historical.draftOrderMacroSpearman} />
                <Metric label="General Board binary AUC" value={historical.generalBoardBinaryAuc} />
                <Metric label="General Board graded NDCG" value={historical.generalBoardGradedNdcg} />
              </div>
              {holdout2026 && (
                <div className={styles.metricGroup}>
                  <h3 className={styles.metricGroupTitle}>2026 holdout replay</h3>
                  <Metric label="General Board graded NDCG" value={holdout2026.generalBoardGradedNdcg} />
                  {holdout2026.supportLabel && (
                    <p className={styles.warning}>
                      Draft Probability's 2026 classification metrics have
                      very few undrafted examples (
                      {holdout2026.draftedShare}% of the class was drafted)
                      and are descriptive only —{" "}
                      {holdout2026.supportLabel.toLowerCase()}.
                    </p>
                  )}
                </div>
              )}
            </div>
          </section>

          {/* 17. Limitations */}
          <section id="limitations" className={styles.section}>
            <h2 className={styles.sectionTitle}>17. Limitations</h2>
            <ul className={styles.factList}>
              <li>
                <strong>Draft Order's exact predicted pick is not shown</strong> —
                historical error is about 13 picks on a 60-pick draft. Only
                the ordering is used.
              </li>
              <li>
                <strong>Team Need and NBA Comparables have no ground truth</strong>{" "}
                to validate against — they're checked for consistency,
                stability, and transparency instead of predictive accuracy.
              </li>
              <li>
                <strong>The 2026 board covers declared NCAA early entrants
                only</strong> — not every player technically eligible for the
                draft, and not international-only prospects, for the reasons
                explained in "The data" above.
              </li>
              <li>
                <strong>No workouts, medicals, interviews, or team fit
                information</strong> exist in this data and never will —
                pre-draft NCAA box scores explain a real but limited share of
                Draft outcomes.
              </li>
              <li>
                <strong>The 2027 Watchlist is a media-sourced projection</strong>,
                not an official declaration — see the Watchlist page for
                exactly what is and isn't computed for it.
              </li>
            </ul>
            <p className={styles.note}>{note}</p>
          </section>
        </div>
      </div>
    </div>
  );
}

function TechnicalDetails({ summary, children }: { summary: string; children: ReactNode }) {
  return (
    <details className={styles.techDetails}>
      <summary className={styles.techSummary}>{summary}</summary>
      <div className={styles.techBody}>{children}</div>
    </details>
  );
}

function FormulaBox({ parts, result }: { parts: string[]; result: string }) {
  return (
    <div className={styles.formulaBox}>
      <div className={styles.formulaParts}>
        {parts.map((p, i) => (
          <span key={i} className={i % 2 === 1 ? styles.formulaOperator : styles.formulaTerm}>
            {p}
          </span>
        ))}
      </div>
      <div className={styles.formulaArrow}>↓</div>
      <div className={styles.formulaResult}>{result}</div>
    </div>
  );
}

function ArchetypeBlock({
  name,
  meaning,
  metrics,
  formula,
  method,
  why,
  highMeaning,
  eligibility,
}: {
  name: string;
  meaning: string;
  metrics: string[];
  formula: ReactNode;
  method: string;
  why: string;
  highMeaning: string;
  eligibility?: string;
}) {
  return (
    <div className={styles.archetypeBlock}>
      <h3 className={styles.archetypeName}>{name}</h3>
      <p className={styles.archetypeMeaning}>{meaning}</p>
      {formula}
      <dl className={styles.archetypeDetails}>
        <dt>Metrics used</dt>
        <dd>{metrics.join(", ")}</dd>
        <dt>Combination method</dt>
        <dd>{method}</dd>
        <dt>Why</dt>
        <dd>{why}</dd>
        <dt>A high Fit Score means</dt>
        <dd>{highMeaning}</dd>
        {eligibility && (
          <>
            <dt>Eligibility</dt>
            <dd>{eligibility}</dd>
          </>
        )}
      </dl>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number | null }) {
  return (
    <div className={styles.metric}>
      <span className={styles.metricLabel}>{label}</span>
      <span className={styles.metricValue}>{value?.toFixed(4) ?? "—"}</span>
    </div>
  );
}
