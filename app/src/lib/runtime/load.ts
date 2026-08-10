/** Fetching the frozen runtime, on demand.
 *
 * The bundle is large and only the Dataset Lab needs it, so nothing is
 * fetched until someone actually imports a file — the built-in product never
 * pays for it. Season references are fetched one season at a time for the
 * same reason, and cached for the session.
 *
 * These are static assets from the same origin as the app. No dataset is
 * ever sent anywhere; traffic goes one way. */

import type { RuntimeCore, RuntimeSeason } from "./types";

const BASE = `${import.meta.env.BASE_URL}data/runtime/`;

let corePromise: Promise<RuntimeCore> | null = null;
const seasonPromises = new Map<number, Promise<RuntimeSeason>>();

async function fetchJson<T>(url: string, label: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Could not load ${label} (HTTP ${response.status}). The `
      + "analysis runtime is part of the deployed site; try reloading.");
  }
  return (await response.json()) as T;
}

export function loadCore(): Promise<RuntimeCore> {
  if (!corePromise) {
    corePromise = fetchJson<RuntimeCore>(`${BASE}core.json`,
                                         "the DraftLens analysis runtime")
      .catch((error) => {
        corePromise = null;
        throw error;
      });
  }
  return corePromise;
}

export function loadSeason(season: number): Promise<RuntimeSeason> {
  const cached = seasonPromises.get(season);
  if (cached) return cached;
  const promise = fetchJson<RuntimeSeason>(
    `${BASE}season-${season}.json`, `the ${season} NCAA peer reference`)
    .catch((error) => {
      seasonPromises.delete(season);
      throw error;
    });
  seasonPromises.set(season, promise);
  return promise;
}
