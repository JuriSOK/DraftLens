import { Link, useParams } from "react-router-dom";
import { useDraftLensData } from "../data/DataProvider";
import { LoadingState, ErrorState } from "../components/DataStates";
import { ScoreBadge } from "../components/ScoreBadge";
import { PercentileBar } from "../components/PercentileBar";
import { ProfileCard } from "../components/ProfileCard";
import { ComparableCard } from "../components/ComparableCard";
import { MetricTooltip } from "../components/MetricTooltip";
import { formatDecimal, formatPercent, formatInt, formatPercentile } from "../lib/format";
import { DIMENSION_LABELS, PROFILE_LABELS } from "../types/data";
import type { Dimensions, Prospect } from "../types/data";
import styles from "./ProspectDetailPage.module.css";

const DIMENSION_ORDER: (keyof Dimensions)[] = [
  "shooting",
  "playmaking",
  "defensiveProduction",
  "rebounding",
  "size",
  "rimPressure",
];

function strengthsAndWeaknesses(p: Prospect) {
  const entries = DIMENSION_ORDER.map((key) => ({
    key,
    label: DIMENSION_LABELS[key],
    value: p.dimensions[key],
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

  const prospect = data.prospects.find((p) => p.id === id);
  if (!prospect) {
    return (
      <div className={`container ${styles.notFound}`}>
        <p>Prospect not found.</p>
        <Link to="/">Back to the board</Link>
      </div>
    );
  }

  const { strengths, weaknesses } = strengthsAndWeaknesses(prospect);

  return (
    <div className="container">
      <Link to="/" className={styles.back}>
        ← Board
      </Link>

      <header className={styles.header}>
        <div>
          <h1 className={styles.name}>{prospect.name}</h1>
          <p className={styles.meta}>
            {prospect.school} · {prospect.position}
          </p>
        </div>
        <div className={styles.headerStats}>
          <div className={styles.headerStat}>
            <span className={styles.headerStatLabel}>Board Rank</span>
            <span className={styles.headerStatValue}>#{prospect.board.rank}</span>
          </div>
          <div className={styles.headerStat}>
            <span className={styles.headerStatLabel}>
              Overall Score
              <MetricTooltip text="Relative ranking score within this Draft class. 0-100, not a probability or predicted pick." />
            </span>
            <ScoreBadge value={prospect.board.overallScore} size="lg" />
          </div>
          <div className={styles.headerStat}>
            <span className={styles.headerStatLabel}>Draft Probability</span>
            <span className={styles.headerStatValue}>
              {formatPercent(prospect.board.draftProbability)}
            </span>
          </div>
        </div>
      </header>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Profile</h2>
        <div className={styles.statsGrid}>
          <Stat label="PTS/40" value={formatDecimal(prospect.stats.pointsPer40)} />
          <Stat label="REB/40" value={formatDecimal(prospect.stats.reboundsPer40)} />
          <Stat label="AST/40" value={formatDecimal(prospect.stats.assistsPer40)} />
          <Stat label="3P%" value={formatPercent(prospect.stats.threePointPct)} />
          <Stat label="FT%" value={formatPercent(prospect.stats.ftPct)} />
          <Stat label="TS%" value={formatPercent(prospect.stats.tsPct)} />
          <Stat label="MIN/G" value={formatDecimal(prospect.stats.minutesPerGame)} />
          <Stat label="GP" value={formatInt(prospect.stats.gamesPlayed)} />
        </div>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Basketball Profile</h2>
        <p className={styles.sectionSub}>Percentile vs NCAA peers</p>
        <div className={styles.dimensionGrid}>
          {DIMENSION_ORDER.map((key) => (
            <PercentileBar
              key={key}
              label={DIMENSION_LABELS[key]}
              value={prospect.dimensions[key]}
              hint={
                key === "defensiveProduction"
                  ? "Based on steals and blocks; not a complete measure of defensive quality."
                  : undefined
              }
            />
          ))}
          <div className={styles.athleticism}>
            <span className={styles.athleticismLabel}>Athleticism</span>
            <span className={styles.athleticismValue}>Not available</span>
            <p className={styles.athleticismNote}>
              No reliable Combine measurement available.
            </p>
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
                      {s.label} — {formatPercentile(s.value)} percentile
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
                      {w.label} — {formatPercentile(w.value)} percentile
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Team Need Fit</h2>
        <p className={styles.sectionSub}>
          How strongly this prospect's statistical profile matches each
          predefined basketball need. Independent of Overall Score.
        </p>
        <div className={styles.profileGrid}>
          {(Object.keys(prospect.profiles) as (keyof typeof prospect.profiles)[]).map(
            (key) => (
              <ProfileCard
                key={key}
                label={PROFILE_LABELS[key]}
                fit={prospect.profiles[key]}
              />
            ),
          )}
        </div>
      </section>

      {prospect.comparables.length > 0 && (
        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>NBA Statistical Comparables</h2>
          <p className={styles.sectionSub}>
            Closest NBA statistical profiles in DraftLens's normalized
            comparison space. Descriptive resemblance, not a projection.
          </p>
          <div className={styles.comparableGrid}>
            {prospect.comparables.map((c) => (
              <ComparableCard key={c.nbaPlayerName} comparable={c} />
            ))}
          </div>
        </section>
      )}

      <p className={styles.coverage}>
        Data coverage: {formatPercent(prospect.coverage)}
      </p>
    </div>
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
