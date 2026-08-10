import { Link, useParams } from "react-router-dom";
import { useDraftLensData } from "../data/DataProvider";
import { LoadingState, ErrorState } from "../components/DataStates";
import { ScoreBadge } from "../components/ScoreBadge";
import { PercentileBar } from "../components/PercentileBar";
import { ProfileCard } from "../components/ProfileCard";
import { ComparableCard } from "../components/ComparableCard";
import { ProspectPhoto } from "../components/ProspectPhoto";
import { MetricTooltip } from "../components/MetricTooltip";
import {
  formatDecimal,
  formatPercent,
  formatInt,
  formatHeight,
  formatScoreOutOf100,
} from "../lib/format";
import { Radar } from "../components/charts/Charts";
import { TOOLTIPS } from "../lib/tooltips";
import {
  DIMENSION_LABELS,
  DIMENSION_PEER_GROUP,
  PROFILE_DESCRIPTIONS,
  PROFILE_LABELS,
} from "../types/data";
import type { Dimensions, Prospect, WatchlistProspect } from "../types/data";
import styles from "./ProspectDetailPage.module.css";

/** Short labels so the six radar axes fit without overlapping. */
const RADAR_LABELS: Record<keyof Dimensions, string> = {
  shooting: "Shoot",
  playmaking: "Play",
  defensiveProduction: "Def",
  rebounding: "Reb",
  size: "Size",
  rimPressure: "Rim",
};

const DIMENSION_ORDER: (keyof Dimensions)[] = [
  "shooting",
  "playmaking",
  "defensiveProduction",
  "rebounding",
  "size",
  "rimPressure",
];

function strengthsAndWeaknesses(dimensions: Dimensions) {
  const entries = DIMENSION_ORDER.map((key) => ({
    key,
    label: DIMENSION_LABELS[key],
    value: dimensions[key],
  })).filter((e): e is { key: keyof Dimensions; label: string; value: number } =>
    e.value !== null,
  );
  const strengths = entries
    .filter((e) => e.value >= 70)
    .sort((a, b) => b.value - a.value)
    .slice(0, 3);
  const weaknesses = entries
    .filter((e) => e.value <= 35)
    .sort((a, b) => a.value - b.value)
    .slice(0, 2);
  return { strengths, weaknesses };
}

export function ProspectDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data, error, loading } = useDraftLensData();

  if (loading) return <LoadingState />;
  if (error || !data) return <ErrorState message={error ?? "Unknown error"} />;

  if (id?.startsWith("2027-")) {
    const year2027 = data.years["2027"];
    const wp =
      year2027.status === "watchlist"
        ? year2027.prospects.find((p) => p.id === id)
        : undefined;
    if (!wp) {
      return (
        <div className={`container ${styles.notFound}`}>
          <p>Prospect not found.</p>
          <Link to="/2027">Back to the Watchlist</Link>
        </div>
      );
    }
    return <WatchlistDetail prospect={wp} />;
  }

  const year2026 = data.years["2026"];
  const prospect =
    year2026.status === "available"
      ? year2026.prospects.find((p) => p.id === id)
      : undefined;
  if (!prospect) {
    return (
      <div className={`container ${styles.notFound}`}>
        <p>Prospect not found.</p>
        <Link to="/board">Back to the board</Link>
      </div>
    );
  }

  return <BoardDetail prospect={prospect} />;
}

