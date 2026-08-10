/** Draft Probability, Draft Order and the General Board, in the browser.
 *
 * The parameters come from the frozen fitted pipelines via the runtime
 * bundle — no coefficient is written here and none is fitted here. What this
 * file contributes is the inference path those pipelines imply:
 *
 *     season-relative representation -> train-median imputation
 *     -> standard scaling -> one-hot position -> linear model
 *
 * and then the frozen board combination. Each step mirrors one scikit-learn
 * transformer, with the same treatment of missing values, so the browser and
 * Python answer identically. The parity harness enforces that claim.
 */

import { NA, clamp, isFinite_, rintHalfEven, withinBoardPercentile } from "./numeric";
import type { Features } from "./features";
import type { DraftOrderModel, LinearModel, RuntimeCore, RuntimeSeason } from "./types";

/** `board.preprocessing.season_relative`.
 *
 * Replaces a covered metric by its z-score against the SAME season and coarse
 * position in the full NCAA population. A prospect whose (season, position)
 * reference is absent falls back to the "G" reference exactly as Python does;
 * if that is missing too, or the standard deviation is not usable, the value
 * becomes missing and the imputer handles it downstream. Nothing is guessed.
 */
export function seasonRelative(
  features: Features,
  position: string,
  metrics: string[],
  season: RuntimeSeason,
): Features {
  const out: Features = { ...features };
  for (const metric of metrics) {
    let ref = season.seasonRelative[position]?.[metric];
    if (!ref) ref = season.seasonRelative.G?.[metric];
    if (!ref) {
      out[metric] = NA;
      continue;
    }
    const { mean, std } = ref;
    if (mean === null || std === null || !isFinite_(std) || std <= 0) {
      out[metric] = NA;
      continue;
    }
    const v = features[metric];
    out[metric] = isFinite_(v) ? (v - mean) / std : NA;
  }
  return out;
}

/** Impute -> scale -> one-hot -> dot product. One row of a fitted
 * `ColumnTransformer` + linear estimator. */
function linearScore(model: LinearModel, features: Features, position: string): number {
  let z = model.intercept;
  for (let i = 0; i < model.featureOrder.length; i += 1) {
    const raw = features[model.featureOrder[i]];
    // SimpleImputer(strategy="median"), fitted on the training population
    const filled = isFinite_(raw) ? raw : model.imputerMedians[i];
    // StandardScaler
    const scaled = (filled - model.scalerMean[i]) / model.scalerScale[i];
    z += scaled * model.coefNumeric[i];
  }
  // OneHotEncoder(handle_unknown="ignore"): an unseen position contributes
  // nothing rather than falling back to some other category.
  const idx = model.positionCategories.indexOf(position);
  if (idx >= 0) z += model.coefPosition[idx];
  return z;
}

export function draftProbability(
  core: RuntimeCore,
  season: RuntimeSeason,
  features: Features,
  position: string,
): number {
  const represented = seasonRelative(
    features, position, core.seasonRelativeMetrics, season);
  const z = linearScore(core.draftProbability, represented, position);
  return 1 / (1 + Math.exp(-z));
}

/** The internal Draft Order signal, on the raw pick scale.
 *
 * NEVER shown to a user as a pick: the frozen model's error is 13.2 picks of
 * 60 and it emits illegal picks. It exists only to feed the board. */
export function draftOrderPick(core: RuntimeCore, features: Features,
                               position: string): number {
  const model: DraftOrderModel = core.draftOrder;
  // Draft Order's frozen representation is STANDARD — no season-relative step.
  const standardised = linearScore(model, features, position);
  const y = standardised * model.targetStd + model.targetMean;
  if (model.target !== "RAW_PICK") {
    throw new Error(`unsupported Draft Order target ${model.target}`);
  }
  return y;
}

/** `board.scoring.draft_slot_utility` — predicted pick -> (0, 1] utility. */
export function draftSlotUtility(pick: number, draftSize: number): number {
  const clipped = clamp(pick, 1.0, draftSize);
  return (draftSize + 1.0 - clipped) / draftSize;
}

export interface BoardRow {
  prospectId: string;
  draftProbability: number;
  orderPick: number;
  stageBQuality: number;
  boardSignal: number;
  overallScore: number;
  boardRank: number;
}

/** The frozen General Board: probability x draft-slot utility, scored as a
 * percentile WITHIN THIS CLASS. Overall Score is class-relative by
 * definition, so an imported class is ranked against itself and never mixed
 * with DraftLens's own 2026 pool. */
export function buildBoard(
  rows: { prospectId: string; probability: number; orderPick: number }[],
  draftSize: number,
  neutralQuality: number,
): BoardRow[] {
  const quality = rows.map((r) => {
    const q = isFinite_(r.orderPick) ? draftSlotUtility(r.orderPick, draftSize) : NA;
    return q;
  });
  // A missing Stage B prediction takes the board's median utility, not a low
  // one: rows with missing data were disproportionately undrafted
  // historically, so penalising missingness would smuggle the outcome back in.
  const finite = quality.filter(isFinite_).sort((a, b) => a - b);
  const median = finite.length === 0
    ? neutralQuality
    : finite.length % 2
      ? finite[(finite.length - 1) / 2]
      : (finite[finite.length / 2 - 1] + finite[finite.length / 2]) / 2;
  const q = quality.map((v) => (isFinite_(v) ? v : median));

  const signal = rows.map((r, i) => r.probability * q[i]);
  const pct = withinBoardPercentile(signal, neutralQuality);
  const score = pct.map((p) => rintHalfEven(clamp(p, 0, 1) * 100));

  const out: BoardRow[] = rows.map((r, i) => ({
    prospectId: r.prospectId,
    draftProbability: r.probability,
    orderPick: r.orderPick,
    stageBQuality: q[i],
    boardSignal: signal[i],
    overallScore: score[i],
    boardRank: 0,
  }));

  // Order by the CONTINUOUS signal so integer-score ties never reorder
  // anything — `board.scoring.rank_board`, stable sort.
  const order = out.map((row, i) => ({ row, i }));
  order.sort((a, b) => (b.row.boardSignal - a.row.boardSignal) || (a.i - b.i));
  order.forEach((entry, rank) => {
    entry.row.boardRank = rank + 1;
  });
  return out;
}
