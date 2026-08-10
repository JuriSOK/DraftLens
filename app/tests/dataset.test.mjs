/** Dataset Lab unit tests: parsing, validation, and capability detection.
 *
 * These cover the decisions a user actually hits — a wrong unit, a duplicate
 * id, an outcome column, an unsupported season — and assert that each is
 * reported rather than absorbed. The analytical stack is covered separately
 * and far more strictly by `parity.mjs`.
 *
 *     node --test app/tests/
 */

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { register } from "node:module";
import test from "node:test";
import assert from "node:assert/strict";

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, "../..");
register("./ts-loader.mjs", import.meta.url);

const { parseJsonDataset, parseWorkbookSheets, DatasetParseError } =
  await import("../src/lib/dataset/parse.ts");
const { validateDataset } = await import("../src/lib/dataset/validate.ts");
const { detectCapabilities } = await import("../src/lib/runtime/analyze.ts");

const core = JSON.parse(
  readFileSync(resolve(root, "app/public/data/runtime/core.json"), "utf8"));
const schema = core.datasetFormat;
const seasons = core.supportedSeasons;

const TEMPLATE = JSON.parse(readFileSync(
  resolve(root, "app/public/templates/draftlens_dataset_template.json"), "utf8"));

/** A minimal valid file: the template's example row, repeated with unique
 * ids so it clears the minimum class size. */
function makeDataset(overrides = {}, rowOverrides = []) {
  const rows = [];
  for (let i = 0; i < 8; i += 1) {
    rows.push({
      ...TEMPLATE.prospects[0],
      prospect_id: `P${i}`,
      name: `Player ${i}`,
      ...(rowOverrides[i] ?? {}),
    });
  }
  return {
    schemaVersion: 1,
    metadata: { ...TEMPLATE.metadata, ...overrides },
    prospects: rows,
    sourceName: "test.json",
    sourceKind: "json",
  };
}

const validate = (dataset) => validateDataset(dataset, schema, seasons);

// ------------------------------------------------------------------ parsing
test("JSON parser rejects malformed JSON with a readable message", () => {
  assert.throws(() => parseJsonDataset("{not json", "bad.json"),
                (e) => e instanceof DatasetParseError
                  && /not valid JSON/.test(e.message));
});

test("JSON parser rejects a file with no prospects list", () => {
  assert.throws(() => parseJsonDataset('{"metadata":{}}', "bad.json"),
                (e) => /prospects/.test(e.message));
});

test("JSON parser reads metadata and rows", () => {
  const parsed = parseJsonDataset(JSON.stringify(TEMPLATE), "t.json");
  assert.equal(parsed.metadata.season, 2026);
  assert.equal(parsed.metadata.population_type, "ncaa_early_entry");
  assert.equal(parsed.prospects.length, 1);
});

test("Excel and JSON produce the same canonical representation", () => {
  const row = TEMPLATE.prospects[0];
  const header = Object.keys(row);
  const parsed = parseWorkbookSheets(
    [["Key", "Value"],
     ["schema_version", 1],
     ["dataset_name", "My Draft Class"],
     ["season", 2026],
     ["population_type", "ncaa_early_entry"],
     ["draft_size", 60]],
    [header, header.map((k) => row[k])],
    "t.xlsx");

  assert.equal(parsed.schemaVersion, 1);
  assert.equal(parsed.metadata.season, 2026);
  assert.equal(parsed.metadata.draft_size, 60);
  assert.equal(parsed.sourceKind, "excel");
  assert.deepEqual(parsed.prospects[0], row);
});

test("Excel parser rejects a sheet with no header row", () => {
  assert.throws(() => parseWorkbookSheets([["Key", "Value"]], [], "t.xlsx"),
                (e) => e instanceof DatasetParseError);
});

// --------------------------------------------------------------- validation
test("a well-formed dataset validates", () => {
  const result = validate(makeDataset());
  assert.equal(result.errors.length, 0, JSON.stringify(result.errors));
  assert.equal(result.ok, true);
  assert.equal(result.validProspects, 8);
});

test("a missing required field is an error naming the row and column", () => {
  const result = validate(makeDataset({}, [{ points: null }]));
  const issue = result.errors.find((e) => e.field === "points");
  assert.ok(issue, "expected a points error");
  assert.equal(issue.row, 1);
  assert.match(issue.message, /required/);
  assert.equal(result.ok, false);
});

test("an invalid position lists the accepted vocabulary", () => {
  const result = validate(makeDataset({}, [{ position: "Point Guard" }]));
  const issue = result.errors.find((e) => e.field === "position");
  assert.ok(issue);
  assert.match(issue.message, /G, F, C, UNKNOWN/);
  assert.match(issue.message, /Point Guard/);
});

test("a percentage in a makes column is caught as a count violation", () => {
  // 41.2 in three_points_made against 150 attempts is legal on its own; the
  // giveaway used here is makes exceeding attempts.
  const result = validate(makeDataset({}, [{ three_points_made: 200 }]));
  const issue = result.errors.find((e) => e.field === "three_points_made");
  assert.ok(issue);
  assert.match(issue.message, /exceeds three_points_attempted/);
  assert.match(issue.message, /COUNTS, not percentages/);
});

test("a non-integer count is rejected", () => {
  const result = validate(makeDataset({}, [{ assists: 12.4 }]));
  const issue = result.errors.find((e) => e.field === "assists");
  assert.ok(issue);
  assert.match(issue.message, /whole number/);
});

