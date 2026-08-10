/** Validation of an imported file against DraftLens Dataset Format v1.
 *
 * The schema itself is Python's (`src/dataset_format.py`) and arrives in the
 * runtime bundle, so the browser cannot drift from what the analysis actually
 * requires. This file decides what to DO about a violation, and the
 * distinction it draws is the important part:
 *
 *   ERROR    the analysis would be wrong or impossible. Nothing is scored.
 *   WARNING  something is unavailable, and the rest still works.
 *
 * Messages name the row, the column, what was expected and what arrived,
 * because "invalid dataset" is not a fixable statement.
 */

import type { DatasetFormatSchema, FieldSpec, ParsedDataset, ProspectRow }
  from "../runtime/types";

export interface Issue {
  severity: "error" | "warning";
  row: number | null;
  field: string | null;
  message: string;
}

export interface ValidationResult {
  ok: boolean;
  errors: Issue[];
  warnings: Issue[];
  rowsDetected: number;
  validProspects: number;
  dataset: ParsedDataset | null;
}

function err(message: string, row: number | null = null,
             field: string | null = null): Issue {
  return { severity: "error", row, field, message };
}

function warn(message: string, row: number | null = null,
              field: string | null = null): Issue {
  return { severity: "warning", row, field, message };
}

function isBlank(value: unknown): boolean {
  return value === null || value === undefined || value === ""
    || (typeof value === "string" && value.trim() === "");
}

/** Numbers only. A string that is not a clean number is an error rather than
 * a silent NaN, because a silent NaN would become "not measured" and quietly
 * change what the prospect is scored on. */
