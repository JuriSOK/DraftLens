import { useMemo, useState } from "react";
import { BarRow, CategoryMix, Histogram, Radar } from "../charts/Charts";
import { PercentileBar } from "../PercentileBar";
import { binValues, categoryCounts } from "../../lib/summaries";
import {
  METRICS, METRIC_FEATURE_KEY, METRIC_GROUPS, RELIABILITY_MIN_ATTEMPTS,
} from "../../lib/statMetrics";
import type { MetricDef } from "../../lib/statMetrics";
import { formatDecimal, formatPercent } from "../../lib/format";
import type { AnalysisResult, AnalyzedProspect, Capability }
  from "../../lib/runtime/analyze";
import type { ValidationResult } from "../../lib/dataset/validate";
import styles from "./AnalysisWorkspace.module.css";

/** The imported analysis, once a file has passed validation.
 *
 * A separate, temporary session: nothing here touches or replaces the
 * built-in 2026 and 2027 data, and refreshing the page loses it because the
 * dataset was never stored anywhere.
 *
 * Every tab is hidden or disabled with its reason when the data cannot
 * support it — the workspace never shows an empty board where a real one
 * would be. */

type TabId = "overview" | "board" | "stats" | "teamNeed" | "players";

const DIMENSION_LABELS: Record<string, string> = {
  SHOOTING: "Shooting",
  PLAYMAKING: "Playmaking",
  BOX_SCORE_DEFENSIVE_PRODUCTION: "Defensive Production",
  REBOUNDING: "Rebounding",
  SIZE: "Size",
  RIM_PRESSURE: "Rim Pressure",
};
const RADAR_LABELS: Record<string, string> = {
  SHOOTING: "Shoot",
  PLAYMAKING: "Play",
  BOX_SCORE_DEFENSIVE_PRODUCTION: "Def",
  REBOUNDING: "Reb",
  SIZE: "Size",
  RIM_PRESSURE: "Rim",
};
const DIMENSION_ORDER = Object.keys(DIMENSION_LABELS);

const PROFILE_LABELS: Record<string, string> = {
  SHOOTER: "Shooter",
  SLASHER: "Slasher / Rim Attacker",
  PLAYMAKER: "Playmaker",
  THREE_AND_D: "3&D Wing",
  RIM_PROTECTOR: "Rim Protector",
  STRETCH_BIG: "Stretch Big",
};

function num(value: number | null | undefined): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

export function AnalysisWorkspace({
  analysis, validation, fileName, onReset,
}: {
  analysis: AnalysisResult;
  validation: ValidationResult;
  fileName: string | null;
  onReset: () => void;
}) {
  const caps = useMemo(
    () => Object.fromEntries(analysis.capabilities.map((c) => [c.id, c])) as
      Record<string, Capability>, [analysis.capabilities]);
  const [tab, setTab] = useState<TabId>("overview");
  const [selected, setSelected] = useState<string | null>(null);

  const tabs: { id: TabId; label: string; available: boolean; reason?: string }[] = [
    { id: "overview", label: "Overview", available: true },
    { id: "board", label: "Board", available: caps.generalBoard.available,
      reason: caps.generalBoard.reason },
    { id: "stats", label: "Stats", available: true },
    { id: "teamNeed", label: "Team Need", available: caps.teamNeed.available,
      reason: caps.teamNeed.reason },
    { id: "players", label: "Players", available: true },
  ];

  const player = selected
    ? analysis.prospects.find((p) => p.id === selected) ?? null : null;

  return (
    <section className={styles.workspace}>
      <header className={styles.head}>
        <div>
          <h2 className={styles.datasetName}>{analysis.datasetName}</h2>
          <p className={styles.datasetMeta}>
            {analysis.prospects.length} prospects · {analysis.season} NCAA
            season · {analysis.populationType}
            {fileName ? ` · ${fileName}` : ""}
          </p>
        </div>
        <button type="button" className={styles.ghostButton} onClick={onReset}>
          Analyze another file
        </button>
      </header>

      <nav className={styles.tabs} aria-label="Imported analysis sections">
        {tabs.map((t) => (
          <button
            key={t.id}
            type="button"
            className={t.id === tab ? `${styles.tab} ${styles.tabActive}` : styles.tab}
            onClick={() => t.available && setTab(t.id)}
            disabled={!t.available}
            title={t.available ? undefined : t.reason}
            aria-current={t.id === tab}
          >
            {t.label}
            {!t.available && <span className={styles.tabOff}> — unavailable</span>}
          </button>
        ))}
      </nav>

      {tab === "overview" && (
        <OverviewTab analysis={analysis} validation={validation} />
      )}
      {tab === "board" && <BoardTab analysis={analysis} onOpen={(id) => {
        setSelected(id); setTab("players");
      }} />}
      {tab === "stats" && <StatsTab analysis={analysis} />}
      {tab === "teamNeed" && <TeamNeedTab analysis={analysis} />}
      {tab === "players" && (
        <PlayersTab analysis={analysis} selected={player}
                    onSelect={setSelected} />
      )}
    </section>
  );
}

