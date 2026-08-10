/** NBA Statistical Comparables in the browser.
 *
 * Unchanged methodology: percentiles within each league, six role dimensions,
 * a height plausibility GATE applied before any distance is computed, then
 * coverage-normalised Euclidean distance over the gated candidates.
 *
 * The NBA reference pool is fixed and ships in the runtime bundle. An
 * imported dataset supplies prospects to compare, never candidates to be
 * compared against — a user's file cannot add players to or replace the NBA
 * pool.
 */

import { NA, isFinite_, midRankPercentile, nanMean, rintHalfEven, unpackSorted }
  from "./numeric";
import type { Features } from "./features";
import type { RuntimeCore, RuntimeSeason } from "./types";

export const UNAVAILABLE = "UNAVAILABLE";

/** A prospect's position in the common space: NCAA percentiles collapsed into
 * the six role dimensions. `comparables.space.build_ncaa_space`. */
export function ncaaDimensions(
  features: Features,
  core: RuntimeCore,
  season: RuntimeSeason,
  cache: Map<string, Float64Array>,
): number[] {
  const pct: Record<string, number> = {};
  for (const [metric, packed] of Object.entries(season.comparableReference)) {
    let ref = cache.get(metric);
    if (!ref) {
      ref = unpackSorted(packed);
      cache.set(metric, ref);
    }
    pct[metric] = midRankPercentile(features[metric], ref);
  }

  return core.comparables.dimensionOrder.map((name) => {
    const spec = core.comparables.dimensions[name];
    const values = spec.metrics.map((m) => {
      const p = pct[m];
      if (!isFinite_(p)) return NA;
      return spec.invert.includes(m) ? 100.0 - p : p;
    });
    return nanMean(values);
  });
}

interface Distance {
  distance: number;
  shared: number;
}

/** Coverage-normalised distance: computed over the dimensions available for
 * BOTH players and divided by how many that was, so a prospect missing three
 * dimensions does not appear mechanically closer to everyone. */
function distanceTo(prospect: number[], pool: (number | null)[]): Distance {
  let sum = 0;
  let shared = 0;
  for (let i = 0; i < prospect.length; i += 1) {
    const a = prospect[i];
    const b = pool[i];
    if (isFinite_(a) && b !== null && isFinite_(b)) {
      const diff = b - a;
      sum += diff * diff;
      shared += 1;
    }
  }
  if (shared === 0) return { distance: NA, shared: 0 };
  return { distance: Math.sqrt(sum / shared), shared };
}

/** The empirical distance percentile, read off the frozen cut-points the
 * bundle carries. Not a probability and not a percentage of shared traits. */
function similarityScore(distance: number, core: RuntimeCore): number {
  const t = core.comparables.similarityThresholds;
  if (!isFinite_(distance)) return NA;
  for (let i = 0; i < t.scores.length; i += 1) {
    const upper = t.upperDistance[i];
    if (upper !== null && distance <= upper) return t.scores[i];
  }
  return 0;
}

export interface ComparablePlayer {
  rank: number;
  id: number;
  name: string;
  heightInches: number | null;
  heightDifferenceInches: number | null;
  referenceSeasons: number[];
  similarityScore: number;
  rawDistance: number;
  sharedDimensionCount: number;
}

export interface ComparableResult {
  status: "OK" | typeof UNAVAILABLE;
  reason?: string;
  comparables: ComparablePlayer[];
  prospectCoverage: number;
  prospectHeightInches: number | null;
  heightWindowInches: number | null;
  thirdVsFourthMargin: number | null;
  poolSize: number;
}

export function findComparables(
  dimensions: number[],
  heightInches: number,
  core: RuntimeCore,
): ComparableResult {
  const cfg = core.comparables;
  const nDims = cfg.dimensionOrder.length;
  const available = dimensions.filter(isFinite_).length;
  const coverage = available / nDims;

  const empty = {
    comparables: [] as ComparablePlayer[],
    prospectCoverage: Number(coverage.toFixed(3)),
    prospectHeightInches: isFinite_(heightInches) ? Math.trunc(heightInches) : null,
    heightWindowInches: null,
    thirdVsFourthMargin: null,
    poolSize: 0,
  };

  if (coverage < cfg.minSharedCoverage) {
    return {
      status: UNAVAILABLE,
      reason: `prospect has ${available}/${nDims} dimensions, below the `
        + `${Math.round(cfg.minSharedCoverage * 100)}% minimum`,
      ...empty,
    };
  }

  const need = Math.ceil(cfg.minSharedCoverage * nDims);
  const distances = cfg.nbaPool.map((p) => distanceTo(dimensions, p.dimensions));
  const eligible = cfg.nbaPool.map((_, i) =>
    isFinite_(distances[i].distance) && distances[i].shared >= need);

  // HEIGHT GATE, applied BEFORE any ranking. A missing height never bypasses
  // it: an unmeasured player is not a plausible match, it is an unknown one.
  if (!isFinite_(heightInches)) {
    return {
      status: UNAVAILABLE,
      reason: "prospect height is unavailable, so no physically plausible NBA "
        + "candidate pool can be formed",
      ...empty,
    };
  }
  let window: number | null = null;
  let gated: boolean[] = [];
  for (const w of cfg.heightWindowsInches) {
    const mask = cfg.nbaPool.map((p, i) =>
      eligible[i] && p.heightInches !== null
      && Math.abs(p.heightInches - heightInches) <= w);
    if (mask.filter(Boolean).length >= cfg.nComparables) {
      window = w;
      gated = mask;
      break;
    }
  }
  if (window === null) {
    const widest = Math.max(...cfg.heightWindowsInches);
    return {
      status: UNAVAILABLE,
      reason: `fewer than ${cfg.nComparables} NBA players fall within `
        + `±${widest}in of the prospect`,
      ...empty,
    };
  }

  const idx: number[] = [];
  gated.forEach((ok, i) => {
    if (ok) idx.push(i);
  });
  // deterministic ties: exact distance, then the stable analytical id
  idx.sort((a, b) =>
    (distances[a].distance - distances[b].distance)
    || (cfg.nbaPool[a].id - cfg.nbaPool[b].id));

  const top = idx.slice(0, cfg.nComparables);
  const margin = idx.length > cfg.nComparables
    ? distances[idx[cfg.nComparables]].distance
      - distances[idx[cfg.nComparables - 1]].distance
    : null;

  const pHeight = Math.trunc(heightInches);
  const comparables: ComparablePlayer[] = top.map((i, k) => {
    const p = cfg.nbaPool[i];
    return {
      rank: k + 1,
      id: p.id,
      name: p.name,
      heightInches: p.heightInches,
      heightDifferenceInches: p.heightInches === null
        ? null : Math.abs(p.heightInches - pHeight),
      referenceSeasons: p.referenceSeasons,
      similarityScore: rintHalfEven(similarityScore(distances[i].distance, core)),
      rawDistance: Number(distances[i].distance.toFixed(4)),
      sharedDimensionCount: distances[i].shared,
    };
  });

  return {
    status: "OK",
    comparables,
    prospectCoverage: Number(coverage.toFixed(3)),
    prospectHeightInches: pHeight,
    heightWindowInches: window,
    thirdVsFourthMargin: margin === null ? null : Number(margin.toFixed(4)),
    poolSize: idx.length,
  };
}
