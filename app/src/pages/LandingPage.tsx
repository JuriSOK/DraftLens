import { Link, useNavigate } from "react-router-dom";
import { useOnboarding } from "../onboarding/OnboardingContext";
import { useDraftLensData } from "../data/DataProvider";
import { HeroVisual, Sparkline } from "../components/HeroVisual";
import styles from "./LandingPage.module.css";

const CAPABILITIES = [
  {
    title: "General Board",
    body: "Independent pre-draft ranking, built from NCAA production alone.",
  },
  {
    title: "Team Need",
    body: "Rank prospects for the traits your team wants.",
  },
  {
    title: "NBA Comparables",
    body: "Statistically similar NBA profiles for each prospect.",
  },
];

export function LandingPage() {
  const { start } = useOnboarding();
  const navigate = useNavigate();
  const { data } = useDraftLensData();

  // Real, already-published facts only — never invented figures. The count
  // comes from the live export; the others are frozen methodology constants
  // documented on the Methodology page.
  const year2026 = data?.years["2026"];
  const prospectCount =
    year2026?.status === "available" ? year2026.scoreableDeclaredCount : null;

  const stats = [
    { value: prospectCount !== null ? String(prospectCount) : "—", label: "prospects ranked" },
    { value: "887", label: "training prospects" },
    { value: "6", label: "archetypes" },
  ];

  return (
    <div className={styles.page}>
      <main className={styles.hero}>
        <div className={styles.heroInner}>
          <div className={styles.content}>
            <span className={styles.eyebrow}>
              <span className={styles.eyebrowDot} aria-hidden="true" />
              NBA Draft Analytics · 2026 Class
            </span>

            <h1 className={styles.title}>
              Scout the <span className={styles.titleAccent}>numbers</span>,
              <br />
              not the noise.
            </h1>

            <p className={styles.tagline}>
              Pre-draft analytics for smarter NBA Draft decisions — every score
              traced to a statistic.
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

            <div className={styles.statStrip}>
              {stats.map((s) => (
                <div key={s.label} className={styles.statChip}>
                  <span className={styles.statValue}>{s.value}</span>
                  <span className={styles.statLabel}>{s.label}</span>
                </div>
              ))}
              <div className={styles.statSpark} aria-hidden="true">
                <Sparkline />
                <span className={styles.statLabel}>board signal</span>
              </div>
            </div>
          </div>

          <div className={styles.visualWrap} aria-hidden="true">
            <HeroVisual />
          </div>
        </div>
      </main>

      <section className={styles.capabilities}>
        {CAPABILITIES.map((c) => (
          <div key={c.title} className={styles.capabilityCard}>
            <h2 className={styles.capabilityTitle}>{c.title}</h2>
            <p className={styles.capabilityBody}>{c.body}</p>
          </div>
        ))}
      </section>

      <footer className={styles.footer}>
        <span>DraftLens — AQX Sports Analytics Data Bowl 3.0</span>
        <Link to="/methodology" className={styles.footerLink}>
          Methodology
        </Link>
      </footer>
    </div>
  );
}
