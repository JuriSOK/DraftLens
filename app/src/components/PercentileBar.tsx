import { formatScoreOutOf100 } from "../lib/format";
import styles from "./PercentileBar.module.css";

const PEER_GROUP_TEXT = {
  GLOBAL: "NCAA peers",
  POSITION: "NCAA players at a similar position",
} as const;

/** Horizontal bar for a 0-100 peer-relative score. Plain CSS, no charting
 * dependency — a single bar doesn't need one.
 *
 * Deliberately avoids ordinal percentile language ("81st percentile") —
 * "81st" reads as unclear and "81th" is a common, ungrammatical mistake.
 * Shows "81 / 100" plus a plain-language peer sentence instead. */
export function PercentileBar({
  label,
  value,
  peerGroup = "GLOBAL",
  hint,
}: {
  label: string;
  value: number | null;
  peerGroup?: "GLOBAL" | "POSITION";
  hint?: string;
}) {
  const pct = value === null ? 0 : Math.min(100, Math.max(0, value));
  const rounded = value === null ? null : Math.round(value);
  return (
    <div className={styles.row}>
      <div className={styles.labelRow}>
        <span className={styles.label}>{label}</span>
        <span className={styles.value}>{formatScoreOutOf100(value)}</span>
      </div>
      <div
        className={styles.track}
        role="img"
        aria-label={`${label}: ${value === null ? "unavailable" : `${rounded} of 100`}`}
      >
        {value !== null && (
          <div className={styles.fill} style={{ width: `${pct}%` }} />
        )}
      </div>
      <p className={styles.peerLine}>
        {rounded === null
          ? "Unavailable"
          : `Higher than ${rounded}% of ${PEER_GROUP_TEXT[peerGroup]}.`}
      </p>
      {hint && <p className={styles.hint}>{hint}</p>}
    </div>
  );
}
