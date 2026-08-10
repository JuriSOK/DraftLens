import { useEffect, useRef } from "react";
import type { DatasetFormatSchema, FieldSpec } from "../../lib/runtime/types";
import styles from "./FormatReference.module.css";

/** The full column reference, behind a disclosure.
 *
 * Kept out of the default screen deliberately: someone arriving with a file
 * wants to try it, and someone building one wants the whole table. The rows
 * are generated from the schema the runtime actually validates against, so
 * this cannot document a format the product does not enforce. */

function Row({ field }: { field: FieldSpec }) {
  return (
    <tr>
      <td className={styles.name}>{field.name}</td>
      <td className={styles.required}>
        {field.required ? "Required" : "Optional"}
      </td>
      <td>{field.type}</td>
      <td className={styles.unit}>{field.unit}</td>
      <td className={styles.description}>{field.description}</td>
    </tr>
  );
}

export function FormatReference({
  schema, onClose,
}: {
  schema: DatasetFormatSchema;
  onClose: () => void;
}) {
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    closeRef.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  const groups = Object.entries(schema.groups);

  return (
    <div className={styles.backdrop} onClick={onClose} role="presentation">
      <div
        className={styles.modal}
        role="dialog"
        aria-modal="true"
        aria-label="DraftLens Dataset Format reference"
        onClick={(e) => e.stopPropagation()}
      >
        <header className={styles.head}>
          <h2 className={styles.title}>
            {schema.name} v{schema.schemaVersion}
          </h2>
          <button ref={closeRef} type="button" className={styles.close}
                  onClick={onClose} aria-label="Close format reference">
            ✕
          </button>
        </header>

        <div className={styles.body}>
          <p className={styles.note}>
            Every input is a season <strong>total</strong> or a physical
            measurement. DraftLens computes each percentage itself, so no
            column is a rate and there is no ambiguity about whether 41.2
            means 41.2% or 0.412. Minutes are the season total, height is in
            inches, weight in pounds, and <code>season</code> is the year the
            NCAA season ends — 2026 is the 2025-26 season.
          </p>

          <h3 className={styles.groupTitle}>Metadata</h3>
          <p className={styles.groupNote}>
            In Excel these live on the <code>{schema.excelSheets.metadata}</code>{" "}
            sheet as Key / Value rows.
          </p>
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th scope="col">Column</th><th scope="col">Required?</th>
                  <th scope="col">Type</th><th scope="col">Unit</th>
                  <th scope="col">Description</th>
                </tr>
              </thead>
              <tbody>
                {schema.metadataFields.map((f) => <Row key={f.name} field={f} />)}
              </tbody>
            </table>
          </div>

          {groups.map(([group, description]) => {
            const fields = schema.prospectFields.filter((f) => f.group === group);
            if (fields.length === 0) return null;
            return (
              <div key={group}>
                <h3 className={styles.groupTitle}>
                  {group.replace(/_/g, " ")}
                </h3>
                <p className={styles.groupNote}>{description}</p>
                <div className={styles.tableWrap}>
                  <table className={styles.table}>
                    <thead>
                      <tr>
                        <th scope="col">Column</th><th scope="col">Required?</th>
                        <th scope="col">Type</th><th scope="col">Unit</th>
                        <th scope="col">Description</th>
                      </tr>
                    </thead>
                    <tbody>
                      {fields.map((f) => <Row key={f.name} field={f} />)}
                    </tbody>
                  </table>
                </div>
              </div>
            );
          })}

          <h3 className={styles.groupTitle}>Refused columns</h3>
          <p className={styles.groupNote}>
            Imported analysis is pre-draft. A file containing any of these is
            rejected rather than having the column ignored:
          </p>
          <p className={styles.codeList}>
            {schema.prohibitedFields.join(", ")}
          </p>
          <p className={styles.groupNote}>
            These rate columns are also refused — send the counts instead, and
            DraftLens derives the rate with its own formula:
          </p>
          <p className={styles.codeList}>
            {schema.derivedRateFields.join(", ")}
          </p>

          <h3 className={styles.groupTitle}>Limits</h3>
          <p className={styles.groupNote}>
            {schema.limits.minRows}–{schema.limits.maxRows} prospects, up to{" "}
            {Math.round(schema.limits.maxFileBytes / (1024 * 1024))} MB. A
            draft class, not a data warehouse — the whole file is parsed and
            held in your browser.
          </p>
        </div>
      </div>
    </div>
  );
}
