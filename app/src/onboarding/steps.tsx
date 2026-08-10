import type { ReactNode } from "react";
import styles from "./OnboardingTour.module.css";

export interface OnboardingStep {
  title: string;
  body: ReactNode;
}

/** The ONE source of onboarding content — used by both the Landing page's
 * "Get Started" flow and Methodology's "Replay Quick Tour" button. Five
 * steps, each readable in a few seconds. Every concept here is explained in
 * full on the Methodology page; skipping loses no information. */
export const ONBOARDING_STEPS: OnboardingStep[] = [
  {
    title: "What is DraftLens?",
    body: (
      <p>
        DraftLens is an independent NCAA pre-draft analytics tool. It doesn't
        try to copy mock drafts — it uses player statistics and historical
        Draft outcomes to build a data-driven view of prospects.
      </p>
    ),
  },
  {
    title: "How the General Board works",
    body: (
      <>
        <div className={styles.flow}>
          <span className={styles.flowNode}>NCAA Stats</span>
          <span className={styles.flowArrow}>↓</span>
          <div className={styles.flowRow}>
            <span className={styles.flowNode}>Draft Probability</span>
            <span className={styles.flowNode}>Draft Order</span>
          </div>
          <span className={styles.flowArrow}>↓</span>
          <span className={styles.flowNodeStrong}>General Board</span>
          <span className={styles.flowArrow}>↓</span>
          <div className={styles.flowRow}>
            <span className={styles.flowNode}>Board Rank</span>
            <span className={styles.flowNode}>Overall Score</span>
          </div>
        </div>
        <ul className={styles.stepList}>
          <li>
            <strong>Draft Probability</strong> — how draftable the prospect's
            NCAA statistical profile looks compared with historical early
            entrants.
          </li>
          <li>
            <strong>Draft Order</strong> — a secondary signal estimating
            where a drafted statistical profile tends to sit within the
            Draft.
          </li>
          <li>
            <strong>General Board</strong> — combines both signals into
            DraftLens's overall prospect ranking.
          </li>
          <li>
            <strong>Overall Score</strong> — a 0-100 class-relative
            presentation of that General Board signal.
          </li>
        </ul>
      </>
    ),
  },
  {
    title: "Team Need",
    body: (
      <>
        <div className={styles.contrastRow}>
          <div className={styles.contrastCard}>
            <span className={styles.contrastLabel}>General Board asks</span>
            <p>"Who ranks highest overall?"</p>
          </div>
          <div className={styles.contrastCard}>
            <span className={styles.contrastLabel}>Team Need asks</span>
            <p>"Who best matches what my team needs?"</p>
          </div>
        </div>
        <p>
          Choose a predefined basketball archetype, or build your own
          weighted need:
        </p>
        <div className={styles.weightExample}>
          <span>Shooting 50</span>
          <span>Playmaking 30</span>
          <span>Defense 20</span>
          <span className={styles.weightArrow}>→</span>
          <span className={styles.weightResult}>Custom Fit ranking</span>
        </div>
      </>
    ),
  },
  {
    title: "Stats + Comparables",
    body: (
      <ul className={styles.stepList}>
        <li>
          <strong>Stats</strong> — rank prospects directly by NCAA production:
          points, rebounds, assists, steals, blocks, or shooting efficiency.
        </li>
        <li>
          <strong>NBA Comparables</strong> — find NBA players of plausible
          height whose statistical profile most resembles a prospect's.
          Height is used only to keep the comparison physically sensible
          before the statistical match runs. This is descriptive
          resemblance, never a prediction of a player's future career.
        </li>
      </ul>
    ),
  },
  {
    title: "What the ranking does — and doesn't — mean",
    body: (
      <>
        <p>
          DraftLens doesn't try to reproduce the real Draft pick-for-pick.
          The actual NBA Draft also depends on information DraftLens
          deliberately doesn't use: private scouting, interviews, workouts,
          medical evaluation, team-specific roster strategy, trades, and
          subjective upside evaluation.
        </p>
        <p>
          DraftLens focuses on pre-draft NCAA statistical evidence — so its
          rank can differ substantially from the real Draft. That's not the
          same as being wrong: its value is an independent quantitative
          viewpoint, consistent comparison across prospects, transparent
          reasoning, and a second opinion alongside scouting.
        </p>
        <p className={styles.emphasis}>
          DraftLens is a decision-support signal, not a mock-draft
          replication engine.
        </p>
      </>
    ),
  },
];
