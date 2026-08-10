/** Orchestration: an imported dataset -> exactly the analyses it qualifies for.
 *
 * Capability detection is the point of this file. DraftLens will not answer a
 * question the data cannot support, and it will not answer a question the
 * METHODOLOGY does not support for that population — a file of NCAA players
 * who are not a declared early-entry class gets no Draft Probability, because
 * that is the only population the model was validated on. The refusal is
 * explicit and carries its reason; nothing degrades into a plausible-looking
 * number.
 */

import { buildBoard, draftOrderPick, draftProbability } from "./board";
import { findComparables, ncaaDimensions } from "./comparables";
import type { ComparableResult } from "./comparables";
import { buildFeatures, toPrimitives } from "./features";
import type { Features } from "./features";
import { isFinite_ } from "./numeric";
import {
  componentPercentiles, computeDimensions, customFit, orientedComponents,
  scoreProfile,
} from "./teamNeed";
import type { ProfileResult } from "./teamNeed";
import type { ParsedDataset, RuntimeCore, RuntimeSeason } from "./types";

export type CapabilityId = "stats" | "teamNeed" | "comparables" | "generalBoard";

export interface Capability {
  id: CapabilityId;
  label: string;
  available: boolean;
  reason: string;
}

export interface AnalyzedProspect {
  id: string;
  name: string;
  school: string | null;
  position: string;
  features: Features;
  dimensions: Record<string, number>;
  dataCoverage: number;
  profiles: Record<string, ProfileResult>;
  comparables: ComparableResult | null;
  draftProbability: number | null;
  orderPick: number | null;
  overallScore: number | null;
  boardRank: number | null;
  boardSignal: number | null;
  stageBQuality: number | null;
}

export interface AnalysisResult {
  datasetName: string;
  season: number;
  populationType: string;
  draftSize: number | null;
  capabilities: Capability[];
  prospects: AnalyzedProspect[];
  imputedModelFeatures: string[];
}

export function capabilityMap(caps: Capability[]): Record<CapabilityId, Capability> {
  return Object.fromEntries(caps.map((c) => [c.id, c])) as
    Record<CapabilityId, Capability>;
}

/** Which analyses this dataset is entitled to, and why not otherwise. */
export function detectCapabilities(
  dataset: ParsedDataset,
  core: RuntimeCore,
  season: RuntimeSeason | null,
): Capability[] {
  const meta = dataset.metadata;
  const seasonSupported = core.supportedSeasons.includes(meta.season);
  // `Number(null)` is 0, which is finite — an unmeasured height must not
  // count as a measured one.
  const heights = dataset.prospects.filter(
    (p) => p.height_inches !== null && p.height_inches !== undefined
      && isFinite_(Number(p.height_inches))).length;

  const caps: Capability[] = [];

  caps.push({
    id: "stats", label: "Stats Explorer", available: true,
    reason: "Rates are computed from the totals in your file.",
  });

  caps.push({
    id: "teamNeed", label: "Basketball Profile & Team Need",
    available: Boolean(season) && seasonSupported,
    reason: seasonSupported
      ? "Scored against the NCAA peer distribution for this season."
      : `DraftLens has no NCAA peer reference for the ${meta.season} season, `
        + "and no neighbouring season is substituted for it.",
  });

  caps.push({
    id: "comparables", label: "NBA Comparables",
    available: Boolean(season) && seasonSupported && heights > 0,
    reason: !seasonSupported
      ? `No NCAA peer reference for the ${meta.season} season.`
      : heights === 0
        ? "No height_inches values, and the comparable pool is gated on "
          + "plausible height."
        : "Height-gated against the frozen NBA reference pool.",
  });

  const populationOk = meta.population_type === core.datasetFormat.fullBoardPopulation;
  const sizeOk = isFinite_(Number(meta.draft_size)) && Number(meta.draft_size) > 0;
  caps.push({
    id: "generalBoard", label: "General Board (Draft Probability & Overall Score)",
    available: Boolean(season) && seasonSupported && populationOk && sizeOk,
    reason: !seasonSupported
      ? `No NCAA season reference for ${meta.season}.`
      : !populationOk
        ? "Draft Probability and Draft Order were validated on final NCAA "
          + "early entrants. This file declares population_type "
          + `"${meta.population_type}", so a draft board would not mean what `
          + "it says — no probability is produced."
        : !sizeOk
          ? "draft_size is required: the board converts a predicted slot into "
            + "utility against the size of the draft being entered."
          : "Full frozen board, ranked within this imported class.",
  });

  return caps;
}

