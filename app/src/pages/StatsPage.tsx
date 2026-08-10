import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useDraftLensData } from "../data/DataProvider";
import { LoadingState, ErrorState } from "../components/DataStates";
import { formatDecimal, formatInt, formatPercent } from "../lib/format";
import {
  isLowSample,
  METRIC_GROUPS,
  METRICS,
  RELIABILITY_MIN_ATTEMPTS,
} from "../lib/statMetrics";
import type { MetricDef, MetricGroup, SortDirection } from "../lib/statMetrics";
import { Histogram, KpiStrip } from "../components/charts/Charts";
import { binValues, maxOf, mean, median } from "../lib/summaries";
import type { Prospect, YearAvailable } from "../types/data";
import styles from "./StatsPage.module.css";

export function StatsPage() {
  const { data, error, loading } = useDraftLensData();
  const navigate = useNavigate();
  const [group, setGroup] = useState<MetricGroup>("Scoring");
  const [metricKey, setMetricKey] = useState<MetricDef["key"]>("pointsPer40");
  const [direction, setDirection] = useState<SortDirection | null>(null);

  const year2026 = data?.years["2026"];
  const available = year2026?.status === "available" ? (year2026 as YearAvailable) : null;

  const metric = METRICS.find((m) => m.key === metricKey) ?? METRICS[0];
  const effectiveDirection = direction ?? metric.defaultDirection;

  const rows = useMemo(() => {
    if (!available) return [];
    const withValue = available.prospects
      .filter((p) => p.declaredBoard !== null)
      .map((p) => ({ prospect: p, value: p.stats[metric.key] }))
      .filter((r): r is { prospect: Prospect; value: number } => r.value !== null);
    withValue.sort((a, b) =>
      effectiveDirection === "desc" ? b.value - a.value : a.value - b.value,
    );
    return withValue;
  }, [available, metric, effectiveDirection]);

  // Presentation-only summaries of the values already listed in the table.
  const values = rows.map((r) => r.value);
  const fmt = (v: number | null) =>
    v === null ? "—" : metric.isPercent ? `${(v * 100).toFixed(1)}%` : v.toFixed(1);
  const lo = values.length ? Math.min(...values) : 0;
  const hi = values.length ? Math.max(...values) : 1;
  const distBins = binValues(values, {
    min: lo,
    max: hi === lo ? lo + 1 : hi,
    buckets: 12,
    format: (n) => (metric.isPercent ? `${Math.round(n * 100)}%` : n.toFixed(1)),
  });
  // "Best" respects the metric's own direction — fewest turnovers is best.
  const leaders = [...rows]
    .sort((a, b) => (metric.lowerIsBetter ? a.value - b.value : b.value - a.value))
    .slice(0, 5);

  if (loading) return <LoadingState />;
  if (error || !data || !available) return <ErrorState message={error ?? "Unknown error"} />;

  const groupMetrics = METRICS.filter((m) => m.group === group);

  return (
    <div className="container">
      <div className={styles.intro}>
        <h1 className={styles.title}>Prospect Stats</h1>
        <p className={styles.sub}>
          Rank prospects by pre-draft NCAA production.
        </p>
      </div>

      <div className={styles.groupRow} role="tablist" aria-label="Stat category">
        {METRIC_GROUPS.map((g) => (
          <button
            key={g}
            type="button"
            role="tab"
            aria-selected={group === g}
            className={styles.groupChip}
            data-active={group === g}
            onClick={() => {
              setGroup(g);
              const first = METRICS.find((m) => m.group === g);
              if (first) {
                setMetricKey(first.key);
                setDirection(null);
              }
            }}
          >
            {g}
          </button>
        ))}
      </div>

      <div className={styles.metricRow} role="tablist" aria-label="Metric">
        {groupMetrics.map((m) => (
          <button
            key={m.key}
            type="button"
            role="tab"
            aria-selected={metric.key === m.key}
            className={styles.metricChip}
            data-active={metric.key === m.key}
            onClick={() => {
              setMetricKey(m.key);
              setDirection(null);
            }}
          >
            {m.label}
          </button>
        ))}
      </div>

      <div className={styles.controls}>
        {/* CRITICAL: without this the ranking direction is genuinely
           ambiguous — a "leader" in turnovers would otherwise read as good. */}
        {metric.lowerIsBetter && (
          <p className={styles.lowerBetterNote}>Lower is better.</p>
        )}
        <div className={styles.directionToggle} role="group" aria-label="Sort direction">
          <button
            type="button"
            className={styles.dirButton}
            data-active={effectiveDirection === "desc"}
            onClick={() => setDirection("desc")}
          >
            Highest first
          </button>
          <button
            type="button"
            className={styles.dirButton}
            data-active={effectiveDirection === "asc"}
            onClick={() => setDirection("asc")}
          >
            Lowest first
          </button>
        </div>
      </div>

      {/* CRITICAL: a shooting leaderboard without a sample-size flag is
         actively misleading — 2-for-3 would top the list. */}
      {metric.attemptsKey && (
        <p className={styles.sampleNote}>
          Under {RELIABILITY_MIN_ATTEMPTS} attempts is flagged{" "}
          <span className={styles.lowSampleTag}>Low sample</span>.
        </p>
      )}

      {rows.length > 0 && (
        <>
          <KpiStrip
            items={[
              { label: "players ranked", value: String(rows.length) },
              { label: `median ${metric.label}`, value: fmt(median(values)) },
              { label: `average ${metric.label}`, value: fmt(mean(values)) },
              {
                label: metric.lowerIsBetter ? "lowest" : "highest",
                value: fmt(metric.lowerIsBetter ? Math.min(...values) : maxOf(values)),
                hint: leaders[0]?.prospect.name,
              },
            ]}
          />
          <div className="analyticsRow">
            <div className="analyticsCard">
              <span className="analyticsTitle">{metric.label} distribution</span>
              <Histogram
                bins={distBins}
                ariaLabel={`Distribution of ${metric.label} across ranked prospects`}
              />
            </div>
            <div className="analyticsCard">
              <span className="analyticsTitle">
                Top 5 {metric.lowerIsBetter ? "(fewest)" : ""}
              </span>
              <ol className={styles.leaderList}>
                {leaders.map((l) => (
                  <li key={l.prospect.id} className={styles.leaderItem}>
                    <span className={styles.leaderName}>{l.prospect.name}</span>
                    <span className={styles.leaderValue}>{fmt(l.value)}</span>
                  </li>
                ))}
              </ol>
            </div>
          </div>
        </>
      )}

      <div className={styles.tableWrap}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th scope="col" className={styles.colRank}>
                Rank
              </th>
              <th scope="col">Prospect</th>
              <th scope="col" className={styles.colHideSm}>
                School
              </th>
              <th scope="col" className={styles.colPos}>
                Pos
              </th>
              <th scope="col" className={styles.colMetric}>
                {metric.label}
              </th>
              <th scope="col" className={styles.colHideSm}>
                MIN/G
              </th>
              <th scope="col" className={styles.colHideSm}>
                GP
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => {
              const low = isLowSample(r.prospect, metric);
              return (
                <tr
                  key={r.prospect.id}
                  className={styles.row}
                  tabIndex={0}
                  role="link"
                  aria-label={`Open ${r.prospect.name}'s prospect detail`}
                  onClick={() => navigate(`/prospect/${r.prospect.id}`)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") navigate(`/prospect/${r.prospect.id}`);
                  }}
                >
                  <td className={styles.colRank}>{i + 1}</td>
                  <td>
                    <span className={styles.name}>{r.prospect.name}</span>
                  </td>
                  <td className={styles.colHideSm}>
                    <span className={styles.school}>{r.prospect.school}</span>
                  </td>
                  <td className={styles.colPos}>{r.prospect.position}</td>
                  <td className={styles.colMetric}>
                    <span className={styles.metricValue}>
                      {metric.isPercent ? formatPercent(r.value) : formatDecimal(r.value)}
                    </span>
                    {metric.attemptsKey && (
                      <span className={styles.attempts}>
                        {formatInt(r.prospect.stats[metric.attemptsKey])} att
                        {low && <span className={styles.lowSampleTag}>Low sample</span>}
                      </span>
                    )}
                  </td>
                  <td className={styles.colHideSm}>
                    {formatDecimal(r.prospect.stats.minutesPerGame)}
                  </td>
                  <td className={styles.colHideSm}>
                    {formatInt(r.prospect.stats.gamesPlayed)}
                  </td>
                </tr>
              );
            })}
            {rows.length === 0 && (
              <tr>
                <td colSpan={7} className={styles.empty}>
                  No data for this metric.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
