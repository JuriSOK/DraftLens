import { useState } from "react";
import type { ProspectPhotoMeta } from "../types/data";
import styles from "./ProspectPhoto.module.css";

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

/** Prospect portrait with a guaranteed non-broken fallback.
 *
 * A photo renders only when the export supplied verified metadata — a
 * thumbnail, an attribution and a licence. Anything else (no free image, an
 * ambiguous identity, a rejected licence) falls through to initials. If the
 * image itself fails to load at runtime, `failed` swaps in the same
 * fallback, so a broken-image icon is never shown. */
export function ProspectPhoto({
  name,
  photo,
}: {
  name: string;
  photo: ProspectPhotoMeta | null;
}) {
  const [failed, setFailed] = useState(false);
  const showPhoto = photo !== null && photo !== undefined && !failed;

  return (
    <div className={styles.wrap}>
      <div className={styles.frame}>
        {showPhoto ? (
          <img
            className={styles.img}
            src={photo.thumbnailUrl}
            alt={`${name}`}
            loading="lazy"
            onError={() => setFailed(true)}
          />
        ) : (
          <span className={styles.initials} aria-hidden="true">
            {initials(name)}
          </span>
        )}
      </div>
      {showPhoto && (
        <details className={styles.credit}>
          <summary className={styles.creditSummary}>Photo info</summary>
          <div className={styles.creditBody}>
            <span>{photo.attribution}</span>
            <span>
              {photo.licenseUrl ? (
                <a href={photo.licenseUrl} target="_blank" rel="noreferrer">
                  {photo.license}
                </a>
              ) : (
                photo.license
              )}
            </span>
            {photo.sourceUrl && (
              <a href={photo.sourceUrl} target="_blank" rel="noreferrer">
                Wikimedia Commons
              </a>
            )}
          </div>
        </details>
      )}
    </div>
  );
}