// ------------------------------------------------------------------ overview
function OverviewTab({
  analysis, validation,
}: { analysis: AnalysisResult; validation: ValidationResult }) {
  const positions = categoryCounts(analysis.prospects.map((p) => p.position));
  const boardAvailable = analysis.capabilities
    .find((c) => c.id === "generalBoard")?.available;
  const scores = analysis.prospects
    .map((p) => p.overallScore).filter((s): s is number => s !== null);

  return (
    <div className={styles.tabBody}>
      <h3 className={styles.blockTitle}>Available analysis</h3>
      <ul className={styles.capabilityList}>
        {analysis.capabilities.map((c) => (
          <li key={c.id} className={styles.capability} data-available={c.available}>
            <span className={styles.capabilityMark} aria-hidden="true">
              {c.available ? "✓" : "—"}
            </span>
            <span>
              <span className={styles.capabilityLabel}>
                {c.label}
                <span className="visually-hidden">
                  {c.available ? " — available" : " — unavailable"}
                </span>
              </span>
              <span className={styles.capabilityReason}>{c.reason}</span>
            </span>
          </li>
        ))}
      </ul>

      {analysis.imputedModelFeatures.length > 0 && (
        <p className={styles.note}>
          {analysis.imputedModelFeatures.length} of the{" "}
          {analysis.imputedModelFeatures.length
            + (25 - analysis.imputedModelFeatures.length)} model inputs are
          absent from this file and reached the estimator as the frozen
          training median — the same treatment DraftLens applies to its own
          missing data. The board is still the frozen model, but it rests on
          fewer measured inputs than the built-in one.
        </p>
      )}

      <div className="analyticsRow">
        {boardAvailable && scores.length > 0 && (
          <div className="analyticsCard">
            <span className="analyticsTitle">Overall Score distribution</span>
            <Histogram
              bins={binValues(scores, { min: 0, max: 100, buckets: 10 })}
              ariaLabel="Distribution of Overall Score across the imported class"
            />
          </div>
        )}
        <div className="analyticsCard">
          <span className="analyticsTitle">Position mix</span>
          <CategoryMix counts={positions}
                       ariaLabel="Position mix across the imported class" />
        </div>
      </div>

      {validation.warnings.length > 0 && (
        <div className={styles.warnings}>
          <h3 className={styles.blockTitle}>
            Warnings ({validation.warnings.length})
          </h3>
          <ul className={styles.warningList}>
            {validation.warnings.slice(0, 12).map((w, i) => (
              <li key={i}>
                {w.field && <span className={styles.warnWhere}>{w.field}</span>}
                {w.message}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

// --------------------------------------------------------------------- board
function BoardTab({
  analysis, onOpen,
}: { analysis: AnalysisResult; onOpen: (id: string) => void }) {
  const rows = [...analysis.prospects]
    .filter((p) => p.boardRank !== null)
    .sort((a, b) => (a.boardRank ?? 0) - (b.boardRank ?? 0));

  return (
    <div className={styles.tabBody}>
      <p className={styles.note}>
        Overall Score is a percentile <strong>within this imported class</strong>,
        exactly as the built-in board is within its own. Imported players are
        never mixed into DraftLens's 2026 pool.
      </p>
      <div className={styles.tableWrap}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th scope="col" className={styles.colRank}>Rank</th>
              <th scope="col">Prospect</th>
              <th scope="col" className={styles.colHideSm}>School</th>
              <th scope="col" className={styles.colPos}>Pos</th>
              <th scope="col" className={styles.colNum}>Overall Score</th>
              <th scope="col" className={styles.colNum}>Draft Probability</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((p) => (
              <tr key={p.id} className={styles.row} tabIndex={0} role="link"
                  aria-label={`Open ${p.name}`}
                  onClick={() => onOpen(p.id)}
                  onKeyDown={(e) => { if (e.key === "Enter") onOpen(p.id); }}>
                <td className={styles.colRank}>{p.boardRank}</td>
                <td className={styles.name}>{p.name}</td>
                <td className={styles.colHideSm}>{p.school ?? "—"}</td>
                <td className={styles.colPos}>{p.position}</td>
                <td className={styles.colNum}>{p.overallScore}</td>
                <td className={styles.colNum}>
                  {formatPercent(num(p.draftProbability))}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// --------------------------------------------------------------------- stats
function StatsTab({ analysis }: { analysis: AnalysisResult }) {
  const [metric, setMetric] = useState<MetricDef>(METRICS[0]);

  const rows = useMemo(() => {
    const featureKey = METRIC_FEATURE_KEY[metric.key];
    const attemptsKey = metric.attemptsKey
      ? METRIC_FEATURE_KEY[metric.attemptsKey] : null;
    return analysis.prospects
      .map((p) => ({
        prospect: p,
        value: num(p.features[featureKey]),
        attempts: attemptsKey ? num(p.features[attemptsKey]) : null,
      }))
      .filter((r): r is { prospect: AnalyzedProspect; value: number;
                          attempts: number | null } => r.value !== null)
      .sort((a, b) => (metric.lowerIsBetter ? a.value - b.value : b.value - a.value));
  }, [analysis.prospects, metric]);

  const values = rows.map((r) => r.value);
  const min = values.length ? Math.min(...values) : 0;
  const max = values.length ? Math.max(...values) : 1;
  const format = (v: number) =>
    metric.isPercent ? formatPercent(v) : formatDecimal(v);

  return (
    <div className={styles.tabBody}>
      <div className={styles.metricGroups}>
        {METRIC_GROUPS.map((group) => (
          <div key={group} className={styles.metricGroup}>
            {METRICS.filter((m) => m.group === group).map((m) => (
              <button
                key={m.key}
                type="button"
                className={m.key === metric.key
                  ? `${styles.chip} ${styles.chipActive}` : styles.chip}
                onClick={() => setMetric(m)}
              >
                {m.label}
              </button>
            ))}
          </div>
        ))}
      </div>

      {metric.lowerIsBetter && (
        <p className={styles.lowerNote}>Lower is better.</p>
      )}

      {rows.length > 0 && (
        <div className="analyticsRow">
          <div className="analyticsCard">
            <span className="analyticsTitle">{metric.label} distribution</span>
            <Histogram
              bins={binValues(values, {
                min, max: max === min ? min + 1 : max, buckets: 12,
                format: (n) => (metric.isPercent
                  ? `${Math.round(n * 100)}%` : n.toFixed(1)),
              })}
              ariaLabel={`Distribution of ${metric.label} in the imported class`}
            />
          </div>
        </div>
      )}

      <div className={styles.tableWrap}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th scope="col" className={styles.colRank}>Rank</th>
              <th scope="col">Prospect</th>
              <th scope="col" className={styles.colHideSm}>School</th>
              <th scope="col" className={styles.colPos}>Pos</th>
              <th scope="col" className={styles.colNum}>{metric.label}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => {
              const lowSample = metric.attemptsKey !== undefined
                && (r.attempts === null || r.attempts < RELIABILITY_MIN_ATTEMPTS);
              return (
                <tr key={r.prospect.id}>
                  <td className={styles.colRank}>{i + 1}</td>
                  <td className={styles.name}>
                    {r.prospect.name}
                    {/* CRITICAL: the same reliability minimum the frozen
                       methodology uses — a rate off a handful of attempts is
                       not evidence. */}
                    {lowSample && (
                      <span className={styles.lowSample}>low sample</span>
                    )}
                  </td>
                  <td className={styles.colHideSm}>{r.prospect.school ?? "—"}</td>
                  <td className={styles.colPos}>{r.prospect.position}</td>
                  <td className={styles.colNum}>{format(r.value)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ----------------------------------------------------------------- team need
function TeamNeedTab({ analysis }: { analysis: AnalysisResult }) {
  const profiles = Object.keys(
    analysis.prospects[0]?.profiles ?? {}) as string[];
  const [profile, setProfile] = useState(profiles[0] ?? "");

  const ranked = useMemo(() => analysis.prospects
    .map((p) => ({ prospect: p, fit: p.profiles[profile] }))
    .filter((r) => r.fit && Number.isFinite(r.fit.fitRaw))
    .sort((a, b) => b.fit.fitRaw - a.fit.fitRaw), [analysis.prospects, profile]);

  const topDimensions = useMemo(() => {
    const top = ranked.slice(0, 10).map((r) => r.prospect);
    return DIMENSION_ORDER.map((key) => {
      const values = top.map((p) => p.dimensions[key])
        .filter((v) => Number.isFinite(v));
      return {
        key,
        value: values.length
          ? values.reduce((a, b) => a + b, 0) / values.length : null,
      };
    });
  }, [ranked]);

  if (profiles.length === 0) return null;

  return (
    <div className={styles.tabBody}>
      <div className={styles.metricGroup}>
        {profiles.map((name) => (
          <button key={name} type="button"
                  className={name === profile
                    ? `${styles.chip} ${styles.chipActive}` : styles.chip}
                  onClick={() => setProfile(name)}>
            {PROFILE_LABELS[name] ?? name}
          </button>
        ))}
      </div>

      <div className="analyticsRow">
        <div className="analyticsCard">
          <span className="analyticsTitle">Fit Score distribution</span>
          <Histogram
            bins={binValues(ranked.map((r) => r.fit.fitRaw),
                            { min: 0, max: 100, buckets: 10 })}
            ariaLabel={`Distribution of ${profile} Fit Score`}
          />
        </div>
        <div className="analyticsCard">
          <span className="analyticsTitle">Average dimensions · top 10 fits</span>
          {topDimensions.map((d) => (
            <BarRow key={d.key} label={DIMENSION_LABELS[d.key] ?? d.key}
                    value={d.value} />
          ))}
        </div>
      </div>

      <div className={styles.tableWrap}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th scope="col" className={styles.colRank}>Rank</th>
              <th scope="col">Prospect</th>
              <th scope="col" className={styles.colPos}>Pos</th>
              <th scope="col" className={styles.colNum}>Fit Score</th>
              <th scope="col" className={styles.colHideSm}>Eligibility</th>
            </tr>
          </thead>
          <tbody>
            {ranked.map((r, i) => (
              <tr key={r.prospect.id}>
                <td className={styles.colRank}>{i + 1}</td>
                <td className={styles.name}>{r.prospect.name}</td>
                <td className={styles.colPos}>{r.prospect.position}</td>
                <td className={styles.colNum}>{r.fit.fitScore}</td>
                <td className={styles.colHideSm}>
                  {r.fit.eligibility === "ELIGIBLE" ? "—" : r.fit.eligibility}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ------------------------------------------------------------------- players
function PlayersTab({
  analysis, selected, onSelect,
}: {
  analysis: AnalysisResult;
  selected: AnalyzedProspect | null;
  onSelect: (id: string | null) => void;
}) {
  if (selected) {
    return <PlayerDetail player={selected} onBack={() => onSelect(null)} />;
  }
  return (
    <div className={styles.tabBody}>
      <div className={styles.playerGrid}>
        {analysis.prospects.map((p) => (
          <button key={p.id} type="button" className={styles.playerCard}
                  onClick={() => onSelect(p.id)}>
            <span className={styles.playerInitials} aria-hidden="true">
              {p.name.split(/\s+/).map((w) => w[0]).slice(0, 2).join("")}
            </span>
            <span className={styles.playerName}>{p.name}</span>
            <span className={styles.playerMeta}>
              {p.school ?? "—"} · {p.position}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}

function PlayerDetail({
  player, onBack,
}: { player: AnalyzedProspect; onBack: () => void }) {
  const radarAxes = DIMENSION_ORDER.map((key) => ({
    label: RADAR_LABELS[key] ?? key,
    value: Number.isFinite(player.dimensions[key]) ? player.dimensions[key] : null,
  }));
  const hasDimensions = radarAxes.some((a) => a.value !== null);
  const comparables = player.comparables;

  return (
    <div className={styles.tabBody}>
      <button type="button" className={styles.backLink} onClick={onBack}>
        ← All players
      </button>

      <div className={styles.detailHead}>
        <span className={styles.detailInitials} aria-hidden="true">
          {player.name.split(/\s+/).map((w) => w[0]).slice(0, 2).join("")}
        </span>
        <div>
          <h3 className={styles.detailName}>{player.name}</h3>
          <p className={styles.detailMeta}>
            {player.school ?? "—"} · {player.position}
            {player.boardRank !== null && ` · Board rank #${player.boardRank}`}
            {player.overallScore !== null
              && ` · Overall Score ${player.overallScore}`}
          </p>
        </div>
      </div>

      {hasDimensions && (
        <>
          <h4 className={styles.blockTitle}>Basketball Profile</h4>
          <div className={styles.profileLayout}>
            <div className="analyticsCard">
              <span className="analyticsTitle">Six-dimension shape</span>
              <Radar axes={radarAxes}
                     ariaLabel="Basketball Profile radar across six dimensions" />
            </div>
            <div className={styles.dimensionGrid}>
              {DIMENSION_ORDER.map((key) => (
                <PercentileBar
                  key={key}
                  label={DIMENSION_LABELS[key] ?? key}
                  value={Number.isFinite(player.dimensions[key])
                    ? player.dimensions[key] : null}
                  peerGroup={key === "SIZE" ? "GLOBAL" : "GLOBAL"}
                  hint={key === "BOX_SCORE_DEFENSIVE_PRODUCTION"
                    ? "Based on steals and blocks; not a complete measure of "
                      + "defensive quality."
                    : undefined}
                />
              ))}
            </div>
          </div>
        </>
      )}

      {Object.keys(player.profiles).length > 0 && (
        <>
          <h4 className={styles.blockTitle}>Team Need Fit</h4>
          <div className={styles.fitGrid}>
            {Object.entries(player.profiles).map(([name, fit]) => (
              <div key={name} className={styles.fitCard}>
                <span className={styles.fitLabel}>
                  {PROFILE_LABELS[name] ?? name}
                </span>
                <span className={styles.fitScore}>
                  {Number.isFinite(fit.fitScore) ? `${fit.fitScore} / 100`
                    : "Unavailable"}
                </span>
                {fit.eligibility !== "ELIGIBLE" && (
                  <span className={styles.fitElig}>{fit.eligibility}</span>
                )}
              </div>
            ))}
          </div>
        </>
      )}

      <h4 className={styles.blockTitle}>NBA Statistical Comparables</h4>
      {comparables && comparables.status === "OK" ? (
        <div className={styles.comparableGrid}>
          {comparables.comparables.map((c) => (
            <div key={c.id} className={styles.comparableCard}>
              <span className={styles.comparableRank}>
                #{c.rank} closest profile
              </span>
              <span className={styles.comparableName}>{c.name}</span>
              <span className={styles.comparableMeta}>
                {c.heightInches !== null && `${Math.floor(c.heightInches / 12)}'`}
                {c.heightInches !== null && `${c.heightInches % 12}"`}
                {" · similarity "}{c.similarityScore}
              </span>
            </div>
          ))}
        </div>
      ) : (
        <p className={styles.note}>
          {comparables?.reason
            ?? "NBA Comparables are unavailable for this dataset."}
        </p>
      )}
    </div>
  );
}
