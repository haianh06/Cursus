import React, { useCallback, useEffect, useState } from 'react';
import { AlertCircle, ChevronDown, ChevronRight, History, Search } from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import { getAuditEvents } from '../../lib/api';

function formatTimestamp(iso, lang) {
  try {
    return new Date(iso).toLocaleString(lang === 'vi' ? 'vi-VN' : 'en-US');
  } catch {
    return iso;
  }
}

/** Best-effort list of real `event_type` values this codebase actually
 * writes (grepped from `audit_service.log_event(event_type=...)` call
 * sites), offered as browser-native autocomplete suggestions -- not a
 * hard allowlist, the filter still accepts free text since this list
 * will drift as new event types are added. */
const KNOWN_EVENT_TYPES = [
  'LOGIN_SUCCESS', 'LOGIN_FAILED', 'LOGOUT', 'REGISTER_SUCCESS',
  'EMAIL_CHANGED', 'EMAIL_VERIFICATION_SUCCESS', 'EMAIL_VERIFICATION_FAILED',
  'EMAIL_VERIFICATION_RESEND_REQUESTED',
  'PASSWORD_CHANGE_SUCCESS', 'PASSWORD_CHANGE_FAILED',
  'PASSWORD_RESET_REQUESTED', 'PASSWORD_RESET_SUCCESS', 'PASSWORD_RESET_FAILED',
  'MFA_CHALLENGE_REQUIRED', 'MFA_TOTP_SETUP_STARTED', 'MFA_TOTP_ENABLED', 'MFA_TOTP_ENABLE_FAILED',
  'MFA_LOGIN_FAILED', 'MFA_DISABLED', 'MFA_DISABLE_FAILED',
  'MFA_RECOVERY_CODES_REGENERATED', 'MFA_RECOVERY_CODES_REGENERATE_FAILED',
  'DEMO_SESSION_STARTED', 'TASK_COMPLETED',
  'admin_course_added', 'admin_course_hidden', 'admin_course_restored', 'admin_settings_updated',
  'guardrail_rule_updated', 'risk_policy_published', 'risk_policy_rolled_back',
  'mock_lms_sync_published', 'mock_lms_sync_rolled_back',
];

/** mục 6.5 Admin Console: read-only viewer for the already-existing
 * GET /api/v1/audit/events (src/api/audit.py). Organization-scoped
 * server-side as of 22/08 (docs/PENDING_DECISIONS.md #2, resolved) -- this
 * tab shows exactly what that endpoint returns, nothing added or hidden;
 * no client-side org filtering needed here. */
