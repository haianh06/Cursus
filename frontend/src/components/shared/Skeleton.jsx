import React from 'react';

/**
 * Skeleton — a placeholder block shaped like the real content it stands
 * in for (per docs/frontend/03: "card skeleton = card-shaped block, not a
 * generic spinner"). Use for section/page loads; use a spinner only for
 * short inline waits (button submit, etc.).
 */
export default function Skeleton({ className = '', style, 'aria-label': ariaLabel }) {
  return (
    <div
      className={`skeleton ${className}`}
      style={style}
      role="status"
      aria-label={ariaLabel || 'Đang tải'}
    />
  );
}

/** A row of skeleton blocks shaped like a list of cards/rows. */
export function SkeletonRows({ count = 3, rowClassName = 'h-14 rounded-xl' }) {
  return (
    <div className="flex flex-col gap-2.5" role="status" aria-label="Đang tải danh sách">
      {Array.from({ length: count }).map((_, i) => (
        <Skeleton key={i} className={`w-full ${rowClassName}`} />
      ))}
    </div>
  );
}
