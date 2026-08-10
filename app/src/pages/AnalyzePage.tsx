import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { DatasetParseError, parseDatasetFile } from "../lib/dataset/parse";
import { validateDataset } from "../lib/dataset/validate";
import type { Issue, ValidationResult } from "../lib/dataset/validate";
import { loadCore, loadSeason } from "../lib/runtime/load";
import { analyzeDataset } from "../lib/runtime/analyze";
import type { AnalysisResult } from "../lib/runtime/analyze";
import type { DatasetFormatSchema, RuntimeCore } from "../lib/runtime/types";
import { FormatReference } from "../components/dataset/FormatReference";
import { AnalysisWorkspace } from "../components/dataset/AnalysisWorkspace";
import styles from "./AnalyzePage.module.css";

type Stage = "upload" | "working" | "invalid" | "ready";

export function AnalyzePage() {
  const [stage, setStage] = useState<Stage>("upload");
  const [fileName, setFileName] = useState<string | null>(null);
  const [fatal, setFatal] = useState<string | null>(null);
  const [validation, setValidation] = useState<ValidationResult | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [schema, setSchema] = useState<DatasetFormatSchema | null>(null);
  const [showFormat, setShowFormat] = useState(false);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  // The format reference must be readable BEFORE anyone uploads anything —
  // that is exactly when someone needs it. Fetching the core bundle here also
  // means the first upload has the schema already in hand.
  useEffect(() => {
    let cancelled = false;
    loadCore()
      .then((core) => { if (!cancelled) setSchema(core.datasetFormat); })
      .catch(() => { /* surfaced on upload, where it blocks something */ });
    return () => { cancelled = true; };
  }, []);

  const reset = useCallback(() => {
    setStage("upload");
    setFileName(null);
    setFatal(null);
    setValidation(null);
    setAnalysis(null);
    if (inputRef.current) inputRef.current.value = "";
  }, []);

  const handleFile = useCallback(async (file: File) => {
    setStage("working");
    setFatal(null);
    setValidation(null);
    setAnalysis(null);
    setFileName(file.name);

    let core: RuntimeCore;
    try {
      core = await loadCore();
      setSchema(core.datasetFormat);
    } catch (error) {
      setFatal((error as Error).message);
      setStage("invalid");
      return;
    }

    try {
      const parsed = await parseDatasetFile(file, core.datasetFormat);
      const result = validateDataset(parsed, core.datasetFormat,
                                     core.supportedSeasons);
      setValidation(result);
      if (!result.ok || !result.dataset) {
        setStage("invalid");
        return;
      }
      const season = core.supportedSeasons.includes(result.dataset.metadata.season)
        ? await loadSeason(result.dataset.metadata.season)
        : null;
      setAnalysis(analyzeDataset(result.dataset, core, season));
      setStage("ready");
    } catch (error) {
      setFatal(error instanceof DatasetParseError
        ? error.message
        : `Could not read this file: ${(error as Error).message}`);
      setStage("invalid");
    }
  }, []);

  const onDrop = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    setDragging(false);
    const file = event.dataTransfer.files?.[0];
    if (file) void handleFile(file);
  }, [handleFile]);

  const base = import.meta.env.BASE_URL;

  return (
    <div className="container">
      <div className={styles.intro}>
        <h1 className={styles.title}>Analyze your own Draft class</h1>
        <p className={styles.sub}>
          Import an NCAA prospect dataset and run the same frozen DraftLens
          analyses — scored against real NCAA peer distributions, and limited
          to what your data methodologically supports.
        </p>
      </div>

      {stage !== "ready" && (
        <section
          className={styles.dropZone}
          data-dragging={dragging}
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
        >
          <p className={styles.dropTitle}>Excel (.xlsx, .xls) or JSON (.json)</p>
          <label className={styles.chooseButton}>
            Choose file
            <input
              ref={inputRef}
              type="file"
              accept=".xlsx,.xls,.json"
              className="visually-hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) void handleFile(file);
              }}
            />
          </label>
          <p className={styles.dropHint}>or drop a file here</p>
          {/* Real product value, and true: the file is parsed by this page in
             this browser. There is no upload and no server to upload to. */}
          <p className={styles.privacy}>
            <span className={styles.privacyMark} aria-hidden="true" />
            Your dataset stays in your browser and is not uploaded anywhere.
          </p>
        </section>
      )}

      {stage !== "ready" && (
        <div className={styles.formatRow}>
          <span className={styles.formatLabel}>Need the format?</span>
          <a className={styles.ghostButton}
             href={`${base}templates/draftlens_dataset_template.xlsx`}
             download>
            Download Excel template
          </a>
          <a className={styles.ghostButton}
             href={`${base}templates/draftlens_dataset_template.json`}
             download>
            Download JSON template
          </a>
          <button type="button" className={styles.ghostButton}
                  onClick={() => setShowFormat(true)}>
            View format
          </button>
        </div>
      )}

      {stage === "working" && (
        <p className={styles.working}>Reading {fileName}…</p>
      )}

      {stage === "invalid" && (
        <ValidationReport fileName={fileName} fatal={fatal}
                          validation={validation} onReset={reset} />
      )}

      {stage === "ready" && analysis && validation && (
        <AnalysisWorkspace analysis={analysis} validation={validation}
                           fileName={fileName} onReset={reset} />
      )}

      {showFormat && schema && (
        <FormatReference schema={schema} onClose={() => setShowFormat(false)} />
      )}
    </div>
  );
}

