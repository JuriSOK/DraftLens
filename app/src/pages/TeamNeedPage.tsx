import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useDraftLensData } from "../data/DataProvider";
import { LoadingState, ErrorState } from "../components/DataStates";
import { ScoreBadge } from "../components/ScoreBadge";
import { WeightSlider } from "../components/WeightSlider";
import { MetricTooltip } from "../components/MetricTooltip";
import { TOOLTIPS } from "../lib/tooltips";
import { computeCustomFit } from "../lib/customFit";
import type { Weights } from "../lib/customFit";
import { CUSTOM_DIMENSION_LABELS, PROFILE_LABELS } from "../types/data";
import type { CustomDimensionKey, Prospect, ProfileKey, YearAvailable } from "../types/data";
import styles from "./TeamNeedPage.module.css";

type Mode = "predefined" | "custom";

const EMPTY_WEIGHTS: Weights = {
  shooting: 0,
  playmaking: 0,
  defensiveProduction: 0,
  rebounding: 0,
  size: 0,
};

function boardOf(p: Prospect) {
  return p.declaredBoard;
}

export function TeamNeedPage() {
  const { data, error, loading } = useDraftLensData();
  const [mode, setMode] = useState<Mode>("predefined");
  const [profile, setProfile] = useState<ProfileKey>("shooter");
  const [weights, setWeights] = useState<Weights>({ ...EMPTY_WEIGHTS, shooting: 70 });

  const year2026 = data?.years["2026"];
  const available = year2026?.status === "available" ? (year2026 as YearAvailable) : null;

  const eligibleProspects = useMemo(() => {
    if (!available) return [];
    return available.prospects.filter((p) => boardOf(p) !== null);
  }, [available]);

  const predefinedResults = useMemo(() => {
    return [...eligibleProspects]
      .filter((p) => p.profiles[profile].fitScore !== null)
      .sort((a, b) => {
        const fa = a.profiles[profile].fitScore ?? -1;
        const fb = b.profiles[profile].fitScore ?? -1;
        return fb - fa;
      });
  }, [eligibleProspects, profile]);

  const customResults = useMemo(() => {
    return eligibleProspects
      .map((p) => ({ prospect: p, fit: computeCustomFit(p, weights) }))
      .filter((r) => r.fit.fitScore !== null)
      .sort((a, b) => (b.fit.fitScore ?? -1) - (a.fit.fitScore ?? -1));
  }, [eligibleProspects, weights]);

  if (loading) return <LoadingState />;
  if (error || !data || !available) return <ErrorState message={error ?? "Unknown error"} />;

  const hasActiveWeight = Object.values(weights).some((w) => w > 0);

  return (
    <div className="container">
      <div className={styles.intro}>
        <h1 className={styles.title}>
          Team Need
          <MetricTooltip
            text={TOOLTIPS.teamNeedFit.text}
            learnMoreHref={TOOLTIPS.teamNeedFit.href}
            label="About Team Need Fit Score"
          />
        </h1>
        <p className={styles.sub}>Rank prospects by the traits your team needs.</p>
      </div>

      <div className={styles.modeToggle} role="tablist" aria-label="Team Need mode">
        <button
          type="button"
          role="tab"
          aria-selected={mode === "predefined"}
          className={styles.modeButton}
          data-active={mode === "predefined"}
          onClick={() => setMode("predefined")}
        >
          Predefined Profile
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={mode === "custom"}
          className={styles.modeButton}
          data-active={mode === "custom"}
          onClick={() => setMode("custom")}
        >
          Custom Priorities
        </button>
      </div>

      {mode === "predefined" ? (
        <>
          <div className={styles.chipRow} role="group" aria-label="Choose a profile">
            {data.teamNeedProfiles.map((key) => (
              <button
                key={key}
                type="button"
                className={styles.chip}
                data-active={profile === key}
                aria-pressed={profile === key}
                onClick={() => setProfile(key)}
              >
                {PROFILE_LABELS[key]}
              </button>
            ))}
          </div>

          <ResultsTable
            rows={predefinedResults.map((p) => ({
              id: p.id,
              name: p.name,
              position: p.position,
              overallScore: boardOf(p)!.overallScore,
              boardRank: boardOf(p)!.rank,
              fitScore: p.profiles[profile].fitScore,
            }))}
            fitColumnLabel="Fit Score"
          />
        </>
      ) : (
        <div className={styles.customLayout}>
          <div className={styles.sliderPanel}>
            <p className={styles.sliderHint}>
              Relative weights — they need not sum to 100.
            </p>
            {(Object.keys(weights) as CustomDimensionKey[]).map((key) => (
              <WeightSlider
                key={key}
                id={`weight-${key}`}
                label={CUSTOM_DIMENSION_LABELS[key]}
                value={weights[key]}
                onChange={(value) => setWeights((w) => ({ ...w, [key]: value }))}
              />
            ))}
          </div>

          {hasActiveWeight ? (
            <ResultsTable
              rows={customResults.map(({ prospect, fit }) => ({
                id: prospect.id,
                name: prospect.name,
                position: prospect.position,
                overallScore: boardOf(prospect)!.overallScore,
                boardRank: boardOf(prospect)!.rank,
                fitScore: fit.fitScore,
              }))}
              fitColumnLabel="Custom Fit Score"
            />
          ) : (
            <div className={styles.emptyState}>
              Set at least one priority above 0 to rank prospects.
            </div>
          )}
        </div>
      )}
    </div>
  );
}

interface ResultRow {
  id: string;
  name: string;
  position: string;
  overallScore: number;
  boardRank: number;
  fitScore: number | null;
}

function ResultsTable({
  rows,
  fitColumnLabel,
}: {
  rows: ResultRow[];
  fitColumnLabel: string;
}) {
  return (
    <div className={styles.tableWrap}>
      <table className={styles.table}>
        <thead>
          <tr>
            <th scope="col" className={styles.colRank}>
              Rank
            </th>
            <th scope="col">Prospect</th>
            <th scope="col" className={styles.colPos}>
              Pos
            </th>
            <th scope="col" className={styles.colFit}>
              {fitColumnLabel}
            </th>
            <th scope="col" className={styles.colOverall}>
              Overall Score
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={r.id}>
              <td className={styles.colRank}>{i + 1}</td>
              <td>
                <Link to={`/prospect/${r.id}`} className={styles.nameLink}>
                  {r.name}
                </Link>
                <span className={styles.boardRankNote}>Board #{r.boardRank}</span>
              </td>
              <td className={styles.colPos}>{r.position}</td>
              <td className={styles.colFit}>
                <ScoreBadge value={r.fitScore} size="sm" />
              </td>
              <td className={styles.colOverall}>{r.overallScore}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