/** Model features that reached the estimator as the frozen train-median
 * because this file does not carry them. Reported, never hidden: a board
 * resting on many imputed inputs is a weaker statement than one that isn't. */
function imputedFeatures(core: RuntimeCore, rows: Features[]): string[] {
  const out: string[] = [];
  for (const name of core.draftProbability.featureOrder) {
    const anyPresent = rows.some((f) => isFinite_(f[name]));
    if (!anyPresent) out.push(name);
  }
  return out;
}

export function analyzeDataset(
  dataset: ParsedDataset,
  core: RuntimeCore,
  season: RuntimeSeason | null,
): AnalysisResult {
  const capabilities = detectCapabilities(dataset, core, season);
  const caps = capabilityMap(capabilities);
  const meta = dataset.metadata;

  const prospects: AnalyzedProspect[] = dataset.prospects.map((row) => {
    const features = buildFeatures(toPrimitives(row));
    return {
      id: String(row.prospect_id),
      name: String(row.name),
      school: row.school === null || row.school === undefined
        ? null : String(row.school),
      position: String(row.position ?? "UNKNOWN"),
      features,
      dimensions: {},
      dataCoverage: Number.NaN,
      profiles: {},
      comparables: null,
      draftProbability: null,
      orderPick: null,
      overallScore: null,
      boardRank: null,
      boardSignal: null,
      stageBQuality: null,
    };
  });

  if (season && caps.teamNeed.available) {
    for (const p of prospects) {
      const raw = componentPercentiles(p.features, p.position, core, season);
      const oriented = orientedComponents(raw, core);
      const dims = computeDimensions(oriented, core);
      p.dimensions = dims.scores;
      p.dataCoverage = dims.dataCoverage;
      for (const name of Object.keys(core.teamNeed.profiles)) {
        p.profiles[name] = scoreProfile(
          name, p.features, p.position, raw, oriented, dims.scores, core, season);
      }
    }
  }

  if (season && caps.comparables.available) {
    const cache = new Map<string, Float64Array>();
    for (const p of prospects) {
      const dims = ncaaDimensions(p.features, core, season, cache);
      p.comparables = findComparables(dims, p.features.height, core);
    }
  }

  if (season && caps.generalBoard.available) {
    const size = Number(meta.draft_size);
    const rows = prospects.map((p) => ({
      prospectId: p.id,
      probability: draftProbability(core, season, p.features, p.position),
      orderPick: draftOrderPick(core, p.features, p.position),
    }));
    const board = buildBoard(rows, size, core.frozen.neutralQuality);
    board.forEach((b, i) => {
      const p = prospects[i];
      p.draftProbability = b.draftProbability;
      p.orderPick = b.orderPick;
      p.overallScore = b.overallScore;
      p.boardRank = b.boardRank;
      p.boardSignal = b.boardSignal;
      p.stageBQuality = b.stageBQuality;
    });
  }

  return {
    datasetName: meta.dataset_name,
    season: meta.season,
    populationType: meta.population_type,
    draftSize: meta.draft_size,
    capabilities,
    prospects,
    imputedModelFeatures: caps.generalBoard.available
      ? imputedFeatures(core, prospects.map((p) => p.features)) : [],
  };
}

export { customFit };