test("an out-of-range height is rejected with its unit", () => {
  const result = validate(makeDataset({}, [{ height_inches: 6.8 }]));
  const issue = result.errors.find((e) => e.field === "height_inches");
  assert.ok(issue);
  assert.match(issue.message, /at least 48 \(inches\)/);
});

test("per-game minutes are caught rather than analysed as a season total", () => {
  const result = validate(makeDataset({}, [{ minutes: 31 }]));
  const issue = result.errors.find((e) => e.field === "minutes");
  assert.ok(issue);
  assert.match(issue.message, /TOTAL season minutes/);
});

test("duplicate prospect_id is an error and points at the first row", () => {
  const result = validate(makeDataset({}, [{}, { prospect_id: "P0" }]));
  const issue = result.errors.find((e) => e.field === "prospect_id");
  assert.ok(issue);
  assert.match(issue.message, /Duplicate prospect_id "P0"/);
  assert.match(issue.message, /already used on row 1/);
});

test("an outcome column is refused, not ignored", () => {
  const dataset = makeDataset();
  dataset.prospects[0].actual_pick = 3;
  const result = validate(dataset);
  const issue = result.errors.find((e) => e.field === "actual_pick");
  assert.ok(issue);
  assert.match(issue.message, /PRE-DRAFT/);
  assert.equal(result.ok, false);
});

test("every prohibited column in the schema is actually refused", () => {
  for (const column of schema.prohibitedFields) {
    const dataset = makeDataset();
    dataset.prospects[0][column] = 1;
    const result = validate(dataset);
    assert.equal(result.ok, false, `${column} was accepted`);
  }
});

test("a derived rate column is refused with the fix", () => {
  const dataset = makeDataset();
  dataset.prospects[0].three_point_pct = 0.412;
  const result = validate(dataset);
  const issue = result.errors.find((e) => e.field === "three_point_pct");
  assert.ok(issue);
  assert.match(issue.message, /counts instead/);
});

test("an unknown column is a warning, not an error", () => {
  const dataset = makeDataset();
  dataset.prospects[0].scouting_grade = "A+";
  const result = validate(dataset);
  assert.equal(result.ok, true);
  assert.ok(result.warnings.some((w) => w.field === "scouting_grade"));
});

test("too few rows is an error explaining why", () => {
  const dataset = makeDataset();
  dataset.prospects = dataset.prospects.slice(0, 2);
  const result = validate(dataset);
  assert.equal(result.ok, false);
  assert.ok(result.errors.some((e) => /percentile WITHIN/.test(e.message)));
});

test("an unsupported season warns and does not claim a substitute", () => {
  const result = validate(makeDataset({ season: 1998 }));
  const issue = result.warnings.find((w) => w.field === "season");
  assert.ok(issue);
  assert.match(issue.message, /No neighbouring season is substituted/);
});

test("a non-early-entry population warns that no board will be produced", () => {
  const result = validate(makeDataset({ population_type: "ncaa_all_players" }));
  const issue = result.warnings.find((w) => w.field === "population_type");
  assert.ok(issue);
  assert.match(issue.message, /no General Board/);
});

test("missing optional groups warn about lost capability", () => {
  const result = validate(makeDataset());
  assert.ok(result.warnings.some((w) => /team-context/.test(w.message)));
  assert.ok(result.warnings.some((w) => /shot-profile/.test(w.message)));
});

// ------------------------------------------------------------- capabilities
test("a compatible dataset unlocks every analysis", () => {
  const dataset = validate(makeDataset()).dataset;
  const caps = detectCapabilities(dataset, core, { season: 2026 });
  assert.deepEqual(
    Object.fromEntries(caps.map((c) => [c.id, c.available])),
    { stats: true, teamNeed: true, comparables: true, generalBoard: true });
});

test("the wrong population loses the board but keeps the rest", () => {
  const dataset = validate(
    makeDataset({ population_type: "ncaa_all_players" })).dataset;
  const caps = detectCapabilities(dataset, core, { season: 2026 });
  const board = caps.find((c) => c.id === "generalBoard");
  assert.equal(board.available, false);
  assert.match(board.reason, /validated on final NCAA early entrants/);
  assert.equal(caps.find((c) => c.id === "teamNeed").available, true);
  assert.equal(caps.find((c) => c.id === "stats").available, true);
});

test("a missing draft size blocks the board with an actionable reason", () => {
  const dataset = validate(makeDataset({ draft_size: null })).dataset;
  const caps = detectCapabilities(dataset, core, { season: 2026 });
  const board = caps.find((c) => c.id === "generalBoard");
  assert.equal(board.available, false);
  assert.match(board.reason, /draft_size is required/);
});

test("an unsupported season blocks everything that needs a peer reference", () => {
  const dataset = validate(makeDataset({ season: 1998 })).dataset;
  const caps = detectCapabilities(dataset, core, null);
  assert.equal(caps.find((c) => c.id === "stats").available, true);
  for (const id of ["teamNeed", "comparables", "generalBoard"]) {
    assert.equal(caps.find((c) => c.id === id).available, false, id);
  }
});

test("no heights means no comparables", () => {
  const dataset = validate(makeDataset({}, Array.from(
    { length: 8 }, () => ({ height_inches: null })))).dataset;
  const caps = detectCapabilities(dataset, core, { season: 2026 });
  const comparables = caps.find((c) => c.id === "comparables");
  assert.equal(comparables.available, false);
  assert.match(comparables.reason, /gated on plausible height/);
});
