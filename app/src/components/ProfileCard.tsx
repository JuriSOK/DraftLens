import type { ProfileFit } from "../types/data";
import styles from "./ProfileCard.module.css";

export function ProfileCard({ label, fit }: { label: string; fit: ProfileFit }) {
  const ineligible = fit.eligibility !== "ELIGIBLE";
  return (
    <div className={styles.card} data-ineligible={ineligible}>
      <span className={styles.label}>{label}</span>
      {ineligible ? (
        <span className={styles.notEligible}>Not eligible</span>
      ) : (
        <span className={styles.score}>{fit.fitScore ?? "—"}</span>
      )}
    </div>
  );
}
