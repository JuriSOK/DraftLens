/** BROWSER/PYTHON PARITY — the gate on imported General Board analysis.
 *
 * Runs the frozen 2026 NCAA inputs, expressed as a DraftLens Dataset Format
 * file, through the browser runtime and compares every product number against
 * what Python produced for the same file. Python's answers were themselves
 * checked against the shipped 2026 board, so this closes the chain:
 *
 *     shipped product  ==  Python on the fixture  ==  browser on the fixture
 *
 * Floating values are held to a strict tolerance. Rank, Overall Score,
 * comparable ids, eligibility and availability must be EXACTLY equal — those
 * are decisions, not estimates, and "nearly the same rank" is a different
 * board.
 *
 * THIS IS A RELEASE GATE. It exits non-zero on any mismatch, and the Dataset
 * Lab's General Board must not ship while it does: a browser board that is
 * only approximately the frozen model is not the frozen model. If it ever
 * fails, fix the runtime or restrict imported analysis to the parts that
 * still match — never widen the tolerance.
 *
 *     node app/tests/parity.mjs
 */

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { register } from "node:module";

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, "../..");

// Vite resolves the runtime's extensionless imports; Node needs a hook.
register("./ts-loader.mjs", import.meta.url);

// The runtime modules are plain TypeScript with no JSX and no dependencies,
// so Node's built-in type stripping loads them directly — the browser and
// this harness execute the very same files.
const { analyzeDataset } = await import("../src/lib/runtime/analyze.ts");

const core = JSON.parse(
  readFileSync(resolve(root, "app/public/data/runtime/core.json"), "utf8"));
const season = JSON.parse(
  readFileSync(resolve(root, "app/public/data/runtime/season-2026.json"), "utf8"));
const dataset = JSON.parse(
  readFileSync(resolve(root, "tests/fixtures/parity/dataset_2026.json"), "utf8"));
const expected = JSON.parse(
  readFileSync(resolve(root, "tests/fixtures/parity/expected_2026.json"), "utf8"));

const FLOAT_TOLERANCE = 1e-9;

const parsed = {
  schemaVersion: dataset.schemaVersion,
  metadata: dataset.metadata,
  prospects: dataset.prospects,
  sourceName: "parity fixture",
  sourceKind: "json",
};

const result = analyzeDataset(parsed, core, season);

const failures = [];
const maxDiff = {
  draftProbability: 0, draftOrderPick: 0, boardSignal: 0, stageBQuality: 0,
  dimension: 0, profileFitRaw: 0, comparableDistance: 0,
};

function track(key, a, b) {
  if (a === null || b === null || !Number.isFinite(a) || !Number.isFinite(b)) return;
  maxDiff[key] = Math.max(maxDiff[key], Math.abs(a - b));
}

function exact(label, id, got, want) {
  if (got !== want) {
    failures.push(`${label} [${id}]: got ${JSON.stringify(got)}, `
      + `expected ${JSON.stringify(want)}`);
  }
}

function close(label, id, got, want, key) {
  const gotNull = got === null || !Number.isFinite(got);
  const wantNull = want === null || !Number.isFinite(want);
  if (gotNull !== wantNull) {
    failures.push(`${label} [${id}]: availability differs — got ${got}, expected ${want}`);
    return;
  }
  if (gotNull) return;
  track(key, got, want);
  if (Math.abs(got - want) > FLOAT_TOLERANCE) {
    failures.push(`${label} [${id}]: got ${got}, expected ${want} `
      + `(diff ${Math.abs(got - want)})`);
  }
}

const byId = new Map(result.prospects.map((p) => [p.id, p]));

for (const want of expected.prospects) {
  const got = byId.get(want.prospectId);
  if (!got) {
    failures.push(`missing prospect ${want.prospectId}`);
    continue;
  }
  const id = want.prospectId;

  close("draftProbability", id, got.draftProbability, want.draftProbability,
        "draftProbability");
  close("draftOrderPick", id, got.orderPick, want.draftOrderPick, "draftOrderPick");
  close("stageBQuality", id, got.stageBQuality, want.stageBQuality, "stageBQuality");
  close("boardSignal", id, got.boardSignal, want.boardSignal, "boardSignal");
  exact("overallScore", id, got.overallScore, want.overallScore);
  exact("boardRank", id, got.boardRank, want.boardRank);

  for (const [key, wantValue] of Object.entries(want.dimensions)) {
    const gotValue = got.dimensions[key.toUpperCase()];
    close(`dimension.${key}`, id,
          gotValue === undefined || Number.isNaN(gotValue) ? null : gotValue,
          wantValue, "dimension");
  }

  for (const [key, wantProfile] of Object.entries(want.profiles)) {
    const gotProfile = got.profiles[key.toUpperCase()];
    if (!gotProfile) {
      failures.push(`profile ${key} [${id}] missing`);
      continue;
    }
    close(`profile.${key}.fitRaw`, id,
          Number.isNaN(gotProfile.fitRaw) ? null : gotProfile.fitRaw,
          wantProfile.fitRaw, "profileFitRaw");
    exact(`profile.${key}.fitScore`, id,
          Number.isNaN(gotProfile.fitScore) ? null : gotProfile.fitScore,
          wantProfile.fitScore);
    exact(`profile.${key}.eligibility`, id, gotProfile.eligibility,
          wantProfile.eligibility);
    exact(`profile.${key}.status`, id, gotProfile.status, wantProfile.status);
  }

  const wantCmp = want.comparables;
  const gotCmp = got.comparables;
  if (!gotCmp) {
    failures.push(`comparables [${id}] missing`);
  } else {
    exact("comparables.status", id, gotCmp.status, wantCmp.status);
    exact("comparables.heightWindow", id, gotCmp.heightWindowInches,
          wantCmp.heightWindowInches);
    exact("comparables.ids", id, gotCmp.comparables.map((c) => c.id).join(","),
          wantCmp.players.map((c) => c.id).join(","));
    wantCmp.players.forEach((w, i) => {
      const g = gotCmp.comparables[i];
      if (!g) {
        failures.push(`comparable ${i} [${id}] missing`);
        return;
      }
      exact(`comparable.${i}.similarityScore`, id, g.similarityScore,
            w.similarityScore);
      close(`comparable.${i}.rawDistance`, id, g.rawDistance, w.rawDistance,
            "comparableDistance");
    });
  }
}

const counts = {
  prospects: expected.prospects.length,
  comparablesCompared: expected.prospects.reduce(
    (n, p) => n + p.comparables.players.length, 0),
};

console.log("PARITY — browser runtime vs frozen Python");
console.log(`  prospects compared          ${counts.prospects}`);
console.log(`  comparable slots compared   ${counts.comparablesCompared}`);
console.log("  max |difference|");
for (const [key, value] of Object.entries(maxDiff)) {
  console.log(`    ${key.padEnd(22)} ${value.toExponential(3)}`);
}
console.log(`  exact-match fields          rank, Overall Score, Fit Score, `
  + `eligibility, status, comparable ids, similarity score, height window`);

if (failures.length) {
  console.error(`\nFAILURES (${failures.length}):`);
  for (const f of failures.slice(0, 40)) console.error("  " + f);
  process.exit(1);
}
console.log("\nPARITY PASS — every compared value matches Python.");
