import { useState } from "react";
import { useOnboarding } from "../onboarding/OnboardingContext";
import { HeroVisual } from "../components/HeroVisual";
import styles from "./LandingPage.module.css";

const HERO_IMAGE = `${import.meta.env.BASE_URL}hero/hero-player.jpg`;

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
  // The hero photograph is optional by design: it is not committed to the
  // repository (see .gitignore) because its reuse rights are unverified, and
  // this project refuses to ship an image without a verified licence. When
  // the file is absent the original SVG hero takes over, so the page is
  // never broken and never shows a torn-image icon.
  const [photoOk, setPhotoOk] = useState(true);

  return (
    <div className={styles.page}>
      {photoOk && (
        <div className={styles.photoLayer} aria-hidden="true">
          <img
            className={styles.photo}
            src={HERO_IMAGE}
            alt=""
            onError={() => setPhotoOk(false)}
          />
          <div className={styles.photoScrim} />
        </div>
      )}

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
            </div>
          </div>

          {!photoOk && (
            <div className={styles.visualWrap} aria-hidden="true">
              <HeroVisual />
            </div>
          )}
        </div>

        <section className={styles.capabilities}>
          {CAPABILITIES.map((c) => (
            <div key={c.title} className={styles.capabilityCard}>
              <h2 className={styles.capabilityTitle}>{c.title}</h2>
              <p className={styles.capabilityBody}>{c.body}</p>
            </div>
          ))}
        </section>
      </main>
    </div>
  );
}
