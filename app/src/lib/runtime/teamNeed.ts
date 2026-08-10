/** Team Need in the browser: peer-percentile dimensions, archetypes, custom fit.
 *
 * The dimension definitions, reliability minimums, coverage rules and
 * archetype pillars all arrive from `config/team_need.json` through the
 * runtime bundle — an imported file cannot redefine any of them. What this
 * file implements is the frozen combination logic, and its three
 * non-negotiable rules are the reason it is written out rather than
 * approximated:
 *
 *   ORIENTATION   a LOWER_IS_BETTER component is inverted before combination.
 *   MISSING       an absent component is dropped and the dimension
 *                 renormalises. It is never 0 and never 50.
 *   RELIABILITY   a rate whose denominator is below its declared minimum is
 *                 MISSING, not a real low value.
 */

import { NA, clamp, interp, isFinite_, nanMean, rintHalfEven } from "./numeric";
import type { Features } from "./features";
import type { RuntimeCore, RuntimeSeason } from "./types";

const GLOBAL = "GLOBAL";

/** 0-100 percentile of one value against the season's peer grid.
 * `team_need.reference.PercentileReference.percentile` — interpolated over
 * the 101-point quantile grid, clamped rather than extrapolated. */
function percentile(
  value: number,
  season: RuntimeSeason,
  group: string,
  metric: string,
): number {
  const grid = season.teamNeedGrids[group]?.[metric];
  if (!grid || !isFinite_(value)) return NA;
  const qs = grid.values.map((_, i) => i); // the grid is 0..100 by construction
  return clamp(interp(value, grid.values, qs, 0, 100), 0, 100);
}

/** metric -> reference group, resolved across every dimension. */
export function referenceSpec(core: RuntimeCore): Record<string, string> {
  const spec: Record<string, string> = {};
  for (const dim of Object.values(core.teamNeed.dimensions)) {
    for (const c of dim.components) spec[c.metric] = dim.reference_group;
  }
  return spec;
}

/** Raw (un-inverted) component percentiles, after reliability filtering. */
export function componentPercentiles(
  features: Features,
  position: string,
  core: RuntimeCore,
  season: RuntimeSeason,
): Record<string, number> {
  const spec = referenceSpec(core);
  const raw: Record<string, number> = {};
  for (const [metric, groupKind] of Object.entries(spec)) {
    let group = GLOBAL;
    if (groupKind !== GLOBAL) {
      group = season.teamNeedGrids[position]?.[metric] ? position : GLOBAL;
    }
    raw[metric] = percentile(features[metric], season, group, metric);
  }

  // RELIABILITY: blank out a component whose denominator is too thin. The
  // prospect is never dropped, only that one component.
  for (const [metric, rule] of Object.entries(core.teamNeed.reliabilityMinimums)) {
    if (typeof rule === "string" || !(metric in raw)) continue;
    const den = features[rule.denominator];
    if (!isFinite_(den) || den < rule.min) raw[metric] = NA;
  }
  return raw;
}

/** Oriented components — higher always means better for the trait. */
export function orientedComponents(
  raw: Record<string, number>,
  core: RuntimeCore,
): Record<string, number> {
  const out = { ...raw };
  for (const dim of Object.values(core.teamNeed.dimensions)) {
    for (const c of dim.components) {
      if (c.orientation === "LOWER_IS_BETTER" && isFinite_(out[c.metric])) {
        out[c.metric] = 100.0 - out[c.metric];
      }
    }
  }
  return out;
}

export interface DimensionResult {
  scores: Record<string, number>;
  coverage: Record<string, number>;
  dataCoverage: number;
}

export function computeDimensions(
  oriented: Record<string, number>,
  core: RuntimeCore,
): DimensionResult {
  const minFraction = core.teamNeed.coverage.dimension_min_component_fraction;
  const scores: Record<string, number> = {};
  const coverage: Record<string, number> = {};
  for (const [name, dim] of Object.entries(core.teamNeed.dimensions)) {
    const metrics = dim.components.map((c) => c.metric);
    const values = metrics.map((m) => oriented[m]);
    const available = values.filter(isFinite_).length;
    const need = Math.max(1, Math.ceil(minFraction * metrics.length));
    scores[name] = available >= need ? nanMean(values) : NA;
    coverage[name] = available / Math.max(1, metrics.length);
  }
  const cov = Object.values(coverage);
  return {
    scores,
    coverage,
    dataCoverage: cov.length ? cov.reduce((a, b) => a + b, 0) / cov.length : NA,
  };
}

