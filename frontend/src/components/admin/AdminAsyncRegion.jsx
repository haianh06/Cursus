import React from 'react';
import { AlertCircle, Loader2, ShieldAlert, Clock } from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';

/**
 * One place that decides what an Admin screen shows while it is not showing data.
 *
 * Every cockpit region has the same four failure shapes, and three of them are
 * security states rather than errors: a sensitive session that expired, one that
 * was never granted, and a refusal from the server. Rendering them identically to
 * a network error would teach the operator to retry when they should re-authorise.
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

    let Icon = AlertCircle;
    let messageKey = 'admin.regionError';
    if (sensitive) {
      Icon = ShieldAlert;
      messageKey = 'admin.regionForbidden';
    } else if (unavailable) {
      Icon = Clock;
      messageKey = 'admin.regionUnavailable';
    }

    return (
      <div
        role="alert"
        className={`flex flex-col gap-2 rounded-lg border p-4 text-xs ${
          sensitive
            ? 'border-warning/40 bg-warning-soft text-warning'
            : 'border-danger/40 bg-danger-soft text-danger'
        }`}
      >
        <p className="flex items-center gap-2 font-semibold">
          <Icon size={14} aria-hidden="true" />
          {t(messageKey)}
        </p>
        {error.message && <p className="text-fg-secondary">{error.message}</p>}
        {onRetry && !sensitive && (
          <button
            type="button"
            onClick={onRetry}
            className="w-fit min-h-11 rounded-lg border border-line px-3 font-semibold text-fg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
          >
            {t('admin.retry')}
          </button>
        )}
      </div>
    );
  }

  if (empty) {
    return (
      <p className="rounded-lg border border-dashed border-line p-4 text-xs text-fg-secondary">
        {emptyMessage || t('admin.regionEmpty')}
      </p>
    );
  }

  return children;
}
