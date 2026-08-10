import styles from "./Charts.module.css";

/** Lightweight SVG/CSS chart primitives shared across the product.
 *
 * Every chart here is PRESENTATION ONLY: it summarises values the frozen
 * Python export already produced. Nothing is recomputed, modelled, or
 * invented — a bar height is just a number that is already on screen
 * somewhere else. No charting library. */

// ---------------------------------------------------------------- KPI strip
export interface KpiItem {
  label: string;
  value: string;
  hint?: string;
}

export function KpiStrip({ items }: { items: KpiItem[] }) {
  return (
    <div className={styles.kpiStrip}>
      {items.map((k) => (
        <div key={k.label} className={styles.kpi}>
          <span className={styles.kpiValue}>{k.value}</span>
          <span className={styles.kpiLabel}>{k.label}</span>
          {k.hint && <span className={styles.kpiHint}>{k.hint}</span>}
        </div>
      ))}
    </div>
  );
}

// ------------------------------------------------------------- distribution
export interface Bin {
  label: string;
  count: number;
}

/** A compact vertical histogram. `highlightIndex` tints one bin — used to
 * show where a single prospect sits inside the class distribution. */
export function Histogram({
  bins,
  highlightIndex,
  height = 56,
  ariaLabel,
}: {
  bins: Bin[];
  highlightIndex?: number | null;
  height?: number;
  ariaLabel: string;
}) {
  const max = Math.max(1, ...bins.map((b) => b.count));
  return (
    <div className={styles.histogram} role="img" aria-label={ariaLabel}>
      <div className={styles.histBars} style={{ height }}>
        {bins.map((b, i) => (
          <div key={b.label} className={styles.histCol} title={`${b.label}: ${b.count}`}>
            <div
              className={styles.histBar}
              data-highlight={highlightIndex === i}
              style={{ height: `${Math.max(2, (b.count / max) * 100)}%` }}
            />
          </div>
        ))}
      </div>
      <div className={styles.histAxis}>
        {bins.map((b, i) =>
          i === 0 || i === bins.length - 1 ? (
            <span key={b.label} className={styles.histTick}>
              {b.label}
            </span>
          ) : (
            <span key={b.label} />
          ),
        )}
      </div>
    </div>
  );
}

// ------------------------------------------------------------ horizontal bar
export function BarRow({
  label,
  value,
  max = 100,
  suffix = "",
  muted = false,
}: {
  label: string;
  value: number | null;
  max?: number;
  suffix?: string;
  muted?: boolean;
}) {
  const pct = value === null ? 0 : Math.min(100, Math.max(0, (value / max) * 100));
  return (
    <div className={styles.barRow}>
      <span className={styles.barLabel}>{label}</span>
      <span className={styles.barTrack}>
        <span
          className={styles.barFill}
          data-muted={muted}
          style={{ width: `${pct}%` }}
        />
      </span>
      <span className={styles.barValue}>
        {value === null ? "—" : `${Math.round(value)}${suffix}`}
      </span>
    </div>
  );
}

// -------------------------------------------------------------------- radar
export interface RadarAxis {
  label: string;
  value: number | null;
}

/** Six-axis radar for the Basketball Profile dimensions. Values are the
 * 0-100 peer scores already exported — the polygon is only a re-drawing of
 * the same numbers shown as bars elsewhere on the page. */
export function Radar({
  axes,
  size = 200,
  ariaLabel,
}: {
  axes: RadarAxis[];
  size?: number;
  ariaLabel: string;
}) {
  const cx = size / 2;
  const cy = size / 2;
  const r = size / 2 - 26;
  const n = axes.length;

  const point = (i: number, frac: number) => {
    const angle = (Math.PI * 2 * i) / n - Math.PI / 2;
    return [cx + Math.cos(angle) * r * frac, cy + Math.sin(angle) * r * frac];
  };

  const polygon = axes
    .map((a, i) => point(i, a.value === null ? 0 : a.value / 100))
    .map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`)
    .join(" ");

  return (
    <svg
      className={styles.radar}
      viewBox={`0 0 ${size} ${size}`}
      role="img"
      aria-label={ariaLabel}
    >
      {[0.25, 0.5, 0.75, 1].map((f) => (
        <polygon
          key={f}
          points={axes
            .map((_, i) => point(i, f))
            .map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`)
            .join(" ")}
          className={styles.radarGrid}
        />
      ))}
      {axes.map((_, i) => {
        const [x, y] = point(i, 1);
        return (
          <line key={i} x1={cx} y1={cy} x2={x} y2={y} className={styles.radarSpoke} />
        );
      })}
      <polygon points={polygon} className={styles.radarShape} />
      {axes.map((a, i) => {
        const [x, y] = point(i, 1.18);
        return (
          <text
            key={a.label}
            x={x}
            y={y}
            className={styles.radarLabel}
            textAnchor={x > cx + 4 ? "start" : x < cx - 4 ? "end" : "middle"}
            dominantBaseline="middle"
          >
            {a.label}
          </text>
        );
      })}
    </svg>
  );
}

// ------------------------------------------------------------- category mix
/** A single stacked bar plus legend for any small categorical breakdown —
 * used for board position mix and watchlist class mix. Colours are assigned
 * by index from the shared accent ramp, so the component doesn't need to
 * know what the categories mean. */
export function CategoryMix({
  counts,
  ariaLabel,
}: {
  counts: { label: string; count: number }[];
  ariaLabel: string;
}) {
  const total = counts.reduce((s, c) => s + c.count, 0) || 1;
  return (
    <div className={styles.mix} role="img" aria-label={ariaLabel}>
      <div className={styles.mixBar}>
        {counts.map((c, i) => (
          <span
            key={c.label}
            className={styles.mixSeg}
            data-index={i % 4}
            style={{ width: `${(c.count / total) * 100}%` }}
            title={`${c.label}: ${c.count}`}
          />
        ))}
      </div>
      <div className={styles.mixLegend}>
        {counts.map((c, i) => (
          <span key={c.label} className={styles.mixLegendItem}>
            <span className={styles.mixDot} data-index={i % 4} />
            {c.label} {c.count}
          </span>
        ))}
      </div>
    </div>
  );
}
