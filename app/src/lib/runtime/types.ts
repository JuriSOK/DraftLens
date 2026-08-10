/** Shapes of the Python-generated runtime bundle and of an imported dataset.
 *
 * The bundle is written by `src/runtime_bundle.py` and is the only source of
 * model parameters in the browser. Nothing here is a default or a fallback:
 * if a field is missing from the bundle the runtime refuses to score rather
 * than substituting a value. */

export interface PackedSorted {
  encoding: "f64le-b64";
  count: number;
  data: string;
}

export interface LinearModel {
  featureOrder: string[];
  imputerMedians: number[];
  scalerMean: number[];
  scalerScale: number[];
  positionCategories: string[];
  coefNumeric: number[];
  coefPosition: number[];
  intercept: number;
}

export interface DraftOrderModel extends LinearModel {
  targetMean: number;
  targetStd: number;
  target: string;
}

export interface FieldSpec {
  name: string;
  group: string;
  required: boolean;
  type: "string" | "number" | "integer" | "enum";
  unit: string;
  description: string;
  min: number | null;
  max: number | null;
  integer: boolean;
}

export interface DatasetFormatSchema {
  schemaVersion: number;
  name: string;
  positions: string[];
  populationTypes: Record<string, string>;
  fullBoardPopulation: string;
  groups: Record<string, string>;
  metadataFields: FieldSpec[];
  prospectFields: FieldSpec[];
  prohibitedFields: string[];
  derivedRateFields: string[];
  limits: { maxFileBytes: number; maxRows: number; minRows: number };
  excelSheets: { metadata: string; prospects: string };
}

export interface TeamNeedComponent {
  metric: string;
  orientation: "HIGHER_IS_BETTER" | "LOWER_IS_BETTER";
}

export interface TeamNeedDimension {
  components: TeamNeedComponent[];
  reference_group: string;
  [key: string]: unknown;
}

export interface NbaPoolPlayer {
  id: number;
  name: string;
  position: string;
  heightInches: number | null;
  referenceSeasons: number[];
  dimensions: (number | null)[];
}

export interface RuntimeCore {
  schemaVersion: number;
  generatedAt: string;
  supportedSeasons: number[];
  draftSizeByYear: Record<string, number>;
  frozen: {
    draftProbability: Record<string, unknown>;
    draftOrder: Record<string, unknown>;
    generalBoard: Record<string, unknown>;
    neutralQuality: number;
  };
  draftProbability: LinearModel;
  draftOrder: DraftOrderModel;
  seasonRelativeMetrics: string[];
  datasetFormat: DatasetFormatSchema;
  teamNeed: {
    dimensions: Record<string, TeamNeedDimension>;
    profiles: Record<string, Record<string, unknown>>;
    reliabilityMinimums: Record<string, { denominator: string; min: number } | string>;
    coverage: Record<string, number>;
    customMode: Record<string, unknown>;
  };
  comparables: {
    dimensions: Record<string, { metrics: string[]; invert: string[]; kind: string }>;
    dimensionOrder: string[];
    nComparables: number;
    minSharedCoverage: number;
    heightWindowsInches: number[];
    nbaPool: NbaPoolPlayer[];
    similarityThresholds: {
      scores: number[];
      upperDistance: (number | null)[];
      referenceSize: number;
    };
  };
}

export interface RuntimeSeason {
  schemaVersion: number;
  season: number;
  seasonRelative: Record<string, Record<string, { mean: number | null; std: number | null }>>;
  teamNeedGrids: Record<string, Record<string, { values: number[]; n: number }>>;
  comparableReference: Record<string, PackedSorted>;
}

// ------------------------------------------------------------ imported data
export interface DatasetMetadata {
  dataset_name: string;
  season: number;
  population_type: string;
  draft_size: number | null;
}

export type ProspectRow = Record<string, string | number | null>;

export interface ParsedDataset {
  schemaVersion: number;
  metadata: DatasetMetadata;
  prospects: ProspectRow[];
  sourceName: string;
  sourceKind: "json" | "excel";
}
