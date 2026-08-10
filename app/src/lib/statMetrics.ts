import type { Prospect, ProspectStats } from "../types/data";

export type MetricGroup = "Scoring" | "Rebounding" | "Playmaking" | "Defense" | "Shooting";
export type SortDirection = "desc" | "asc";

/** The reliability minimum DraftLens's frozen Team Need methodology already
 * uses for three_point_pct, ft_pct and rim_make_pct (config/team_need.json
 * `reliability_minimums`, all exactly 20 attempts) — reused here rather than
 * inventing a new number. TS% has no frozen-approved minimum of its own; it
 * is flagged using this same 20-attempt bar applied to field goal attempts
 * (TS%'s own volume denominator) by direct analogy, not a new arbitrary
 * threshold. */
export const RELIABILITY_MIN_ATTEMPTS = 20;

export interface MetricDef {
  key: keyof ProspectStats;
  label: string;
  group: MetricGroup;
  defaultDirection: SortDirection;
  lowerIsBetter?: boolean;
  isPercent?: boolean;
  attemptsKey?: keyof ProspectStats;
}

export const METRICS: MetricDef[] = [
  { key: "pointsPer40", label: "PTS / 40 min", group: "Scoring", defaultDirection: "desc" },
  { key: "reboundsPer40", label: "REB / 40 min", group: "Rebounding", defaultDirection: "desc" },
  { key: "assistsPer40", label: "AST / 40 min", group: "Playmaking", defaultDirection: "desc" },
  {
    key: "turnoversPer40",
    label: "TOV / 40 min",
    group: "Playmaking",
    defaultDirection: "asc",
    lowerIsBetter: true,
  },
  { key: "stealsPer40", label: "STL / 40 min", group: "Defense", defaultDirection: "desc" },
  { key: "blocksPer40", label: "BLK / 40 min", group: "Defense", defaultDirection: "desc" },
  {
    key: "threePointPct",
    label: "3P%",
    group: "Shooting",
    defaultDirection: "desc",
    isPercent: true,
    attemptsKey: "threePointAttempts",
  },
  {
    key: "ftPct",
    label: "FT%",
    group: "Shooting",
    defaultDirection: "desc",
    isPercent: true,
    attemptsKey: "ftAttempts",
  },
  {
    key: "tsPct",
    label: "TS%",
    group: "Shooting",
    defaultDirection: "desc",
    isPercent: true,
    attemptsKey: "fgAttempts",
  },
];

export const METRIC_GROUPS: MetricGroup[] = [
  "Scoring",
  "Rebounding",
  "Playmaking",
  "Defense",
  "Shooting",
];

export function isLowSample(prospect: Prospect, metric: MetricDef): boolean {
  if (!metric.attemptsKey) return false;
  const attempts = prospect.stats[metric.attemptsKey];
  return attempts === null || attempts < RELIABILITY_MIN_ATTEMPTS;
}

/** Where each product statistic lives in the runtime's engineered feature row.
 *
 * The Dataset Lab reuses the METRICS list above rather than defining its own,
 * so an imported class is explored with the same labels, directions,
 * percent handling and reliability minimums as the built-in board. This map
 * is the only translation needed, because the two sides name the same
 * quantity differently — nothing about the metric itself changes. */
export const METRIC_FEATURE_KEY: Record<keyof ProspectStats, string> = {
  heightInches: "height",
  pointsPer40: "points_per_40",
  reboundsPer40: "reb_per_40",
  assistsPer40: "assists_per_40",
  stealsPer40: "steals_per_40",
  blocksPer40: "blocks_per_40",
  turnoversPer40: "turnovers_per_40",
  threePointPct: "three_point_pct",
  threePointAttempts: "three_points_attempted",
  ftPct: "ft_pct",
  ftAttempts: "free_throws_attempted",
  tsPct: "ts_pct",
  fgAttempts: "field_goals_attempted",
  minutesPerGame: "minutes_per_game",
  gamesPlayed: "games_played",
};
