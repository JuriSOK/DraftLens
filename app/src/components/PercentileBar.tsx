import { formatPercentile } from "../lib/format";
import styles from "./PercentileBar.module.css";

/** Horizontal bar for a 0-100 peer-relative percentile. Plain CSS, no
 * charting dependency — a single bar doesn't need one. */
export function PercentileBar({
  label,
  value,
  hint,
}: {
  label: string;
  value: number | null;
  hint?: string;
}) {
  const pct = value === null ? 0 : Math.min(100, Math.max(0, value));
  return (
    <div className={styles.row}>
      <div className={styles.labelRow}>
        <span className={styles.label}>{label}</span>
        <span className={styles.value}>
          {value === null ? "Unavailable" : formatPercentile(value)}
        </span>
      </div>
      <div
        className={styles.track}
        role="img"
        aria-label={`${label}: ${value === null ? "unavailable" : `${Math.round(value)}th percentile`}`}
      >
        {value !== null && (
          <div className={styles.fill} style={{ width: `${pct}%` }} />
        )}
      </div>
      {hint && <p className={styles.hint}>{hint}</p>}
    </div>
  );
}
