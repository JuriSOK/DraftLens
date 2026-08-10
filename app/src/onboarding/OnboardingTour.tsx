import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { markOnboardingCompleted, useOnboarding } from "./OnboardingContext";
import { ONBOARDING_STEPS } from "./steps";
import styles from "./OnboardingTour.module.css";

/** The one onboarding implementation, mounted once at the app root and
 * driven entirely by OnboardingContext — Landing's "Get Started" and
 * Methodology's "Replay Quick Tour" both call the same `start()`, so there
 * is exactly one set of step content and one component. Plain React state +
 * CSS; no tour/animation library. */
export function OnboardingTour() {
  const { isOpen, step, close, setStep } = useOnboarding();
  const navigate = useNavigate();
  const dialogRef = useRef<HTMLDivElement>(null);

  const total = ONBOARDING_STEPS.length;
  const isLast = step === total - 1;
  const current = ONBOARDING_STEPS[step];

  useEffect(() => {
    if (isOpen) dialogRef.current?.focus();
  }, [isOpen, step]);

  useEffect(() => {
    if (!isOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") finishTour();
      if (e.key === "ArrowRight" && !isLast) setStep(step + 1);
      if (e.key === "ArrowLeft" && step > 0) setStep(step - 1);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, step, isLast]);

  if (!isOpen || !current) return null;

  function finishTour() {
    markOnboardingCompleted();
    close();
    navigate("/board");
  }

  return (
    <div className={styles.backdrop} role="presentation">
      <div
        ref={dialogRef}
        className={styles.dialog}
        role="dialog"
        aria-modal="true"
        aria-labelledby="onboarding-title"
        tabIndex={-1}
      >
        <div className={styles.progress}>
          {ONBOARDING_STEPS.map((_, i) => (
            <span
              key={i}
              className={styles.progressDot}
              data-active={i === step}
              data-done={i < step}
            />
          ))}
        </div>

        <h2 id="onboarding-title" className={styles.title}>
          {current.title}
        </h2>
        <div className={styles.body}>{current.body}</div>

        <div className={styles.actions}>
          <button type="button" className={styles.skipButton} onClick={finishTour}>
            Skip tutorial
          </button>
          <div className={styles.navButtons}>
            <button
              type="button"
              className={styles.secondaryButton}
              onClick={() => setStep(step - 1)}
              disabled={step === 0}
            >
              Back
            </button>
            {isLast ? (
              <button type="button" className={styles.primaryButton} onClick={finishTour}>
                Explore DraftLens
              </button>
            ) : (
              <button
                type="button"
                className={styles.primaryButton}
                onClick={() => setStep(step + 1)}
              >
                Next
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
