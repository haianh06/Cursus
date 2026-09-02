import React from 'react';
import { Loader2 } from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import EmptyState from '../shared/EmptyState';
import ErrorState from '../shared/ErrorState';

/**
 * One place that decides what an Admin screen shows while it is not showing
 * data — same shared EmptyState/ErrorState shell every Student screen uses
 * (see docs/frontend/03), so an Admin cockpit region and a Student page look
 * like the same product instead of two.
 *
 * Every cockpit region has the same four failure shapes, and two of them are
 * security states rather than errors: a sensitive session that expired or
 * was never granted, and a refusal from the server. Rendering them
 * identically to a network error would teach the operator to retry when
 * they should re-authorise instead — that distinction is kept via
 * ErrorState's `severity` (warning = re-authorise, error = safe to retry)
 * and by only offering the retry button when it isn't a permissions wall.
 */
export default function AdminAsyncRegion({
  loading,
  error,
  empty,
  emptyMessage,
  children,
  onRetry,
  label,
}) {
  const { t } = useLanguage();

  if (loading) {
    return (
      <div
        role="status"
        aria-live="polite"
        aria-label={label || t('admin.loading')}
        className="flex items-center gap-2 rounded-lg border border-line bg-surface p-4 text-xs text-fg-secondary"
      >
        <Loader2 size={14} className="animate-spin text-accent" aria-hidden="true" />
        {t('admin.loading')}
      </div>
    );
  }

  if (error) {
    const status = error.status ?? 0;
    const code = error.code || '';
    const sensitive =
      code === 'SENSITIVE_ACCESS_DENIED' ||
      code === 'SENSITIVE_SESSION_EXPIRED' ||
      status === 403;
    const unavailable = code === 'SENSITIVE_AUDIT_UNAVAILABLE' || status === 503;

    const messageKey = sensitive
      ? 'admin.regionForbidden'
      : unavailable
        ? 'admin.regionUnavailable'
        : 'admin.regionError';

    return (
      <ErrorState
        title={t(messageKey)}
        description={error.message}
        severity={sensitive ? 'warning' : 'error'}
        onRetry={sensitive ? undefined : onRetry}
        retryLabel={t('admin.retry')}
      />
    );
  }

  if (empty) {
    return <EmptyState title={emptyMessage || t('admin.regionEmpty')} />;
  }

  return children;
}
