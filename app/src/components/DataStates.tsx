import styles from "./DataStates.module.css";

export function LoadingState() {
  return (
    <div className={`container ${styles.state}`} role="status">
      Loading the 2026 board…
    </div>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className={`container ${styles.state}`} role="alert">
      <p className={styles.title}>Couldn't load DraftLens data.</p>
      <p className={styles.detail}>{message}</p>
      <p className={styles.detail}>
        Run <code>python scripts/build.py app-data</code> to (re)generate{" "}
        <code>app/public/data/draftlens_2026.json</code>.
      </p>
    </div>
  );
}
