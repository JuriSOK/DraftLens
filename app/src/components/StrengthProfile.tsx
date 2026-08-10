import { DIMENSION_LABELS, DIMENSION_PEER_GROUP } from "../types/data";
import type { DimensionEvidence, Dimensions, EvidenceItem } from "../types/data";
import styles from "./StrengthProfile.module.css";

/** Key Strengths and Areas to Watch — a scouting summary that shows its work.
 *
 * SELECTION IS DETERMINISTIC AND HAS NO EXCEPTIONS. The three highest scored
 * dimensions are the strengths; the two lowest of what remains are the areas
 * to watch. There is no threshold to argue about, no per-player override, and
 * no way for a card to appear because it flattered someone.
 *
 * EVIDENCE IS THE DIMENSION'S OWN INPUTS. Each card quotes the statistics the
 * frozen configuration says that dimension is computed from, with the
 * prospect's real values. Nothing is generated prose and nothing is
 * projection: the wording states where a trait sits relative to NCAA peers
 * and relative to this player's other traits, and stops there.
 *
 * A dimension with no score is absent, not zero — it was never measured. */

const STRENGTH_COUNT = 3;
const WATCH_COUNT = 2;

interface Entry {
  key: keyof Dimensions;
  label: string;
  value: number;
  evidence: EvidenceItem[];
}

const ORDER: (keyof Dimensions)[] = [
  "shooting", "playmaking", "defensiveProduction", "rebounding", "size",
  "rimPressure",
];

export function selectStrengths(
  dimensions: Dimensions,
  evidence: DimensionEvidence | null,
): { strengths: Entry[]; watch: Entry[] } {
  const scored: Entry[] = ORDER
    .map((key) => ({
      key,
      label: DIMENSION_LABELS[key],
      value: dimensions[key],
      evidence: evidence?.[key] ?? [],
    }))
    .filter((e): e is Entry => e.value !== null && Number.isFinite(e.value))
    .sort((a, b) => b.value - a.value);

  const strengths = scored.slice(0, STRENGTH_COUNT);
  // Disjoint by construction: the areas to watch are drawn only from what the
  // strengths did not take, so a dimension is never both.
  const remaining = scored.slice(STRENGTH_COUNT);
  const watch = remaining.slice(-WATCH_COUNT).reverse();
  return { strengths, watch };
}

function peerGroup(key: keyof Dimensions): string {
  return DIMENSION_PEER_GROUP[key] === "POSITION"
    ? "NCAA players at a similar position" : "NCAA peers";
}

function Card({ entry, kind }: { entry: Entry; kind: "strength" | "watch" }) {
  const pct = Math.max(0, Math.min(100, entry.value));
  return (
    <article className={styles.card} data-kind={kind}>
      <header className={styles.cardHead}>
        <h4 className={styles.cardTitle}>{entry.label}</h4>
        <span className={styles.score}>
          {Math.round(entry.value)}
          <span className={styles.scoreOutOf}> / 100</span>
        </span>
      </header>

      <div className={styles.track} role="img"
           aria-label={`${Math.round(entry.value)} out of 100 versus ${peerGroup(entry.key)}`}>
        <span className={styles.fill} style={{ width: `${pct}%` }} />
      </div>

      {entry.evidence.length > 0 && (
        <ul className={styles.evidence}>
          {entry.evidence.map((item) => (
            <li key={item.label} className={styles.evidenceItem}>
              <span className={styles.evidenceValue}>{item.formattedValue}</span>
              <span className={styles.evidenceLabel}>
                {item.label}
                {item.lowerIsBetter && (
                  <span className={styles.lowerIsBetter}> (lower is better)</span>
                )}
              </span>
            </li>
          ))}
        </ul>
      )}

      <p className={styles.context}>
        {kind === "strength"
          ? `Ranks above ${Math.round(entry.value)}% of ${peerGroup(entry.key)}, `
            + "and is among the strongest measured traits in this profile."
          : `Ranks above ${Math.round(entry.value)}% of ${peerGroup(entry.key)}, `
            + "and sits below this player's other measured dimensions."}
      </p>
    </article>
  );
}

export function StrengthProfile({
  dimensions,
  evidence,
}: {
  dimensions: Dimensions;
  evidence: DimensionEvidence | null;
}) {
  const { strengths, watch } = selectStrengths(dimensions, evidence);
  if (strengths.length === 0) return null;

  return (
    <div className={styles.wrap}>
      <div className={styles.group}>
        <h3 className={styles.groupTitle}>Key Strengths</h3>
        <div className={styles.cards}>
          {strengths.map((e) => <Card key={e.key} entry={e} kind="strength" />)}
        </div>
      </div>
      {watch.length > 0 && (
        <div className={styles.group}>
          <h3 className={styles.groupTitle}>Areas to Watch</h3>
          <div className={styles.cards}>
            {watch.map((e) => <Card key={e.key} entry={e} kind="watch" />)}
          </div>
        </div>
      )}
    </div>
  );
}
