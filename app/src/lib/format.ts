/** Display formatting only — no analytical computation. Every value here was
 * already computed by the frozen Python systems; this module just rounds
 * sensibly and fills in an explicit "unavailable" marker instead of NaN. */

export const UNAVAILABLE = "—";

export function formatPercent(value: number | null, decimals = 0): string {
  if (value === null || Number.isNaN(value)) return UNAVAILABLE;
  return `${(value * 100).toFixed(decimals)}%`;
}

export function formatInt(value: number | null): string {
  if (value === null || Number.isNaN(value)) return UNAVAILABLE;
  return String(Math.round(value));
}

export function formatDecimal(value: number | null, decimals = 1): string {
  if (value === null || Number.isNaN(value)) return UNAVAILABLE;
  return value.toFixed(decimals);
}

/** "81 / 100" rather than an ordinal ("81st") — clearer to a non-technical
 * reader and avoids "81th" grammar bugs. Never implies a probability or an
 * accuracy percentage; pair with a "Higher than X% of ..." sentence. */
export function formatScoreOutOf100(value: number | null): string {
  if (value === null || Number.isNaN(value)) return UNAVAILABLE;
  return `${Math.round(value)} / 100`;
}

/** Height in inches -> feet/inches, e.g. 80 -> `6'8"`. */
export function formatHeight(inches: number | null): string {
  if (inches === null || Number.isNaN(inches)) return UNAVAILABLE;
  const total = Math.round(inches);
  const feet = Math.floor(total / 12);
  const rem = total % 12;
  return `${feet}'${rem}"`;
}
