import { useEffect, useId, useRef, useState } from "react";
import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import styles from "./MetricTooltip.module.css";

/** The ONE contextual-help affordance used across the product.
 *
 * Works with all three input modes, which a hover-only tooltip does not:
 *   mouse    — opens on hover
 *   keyboard — the trigger is a real <button>, opens on focus, Escape closes
 *   touch    — click/tap toggles it open and closed
 *
 * No tooltip library; plain React state and CSS. */
export function MetricTooltip({
  text,
  learnMoreHref,
  label = "More information",
}: {
  text: string;
  learnMoreHref?: string;
  label?: string;
}) {
  const [open, setOpen] = useState(false);
  const [pinned, setPinned] = useState(false);
  const id = useId();
  const wrapRef = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (!pinned) return;
    const onDocClick = (e: MouseEvent) => {
      if (!wrapRef.current?.contains(e.target as Node)) {
        setPinned(false);
        setOpen(false);
      }
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setPinned(false);
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onDocClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDocClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [pinned]);

  return (
    <span className={styles.wrap} ref={wrapRef}>
      <button
        type="button"
        className={styles.trigger}
        aria-describedby={open ? id : undefined}
        aria-expanded={open}
        aria-label={label}
        onClick={() => {
          const next = !pinned;
          setPinned(next);
          setOpen(next);
        }}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => !pinned && setOpen(false)}
        onFocus={() => setOpen(true)}
        onBlur={() => !pinned && setOpen(false)}
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
