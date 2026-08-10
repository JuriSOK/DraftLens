import type { ProfileFit } from "../types/data";
import styles from "./ProfileCard.module.css";

export function ProfileCard({
  label,
  description,
  fit,
}: {
  label: string;
  description: string;
  fit: ProfileFit;
}) {
  const ineligible = fit.eligibility !== "ELIGIBLE";
  return (
    <div className={styles.card} data-ineligible={ineligible}>
      <span className={styles.label}>{label}</span>
      <p className={styles.description}>{description}</p>
      {ineligible ? (
        <span className={styles.notEligible}>
          {fit.eligibility === "OUT_OF_POSITION" ? "Not eligible — wrong position" : "Not eligible"}
        </span>
      ) : fit.fitScore === null ? (
        <span className={styles.notEligible}>Unavailable</span>
      ) : (
        <>
          <span className={styles.score}>{fit.fitScore} / 100</span>
          <span className={styles.peerLine}>
            Fits this archetype better than approximately {fit.fitScore}% of
            NCAA peers.
          </span>
        </>
      )}
    </div>
  );
}
