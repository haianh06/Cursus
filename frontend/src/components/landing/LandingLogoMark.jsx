import React, { useEffect, useRef, useState } from 'react';
import { useTheme } from '../../context/ThemeContext';

/**
 * Solid "C" disc with a wedge cut out (not a thin stroked ring) — a filled
 * shape reads as a lettermark/monogram, never as a loading spinner, which
 * is what a thin open arc (even a single continuous one, even without
 * looping animation) kept getting mistaken for. Same verified outer curve
 * as before, just closed back to center and filled instead of stroked, so
 * it renders as one bold, static geometric "C" at every size.
 *
 * A static sky-blue point sits in the open notch — Cursus Assistant's signal, not a
 * progress indicator. It never moves on its own; only a 2px nudge on
 * hover/focus (see .landing-logo-dot in index.css), which is inert under
 * prefers-reduced-motion. It also blips once (scale+opacity, see
 * .landing-logo-dot--pulse) whenever the theme flips — driven by the same
 * `theme` value ThemeToggle's sun/moon crossfade reacts to, so both start
 * on the same render and never drift out of sync. Skipped on mount and on
 * hover; fires exactly once per toggle, never loops.
 *
 * This is the ONE mark used everywhere in the app (landing, auth screens,
 * error screens) — not just marketing. The two color classes default to
 * the landing page's `--landing-*` token names, but every screen outside
 * `.landing-page-scope` runs on the app's `--fg`/`--accent` token set
 * instead, so callers there must pass `strokeClassName`/`dotClassName`
 * pointing at those tokens or the mark renders in whatever `currentColor`
 * falls back to.
 */
export default function LandingLogoMark({ size = 28, strokeClassName = 'text-landing-text', dotClassName = 'fill-landing-accent' }) {
  const { theme } = useTheme();
  const hasMounted = useRef(false);
  const [isPulsing, setIsPulsing] = useState(false);

  useEffect(() => {
    if (!hasMounted.current) {
      hasMounted.current = true;
      return;
    }
    setIsPulsing(true);
  }, [theme]);

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className="shrink-0"
      aria-hidden="true"
    >
      <path
        d="M16 28C9.37258 28 4 22.6274 4 16C4 9.37258 9.37258 4 16 4C20.6094 4 24.6136 6.59858 26.6577 10.5"
        stroke="currentColor"
        strokeWidth="4"
        strokeLinecap="round"
        className={strokeClassName}
      />
      <circle
        cx="26"
        cy="18"
        r="2.5"
        className={`${dotClassName} landing-logo-dot transition-transform duration-[var(--motion-fast)] ${isPulsing ? 'landing-logo-dot--pulse' : ''}`}
        onAnimationEnd={() => setIsPulsing(false)}
      />
    </svg>
  );
}
