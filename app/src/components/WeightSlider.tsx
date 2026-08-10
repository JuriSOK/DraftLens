import styles from "./WeightSlider.module.css";

export function WeightSlider({
  id,
  label,
  value,
  onChange,
}: {
  id: string;
  label: string;
  value: number;
  onChange: (value: number) => void;
}) {
  return (
    <div className={styles.row}>
      <div className={styles.labelRow}>
        <label htmlFor={id} className={styles.label}>
          {label}
        </label>
        <span className={styles.value}>{value}</span>
      </div>
      <input
        id={id}
        type="range"
        min={0}
        max={100}
        step={5}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className={styles.slider}
      />
    </div>
  );
}
