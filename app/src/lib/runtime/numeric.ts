/** Numeric primitives that must agree with NumPy/pandas bit for bit.
 *
 * The Dataset Lab runs DraftLens's frozen models in the browser, and a
 * browser answer is only worth showing if it is the SAME answer Python gives.
 * Everything here therefore mirrors a specific NumPy or pandas behaviour
 * rather than the closest convenient JavaScript equivalent — `Math.round` and
 * `np.rint` disagree on halves, and that disagreement would move a prospect
 * on the board.
 *
 * `tests/parity` runs the frozen 2026 inputs through this stack and requires
 * identical output.
 */

/** Missing is NaN throughout, matching the Python pipeline's NaN semantics. */
export const NA = Number.NaN;

export function isFinite_(x: number | null | undefined): x is number {
  return typeof x === "number" && Number.isFinite(x);
}

/** JSON null -> NaN, so an absent measurement stays absent rather than 0. */
export function num(x: unknown): number {
  if (x === null || x === undefined || x === "") return NA;
  const v = typeof x === "number" ? x : Number(x);
  return Number.isFinite(v) ? v : NA;
}

/** `features.basketball.safe_div`: NaN when the denominator is missing or
 * <= 0, or the numerator is missing. Never Infinity, never a substituted 0. */
export function safeDiv(numerator: number, denominator: number): number {
  if (!isFinite_(numerator) || !isFinite_(denominator) || denominator <= 0) {
    return NA;
  }
  const out = numerator / denominator;
  return Number.isFinite(out) ? out : NA;
}

export function perGame(stat: number, games: number): number {
  return safeDiv(stat, games);
}

export function per40(stat: number, minutes: number): number {
  return safeDiv(40.0 * stat, minutes);
}

export function per100(stat: number, possessions: number): number {
  return safeDiv(100.0 * stat, possessions);
}

/** `np.rint` / Python `round`: half away from zero is WRONG here — both round
 * halves to the nearest even integer. Overall Score, Fit Score and the
 * similarity score all pass through this. */
export function rintHalfEven(x: number): number {
  if (!isFinite_(x)) return NA;
  const floor = Math.floor(x);
  const frac = x - floor;
  if (frac > 0.5) return floor + 1;
  if (frac < 0.5) return floor;
  return floor % 2 === 0 ? floor : floor + 1;
}

export function clamp(x: number, lo: number, hi: number): number {
  if (!isFinite_(x)) return x;
  return Math.min(hi, Math.max(lo, x));
}

/** Mean over the finite entries only; NaN when nothing is finite.
 * `np.nanmean` of an all-NaN slice — the "dimension unavailable" case. */
export function nanMean(values: number[]): number {
  let sum = 0;
  let n = 0;
  for (const v of values) {
    if (isFinite_(v)) {
      sum += v;
      n += 1;
    }
  }
  return n === 0 ? NA : sum / n;
}

/** Index of the first element >= key (`np.searchsorted(..., side="left")`). */
export function lowerBound(sorted: number[] | Float64Array, key: number): number {
  let lo = 0;
  let hi = sorted.length;
  while (lo < hi) {
    const mid = (lo + hi) >>> 1;
    if (sorted[mid] < key) lo = mid + 1;
    else hi = mid;
  }
  return lo;
}

/** Index of the first element > key (`np.searchsorted(..., side="right")`). */
export function upperBound(sorted: number[] | Float64Array, key: number): number {
  let lo = 0;
  let hi = sorted.length;
  while (lo < hi) {
    const mid = (lo + hi) >>> 1;
    if (sorted[mid] <= key) lo = mid + 1;
    else hi = mid;
  }
  return lo;
}

/** `np.interp` over a non-decreasing grid, including its duplicate-x and
 * out-of-range behaviour. Team Need percentiles are read off a 101-point
 * quantile grid this way. */
export function interp(
  x: number,
  xs: Float64Array | number[],
  ys: Float64Array | number[],
  left: number,
  right: number,
): number {
  const n = xs.length;
  if (n === 0 || !isFinite_(x)) return NA;
  if (x < xs[0]) return left;
  if (x > xs[n - 1]) return right;
  const j = upperBound(xs, x) - 1;
  if (j >= n - 1) return ys[n - 1];
  if (j < 0) return ys[0];
  if (xs[j] === x) return ys[j];
  const slope = (ys[j + 1] - ys[j]) / (xs[j + 1] - xs[j]);
  const out = slope * (x - xs[j]) + ys[j];
  return Number.isFinite(out) ? out : ys[j];
}

/** Mid-rank percentile of `value` within a sorted reference, 0-100.
 * `comparables.space._percentile_within`. NaN in, NaN out. */
export function midRankPercentile(value: number, sortedRef: Float64Array): number {
  if (!isFinite_(value) || sortedRef.length === 0) return NA;
  const lo = lowerBound(sortedRef, value);
  const hi = upperBound(sortedRef, value);
  return clamp((100.0 * (lo + hi)) / (2.0 * sortedRef.length), 0, 100);
}

/** Percentile rank within one board, mid-rank, mapped to (0, 1).
 * `board.scoring.within_board_percentile` — ties share a percentile and the
 * result is never exactly 0 or 1. */
export function withinBoardPercentile(values: number[], neutral: number): number[] {
  const n = values.length;
  const finite: { v: number; i: number }[] = [];
  for (let i = 0; i < n; i += 1) {
    if (isFinite_(values[i])) finite.push({ v: values[i], i });
  }
  const out = new Array<number>(n).fill(neutral);
  const count = finite.length;
  if (count === 0) return out;

  finite.sort((a, b) => a.v - b.v);
  // average rank for ties, 1-based, exactly as pandas `rank(method="average")`
  let k = 0;
  while (k < finite.length) {
    let j = k;
    while (j + 1 < finite.length && finite[j + 1].v === finite[k].v) j += 1;
    const avgRank = (k + 1 + (j + 1)) / 2;
    for (let t = k; t <= j; t += 1) {
      out[finite[t].i] = (avgRank - 0.5) / count;
    }
    k = j + 1;
  }
  return out;
}

/** Rebuild a sorted peer distribution from the runtime bundle.
 *
 * The bytes are little-endian float64, so the array the browser ranks against
 * is bit-for-bit the one Python ranked against. That matters because the
 * comparables percentile is a mid-rank: a value EQUAL to a reference entry
 * scores half a step differently from one just above it, and any rounding of
 * the reference would silently break those equalities. */
export function unpackSorted(packed: { count: number; data: string }): Float64Array {
  const binary = atob(packed.data);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
  return new Float64Array(bytes.buffer, bytes.byteOffset, packed.count);
}
