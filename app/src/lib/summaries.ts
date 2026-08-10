import type { Bin } from "../components/charts/Charts";

/** Presentation-only summaries of values the frozen export already produced.
 *
 * Nothing here models, predicts, or re-derives anything: these are averages,
 * counts and bucket tallies over numbers that are already rendered elsewhere
 * on the same page. No analytical value is changed by any of it. */

export function mean(values: (number | null | undefined)[]): number | null {
  const v = values.filter((x): x is number => typeof x === "number" && !Number.isNaN(x));
  if (v.length === 0) return null;
  return v.reduce((a, b) => a + b, 0) / v.length;
}

export function median(values: (number | null | undefined)[]): number | null {
  const v = values
    .filter((x): x is number => typeof x === "number" && !Number.isNaN(x))
    .sort((a, b) => a - b);
  if (v.length === 0) return null;
  const mid = Math.floor(v.length / 2);
  return v.length % 2 ? v[mid] : (v[mid - 1] + v[mid]) / 2;
}

export function maxOf(values: (number | null | undefined)[]): number | null {
  const v = values.filter((x): x is number => typeof x === "number" && !Number.isNaN(x));
  return v.length ? Math.max(...v) : null;
}

/** Fixed-width bucket tally, e.g. Overall Score 0-100 in tens. */
export function binValues(
  values: (number | null | undefined)[],
  opts: { min: number; max: number; buckets: number; format?: (n: number) => string },
): Bin[] {
  const { min, max, buckets } = opts;
  const format = opts.format ?? ((n: number) => String(Math.round(n)));
  const width = (max - min) / buckets;
  const bins: Bin[] = Array.from({ length: buckets }, (_, i) => ({
    label: format(min + i * width),
    count: 0,
  }));
  for (const raw of values) {
    if (typeof raw !== "number" || Number.isNaN(raw)) continue;
    const clamped = Math.min(max, Math.max(min, raw));
    let idx = Math.floor((clamped - min) / width);
    if (idx >= buckets) idx = buckets - 1;
    if (idx < 0) idx = 0;
    bins[idx].count += 1;
  }
  return bins;
}

/** Which bucket a single value falls into — used to highlight one prospect
 * inside the class distribution. */
export function binIndexOf(
  value: number | null | undefined,
  opts: { min: number; max: number; buckets: number },
): number | null {
  if (typeof value !== "number" || Number.isNaN(value)) return null;
  const { min, max, buckets } = opts;
  const width = (max - min) / buckets;
  const clamped = Math.min(max, Math.max(min, value));
  let idx = Math.floor((clamped - min) / width);
  if (idx >= buckets) idx = buckets - 1;
  if (idx < 0) idx = 0;
  return idx;
}

export function positionCounts(
  positions: (string | null | undefined)[],
): { label: string; count: number }[] {
  const order = ["G", "F", "C", "UNKNOWN"];
  const tally = new Map<string, number>();
  for (const p of positions) {
    const key = p && order.includes(p) ? p : "UNKNOWN";
    tally.set(key, (tally.get(key) ?? 0) + 1);
  }
  return order
    .filter((p) => (tally.get(p) ?? 0) > 0)
    .map((p) => ({ label: p, count: tally.get(p) as number }));
}

/** Tally any small set of category strings, most common first. */
export function categoryCounts(
  values: (string | null | undefined)[],
): { label: string; count: number }[] {
  const tally = new Map<string, number>();
  for (const v of values) {
    const key = (v ?? "unknown").toString();
    tally.set(key, (tally.get(key) ?? 0) + 1);
  }
  return [...tally.entries()]
    .map(([label, count]) => ({ label, count }))
    .sort((a, b) => b.count - a.count);
}