function BoardDetail({ prospect }: { prospect: Prospect }) {
  const { strengths, weaknesses } = strengthsAndWeaknesses(prospect.dimensions);
  const board = prospect.declaredBoard;

  return (
    <div className="container">
      <Link to="/board" className={styles.back}>
        ← Board
      </Link>

      <header className={styles.header}>
        <div className={styles.identity}>
          <ProspectPhoto name={prospect.name} photo={prospect.photo} />
          <div>
            <h1 className={styles.name}>{prospect.name}</h1>
            <p className={styles.meta}>
              {prospect.school} · {prospect.position}
            </p>
          </div>
        </div>
        {board && (
          <div className={styles.headerStats}>
            <div className={styles.headerStat}>
              <span className={styles.headerStatLabel}>Board Rank</span>
              <span className={styles.headerStatValue}>#{board.rank}</span>
            </div>
            <div className={styles.headerStat}>
              <span className={styles.headerStatLabel}>
                Overall Score
                <MetricTooltip
                  text={TOOLTIPS.overallScore.text}
                  learnMoreHref={TOOLTIPS.overallScore.href}
                  label="About Overall Score"
                />
              </span>
              <ScoreBadge value={board.overallScore} size="lg" />
            </div>
            <div className={styles.headerStat}>
              <span className={styles.headerStatLabel}>
                Draft Probability
                <MetricTooltip
                  text={TOOLTIPS.draftProbability.text}
                  learnMoreHref={TOOLTIPS.draftProbability.href}
                  label="About Draft Probability"
                />
              </span>
              <span className={styles.headerStatValue}>
                {formatPercent(board.draftProbability)}
              </span>
            </div>
          </div>
        )}
      </header>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Profile</h2>
        <div className={styles.statsGrid}>
          <Stat label="Height" value={formatHeight(prospect.stats.heightInches)} />
          <Stat label="MIN/G" value={formatDecimal(prospect.stats.minutesPerGame)} />
          <Stat label="GP" value={formatInt(prospect.stats.gamesPlayed)} />
          <Stat label="PTS/40 min" value={formatDecimal(prospect.stats.pointsPer40)} />
          <Stat label="REB/40 min" value={formatDecimal(prospect.stats.reboundsPer40)} />
          <Stat label="AST/40 min" value={formatDecimal(prospect.stats.assistsPer40)} />
          <Stat label="STL/40 min" value={formatDecimal(prospect.stats.stealsPer40)} />
          <Stat label="BLK/40 min" value={formatDecimal(prospect.stats.blocksPer40)} />
          <Stat label="TOV/40 min" value={formatDecimal(prospect.stats.turnoversPer40)} />
          <Stat label="3P%" value={formatPercent(prospect.stats.threePointPct)} />
          <Stat label="FT%" value={formatPercent(prospect.stats.ftPct)} />
          <Stat label="TS%" value={formatPercent(prospect.stats.tsPct)} />
        </div>
      </section>

      <BasketballProfileSection
        dimensions={prospect.dimensions}
        strengths={strengths}
        weaknesses={weaknesses}
      />

      <TeamNeedSection profiles={prospect.profiles} />

      {prospect.comparables.length > 0 && <ComparablesSection comparables={prospect.comparables} />}

      <p className={styles.coverage}>
        Data coverage: {formatPercent(prospect.coverage)}
      </p>
    </div>
  );
}

function WatchlistDetail({ prospect }: { prospect: WatchlistProspect }) {
  return (
    <div className="container">
      <Link to="/2027" className={styles.back}>
        ← 2027 Watchlist
      </Link>

      <header className={styles.header}>
        <div className={styles.identity}>
          <ProspectPhoto name={prospect.name} photo={prospect.photo} />
          <div>
            <h1 className={styles.name}>{prospect.name}</h1>
            <p className={styles.meta}>
              {prospect.school ?? "—"}
              {prospect.classYear ? ` · ${prospect.classYear}` : ""}
            </p>
            {/* CRITICAL: never let a projection read as an official entry. */}
            <span className={styles.projectedBadge}>
              Projected — not an official Draft entrant
            </span>
          </div>
        </div>
      </header>

      {!prospect.hasStats || !prospect.stats ? (
        <div className={styles.noStats}>
          NCAA stats available after the 2026-27 season begins.
        </div>
      ) : (
        <>
          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>Profile</h2>
            <div className={styles.statsGrid}>
              <Stat label="Height" value={formatHeight(prospect.stats.heightInches)} />
              <Stat label="MIN/G" value={formatDecimal(prospect.stats.minutesPerGame)} />
              <Stat label="GP" value={formatInt(prospect.stats.gamesPlayed)} />
              <Stat label="PTS/40 min" value={formatDecimal(prospect.stats.pointsPer40)} />
              <Stat label="REB/40 min" value={formatDecimal(prospect.stats.reboundsPer40)} />
              <Stat label="AST/40 min" value={formatDecimal(prospect.stats.assistsPer40)} />
              <Stat label="STL/40 min" value={formatDecimal(prospect.stats.stealsPer40)} />
              <Stat label="BLK/40 min" value={formatDecimal(prospect.stats.blocksPer40)} />
              <Stat label="TOV/40 min" value={formatDecimal(prospect.stats.turnoversPer40)} />
              <Stat label="3P%" value={formatPercent(prospect.stats.threePointPct)} />
              <Stat label="FT%" value={formatPercent(prospect.stats.ftPct)} />
              <Stat label="TS%" value={formatPercent(prospect.stats.tsPct)} />
            </div>
            <p className={styles.noteSmall}>
              Stats are from the 2025-26 NCAA season (their most recent
              completed season). No Draft Probability, Draft Order or Overall
              Score is computed for 2027 watchlist players.
            </p>
          </section>

          {prospect.dimensions && (
            <BasketballProfileSection
              dimensions={prospect.dimensions}
              strengths={strengthsAndWeaknesses(prospect.dimensions).strengths}
              weaknesses={strengthsAndWeaknesses(prospect.dimensions).weaknesses}
            />
          )}

          {prospect.profiles && <TeamNeedSection profiles={prospect.profiles} />}

          {prospect.comparables.length > 0 && (
            <ComparablesSection comparables={prospect.comparables} />
          )}

          <p className={styles.coverage}>
            Data coverage: {formatPercent(prospect.coverage)}
          </p>
        </>
      )}
    </div>
  );
}

