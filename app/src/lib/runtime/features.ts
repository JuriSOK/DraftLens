/** The engineered feature layer, mirroring `features.basketball.build_features`.
 *
 * Every formula here is a transcription of the frozen Python definition and
 * of nothing else. It exists because an imported dataset is analysed in the
 * browser, so the browser has to be able to turn season totals into the same
 * rates DraftLens computes for its own data. A difference here is a bug, and
 * the parity harness is what proves there isn't one: it runs the real 2026
 * inputs through this file and compares against Python's output.
 *
 * Nothing is invented. There is no feature here that the frozen pipeline does
 * not already produce, and no alternative definition of one that it does.
 */

import { NA, num, per100, per40, perGame, safeDiv } from "./numeric";

/** Free-throw possession coefficient, `features.basketball.FT_POSSESSION_COEF`. */
const FT = 0.44;

export type Primitives = Record<string, number>;
export type Features = Record<string, number>;

function teamPossessions(fga: number, fta: number, orb: number, tov: number): number {
  return fga + FT * fta - orb + tov;
}

function efgPct(fgm: number, fg3m: number, fga: number): number {
  return safeDiv(fgm + 0.5 * fg3m, fga);
}

function tsPct(points: number, fga: number, fta: number): number {
  return safeDiv(points, 2.0 * (fga + FT * fta));
}

function usagePct(
  fga: number, fta: number, tov: number, minutes: number,
  tmFga: number, tmFta: number, tmTov: number, tmMinutes: number,
): number {
  const numerator = (fga + FT * fta + tov) * (tmMinutes / 5.0);
  const denominator = minutes * (tmFga + FT * tmFta + tmTov);
  return 100.0 * safeDiv(numerator, denominator);
}

function tovPct(tov: number, fga: number, fta: number): number {
  return 100.0 * safeDiv(tov, fga + FT * fta + tov);
}

function astPct(
  ast: number, minutes: number, tmMinutes: number, tmFgm: number, fgm: number,
): number {
  const share = safeDiv(minutes, tmMinutes / 5.0);
  return 100.0 * safeDiv(ast, share * tmFgm - fgm);
}

function reboundPct(
  reb: number, minutes: number, tmMinutes: number, tmReb: number, oppReb: number,
): number {
  return 100.0 * safeDiv(reb * (tmMinutes / 5.0), minutes * (tmReb + oppReb));
}

function stlPct(
  stl: number, minutes: number, tmMinutes: number, oppPossessions: number,
): number {
  return 100.0 * safeDiv(stl * (tmMinutes / 5.0), minutes * oppPossessions);
}

function blkPct(
  blk: number, minutes: number, tmMinutes: number, oppFga: number, oppFg3a: number,
): number {
  return 100.0 * safeDiv(blk * (tmMinutes / 5.0), minutes * (oppFga - oppFg3a));
}

/** Import column -> the primitive name the formulas read.
 * Mirrors `dataset_format.TO_PRIMITIVE`; the runtime bundle carries the
 * authoritative copy and `assertMappingMatchesBundle` checks this against it. */
export const TO_PRIMITIVE: Record<string, string> = {
  team_minutes: "tm_minutes",
  team_field_goals_made: "tm_field_goals_made",
  team_field_goals_attempted: "tm_field_goals_attempted",
  team_free_throws_attempted: "tm_free_throws_attempted",
  team_turnovers: "tm_turnovers",
  team_offensive_rebounds: "tm_offensive_rebounds",
  team_defensive_rebounds: "tm_defensive_rebounds",
  team_rebounds: "tm_rebounds",
  opp_field_goals_attempted: "opp_field_goals_attempted",
  opp_three_points_attempted: "opp_three_point_field_goals_attempted",
  opp_free_throws_attempted: "opp_free_throws_attempted",
  opp_offensive_rebounds: "opp_offensive_rebounds",
  opp_defensive_rebounds: "opp_defensive_rebounds",
  opp_rebounds: "opp_rebounds",
  opp_turnovers: "opp_turnovers",
  shot_fg_attempts: "fg_attempts_shotfile",
  shot_fg_makes: "fg_makes_shotfile",
  height_inches: "height",
  weight_lbs: "weight",
};