function IssueList({ issues, kind }: { issues: Issue[]; kind: "error" | "warning" }) {
  if (issues.length === 0) return null;
  return (
    <div className={styles.issueBlock} data-kind={kind}>
      <h3 className={styles.issueTitle}>
        {/* Never colour alone: the count and the word carry the meaning. */}
        {kind === "error" ? "Errors" : "Warnings"} ({issues.length})
      </h3>
      <ul className={styles.issueList}>
        {issues.slice(0, 40).map((issue, i) => (
          <li key={i} className={styles.issue}>
            {(issue.row !== null || issue.field) && (
              <span className={styles.issueWhere}>
                {issue.row !== null ? `Row ${issue.row}` : "File"}
                {issue.field ? ` · ${issue.field}` : ""}
              </span>
            )}
            <span className={styles.issueText}>{issue.message}</span>
          </li>
        ))}
        {issues.length > 40 && (
          <li className={styles.issue}>
            <span className={styles.issueText}>
              …and {issues.length - 40} more.
            </span>
          </li>
        )}
      </ul>
    </div>
  );
}

function ValidationReport({
  fileName, fatal, validation, onReset,
}: {
  fileName: string | null;
  fatal: string | null;
  validation: ValidationResult | null;
  onReset: () => void;
}) {
  const summary = useMemo(() => validation && [
    { label: "rows detected", value: String(validation.rowsDetected) },
    { label: "valid prospects", value: String(validation.validProspects) },
    { label: "errors", value: String(validation.errors.length) },
    { label: "warnings", value: String(validation.warnings.length) },
  ], [validation]);

  return (
    <section className={styles.report}>
      <div className={styles.reportHead}>
        <h2 className={styles.reportTitle}>
          {fileName ?? "This file"} was not analysed
        </h2>
        <button type="button" className={styles.ghostButton} onClick={onReset}>
          Choose another file
        </button>
      </div>

      {fatal && <p className={styles.fatal}>{fatal}</p>}

      {summary && (
        <div className={styles.summaryRow}>
          {summary.map((item) => (
            <div key={item.label} className={styles.summaryItem}>
              <span className={styles.summaryValue}>{item.value}</span>
              <span className={styles.summaryLabel}>{item.label}</span>
            </div>
          ))}
        </div>
      )}

      {validation && <IssueList issues={validation.errors} kind="error" />}
      {validation && <IssueList issues={validation.warnings} kind="warning" />}
    </section>
  );
}

export { IssueList };
