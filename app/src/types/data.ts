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
  /** Raw 3PA — for flagging thin shooting samples. */
  threePointAttempts: number | null;
  ftPct: number | null;
  /** Raw FTA — for flagging thin shooting samples. */
  ftAttempts: number | null;
  tsPct: number | null;
  /** Raw FGA — for flagging thin shooting samples (TS% has no frozen
   * reliability minimum, so this is shown alongside rather than used to
   * silently exclude anyone; see lib/statThresholds.ts). */
  fgAttempts: number | null;
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

/** A verified, freely-licensed portrait. Present only when identity AND
 * licence were both confirmed at export time — attribution and licence are
 * never optional for a shipped photo. */
export interface ProspectPhotoMeta {
  thumbnailUrl: string;
  sourceUrl: string | null;
  attribution: string;
  license: string;
  licenseUrl: string | null;
}

export interface Comparable {
  rank: number;
  nbaPlayerName: string;
  /** NBA player's height in inches — the plausibility gate's input, shown so
   * the comparison is checkable. */
  nbaHeightInches: number | null;
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
  /** Null when no verified, freely-licensed photo could be resolved. */
  photo: ProspectPhotoMeta | null;
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

export interface WatchlistSource {
  name: string;
  url: string;
  publicationDate: string;
  playersListed: number;
}

/** A 2027 projected watchlist entry. Never carries a board, Draft
 * Probability, or Overall Score — see docs/VALIDATION.md and the
 * Methodology page for why. */
export interface WatchlistProspect {
  id: string;
  name: string;
  school: string | null;
  classYear: string | null;
  photo: ProspectPhotoMeta | null;
  /** False for incoming freshmen with no NCAA record yet — every stats/
   * dimensions/profiles/comparables field below is null in that case, never
   * fabricated. */
  hasStats: boolean;
  stats: ProspectStats | null;
  dimensions: Dimensions | null;
  profiles: Profiles | null;
  coverage: number | null;
  comparables: Comparable[];
}

export interface YearWatchlist {
  status: "watchlist";
  label: string;
  consensusRule: string;
  sources: WatchlistSource[];
  prospectCount: number;
  returningCount: number;
  incomingCount: number;
  prospects: WatchlistProspect[];
}

export type YearData = YearAvailable | YearUnavailable | YearWatchlist;

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

/** One-line archetype meaning, derived directly from config/team_need.json's
 * profile definitions and rationale — not marketing copy. See the
 * Methodology page for the full formula behind each. */
export const PROFILE_DESCRIPTIONS: Record<ProfileKey, string> = {
  shooter:
    "Efficient AND high-volume perimeter shooting — needs both together, not one covering for the other.",
  slasher:
    "Shot diet and finishing at the rim: attempts near the basket, drawing contact, converting, and creating without an assist.",
  playmaker: "Creating shots for teammates while taking care of the ball.",
  threeAndD:
    "Perimeter shooting combined with box-score defensive production (steals and blocks) — needs real strength in both.",
  rimProtector:
    "Shot-blocking, defensive rebounding and size together — an interior presence, not just a shot-blocker.",
  stretchBig: "Frontcourt size combined with real perimeter shooting ability.",
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
