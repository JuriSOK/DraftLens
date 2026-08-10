import { Link, useNavigate } from "react-router-dom";
import { useOnboarding } from "../onboarding/OnboardingContext";
import styles from "./LandingPage.module.css";

const CAPABILITIES = [
  {
    title: "General Board",
    body: "Independent pre-draft ranking, built from NCAA production alone.",
  },
  {
    title: "Team Need",
    body: "Rank prospects for the traits your team wants — predefined or custom.",
  },
  {
    title: "NBA Comparables",
    body: "Find statistically similar NBA profiles for each prospect.",
  },
];

export function LandingPage() {
  const { start } = useOnboarding();
  const navigate = useNavigate();

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <span className={styles.brand}>
          <span className={styles.brandMark} aria-hidden="true" />
          DraftLens
        </span>
      </header>

      <main className={styles.hero}>
        <h1 className={styles.title}>DraftLens</h1>
        <p className={styles.tagline}>
          Pre-draft analytics for smarter NBA Draft decisions.
        </p>
        <p className={styles.sub}>
          Rank NCAA prospects, explore team fit, compare statistical profiles
          and understand what drives each score.
        </p>

        <div className={styles.ctaRow}>
          <button type="button" className={styles.primaryCta} onClick={start}>
            Get Started
          </button>
          <button
            type="button"
            className={styles.secondaryCta}
            onClick={() => navigate("/board")}
          >
            Explore the Board
          </button>
        </div>

        <div className={styles.capabilities}>
          {CAPABILITIES.map((c) => (
            <div key={c.title} className={styles.capabilityCard}>
              <h2 className={styles.capabilityTitle}>{c.title}</h2>
              <p className={styles.capabilityBody}>{c.body}</p>
            </div>
          ))}
        </div>

        <Link to="/stats" className={styles.statsLink}>
          Also: rank prospects directly by raw statistics in Stats →
        </Link>
      </main>

      <footer className={styles.footer}>
        <span>DraftLens — AQX Sports Analytics Data Bowl 3.0</span>
        <Link to="/methodology" className={styles.footerLink}>
          Methodology
        </Link>
      </footer>
    </div>
  );
}
