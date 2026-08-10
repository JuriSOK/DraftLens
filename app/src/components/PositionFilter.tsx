import styles from "./PositionFilter.module.css";

const POSITIONS = ["ALL", "G", "F", "C"] as const;
export type PositionValue = (typeof POSITIONS)[number];

export function PositionFilter({
  value,
  onChange,
}: {
  value: PositionValue;
  onChange: (value: PositionValue) => void;
}) {
  return (
    <div className={styles.group} role="group" aria-label="Filter by position">
      {POSITIONS.map((pos) => (
        <button
          key={pos}
          type="button"
          className={styles.chip}
          data-active={value === pos}
          onClick={() => onChange(pos)}
          aria-pressed={value === pos}
        >
          {pos === "ALL" ? "All" : pos}
        </button>
      ))}
    </div>
  );
}