function toNumber(value: unknown): number | null {
  if (typeof value === "number") return Number.isFinite(value) ? value : null;
  if (typeof value === "string") {
    const trimmed = value.trim().replace(/,/g, "");
    if (trimmed === "") return null;
    const parsed = Number(trimmed);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function checkField(spec: FieldSpec, raw: unknown, rowNumber: number,
                    schema: DatasetFormatSchema, issues: Issue[]): unknown {
  if (isBlank(raw)) {
    if (spec.required) {
      issues.push(err(`${spec.name} is required and is empty.`, rowNumber,
                      spec.name));
    }
    return null;
  }

  if (spec.type === "string") return String(raw).trim();

  if (spec.type === "enum") {
    const value = String(raw).trim();
    if (spec.name === "position" && !schema.positions.includes(value)) {
      issues.push(err(
        `Expected one of ${schema.positions.join(", ")}. Received "${value}". `
        + "Use UNKNOWN rather than a guess — DraftLens treats an unknown "
        + "position as unknown, never as an average.", rowNumber, spec.name));
      return null;
    }
    return value;
  }

  const value = toNumber(raw);
  if (value === null) {
    issues.push(err(`Expected a number. Received "${String(raw)}".`, rowNumber,
                    spec.name));
    return null;
  }
  if (spec.integer && !Number.isInteger(value)) {
    issues.push(err(`Expected a whole number (a season total). Received `
      + `${value}.`, rowNumber, spec.name));
    return null;
  }
  if (spec.min !== null && value < spec.min) {
    issues.push(err(`Expected a value of at least ${spec.min} (${spec.unit}). `
      + `Received ${value}.`, rowNumber, spec.name));
    return null;
  }
  if (spec.max !== null && value > spec.max) {
    issues.push(err(`Expected a value of at most ${spec.max} (${spec.unit}). `
      + `Received ${value}.`, rowNumber, spec.name));
    return null;
  }
  return value;
}

/** Internal consistency a range check cannot catch — and the place a
 * misunderstood unit actually shows up. Someone who puts 41.2 in
 * `three_points_made` meaning "41.2%" produces more makes than attempts. */
function checkConsistency(row: ProspectRow, rowNumber: number, issues: Issue[]) {
  const pairs: [string, string][] = [
    ["field_goals_made", "field_goals_attempted"],
    ["three_points_made", "three_points_attempted"],
    ["free_throws_made", "free_throws_attempted"],
  ];
  for (const [made, attempted] of pairs) {
    const m = toNumber(row[made]);
    const a = toNumber(row[attempted]);
    if (m !== null && a !== null && m > a) {
      issues.push(err(
        `${made} (${m}) exceeds ${attempted} (${a}). DraftLens takes season `
        + "COUNTS, not percentages — a shooting percentage in a makes column "
        + "looks like this.", rowNumber, made));
    }
  }

  const three = toNumber(row.three_points_attempted);
  const fga = toNumber(row.field_goals_attempted);
  if (three !== null && fga !== null && three > fga) {
    issues.push(err(
      `three_points_attempted (${three}) exceeds field_goals_attempted `
      + `(${fga}). Field goals attempted must include three-point attempts.`,
      rowNumber, "three_points_attempted"));
  }

  const orb = toNumber(row.offensive_rebounds);
  const drb = toNumber(row.defensive_rebounds);
  const trb = toNumber(row.total_rebounds);
  if (orb !== null && drb !== null && trb !== null
      && Math.abs(orb + drb - trb) > 1) {
    issues.push(warn(
      `total_rebounds (${trb}) does not equal offensive + defensive `
      + `(${orb + drb}). DraftLens uses the value you supplied for each.`,
      rowNumber, "total_rebounds"));
  }

  const minutes = toNumber(row.minutes);
  const games = toNumber(row.games_played);
  if (minutes !== null && games !== null && games > 0) {
    const perGame = minutes / games;
    if (perGame > 45) {
      issues.push(err(
        `minutes (${minutes}) over ${games} games is ${perGame.toFixed(1)} `
        + "per game, which exceeds a full game. DraftLens expects TOTAL "
        + "season minutes.", rowNumber, "minutes"));
    } else if (perGame < 1) {
      // Supplying minutes PER GAME instead of the season total lands here:
      // the number is roughly one game's worth spread across a whole season.
      issues.push(err(
        `minutes (${minutes}) over ${games} games is ${perGame.toFixed(2)} `
        + "per game. DraftLens expects TOTAL season minutes, not minutes per "
        + "game — multiply by games played.", rowNumber, "minutes"));
    }
  }

  const started = toNumber(row.games_started);
  if (started !== null && games !== null && started > games) {
    issues.push(err(`games_started (${started}) exceeds games_played `
      + `(${games}).`, rowNumber, "games_started"));
  }
}

export function validateDataset(
  dataset: ParsedDataset,
  schema: DatasetFormatSchema,
  supportedSeasons: number[],
): ValidationResult {
  const errors: Issue[] = [];
  const warnings: Issue[] = [];

  // ---------------------------------------------------------- metadata
  if (dataset.schemaVersion !== schema.schemaVersion) {
    errors.push(err(`schema_version must be ${schema.schemaVersion}. Received `
      + `${String(dataset.schemaVersion)}.`, null, "schema_version"));
  }
  const meta = dataset.metadata;
  if (isBlank(meta.dataset_name)) {
    errors.push(err("dataset_name is required.", null, "dataset_name"));
  }
  const season = toNumber(meta.season);
  if (season === null || !Number.isInteger(season)) {
    errors.push(err(`season must be a whole year, e.g. 2026 for the 2025-26 `
      + `season. Received "${String(meta.season)}".`, null, "season"));
  } else if (!supportedSeasons.includes(season)) {
    // Not an error: descriptive analysis still works. But nothing that needs
    // a peer distribution can be produced, and no nearby season stands in.
    warnings.push(warn(
      `DraftLens has NCAA peer references for `
      + `${Math.min(...supportedSeasons)}-${Math.max(...supportedSeasons)} `
      + `only. Season ${season} is outside that range, so Basketball `
      + "Profile, Team Need, NBA Comparables and the General Board are "
      + "unavailable. No neighbouring season is substituted.",
      null, "season"));
  }
  if (!Object.keys(schema.populationTypes).includes(meta.population_type)) {
    errors.push(err(
      `population_type must be one of `
      + `${Object.keys(schema.populationTypes).join(", ")}. Received `
      + `"${String(meta.population_type)}".`, null, "population_type"));
  } else if (meta.population_type !== schema.fullBoardPopulation) {
    warnings.push(warn(
      `population_type is "${meta.population_type}", so no General Board is `
      + "produced. Draft Probability and Draft Order were validated on final "
      + "NCAA early entrants; applied to another population they would not "
      + "mean what they say.", null, "population_type"));
  }
  const draftSize = toNumber(meta.draft_size);
  if (draftSize === null && meta.population_type === schema.fullBoardPopulation) {
    warnings.push(warn(
      "draft_size is required for General Board analysis — the board converts "
      + "a predicted slot into utility against the size of the draft being "
      + "entered.", null, "draft_size"));
  }

  // ------------------------------------------------------------- rows
  const rows = dataset.prospects;
  const limits = schema.limits;
  if (rows.length === 0) {
    errors.push(err("No prospect rows found."));
  } else if (rows.length < limits.minRows) {
    errors.push(err(
      `${rows.length} rows found; at least ${limits.minRows} are needed. `
      + "Overall Score is a percentile WITHIN the imported class, so a "
      + "handful of players cannot produce a meaningful board."));
  } else if (rows.length > limits.maxRows) {
    errors.push(err(`${rows.length} rows found; the limit is `
      + `${limits.maxRows}. This tool analyses a draft class, and the whole `
      + "file is held in browser memory."));
  }

  // Columns that state what actually happened. Refused, not ignored: a file
  // carrying one is a file whose author may expect it to be used.
  const present = new Set<string>();
  for (const row of rows) for (const key of Object.keys(row)) present.add(key);
  const known = new Set(schema.prospectFields.map((f) => f.name));

  for (const column of present) {
    const lower = column.toLowerCase().trim();
    if (schema.prohibitedFields.includes(lower)) {
      errors.push(err(
        `Column "${column}" records a draft outcome. Imported analysis is `
        + "PRE-DRAFT: DraftLens will not run with an outcome column present, "
        + "even unused. Remove the column and upload again.", null, column));
    } else if (schema.derivedRateFields.includes(lower)) {
      errors.push(err(
        `Column "${column}" is a rate DraftLens computes itself. Supply the `
        + "season counts instead (makes and attempts); every percentage is "
        + "derived with the same formula used for DraftLens's own data.",
        null, column));
    } else if (!known.has(column)) {
      warnings.push(warn(`Column "${column}" is not part of the format and is `
        + "ignored.", null, column));
    }
  }

  const seenIds = new Map<string, number>();
  const cleaned: ProspectRow[] = [];
  const specs = schema.prospectFields;

  rows.forEach((row, index) => {
    const rowNumber = index + 1;
    const rowIssues: Issue[] = [];
    const out: ProspectRow = {};

    for (const spec of specs) {
      const value = checkField(spec, row[spec.name], rowNumber, schema, rowIssues);
      out[spec.name] = value as string | number | null;
    }
    checkConsistency(row, rowNumber, rowIssues);

    const id = out.prospect_id;
    if (typeof id === "string" && id !== "") {
      const first = seenIds.get(id);
      if (first !== undefined) {
        rowIssues.push(err(
          `Duplicate prospect_id "${id}" (already used on row ${first}). Ids `
          + "must be unique — DraftLens will not merge two rows into one "
          + "player.", rowNumber, "prospect_id"));
      } else {
        seenIds.set(id, rowNumber);
      }
    }

    for (const issue of rowIssues) {
      (issue.severity === "error" ? errors : warnings).push(issue);
    }
    if (!rowIssues.some((i) => i.severity === "error")) cleaned.push(out);
  });

  // ------------------------------------------------- optional capability
  const groupPresence = (group: string) => {
    const names = specs.filter((f) => f.group === group).map((f) => f.name);
    return cleaned.some((r) => names.some((n) => r[n] !== null));
  };
  if (cleaned.length > 0) {
    if (!groupPresence("team_context")) {
      warnings.push(warn(
        "No team-context columns. Usage, assist, rebound, steal and block "
        + "rates cannot be computed, so the dimensions built on them lose "
        + "components and the model receives the frozen training median for "
        + "usage rate."));
    }
    if (!groupPresence("shot_profile")) {
      warnings.push(warn(
        "No shot-profile columns. The Rim Pressure dimension is unavailable "
        + "and the shot-location model features reach the estimator as the "
        + "frozen training median."));
    }
    const withHeight = cleaned.filter((r) => r.height_inches !== null).length;
    if (withHeight < cleaned.length) {
      warnings.push(warn(
        `${cleaned.length - withHeight} of ${cleaned.length} players have no `
        + "height_inches. Those players get no Size dimension and no NBA "
        + "Comparables — the comparable pool is gated on plausible height."));
    }
  }

  return {
    ok: errors.length === 0 && cleaned.length > 0,
    errors,
    warnings,
    rowsDetected: rows.length,
    validProspects: cleaned.length,
    dataset: errors.length === 0 && cleaned.length > 0
      ? { ...dataset, metadata: { ...meta, season: season as number,
                                  draft_size: draftSize },
          prospects: cleaned }
      : null,
  };
}
