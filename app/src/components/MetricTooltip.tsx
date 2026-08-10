import { useId, useState } from "react";
import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import styles from "./MetricTooltip.module.css";

/** A small "?" affordance that reveals an explanatory note on hover/focus.
 * Keyboard-accessible: the trigger is a real button, the note is linked via
 * aria-describedby and toggled on focus as well as hover. An optional
 * `learnMoreHref` adds a link into the corresponding Methodology section —
 * used sparingly, not on every tooltip. */
export function MetricTooltip({
  text,
  learnMoreHref,
}: {
  text: string;
  learnMoreHref?: string;
}) {
  const [open, setOpen] = useState(false);
  const id = useId();

  return (
    <span className={styles.wrap}>
      <button
        type="button"
        className={styles.trigger}
        aria-describedby={id}
        aria-label="More information"
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
      >
        ?
      </button>
      <span role="tooltip" id={id} className={styles.bubble} data-open={open}>
        {text}
        {learnMoreHref && (
          <>
            {" "}
            <Link to={learnMoreHref} className={styles.learnMore}>
              Learn more →
            </Link>
          </>
        )}
      </span>
    </span>
  );
}

export function InlineNote({ children }: { children: ReactNode }) {
  return <p className={styles.note}>{children}</p>;
}
