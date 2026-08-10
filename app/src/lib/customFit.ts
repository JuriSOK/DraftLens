import type { CustomDimensionKey, Prospect } from "../types/data";

/**
 * The ONE piece of scoring arithmetic this frontend is allowed to perform —
 * the frozen custom Team Need formula (config/team_need.json `custom_mode`,
 * docs/METHODOLOGY.md §3.3), not a re-derivation of any model:
 *
 *   fit = sum(weight_i * dimension_i) / sum(active weights)
 *
 * over dimensions with a positive weight AND available data for that
 * prospect. A dimension missing for a prospect is dropped from that
 * prospect's calculation, exactly as the frozen engine does — never imputed,
 * never zero-filled. This mirrors src/team_need/scoring.py:custom_fit,
 * applied here only because the weights are a live user preference that
 * cannot be precomputed for every possible combination.
 */
export type Weights = Record<CustomDimensionKey, number>;

export interface CustomFitResult {
  fitRaw: number | null;
  fitScore: number | null;
  supportedWeightFraction: number;
}

export function computeCustomFit(
  prospect: Prospect,
  weights: Weights,
): CustomFitResult {
  const totalWeight = Object.values(weights).reduce((a, b) => a + b, 0);
  if (totalWeight <= 0) {
    return { fitRaw: null, fitScore: null, supportedWeightFraction: 0 };
  }

  let numerator = 0;
  let supportedWeight = 0;
  (Object.keys(weights) as CustomDimensionKey[]).forEach((key) => {
    const w = weights[key];
    if (w <= 0) return;
    const value = prospect.dimensions[key];
    if (value === null || Number.isNaN(value)) return;
    numerator += w * value;
    supportedWeight += w;
  });

  if (supportedWeight === 0) {
    return { fitRaw: null, fitScore: null, supportedWeightFraction: 0 };
  }

  const fitRaw = numerator / supportedWeight;
  return {
    fitRaw,
    fitScore: Math.round(Math.min(100, Math.max(0, fitRaw))),
    supportedWeightFraction: supportedWeight / totalWeight,
  };
}
