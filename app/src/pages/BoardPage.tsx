import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useDraftLensData } from "../data/DataProvider";
import { LoadingState, ErrorState } from "../components/DataStates";
import { SearchInput } from "../components/SearchInput";
import { PositionFilter } from "../components/PositionFilter";
import type { PositionValue } from "../components/PositionFilter";
import { ScoreBadge, RankBadge } from "../components/ScoreBadge";
import { formatPercent } from "../lib/format";
import { PROFILE_LABELS } from "../types/data";
import type { Prospect, YearAvailable } from "../types/data";
import styles from "./BoardPage.module.css";

type Population = "finalEntrants" | "allDeclared";

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

const POPULATION_HELP: Record<Population, string> = {
  finalEntrants: "Players who remained eligible after the withdrawal deadline.",
  allDeclared:
    "All NCAA players who initially filed for early entry, including players who later withdrew.",
};

export function BoardPage() {
  const { data, error, loading } = useDraftLensData();
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [position, setPosition] = useState<PositionValue>("ALL");
  const [population, setPopulation] = useState<Population>("finalEntrants");

  const year2026 = data?.years["2026"];
  const available = year2026?.status === "available" ? (year2026 as YearAvailable) : null;

  const prospects = useMemo(() => {
    if (!available) return [];
    return available.prospects
      .filter((p) =>
        population === "finalEntrants" ? p.finalEntrantsBoard !== null : p.declaredBoard !== null,
      )
      .filter((p) => position === "ALL" || p.position === position)
      .filter((p) => p.name.toLowerCase().includes(query.trim().toLowerCase()))
      .sort((a, b) => {
        const ra = (population === "finalEntrants" ? a.finalEntrantsBoard : a.declaredBoard)!.rank;
        const rb = (population === "finalEntrants" ? b.finalEntrantsBoard : b.declaredBoard)!.rank;
        return ra - rb;
      });
  }, [available, query, position, population]);

  const insufficientData = useMemo(() => {
    if (!available || population !== "allDeclared") return [];
    if (position !== "ALL") return [];
    return available.insufficientDataProspects.filter((p) =>
      p.name.toLowerCase().includes(query.trim().toLowerCase()),
    );
  }, [available, population, position, query]);

  if (loading) return <LoadingState />;
  if (error || !data || !available) return <ErrorState message={error ?? "Unknown error"} />;

  const boardOf = (p: Prospect) => (population === "finalEntrants" ? p.finalEntrantsBoard! : p.declaredBoard!);

  return (
    <div className="container">
      <div className={styles.hero}>
        <h1 className={styles.title}>DraftLens</h1>
        <p className={styles.tagline}>
          Pre-draft analytics for smarter NBA Draft decisions.
        </p>
      </div>

      <div className={styles.boardHead}>
        <h2 className={styles.boardTitle}>
          {population === "finalEntrants" ? "2026 General Draft Board" : "2026 All-Declared Board"}
        </h2>
        <p className={styles.boardSub}>
          {population === "finalEntrants"
            ? `${available.finalEntrantsCount} declared NCAA early entrants, ranked by Overall Score — Draft Probability × Draft Order quality.`
            : `${available.scoreableDeclaredCount} NCAA players who initially declared for the 2026 Draft, ranked by Overall Score within this larger pool — an additional exploration, not the evaluated holdout board.`}
        </p>
      </div>

      <div className={styles.controls}>
        <div
          className={styles.populationToggle}
          role="tablist"
          aria-label="Population"
        >
          <button
            type="button"
            role="tab"
            aria-selected={population === "finalEntrants"}
            className={styles.popButton}
            data-active={population === "finalEntrants"}
            onClick={() => setPopulation("finalEntrants")}
          >
            Final entrants
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={population === "allDeclared"}
            className={styles.popButton}
            data-active={population === "allDeclared"}
            onClick={() => setPopulation("allDeclared")}
          >
            All declared
          </button>
        </div>
        <SearchInput value={query} onChange={setQuery} />
        <PositionFilter value={position} onChange={setPosition} />
      </div>
      <p className={styles.populationHelp}>{POPULATION_HELP[population]}</p>

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
                Overall Score
              </th>
              <th scope="col" className={styles.colProb}>
                Draft Probability
              </th>
            </tr>
          </thead>
          <tbody>
            {prospects.map((p) => {
              const board = boardOf(p);
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
                    {p.populationStatus === "WITHDRAWN" && (
                      <span className={styles.withdrawnBadge}>Withdrawn</span>
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
            {insufficientData.map((p) => (
              <tr key={p.id} className={styles.insufficientRow}>
                <td className={styles.colRank}>—</td>
                <td>
                  <span className={styles.name}>{p.name}</span>
                  <span className={styles.insufficientBadge}>Insufficient data</span>
                  {p.populationStatus === "WITHDRAWN" && (
                    <span className={styles.withdrawnBadge}>Withdrawn</span>
                  )}
                </td>
                <td className={styles.colHideSm}>
                  <span className={styles.school}>{p.school ?? "—"}</span>
                </td>
                <td className={styles.colPos}>{p.position ?? "—"}</td>
                <td className={styles.colScore}>—</td>
                <td className={styles.colProb}>—</td>
              </tr>
            ))}
            {prospects.length === 0 && insufficientData.length === 0 && (
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