export default function AdminAudit() {
  const { t, lang } = useLanguage();
  const [events, setEvents] = useState(null);
  const [error, setError] = useState('');
  const [eventTypeFilter, setEventTypeFilter] = useState('');
  const [appliedFilter, setAppliedFilter] = useState('');
  const [expandedId, setExpandedId] = useState(null);

  const load = useCallback((eventType) => {
    setError('');
    return getAuditEvents({ eventType: eventType || null })
      .then(setEvents)
      .catch((err) => setError(err.message || String(err)));
  }, []);

  useEffect(() => {
    load(appliedFilter);
  }, [load, appliedFilter]);

  function submitFilter(event) {
    event.preventDefault();
    setAppliedFilter(eventTypeFilter.trim());
  }

  return (
    <section className="card p-5 sm:p-6 space-y-4 text-left" aria-labelledby="audit-title">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 id="audit-title" className="text-sm font-bold text-fg flex items-center gap-2">
          <History size={16} className="text-accent" /> {t('admin.auditTitle')}
        </h2>
        <form onSubmit={submitFilter} className="flex items-center gap-2">
          <label htmlFor="audit-event-type-filter" className="sr-only">
            {t('admin.auditFilterLabel')}
          </label>
          <input
            id="audit-event-type-filter"
            type="text"
            list="audit-event-type-options"
            className="input text-xs h-9 w-48"
            placeholder={t('admin.auditFilterPlaceholder')}
            value={eventTypeFilter}
            onChange={(event) => setEventTypeFilter(event.target.value)}
          />
          <datalist id="audit-event-type-options">
            {KNOWN_EVENT_TYPES.map((value) => (
              <option key={value} value={value} />
            ))}
          </datalist>
          <button type="submit" className="btn btn-outline text-xs px-3 h-9 cursor-pointer">
            <Search size={13} /> {t('admin.auditFilterApply')}
          </button>
        </form>
      </div>

      {appliedFilter && (
        <p className="text-[11px] text-fg-muted">
          {t('admin.auditFilteredBy')} <span className="mono font-bold text-fg">{appliedFilter}</span>
          {' · '}
          <button type="button" className="underline cursor-pointer" onClick={() => { setEventTypeFilter(''); setAppliedFilter(''); }}>
            {t('admin.auditClearFilter')}
          </button>
        </p>
      )}

      {error && (
        <p className="flex items-center gap-2 text-xs text-danger" role="alert">
          <AlertCircle size={14} className="shrink-0" />{error}
        </p>
      )}

      {events === null ? (
        <p className="text-xs text-fg-muted">{t('admin.loading')}</p>
      ) : events.length === 0 ? (
        <p className="text-xs text-fg-muted">{t('admin.auditEmpty')}</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="data-table">
            <thead>
              <tr>
                <th scope="col" />
                <th scope="col">{t('admin.auditColTime')}</th>
                <th scope="col">{t('admin.auditColEvent')}</th>
                <th scope="col">{t('admin.auditColActor')}</th>
                <th scope="col">{t('admin.auditColResource')}</th>
                <th scope="col">{t('admin.auditColDecision')}</th>
              </tr>
            </thead>
            <tbody>
              {events.map((event) => {
                const isOpen = expandedId === event.id;
                return (
                  <React.Fragment key={event.id}>
                    <tr>
                      <td>
                        <button
                          type="button"
                          className="min-w-[24px] min-h-[24px] inline-flex items-center justify-center text-fg-muted hover:text-fg cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-accent rounded"
                          aria-expanded={isOpen}
                          aria-controls={`audit-row-detail-${event.id}`}
                          aria-label={t('admin.auditToggleDetails')}
                          onClick={() => setExpandedId(isOpen ? null : event.id)}
                        >
                          {isOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                        </button>
                      </td>
                      <td className="text-fg-muted whitespace-nowrap">{formatTimestamp(event.created_at, lang)}</td>
                      <td className="mono text-fg font-semibold">{event.event_type}</td>
                      <td className="text-fg-secondary">{event.actor_user_id || '—'}</td>
                      <td className="text-fg-secondary">
                        {event.resource_type ? `${event.resource_type}${event.resource_id ? ` · ${event.resource_id}` : ''}` : '—'}
                      </td>
                      <td>
                        <span className={`badge text-[9px] font-bold ${event.decision === 'ALLOW' ? 'badge-success' : 'badge-danger'}`}>
                          {event.decision}
                        </span>
                      </td>
                    </tr>
                    {isOpen && (
                      <tr id={`audit-row-detail-${event.id}`} style={{ background: 'var(--bg-elevated)' }}>
                        <td />
                        <td colSpan={5}>
                          <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-[11px]">
                            <dt className="text-fg-muted">{t('admin.auditColIp')}</dt>
                            <dd className="text-fg-secondary mono">{event.ip_address || '—'}</dd>
                            <dt className="text-fg-muted">{t('admin.auditColUserAgent')}</dt>
                            <dd className="text-fg-secondary truncate">{event.user_agent || '—'}</dd>
                          </dl>
                          {Object.keys(event.metadata || {}).length > 0 && (
                            <pre className="mt-2 text-[10px] mono bg-surface-elevated rounded-lg p-3 overflow-x-auto text-fg-secondary">
                              {JSON.stringify(event.metadata, null, 2)}
                            </pre>
                          )}
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
