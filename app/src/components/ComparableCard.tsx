import type { Comparable } from "../types/data";
import styles from "./ComparableCard.module.css";

const RANK_LABEL: Record<number, string> = {
  1: "#1 closest profile",
  2: "#2 closest profile",
  3: "#3 closest profile",
};

export function ComparableCard({ comparable }: { comparable: Comparable }) {
  return (
    <div className={styles.card}>
      <div className={styles.rankLine}>
        {RANK_LABEL[comparable.rank] ?? `#${comparable.rank} closest profile`}
      </div>
      <h3 className={styles.name}>{comparable.nbaPlayerName}</h3>

      {comparable.closestDimensions.length > 0 && (
        <div className={styles.block}>
          <span className={styles.blockLabel}>Similar in</span>
          <ul className={styles.list}>
            {comparable.closestDimensions.map((d) => (
              <li key={d.label}>{d.label}</li>
            ))}
          </ul>
        </div>
      )}

      {comparable.differences.length > 0 && (
        <div className={styles.block}>
          <span className={styles.blockLabel}>Differs in</span>
          <ul className={styles.list}>
            {comparable.differences.map((d) => (
              <li key={d.label}>{d.label}</li>
            ))}
          </ul>
        </div>
      )}

      <details className={styles.details}>
        <summary>Similarity details</summary>
        <p className={styles.similarity}>
          Similarity score {comparable.similarityScore ?? "—"} · NBA reference
          seasons {comparable.referenceSeasons.join("–")}
        </p>
      </details>
    </div>
  );
}
