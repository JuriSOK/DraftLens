import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useDraftLensData } from "../data/DataProvider";
import { LoadingState, ErrorState } from "../components/DataStates";
import { SearchInput } from "../components/SearchInput";
import { PositionFilter } from "../components/PositionFilter";
import type { PositionValue } from "../components/PositionFilter";
import { ScoreBadge, RankBadge } from "../components/ScoreBadge";
import { MetricTooltip } from "../components/MetricTooltip";
import { TOOLTIPS } from "../lib/tooltips";
import { formatPercent } from "../lib/format";
import { PROFILE_LABELS } from "../types/data";
import type { Prospect, YearAvailable } from "../types/data";
import styles from "./BoardPage.module.css";

interface TopProfile {
  key: keyof Prospect["profiles"];
  score: number;
}

function topProfile(prospect: Prospect): TopProfile | null {
  const keys = Object.keys(prospect.profiles) as (keyof Prospect["profiles"])[];
  const candidates: TopProfile[] = [];
  for (const key of keys) {
    const p = prospect.profiles[key];
    if (p.eligibility === "ELIGIBLE" && p.fitScore !== null && p.fitScore >= 80) {
      candidates.push({ key, score: p.fitScore });
    }
  }
  if (candidates.length === 0) return null;
  return candidates.reduce((a, b) => (b.score > a.score ? b : a));
}

/** The single primary 2026 dataset: every scoreable prospect in the 2026 NCAA
 * Prospect Pool, ranked by their board. Declaration/withdrawal status is kept
 * in the data (see types/data.ts `populationStatus`) for reproducibility and
 * audit, but does not drive the normal board experience — DraftLens ranks
 * basketball evaluation here, not administrative Draft process. */
export function BoardPage() {
  const { data, error, loading } = useDraftLensData();
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [position, setPosition] = useState<PositionValue>("ALL");

  const year2026 = data?.years["2026"];
  const available = year2026?.status === "available" ? (year2026 as YearAvailable) : null;

  const prospects = useMemo(() => {
    if (!available) return [];
    return available.prospects
      .filter((p) => p.declaredBoard !== null)
      .filter((p) => position === "ALL" || p.position === position)
      .filter((p) => p.name.toLowerCase().includes(query.trim().toLowerCase()))
      .sort((a, b) => a.declaredBoard!.rank - b.declaredBoard!.rank);
  }, [available, query, position]);

  if (loading) return <LoadingState />;
  if (error || !data || !available) return <ErrorState message={error ?? "Unknown error"} />;

  return (
    <div className="container">
      <div className={styles.hero}>
        <h1 className={styles.title}>DraftLens</h1>
        <p className={styles.tagline}>
          Pre-draft analytics for smarter NBA Draft decisions.
        </p>
      </div>

      <div className={styles.boardHead}>
        <h2 className={styles.boardTitle}>2026 General Draft Board</h2>
        <p className={styles.boardSub}>
          {available.scoreableDeclaredCount} players · 2026 NCAA Prospect Pool
        </p>
      </div>

      <div className={styles.controls}>
        <SearchInput value={query} onChange={setQuery} />
        <PositionFilter value={position} onChange={setPosition} />
      </div>

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
              <th scope="col" className={styles.colScore}>
                <span className={styles.thWithHelp}>
                  Overall Score
                  <MetricTooltip
                    text={TOOLTIPS.overallScore.text}
                    learnMoreHref={TOOLTIPS.overallScore.href}
                    label="About Overall Score"
                  />
                </span>
              </th>
              <th scope="col" className={styles.colProb}>
                <span className={styles.thWithHelp}>
                  Draft Probability
                  <MetricTooltip
                    text={TOOLTIPS.draftProbability.text}
                    learnMoreHref={TOOLTIPS.draftProbability.href}
                    label="About Draft Probability"
                  />
                </span>
              </th>
            </tr>
          </thead>
          <tbody>
            {prospects.map((p) => {
              const board = p.declaredBoard!;
              const best = topProfile(p);
              return (
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
                  <td className={styles.colRank}>
                    <RankBadge rank={board.rank} />
                  </td>
                  <td>
                    <span className={styles.name}>{p.name}</span>
                    {best && (
                      <span className={styles.archetype}>
                        {PROFILE_LABELS[best.key]}
                      </span>
                    )}
                  </td>
                  <td className={styles.colHideSm}>
                    <span className={styles.school}>{p.school}</span>
                  </td>
                  <td className={styles.colPos}>{p.position}</td>
                  <td className={styles.colScore}>
                    <ScoreBadge value={board.overallScore} size="sm" />
                  </td>
                  <td className={styles.colProb}>
                    {formatPercent(board.draftProbability)}
                  </td>
                </tr>
              );
            })}
            {prospects.length === 0 && (
              <tr>
                <td colSpan={6} className={styles.empty}>
                  No prospects match this search.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
