import { useNavigate } from "react-router-dom";
import { useDraftLensData } from "../data/DataProvider";
import { LoadingState, ErrorState } from "../components/DataStates";
import { formatDecimal } from "../lib/format";
import type { YearWatchlist } from "../types/data";
import styles from "./WatchlistPage.module.css";

export function WatchlistPage() {
  const { data, error, loading } = useDraftLensData();
  const navigate = useNavigate();

  if (loading) return <LoadingState />;
  if (error || !data) return <ErrorState message={error ?? "Unknown error"} />;

  const year2027 = data.years["2027"];

  if (year2027.status !== "watchlist") {
    return (
      <div className="container">
        <div className={styles.intro}>
          <h1 className={styles.title}>2027 Watchlist</h1>
        </div>
        <div className={styles.unavailable}>
          <p>{year2027.status === "unavailable" ? year2027.reason : "Not available."}</p>
        </div>
      </div>
    );
  }

  const w = year2027 as YearWatchlist;
  const returning = w.prospects.filter((p) => p.hasStats);
  const incoming = w.prospects.filter((p) => !p.hasStats);

  return (
    <div className="container">
      <div className={styles.intro}>
        <h1 className={styles.title}>2027 Watchlist</h1>
        {/* CRITICAL: a projection must never read as an official declaration. */}
        <span className={styles.projectedBadge}>Projected — not official declarations</span>
        <p className={styles.sub}>
          No official NBA early-entry declaration list exists for 2027 yet.
        </p>
      </div>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>How this list is built</h2>
        <p className={styles.sectionSub}>
          {w.consensusRule}. Source rank decides only who belongs on the
          list — never a DraftLens feature, and never its order.
        </p>
        <ul className={styles.sourceList}>
          {w.sources.map((s) => (
            <li key={s.name}>
              <a href={s.url} target="_blank" rel="noreferrer">
                {s.name}
              </a>{" "}
              — published {s.publicationDate} ({s.playersListed} players listed)
            </li>
          ))}
        </ul>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>
          Returning players with 2025-26 NCAA data ({returning.length})
        </h2>
        {/* CRITICAL: explains an ABSENCE the user would otherwise read as a
           bug, and states the scientific reason no board score is shown. */}
        <p className={styles.sectionSub}>
          No Draft Probability, Draft Order or Overall Score is shown — those
          models were validated on the declared early-entrant population, and
          a media projection is a different sampling frame.
        </p>
        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th scope="col">Prospect</th>
                <th scope="col" className={styles.colHideSm}>
                  School
                </th>
                <th scope="col" className={styles.colClass}>
                  Class
                </th>
                <th scope="col" className={styles.colStat}>
                  PTS/40 min
                </th>
                <th scope="col" className={styles.colStat}>
                  TS%
                </th>
              </tr>
            </thead>
            <tbody>
              {returning.map((p) => (
                <tr
                  key={p.id}
                  className={styles.row}
                  tabIndex={0}
                  role="link"
                  aria-label={`Open ${p.name}'s prospect detail`}
                  onClick={() => navigate(`/prospect/${p.id}`)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") navigate(`/prospect/${p.id}`);
                  }}
                >
                  <td className={styles.name}>{p.name}</td>
                  <td className={styles.colHideSm}>{p.school}</td>
                  <td className={styles.colClass}>{p.classYear ?? "—"}</td>
                  <td className={styles.colStat}>
                    {formatDecimal(p.stats?.pointsPer40 ?? null)}
                  </td>
                  <td className={styles.colStat}>
                    {p.stats?.tsPct !== null && p.stats?.tsPct !== undefined
                      ? `${(p.stats.tsPct * 100).toFixed(1)}%`
                      : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>
          Incoming freshmen — no NCAA stats yet ({incoming.length})
        </h2>
        <p className={styles.sectionSub}>
          NCAA stats available after the 2026-27 season begins. No score of
          any kind is shown for these players.
        </p>
        <ul className={styles.incomingList}>
          {incoming.map((p) => (
            <li key={p.id} className={styles.incomingItem}>
              <span className={styles.name}>{p.name}</span>
              <span className={styles.incomingSchool}>{p.school}</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
