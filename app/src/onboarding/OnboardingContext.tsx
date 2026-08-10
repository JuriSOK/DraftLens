import { createContext, useContext, useState } from "react";
import type { ReactNode } from "react";

export const ONBOARDING_STORAGE_KEY = "draftlens_onboarding_completed";

interface OnboardingState {
  isOpen: boolean;
  step: number;
  start: () => void;
  close: () => void;
  setStep: (step: number) => void;
}

const OnboardingContext = createContext<OnboardingState | null>(null);

/** UI state only — which tour step is showing. No account, no backend, no
 * analytics, and nothing here ever feeds an analytical result: the tour is
 * pure product education layered on top of already-computed data.
 * `hasCompletedOnboarding`/`markOnboardingCompleted` below are the only
 * things that touch localStorage, and only as a UI preference flag. */
export function OnboardingProvider({ children }: { children: ReactNode }) {
  const [isOpen, setIsOpen] = useState(false);
  const [step, setStep] = useState(0);

  const start = () => {
    setStep(0);
    setIsOpen(true);
  };
  const close = () => setIsOpen(false);

  return (
    <OnboardingContext.Provider value={{ isOpen, step, start, close, setStep }}>
      {children}
    </OnboardingContext.Provider>
  );
}

export function useOnboarding() {
  const ctx = useContext(OnboardingContext);
  if (!ctx) throw new Error("useOnboarding must be used within OnboardingProvider");
  return ctx;
}

export function hasCompletedOnboarding(): boolean {
  try {
    return window.localStorage.getItem(ONBOARDING_STORAGE_KEY) === "true";
  } catch {
    return false;
  }
}

export function markOnboardingCompleted() {
  try {
    window.localStorage.setItem(ONBOARDING_STORAGE_KEY, "true");
  } catch {
    // localStorage unavailable (private mode, etc.) — non-fatal, UI-only state
  }
}
