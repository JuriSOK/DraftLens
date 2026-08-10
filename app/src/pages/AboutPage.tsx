import { useDraftLensData } from "../data/DataProvider";
import { LoadingState, ErrorState } from "../components/DataStates";
import styles from "./AboutPage.module.css";

export function AboutPage() {
  const { data, error, loading } = useDraftLensData();

  if (loading) return <LoadingState />;
  if (error || !data) return <ErrorState message={error ?? "Unknown error"} />;

  const { historical, holdout2026, note } = data.validationSummary;
  const year2026 = data.years["2026"];
  const available = year2026.status === "available" ? year2026 : null;

  return (
    <div className="container">
      <div className={styles.intro}>
        <h1 className={styles.title}>Methodology</h1>
        <p className={styles.sub}>
          DraftLens ranks NCAA early entrants from their pre-draft statistical
          record only — no scouting opinion, no mock draft, no post-draft
          information.
        </p>
      </div>

      <div className={styles.summaryGrid}>
        <SummaryCard title="General Board" body={data.methodologySummary.generalBoard} />
        <SummaryCard title="Team Need" body={data.methodologySummary.teamNeed} />
        <SummaryCard
          title="NBA Comparables"
          body={data.methodologySummary.comparables}
        />
        <SummaryCard title="Validation" body={data.methodologySummary.validation} />
      </div>

      {available && (
        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>Two 2026 populations</h2>
          <p className={styles.sectionSub}>
            The Board page offers two different 2026 groups. They are not the
            same thing.
          </p>
          <ul className={styles.factList}>
            <li>
              <strong>Final entrants</strong> ({available.finalEntrantsCount}{" "}
              players) — the players who remained eligible after the
              withdrawal deadline. This is the exact population DraftLens's
              one-time 2026 holdout evaluation scored, and its ranking has not
              changed since that evaluation.
            </li>
            <li>
              <strong>All declared</strong> (
              {available.scoreableDeclaredCount} scoreable of{" "}
              {available.declaredCount} total) — every NCAA player who
              initially filed for early entry, including{" "}
              {available.declaredCount - available.finalEntrantsCount} who
              later withdrew, sourced from the{" "}
              {available.officialSource ? (
                <a href={available.officialSource.url} target="_blank" rel="noreferrer">
                  {available.officialSource.name}
                </a>
              ) : (
                "official NBA early-entry announcement"
              )}
              . This ranking was generated separately, after the holdout
              evaluation, using the same frozen methodology — it is an
              additional product exploration, not a re-run or extension of
              the holdout evaluation itself.
            </li>
          </ul>
        </section>
      )}

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>About the validation</h2>
        <ul className={styles.factList}>
          <li>Methodology was frozen before the final 2026 replay.</li>
          <li>
            2026 predictions were generated and cryptographically hashed
            before any 2026 prospect-level outcome was opened.
          </li>
          <li>No analytical change was made after the holdout was unsealed.</li>
        </ul>
        <p className={styles.disclosure}>
          One aggregate, non-matching 2026 diagnostic figure was briefly and
          incidentally observed while sourcing a structural (non-outcome)
          input during preparation, used nowhere, and is recorded in full in
          the project's validation report.
        </p>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Aggregate results</h2>
        <div className={styles.metricsGrid}>
          <div className={styles.metricGroup}>
            <h3 className={styles.metricGroupTitle}>Historical (2019–2025)</h3>
            <Metric
              label="Draft Probability macro ROC-AUC"
              value={historical.draftProbabilityMacroAuc}
            />
            <Metric
              label="Draft Order macro Spearman"
              value={historical.draftOrderMacroSpearman}
            />
            <Metric
              label="General Board binary AUC"
              value={historical.generalBoardBinaryAuc}
            />
            <Metric
              label="General Board graded NDCG"
              value={historical.generalBoardGradedNdcg}
            />
          </div>
          {holdout2026 && (
            <div className={styles.metricGroup}>
              <h3 className={styles.metricGroupTitle}>2026 holdout replay</h3>
              <Metric
                label="General Board graded NDCG"
                value={holdout2026.generalBoardGradedNdcg}
              />
              {holdout2026.supportLabel && (
                <p className={styles.warning}>
                  Draft Probability's 2026 classification metrics have very
                  few undrafted examples ({holdout2026.draftedShare}% of the
                  class was drafted) and are descriptive only —{" "}
                  {holdout2026.supportLabel.toLowerCase()}.
                </p>
              )}
            </div>
          )}
        </div>
      </section>

      <p className={styles.note}>{note}</p>
    </div>
  );
}

function SummaryCard({ title, body }: { title: string; body: string }) {
  return (
    <div className={styles.summaryCard}>
      <h3 className={styles.summaryTitle}>{title}</h3>
      <p className={styles.summaryBody}>{body}</p>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number | null }) {
  return (
    <div className={styles.metric}>
      <span className={styles.metricLabel}>{label}</span>
      <span className={styles.metricValue}>{value?.toFixed(4) ?? "—"}</span>
    </div>
  );
}
