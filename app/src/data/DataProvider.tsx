import { createContext, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";
import type { DraftLensData } from "../types/data";

interface DataState {
  data: DraftLensData | null;
  error: string | null;
  loading: boolean;
}

const DataContext = createContext<DataState>({
  data: null,
  error: null,
  loading: true,
});

/** Minimal runtime shape check — not a full schema validator, just enough to
 * fail loudly if the export is missing the fields the UI depends on, rather
 * than rendering `undefined` everywhere. */
function looksLikeDraftLensData(value: unknown): value is DraftLensData {
  if (typeof value !== "object" || value === null) return false;
  const v = value as Record<string, unknown>;
  return (
    typeof v.version === "string" &&
    typeof v.years === "object" &&
    v.years !== null &&
    Array.isArray(v.teamNeedProfiles) &&
    Array.isArray(v.customDimensions)
  );
}

export function DataProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<DataState>({
    data: null,
    error: null,
    loading: true,
  });

  useEffect(() => {
    let cancelled = false;
    fetch(`${import.meta.env.BASE_URL}data/draftlens_2026.json`)
      .then((res) => {
        if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
        return res.json();
      })
      .then((json: unknown) => {
        if (cancelled) return;
        if (!looksLikeDraftLensData(json)) {
          throw new Error("draftlens_2026.json does not match the expected shape");
        }
        setState({ data: json, error: null, loading: false });
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        const message = err instanceof Error ? err.message : String(err);
        setState({ data: null, error: message, loading: false });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return <DataContext.Provider value={state}>{children}</DataContext.Provider>;
}

export function useDraftLensData(): DataState {
  return useContext(DataContext);
}
