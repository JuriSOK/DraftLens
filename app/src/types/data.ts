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

export interface BoardInfo {
  rank: number;
  overallScore: number;
  /** 0-1 fraction. Display as a percentage. */
  draftProbability: number | null;
  /** 0-1 quality signal, NOT a predicted pick. Internal-facing only if shown. */
  draftOrderSignal: number | null;
}

export interface ProspectStats {
  pointsPer40: number | null;
  reboundsPer40: number | null;
  assistsPer40: number | null;
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
  board: BoardInfo;
  stats: ProspectStats;
  dimensions: Dimensions;
  profiles: Profiles;
  /** 0-1 fraction of Team Need components that had data. */
  coverage: number | null;
  comparables: Comparable[];
}

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
  methodologyFreeze: string;
  prospectCount: number;
  prospects: Prospect[];
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
