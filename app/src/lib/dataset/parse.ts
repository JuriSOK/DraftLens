/** Reading a user's file into one canonical shape.
 *
 * JSON and Excel are two ways of writing the same dataset, so both land on
 * the identical `ParsedDataset` and everything downstream is unaware of which
 * arrived. Parsing NEVER repairs, guesses or coerces meaning — a malformed
 * file raises, and a wrong-looking value is passed through for validation to
 * report with its row and column. Silent repair is how a dataset gets
 * analysed as something other than what its author wrote.
 *
 * THE FILE IS NEVER SENT ANYWHERE. Reading happens through the FileReader
 * API in the user's own browser; there is no request, no upload, no
 * persistence.
 */

import type { DatasetFormatSchema, DatasetMetadata, ParsedDataset, ProspectRow }
  from "../runtime/types";

export class DatasetParseError extends Error {}

function coerceMetadata(raw: Record<string, unknown>): DatasetMetadata {
  return {
    dataset_name: raw.dataset_name === undefined || raw.dataset_name === null
      ? "" : String(raw.dataset_name),
    season: Number(raw.season),
    population_type: raw.population_type === undefined
      || raw.population_type === null ? "" : String(raw.population_type).trim(),
    draft_size: raw.draft_size === undefined || raw.draft_size === null
      || raw.draft_size === "" ? null : Number(raw.draft_size),
  };
}

export function parseJsonDataset(text: string, sourceName: string): ParsedDataset {
  let payload: unknown;
  try {
    payload = JSON.parse(text);
  } catch (error) {
    throw new DatasetParseError(
      `The file is not valid JSON: ${(error as Error).message}`);
  }
  if (typeof payload !== "object" || payload === null || Array.isArray(payload)) {
    throw new DatasetParseError(
      "The top level must be an object with \"metadata\" and \"prospects\".");
  }
  const root = payload as Record<string, unknown>;
  if (!Array.isArray(root.prospects)) {
    throw new DatasetParseError(
      "\"prospects\" is missing or is not a list. See the JSON template.");
  }
  const metadata = typeof root.metadata === "object" && root.metadata !== null
    ? (root.metadata as Record<string, unknown>) : {};

  return {
    schemaVersion: Number(root.schemaVersion ?? metadata.schema_version ?? NaN),
    metadata: coerceMetadata(metadata),
    prospects: root.prospects.map((row) => ({ ...(row as ProspectRow) })),
    sourceName,
    sourceKind: "json",
  };
}

type Sheet = (string | number | boolean | Date | null)[][];

/** Excel workbook -> the same canonical dataset.
 *
 * Sheet 1 is a two-column metadata table; sheet 2 is one row per prospect
 * under the documented headers. Cells arrive as whatever the workbook stored
 * them as and are handed to validation untouched.
 */
export function parseWorkbookSheets(
  metadataSheet: Sheet,
  prospectSheet: Sheet,
  sourceName: string,
): ParsedDataset {
  const meta: Record<string, unknown> = {};
  for (const row of metadataSheet) {
    if (!row || row.length < 2) continue;
    const key = row[0] === null || row[0] === undefined
      ? "" : String(row[0]).trim();
    if (!key || key.toLowerCase() === "key") continue;
    meta[key] = row[1];
  }

  if (prospectSheet.length === 0) {
    throw new DatasetParseError(
      "The prospects sheet is empty. It needs a header row followed by one "
      + "row per player.");
  }
  const header = prospectSheet[0].map((cell) =>
    cell === null || cell === undefined ? "" : String(cell).trim());
  if (header.every((h) => h === "")) {
    throw new DatasetParseError("The prospects sheet has no header row.");
  }

  const prospects: ProspectRow[] = [];
  for (let i = 1; i < prospectSheet.length; i += 1) {
    const row = prospectSheet[i];
    if (!row || row.every((cell) => cell === null || cell === undefined
                                    || String(cell).trim() === "")) continue;
    const out: ProspectRow = {};
    header.forEach((name, column) => {
      if (!name) return;
      const cell = row[column];
      out[name] = cell instanceof Date
        ? cell.toISOString()
        : (cell as string | number | null) ?? null;
    });
    prospects.push(out);
  }

  return {
    schemaVersion: Number(meta.schema_version ?? NaN),
    metadata: coerceMetadata(meta),
    prospects,
    sourceName,
    sourceKind: "excel",
  };
}

/** Read an .xlsx/.xls workbook in the browser.
 *
 * `read-excel-file` is loaded on demand so its parser is downloaded only by
 * someone who actually imports a spreadsheet.
 */
export async function parseExcelDataset(
  file: File,
  schema: DatasetFormatSchema,
): Promise<ParsedDataset> {
  const { readSheet } = await import("read-excel-file/browser");
  const names = schema.excelSheets;

  const read = async (sheet: string | number): Promise<Sheet> => {
    const rows = await readSheet(file, sheet);
    return rows as unknown as Sheet;
  };

  let metadataSheet: Sheet;
  let prospectSheet: Sheet;
  try {
    metadataSheet = await read(names.metadata);
    prospectSheet = await read(names.prospects);
  } catch {
    // Fall back to sheet position for a workbook whose tabs were renamed.
    try {
      metadataSheet = await read(1);
      prospectSheet = await read(2);
    } catch (error) {
      throw new DatasetParseError(
        `Could not read the workbook. It needs a "${names.metadata}" sheet and `
        + `a "${names.prospects}" sheet (or those two as the first and second `
        + `sheets). ${(error as Error).message}`);
    }
  }
  return parseWorkbookSheets(metadataSheet, prospectSheet, file.name);
}

export async function parseDatasetFile(
  file: File,
  schema: DatasetFormatSchema,
): Promise<ParsedDataset> {
  if (file.size > schema.limits.maxFileBytes) {
    throw new DatasetParseError(
      `The file is ${(file.size / (1024 * 1024)).toFixed(1)} MB; the limit is `
      + `${Math.round(schema.limits.maxFileBytes / (1024 * 1024))} MB. This `
      + "tool analyses a draft class, and the whole file is parsed in your "
      + "browser.");
  }
  const name = file.name.toLowerCase();
  if (name.endsWith(".json")) {
    return parseJsonDataset(await file.text(), file.name);
  }
  if (name.endsWith(".xlsx") || name.endsWith(".xls")) {
    return parseExcelDataset(file, schema);
  }
  throw new DatasetParseError(
    `"${file.name}" is not a supported format. DraftLens reads Excel `
    + "(.xlsx, .xls) and JSON (.json).");
}
