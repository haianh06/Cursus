/**
 * EduSync's brand mark -- an open, geometric "E" (three bars off a spine,
 * round caps) with a small accent dot in the open notch, the same visual
 * family as Cursus's own "C" monogram (frontend/src/components/landing/
 * LandingLogoMark.jsx: an open geometric letterform + one signal dot,
 * stroke-only, no background chip). Deliberately not a stock lucide icon
 * boxed in a colored square -- that read as a generic placeholder rather
 * than a mark this product actually owns.
 */
export function EduSyncMark({ size = 26 }: { size?: number }) {
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
        d="M9 6H23M9 6V26M9 6V6M9 16H19.5M9 26H23"
        stroke="var(--accent)"
        strokeWidth="4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="26.5" cy="16" r="2.5" fill="var(--accent-hover)" />
    </svg>
  );
}