/** `team_need.dimensions.combine`. Geometric mean is what makes a conjunctive
 * archetype conjunctive: a prospect elite at shooting and poor at defence is
 * not a 3&D wing. */
function combine(values: number[], method: string): number {
  const v = values.filter(isFinite_);
  if (v.length === 0) return NA;
  if (method === "ARITHMETIC_MEAN") {
    return v.reduce((a, b) => a + b, 0) / v.length;
  }
  if (method === "GEOMETRIC_MEAN") {
    const logs = v.map((x) => Math.log(Math.max(x, 1e-9)));
    return Math.exp(logs.reduce((a, b) => a + b, 0) / logs.length);
  }
  throw new Error(`unknown combination ${method}`);
}

export const ELIGIBLE = "ELIGIBLE";
export const OUT_OF_POSITION = "OUT_OF_POSITION";
export const UNKNOWN_POSITION = "UNKNOWN_POSITION";

function eligibility(profile: Record<string, unknown>, position: string): string {
  const rule = profile.eligibility as { position_3_in: string[] } | null | undefined;
  if (!rule) return ELIGIBLE;
  if (!position || position === "UNKNOWN") return UNKNOWN_POSITION;
  return rule.position_3_in.includes(position) ? ELIGIBLE : OUT_OF_POSITION;
}

export interface ProfileResult {
  fitRaw: number;
  fitScore: number;
  eligibility: string;
  status: "OK" | "UNAVAILABLE";
  pillars: Record<string, number>;
}

export function scoreProfile(
  name: string,
  features: Features,
  position: string,
  raw: Record<string, number>,
  oriented: Record<string, number>,
  dimensions: Record<string, number>,
  core: RuntimeCore,
  season: RuntimeSeason,
): ProfileResult {
  const spec = core.teamNeed.profiles[name];
  const method = spec.combination as string;
  const pillars: Record<string, number> = {};
  let score: number;

  if (method === "DIMENSION") {
    const dim = spec.dimension as string;
    pillars[dim] = dimensions[dim];
    score = dimensions[dim];
  } else {
    const specs = spec.pillars as {
      id: string; source: string; dimension?: string;
      metrics?: string[]; reference_group?: string;
    }[];
    for (const p of specs) {
      if (p.source === "DIMENSION") {
        pillars[p.id] = dimensions[p.dimension as string];
      } else {
        const metrics = p.metrics ?? [];
        const values = p.reference_group === GLOBAL
          // e.g. Rim Protector blocks: absolute shot-blocking, not "good for a
          // guard" — re-percentiled against the global peer group.
          ? metrics.map((m) => percentile(features[m], season, GLOBAL, m))
          : metrics.map((m) => oriented[m]);
        pillars[p.id] = nanMean(values);
      }
    }
    const values = specs.map((p) => pillars[p.id]);
    // a conjunctive profile needs EVERY pillar; a missing one is not a zero
    score = values.every(isFinite_) ? combine(values, method) : NA;
  }

  void raw;
  return {
    fitRaw: score,
    fitScore: isFinite_(score) ? rintHalfEven(clamp(score, 0, 100)) : NA,
    eligibility: eligibility(spec, position),
    status: isFinite_(score) ? "OK" : "UNAVAILABLE",
    pillars,
  };
}

/** `team_need.scoring.custom_fit` — a weighted blend of REQUESTED and
 * AVAILABLE dimensions, refused when too little of the requested weight
 * landed on something scorable. */
export function customFit(
  weights: Record<string, number>,
  dimensions: Record<string, number>,
  core: RuntimeCore,
): { fitRaw: number; fitScore: number; supportedWeightFraction: number } {
  const minSupported = core.teamNeed.coverage.custom_min_supported_weight;
  const active = Object.entries(weights).filter(([, w]) => w > 0);
  const total = active.reduce((a, [, w]) => a + w, 0);
  if (total <= 0) return { fitRaw: NA, fitScore: NA, supportedWeightFraction: 0 };

  let numerator = 0;
  let supported = 0;
  for (const [name, w] of active) {
    const d = dimensions[name];
    if (isFinite_(d)) {
      numerator += d * w;
      supported += w;
    }
  }
  const fraction = supported / total;
  let fitRaw = supported > 0 ? numerator / supported : NA;
  if (fraction < minSupported) fitRaw = NA;
  return {
    fitRaw,
    fitScore: isFinite_(fitRaw) ? rintHalfEven(clamp(fitRaw, 0, 100)) : NA,
    supportedWeightFraction: fraction,
  };
}