/** One validated import row -> the primitive frame the formulas expect. */
export function toPrimitives(row: Record<string, unknown>): Primitives {
  const d: Primitives = {};
  for (const [key, value] of Object.entries(row)) {
    if (key === "prospect_id" || key === "name" || key === "school"
        || key === "position") continue;
    d[TO_PRIMITIVE[key] ?? key] = num(value);
  }
  // `build_features` reads these two directly; all field goals minus threes.
  d.two_points_made = d.field_goals_made - d.three_points_made;
  d.two_points_attempted = d.field_goals_attempted - d.three_points_attempted;
  return d;
}

const G = (d: Primitives, key: string): number =>
  Object.prototype.hasOwnProperty.call(d, key) ? d[key] : NA;

/** The full engineered row for one prospect. */
export function buildFeatures(d: Primitives): Features {
  const f: Features = {};

  const tmMin = G(d, "tm_minutes");
  f.team_minutes = tmMin;
  f.team_possessions = teamPossessions(
    G(d, "tm_field_goals_attempted"), G(d, "tm_free_throws_attempted"),
    G(d, "tm_offensive_rebounds"), G(d, "tm_turnovers"));
  f.opp_possessions = teamPossessions(
    G(d, "opp_field_goals_attempted"), G(d, "opp_free_throws_attempted"),
    G(d, "opp_offensive_rebounds"), G(d, "opp_turnovers"));

  const g = G(d, "games_played");
  const mins = G(d, "minutes");

  // PLAYING TIME
  f.minutes_per_game = perGame(mins, g);
  f.start_share = safeDiv(G(d, "games_started"), g);

  // SHOOTING EFFICIENCY
  f.fg_pct = safeDiv(G(d, "field_goals_made"), G(d, "field_goals_attempted"));
  f.two_point_pct = safeDiv(G(d, "two_points_made"), G(d, "two_points_attempted"));
  f.three_point_pct = safeDiv(G(d, "three_points_made"), G(d, "three_points_attempted"));
  f.ft_pct = safeDiv(G(d, "free_throws_made"), G(d, "free_throws_attempted"));
  f.efg_pct = efgPct(G(d, "field_goals_made"), G(d, "three_points_made"),
                     G(d, "field_goals_attempted"));
  f.ts_pct = tsPct(G(d, "points"), G(d, "field_goals_attempted"),
                   G(d, "free_throws_attempted"));

  // SHOOTING VOLUME
  f.three_point_attempt_rate = safeDiv(G(d, "three_points_attempted"),
                                       G(d, "field_goals_attempted"));
  f.two_point_attempt_rate = safeDiv(G(d, "two_points_attempted"),
                                     G(d, "field_goals_attempted"));
  f.free_throw_rate = safeDiv(G(d, "free_throws_attempted"),
                              G(d, "field_goals_attempted"));
  f.fga_per_40 = per40(G(d, "field_goals_attempted"), mins);
  f.three_pa_per_40 = per40(G(d, "three_points_attempted"), mins);
  f.fta_per_40 = per40(G(d, "free_throws_attempted"), mins);

  // SCORING
  f.points_per_game = perGame(G(d, "points"), g);
  f.points_per_40 = per40(G(d, "points"), mins);
  f.points_per_100 = per100(G(d, "points"), f.team_possessions);

  // PLAYMAKING
  f.assists_per_game = perGame(G(d, "assists"), g);
  f.turnovers_per_game = perGame(G(d, "turnovers"), g);
  f.assists_per_40 = per40(G(d, "assists"), mins);
  f.turnovers_per_40 = per40(G(d, "turnovers"), mins);
  f.assist_to_turnover_ratio = safeDiv(G(d, "assists"), G(d, "turnovers"));
  f.ast_pct = astPct(G(d, "assists"), mins, tmMin, G(d, "tm_field_goals_made"),
                     G(d, "field_goals_made"));
  f.tov_pct = tovPct(G(d, "turnovers"), G(d, "field_goals_attempted"),
                     G(d, "free_throws_attempted"));

  // REBOUNDING
  f.rebounds_per_game = perGame(G(d, "total_rebounds"), g);
  f.oreb_per_40 = per40(G(d, "offensive_rebounds"), mins);
  f.dreb_per_40 = per40(G(d, "defensive_rebounds"), mins);
  f.reb_per_40 = per40(G(d, "total_rebounds"), mins);
  f.orb_pct = reboundPct(G(d, "offensive_rebounds"), mins, tmMin,
                         G(d, "tm_offensive_rebounds"), G(d, "opp_defensive_rebounds"));
  f.drb_pct = reboundPct(G(d, "defensive_rebounds"), mins, tmMin,
                         G(d, "tm_defensive_rebounds"), G(d, "opp_offensive_rebounds"));
  f.trb_pct = reboundPct(G(d, "total_rebounds"), mins, tmMin,
                         G(d, "tm_rebounds"), G(d, "opp_rebounds"));

  // BOX-SCORE DEFENSIVE PRODUCTION (never defensive quality)
  f.steals_per_game = perGame(G(d, "steals"), g);
  f.blocks_per_game = perGame(G(d, "blocks"), g);
  f.steals_per_40 = per40(G(d, "steals"), mins);
  f.blocks_per_40 = per40(G(d, "blocks"), mins);
  f.personal_fouls_per_40 = per40(G(d, "personal_fouls"), mins);
  f.stl_pct = stlPct(G(d, "steals"), mins, tmMin, f.opp_possessions);
  f.blk_pct = blkPct(G(d, "blocks"), mins, tmMin,
                     G(d, "opp_field_goals_attempted"),
                     G(d, "opp_three_point_field_goals_attempted"));

  // SHOT PROFILE — stable families only
  const sf = G(d, "fg_attempts_shotfile");
  f.layup_attempt_share = safeDiv(G(d, "layup_attempts"), sf);
  f.dunk_attempt_share = safeDiv(G(d, "dunk_attempts"), sf);
  f.tip_attempt_share = safeDiv(G(d, "tip_attempts"), sf);
  f.three_point_shot_attempt_share = safeDiv(G(d, "three_point_shot_attempts"), sf);
  const rim = G(d, "layup_attempts") + G(d, "dunk_attempts") + G(d, "tip_attempts");
  f.rim_attempt_share = safeDiv(rim, sf);
  f.layup_make_pct = safeDiv(G(d, "layup_makes"), G(d, "layup_attempts"));
  f.dunk_make_pct = safeDiv(G(d, "dunk_makes"), G(d, "dunk_attempts"));
  f.tip_make_pct = safeDiv(G(d, "tip_makes"), G(d, "tip_attempts"));
  const rimMakes = G(d, "layup_makes") + G(d, "dunk_makes") + G(d, "tip_makes");
  f.rim_make_pct = safeDiv(rimMakes, rim);

  // CREATION
  const madeSf = G(d, "fg_makes_shotfile");
  f.assisted_made_fg_share = safeDiv(G(d, "assisted_made_field_goals"), madeSf);
  f.unassisted_made_fg_share = safeDiv(G(d, "unassisted_made_field_goals"), madeSf);
  f.assisted_layup_make_share = safeDiv(G(d, "assisted_layup_makes"),
                                        G(d, "layup_makes"));
  f.unassisted_layup_make_share = safeDiv(G(d, "unassisted_layup_makes"),
                                          G(d, "layup_makes"));
  f.assisted_dunk_make_share = safeDiv(G(d, "assisted_dunk_makes"), G(d, "dunk_makes"));
  f.unassisted_dunk_make_share = safeDiv(G(d, "unassisted_dunk_makes"),
                                         G(d, "dunk_makes"));

  // PHYSICAL / ROLE
  f.height = G(d, "height");
  f.weight = G(d, "weight");
  f.usage_pct = usagePct(
    G(d, "field_goals_attempted"), G(d, "free_throws_attempted"),
    G(d, "turnovers"), mins, G(d, "tm_field_goals_attempted"),
    G(d, "tm_free_throws_attempted"), G(d, "tm_turnovers"), tmMin);

  f.assists_per_100 = per100(G(d, "assists"), f.team_possessions);
  f.turnovers_per_100 = per100(G(d, "turnovers"), f.team_possessions);
  f.rebounds_per_100 = per100(G(d, "total_rebounds"), f.team_possessions);
  f.steals_per_100 = per100(G(d, "steals"), f.team_possessions);
  f.blocks_per_100 = per100(G(d, "blocks"), f.team_possessions);

  // Denominators travel with the ratios — Team Need's reliability rules read
  // them to decide whether a rate rests on enough attempts to be reported.
  f.games_played = g;
  f.minutes = mins;
  f.field_goals_attempted = G(d, "field_goals_attempted");
  f.three_points_attempted = G(d, "three_points_attempted");
  f.free_throws_attempted = G(d, "free_throws_attempted");
  f.shot_records = G(d, "shot_records");
  f.fg_attempts_shotfile = sf;
  return f;
}
