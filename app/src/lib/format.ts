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

export function formatPercentile(value: number | null): string {
  if (value === null || Number.isNaN(value)) return UNAVAILABLE;
  const rounded = Math.round(value);
  const suffix =
    rounded % 10 === 1 && rounded % 100 !== 11
      ? "st"
      : rounded % 10 === 2 && rounded % 100 !== 12
        ? "nd"
        : rounded % 10 === 3 && rounded % 100 !== 13
          ? "rd"
          : "th";
  return `${rounded}${suffix}`;
}
