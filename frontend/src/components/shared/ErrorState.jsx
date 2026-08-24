import React, { useState } from 'react';
import { RotateCcw } from 'lucide-react';
import CursusMascot from './CursusMascot';

/**
 * ErrorState — shared empty-state shell for in-page data-load failures.
 *
 * Uses CursusMascot in `error` (red) or `warning` (amber) state for brand
 * consistency. Never shows a raw error code as primary content.
 * Retry button shows a spinner while the retry is in-flight.
 *
 * Per docs/frontend/03 — same shell as EmptyState, danger accent.
 */
export default function ErrorState({
  title,
  description,
  onRetry,
  retryLabel = 'Thử lại',
  /** 'error' | 'warning' — controls mascot expression and accent color */
  severity = 'error',
  /** Raw Error object — revealed in a collapsed detail block */
  error,
}) {
  const [retrying, setRetrying] = useState(false);

  const handleRetry = async () => {
    if (!onRetry || retrying) return;
    setRetrying(true);
    try {
      await onRetry();
    } finally {
      setRetrying(false);
    }
  };

  return (
    <div
      className="error-state animate-fade-up"
      role="alert"
      aria-labelledby="error-state-heading"
    >
      {/* Mascot — small, contextual expression */}
      <div className="error-state__mascot" aria-hidden="true">
        <CursusMascot size={72} state={severity === 'warning' ? 'warning' : 'error'} />
      </div>

      <div className="error-state__body">
        <h3 id="error-state-heading" className="error-state__heading">
          {title}
        </h3>
        {description && (
          <p className="error-state__desc">{description}</p>
        )}
      </div>

      {onRetry && (
        <button
          type="button"
          onClick={handleRetry}
          disabled={retrying}
          aria-busy={retrying}
          className="btn btn-outline text-xs px-4 py-2 mt-1 cursor-pointer flex items-center gap-1.5"
        >
          <RotateCcw
            size={13}
            className={retrying ? 'spin' : ''}
            aria-hidden="true"
          />
          {retrying ? 'Đang thử lại…' : retryLabel}
        </button>
      )}

      {/* Collapsed technical detail — power-user escape hatch */}
      {error && <ErrorDetailDisclosure error={error} />}
    </div>
  );
}

function ErrorDetailDisclosure({ error }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="error-state__detail">
      <button
        type="button"
        className="error-state__detail-toggle"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        {open ? '▾' : '▸'} Chi tiết kỹ thuật
      </button>
      {open && (
        <pre className="error-state__detail-body animate-fade-up">
          {error?.message ?? String(error)}
        </pre>
      )}
    </div>
  );
}
