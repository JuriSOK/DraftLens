// Types for the static public export written by `scripts/build.py app-data`
// (src/app_export.py). This is the ONLY data the application reads — no
// field here is computed in the browser except the custom Team Need formula
// in lib/customFit.ts, which is explicitly a weighted average of numbers
// already present below, not a re-derivation of any frozen system.

export type ProfileKey =
  | "shooter"
  | "slasher"
  | "playmaker"
  | "threeAndD"
  | "rimProtector"
  | "stretchBig";

export type CustomDimensionKey =
  | "shooting"
  | "playmaking"
  | "defensiveProduction"
  | "rebounding"
  | "size";

export type Eligibility = "ELIGIBLE" | "OUT_OF_POSITION" | "UNKNOWN_POSITION";

/** A prospect's process status for a Draft class — an eligibility/declaration
 * fact, never a Draft outcome. FINAL_ENTRY = remained through the withdrawal
 * deadline (the population DraftLens's one-time holdout evaluation scored).
 * WITHDRAWN = declared, then withdrew before the draft. */
export type PopulationStatus = "FINAL_ENTRY" | "WITHDRAWN";

export interface BoardInfo {
  rank: number;
  overallScore: number;
  /** 0-1 fraction. Display as a percentage. */
  draftProbability: number | null;
  /** 0-1 quality signal, NOT a predicted pick. Internal-facing only if shown. */
  draftOrderSignal: number | null;
}

export interface ProspectStats {
  /** Inches. Format with formatHeight(). */
  heightInches: number | null;
  pointsPer40: number | null;
  reboundsPer40: number | null;
  assistsPer40: number | null;
  stealsPer40: number | null;
  blocksPer40: number | null;
  turnoversPer40: number | null;
  threePointPct: number | null;
  ftPct: number | null;
  tsPct: number | null;
  minutesPerGame: number | null;
  gamesPlayed: number | null;
}

export interface Dimensions {
  shooting: number | null;
  playmaking: number | null;
  defensiveProduction: number | null;
  rebounding: number | null;
  size: number | null;
  rimPressure: number | null;
}

export interface ProfileFit {
  fitScore: number | null;
  eligibility: Eligibility;
}

export type Profiles = Record<ProfileKey, ProfileFit>;

export interface DimensionDelta {
  label: string;
  prospectPercentile: number | null;
  nbaPercentile: number | null;
}

export interface Comparable {
  rank: number;
  nbaPlayerName: string;
  /** 0-100. Compresses toward 97-100 by design — see docs/VALIDATION.md. */
  similarityScore: number | null;
  referenceSeasons: string[];
  closestDimensions: DimensionDelta[];
  differences: DimensionDelta[];
}

export interface Prospect {
  id: string;
  name: string;
  school: string;
  position: string;
  populationStatus: PopulationStatus;
  /** The frozen 26-prospect holdout board. Null for WITHDRAWN prospects, and
   * for any FINAL_ENTRY prospect the declared-pool computation could not
   * reach (should not happen in practice). */
  finalEntrantsBoard: BoardInfo | null;
  /** The larger all-declared product board — an additional exploration
   * generated after the holdout, not the holdout itself. Null only for a
   * prospect this export could not score at all (see
   * insufficientDataProspects instead). */
  declaredBoard: BoardInfo | null;
  stats: ProspectStats;
  dimensions: Dimensions;
  profiles: Profiles;
  /** 0-1 fraction of Team Need components that had data. */
  coverage: number | null;
  comparables: Comparable[];
}

/** An officially declared prospect DraftLens could not build a feature
 * vector for (no matching NCAA statistical record). Shown with an
 * "Insufficient data" label — never silently dropped, never scored. */
export interface InsufficientDataProspect {
  id: string;
  name: string;
  school: string | null;
  position: string | null;
  populationStatus: PopulationStatus;
}

export interface OfficialSource {
  name: string;
  url: string;
  announcementDate: string;
  note: string;
}

export interface DeclaredAudit {
  official_declared: number;
  matched: number;
  unmatched: number;
  scoreable: number;
  insufficient_data: number;
  box_dupe_rows_removed: number;
}

export interface YearAvailable {
  status: "available";
  methodologyFreeze: string | null;
  finalEntrantsCount: number;
  declaredCount: number;
  scoreableDeclaredCount: number;
  officialSource: OfficialSource | null;
  audit: DeclaredAudit | null;
  prospects: Prospect[];
  insufficientDataProspects: InsufficientDataProspect[];
}

export interface YearUnavailable {
  status: "unavailable";
  reason: string;
}

export type YearData = YearAvailable | YearUnavailable;

export interface HistoricalValidation {
  developmentPopulation: [number, number, number];
  draftProbabilityMacroAuc: number;
  draftOrderMacroSpearman: number;
  generalBoardBinaryAuc: number;
  generalBoardGradedNdcg: number;
}

export interface Holdout2026Validation {
  generalBoardGradedNdcg: number | null;
  supportLabel: string | null;
  draftedShare: number | null;
}

export interface ValidationSummary {
  historical: HistoricalValidation;
  holdout2026: Holdout2026Validation | null;
  noPostHoldoutTuning: boolean;
  note: string;
}

export interface MethodologySummary {
  generalBoard: string;
  teamNeed: string;
  comparables: string;
  validation: string;
}

export interface DraftLensData {
  version: string;
  generatedAt: string;
  years: Record<string, YearData>;
  teamNeedProfiles: ProfileKey[];
  customDimensions: CustomDimensionKey[];
  methodologySummary: MethodologySummary;
  validationSummary: ValidationSummary;
}

export const PROFILE_LABELS: Record<ProfileKey, string> = {
  shooter: "Shooter",
  slasher: "Slasher / Rim Attacker",
  playmaker: "Playmaker",
  threeAndD: "3&D Wing",
  rimProtector: "Rim Protector",
  stretchBig: "Stretch Big",
};

export const DIMENSION_LABELS: Record<keyof Dimensions, string> = {
  shooting: "Shooting",
  playmaking: "Playmaking",
  defensiveProduction: "Defensive Production",
  rebounding: "Rebounding",
  size: "Size",
  rimPressure: "Rim Pressure",
};

export const CUSTOM_DIMENSION_LABELS: Record<CustomDimensionKey, string> = {
  shooting: "Shooting",
  playmaking: "Playmaking",
  defensiveProduction: "Defensive Production",
  rebounding: "Rebounding",
  size: "Size",
};

/** Which NCAA peer group a Basketball Profile dimension is measured against.
 * Mirrors config/team_need.json's per-dimension reference_group — must not
 * claim a uniform peer group across dimensions that don't share one. */
export const DIMENSION_PEER_GROUP: Record<keyof Dimensions, "GLOBAL" | "POSITION"> = {
  shooting: "GLOBAL",
  playmaking: "GLOBAL",
  defensiveProduction: "POSITION",
  rebounding: "POSITION",
  size: "GLOBAL",
  rimPressure: "GLOBAL",
};
