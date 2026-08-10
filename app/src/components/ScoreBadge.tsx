import styles from "./ScoreBadge.module.css";

/** The Overall Score badge. Visually the most prominent number on the
 * board — that's deliberate, it's the headline product number. */
export function ScoreBadge({
  value,
  size = "md",
}: {
  value: number | null;
  size?: "sm" | "md" | "lg";
}) {
  if (value === null) {
    return <span className={`${styles.badge} ${styles[size]} ${styles.empty}`}>—</span>;
  }
  const tier = value >= 90 ? "elite" : value >= 70 ? "strong" : value >= 40 ? "mid" : "low";
  return (
    <span className={`${styles.badge} ${styles[size]} ${styles[tier]}`}>
      {Math.round(value)}
    </span>
  );
}

export function RankBadge({ rank }: { rank: number }) {
  const top3 = rank <= 3;
  return (
    <span className={`${styles.rank} ${top3 ? styles.rankTop : ""}`}>{rank}</span>
  );
}
