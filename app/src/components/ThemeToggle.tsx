import { useTheme } from "../theme/ThemeContext";
import styles from "./ThemeToggle.module.css";

/** A compact sun/moon switch. The accessible name states what pressing it
 * will do, and `aria-pressed` carries the current state, so the control is
 * usable without seeing which icon is lit. */
export function ThemeToggle() {
  const { theme, toggle } = useTheme();
  const dark = theme === "dark";
  return (
    <button
      type="button"
      className={styles.toggle}
      onClick={toggle}
      aria-pressed={dark}
      aria-label={dark ? "Switch to light mode" : "Switch to night mode"}
      title={dark ? "Switch to light mode" : "Switch to night mode"}
    >
      <span className={styles.icon} aria-hidden="true">
        {dark ? (
          <svg viewBox="0 0 20 20" width="15" height="15">
            <path
              d="M16.3 11.9A6.6 6.6 0 0 1 8.1 3.7a6.8 6.8 0 1 0 8.2 8.2Z"
              fill="currentColor"
            />
          </svg>
        ) : (
          <svg viewBox="0 0 20 20" width="15" height="15">
            <circle cx="10" cy="10" r="3.6" fill="currentColor" />
            <g stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
              <path d="M10 1.8v2M10 16.2v2M1.8 10h2M16.2 10h2" />
              <path d="M4.2 4.2 5.6 5.6M14.4 14.4l1.4 1.4M15.8 4.2 14.4 5.6M5.6 14.4 4.2 15.8" />
            </g>
          </svg>
        )}
      </span>
    </button>
  );
}