function BasketballProfileSection({
  dimensions,
  strengths,
  weaknesses,
}: {
  dimensions: Dimensions;
  strengths: ReturnType<typeof strengthsAndWeaknesses>["strengths"];
  weaknesses: ReturnType<typeof strengthsAndWeaknesses>["weaknesses"];
}) {
  // Same six exported scores, drawn as a shape — a second reading of the
  // bars below, not a new computation.
  const radarAxes = DIMENSION_ORDER.map((key) => ({
    label: RADAR_LABELS[key],
    value: dimensions[key],
  }));

  return (
    <section className={styles.section}>
      <h2 className={styles.sectionTitle}>
        Basketball Profile
        <MetricTooltip
          text={TOOLTIPS.basketballProfile.text}
          learnMoreHref={TOOLTIPS.basketballProfile.href}
          label="About Basketball Profile scores"
        />
      </h2>
      <div className={styles.profileLayout}>
        <div className="analyticsCard">
          <span className="analyticsTitle">Six-dimension shape</span>
          <Radar axes={radarAxes} ariaLabel="Basketball Profile radar across six dimensions" />
        </div>
        <div className={styles.dimensionGrid}>
        {DIMENSION_ORDER.map((key) => (
          <PercentileBar
            key={key}
            label={DIMENSION_LABELS[key]}
            value={dimensions[key]}
            peerGroup={DIMENSION_PEER_GROUP[key]}
            hint={
              key === "defensiveProduction"
                ? "Based on steals and blocks; not a complete measure of defensive quality."
                : undefined
            }
          />
        ))}
        </div>
      </div>

      {(strengths.length > 0 || weaknesses.length > 0) && (
        <div className={styles.swGrid}>
          {strengths.length > 0 && (
            <div>
              <h3 className={styles.swTitle}>Strengths</h3>
              <ul className={styles.swList}>
                {strengths.map((s) => (
                  <li key={s.key}>
                    {s.label}
                    <br />
                    {formatScoreOutOf100(s.value)} vs{" "}
                    {DIMENSION_PEER_GROUP[s.key] === "POSITION"
                      ? "similar NCAA players"
                      : "NCAA peers"}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {weaknesses.length > 0 && (
            <div>
              <h3 className={styles.swTitle}>Areas below peers</h3>
              <ul className={styles.swList}>
                {weaknesses.map((w) => (
                  <li key={w.key}>
                    {w.label}
                    <br />
                    {formatScoreOutOf100(w.value)} vs{" "}
                    {DIMENSION_PEER_GROUP[w.key] === "POSITION"
                      ? "similar NCAA players"
                      : "NCAA peers"}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </section>
  );
}

function TeamNeedSection({ profiles }: { profiles: Prospect["profiles"] }) {
  return (
    <section className={styles.section}>
      <h2 className={styles.sectionTitle}>
        Team Need Fit
        <MetricTooltip
          text={TOOLTIPS.teamNeedFit.text}
          learnMoreHref={TOOLTIPS.teamNeedFit.href}
          label="About Team Need Fit"
        />
      </h2>
      <div className={styles.profileGrid}>
        {(Object.keys(profiles) as (keyof typeof profiles)[]).map((key) => (
          <ProfileCard
            key={key}
            label={PROFILE_LABELS[key]}
            description={PROFILE_DESCRIPTIONS[key]}
            fit={profiles[key]}
          />
        ))}
      </div>
    </section>
  );
}

function ComparablesSection({ comparables }: { comparables: Prospect["comparables"] }) {
  return (
    <section className={styles.section}>
      <h2 className={styles.sectionTitle}>
        NBA Statistical Comparables
        <MetricTooltip
          text={TOOLTIPS.comparables.text}
          learnMoreHref={TOOLTIPS.comparables.href}
          label="About NBA Statistical Comparables"
        />
      </h2>
      <div className={styles.comparableGrid}>
        {comparables.map((c) => (
          <ComparableCard key={c.nbaPlayerName} comparable={c} />
        ))}
      </div>
    </section>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className={styles.stat}>
      <span className={styles.statValue}>{value}</span>
      <span className={styles.statLabel}>{label}</span>
    </div>
  );
}
