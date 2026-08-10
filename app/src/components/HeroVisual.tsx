import styles from "./HeroVisual.module.css";

/** The landing hero visual — an ORIGINAL, hand-authored SVG.
 *
 * Deliberately not a photograph: shipping a real player image would mean
 * shipping someone else's copyright, and no verified reusable basketball
 * hero asset exists in this repo. This is drawn from primitives (circle,
 * arcs, a plotting grid, a trend line), so it carries no licensing risk at
 * all while still reading as "basketball + analytics".
 *
 * Purely decorative: it encodes no data and is hidden from assistive tech. */
export function HeroVisual() {
  return (
    <svg
      className={styles.visual}
      viewBox="0 0 520 520"
      role="presentation"
      aria-hidden="true"
      focusable="false"
    >
      <defs>
        <radialGradient id="dl-glow" cx="50%" cy="45%" r="55%">
          <stop offset="0%" stopColor="#ff7a33" stopOpacity="0.55" />
          <stop offset="55%" stopColor="#c4531d" stopOpacity="0.18" />
          <stop offset="100%" stopColor="#c4531d" stopOpacity="0" />
        </radialGradient>
        <linearGradient id="dl-ball" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#ff8c4a" />
          <stop offset="100%" stopColor="#b8420f" />
        </linearGradient>
        <linearGradient id="dl-trend" x1="0%" y1="100%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#ff8c4a" stopOpacity="0.25" />
          <stop offset="100%" stopColor="#ffb27d" stopOpacity="1" />
        </linearGradient>
        <pattern id="dl-grid" width="26" height="26" patternUnits="userSpaceOnUse">
          <path
            d="M26 0H0V26"
            fill="none"
            stroke="#ffffff"
            strokeOpacity="0.05"
            strokeWidth="1"
          />
        </pattern>
      </defs>

      {/* plotting grid + ambient glow */}
      <rect width="520" height="520" fill="url(#dl-grid)" />
      <circle cx="260" cy="240" r="240" fill="url(#dl-glow)" />

      {/* concentric radar rings — the "scouting sweep" motif */}
      {[210, 165, 120].map((r, i) => (
        <circle
          key={r}
          cx="260"
          cy="240"
          r={r}
          fill="none"
          stroke="#ff8c4a"
          strokeOpacity={0.1 + i * 0.04}
          strokeWidth="1"
          strokeDasharray={i === 1 ? "3 7" : undefined}
        />
      ))}

      {/* the basketball: circle + the four classic seams */}
      <g className={styles.ball}>
        <circle
          cx="260"
          cy="240"
          r="132"
          fill="none"
          stroke="url(#dl-ball)"
          strokeWidth="2.5"
          strokeOpacity="0.85"
        />
        <line
          x1="260" y1="108" x2="260" y2="372"
          stroke="url(#dl-ball)" strokeWidth="2" strokeOpacity="0.6"
        />
        <line
          x1="128" y1="240" x2="392" y2="240"
          stroke="url(#dl-ball)" strokeWidth="2" strokeOpacity="0.6"
        />
        <path
          d="M158 148c46 52 46 132 0 184"
          fill="none" stroke="url(#dl-ball)" strokeWidth="2" strokeOpacity="0.6"
        />
        <path
          d="M362 148c-46 52-46 132 0 184"
          fill="none" stroke="url(#dl-ball)" strokeWidth="2" strokeOpacity="0.6"
        />
      </g>

      {/* halftone dot field — editorial sports print texture */}
      <g fill="#ff8c4a">
        {Array.from({ length: 7 }).map((_, row) =>
          Array.from({ length: 7 }).map((__, col) => {
            const cx = 316 + col * 17;
            const cy = 300 + row * 17;
            const r = 2.6 - row * 0.28;
            return (
              <circle
                key={`${row}-${col}`}
                cx={cx}
                cy={cy}
                r={r > 0.4 ? r : 0.4}
                opacity={0.32 - row * 0.035}
              />
            );
          }),
        )}
      </g>

      {/* trend line — the "signal" motif, rising left to right */}
      <path
        d="M60 402 L112 386 L164 396 L216 350 L268 362 L320 300 L372 312 L424 246 L470 214"
        fill="none"
        stroke="url(#dl-trend)"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {[
        [112, 386], [216, 350], [320, 300], [424, 246], [470, 214],
      ].map(([cx, cy]) => (
        <circle key={`${cx}`} cx={cx} cy={cy} r="3.2" fill="#ffb27d" />
      ))}

      {/* baseline axis */}
      <line
        x1="52" y1="440" x2="480" y2="440"
        stroke="#ffffff" strokeOpacity="0.12" strokeWidth="1"
      />
      {[52, 159, 266, 373, 480].map((x) => (
        <line
          key={x}
          x1={x} y1="440" x2={x} y2="446"
          stroke="#ffffff" strokeOpacity="0.12" strokeWidth="1"
        />
      ))}
    </svg>
  );
}

/** A compact decorative sparkline used inside the hero stat strip. */
export function Sparkline() {
  return (
    <svg
      className={styles.spark}
      viewBox="0 0 96 28"
      role="presentation"
      aria-hidden="true"
      focusable="false"
    >
      <path
        d="M2 24 L14 20 L26 22 L38 14 L50 16 L62 9 L74 11 L94 3"
        fill="none"
        stroke="#ff8c4a"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="94" cy="3" r="2.4" fill="#ffb27d" />
    </svg>
  );
}
