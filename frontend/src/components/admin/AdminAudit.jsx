import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { AlertCircle, CheckCircle2, ChevronRight, FileClock, History, KeyRound, Search, Settings2, ShieldAlert, ShieldCheck, XCircle } from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import { getAuditEvents } from '../../lib/api';

// A demo/test org that gets clicked through repeatedly generates a LOGIN_
// SUCCESS/LOGOUT/DEMO_SESSION_STARTED for every single visit -- on a young
// org this routine session noise can outnumber every real admin action
// 10-to-1, which is exactly what buries the log an Admin actually needs to
// scan (found via a live screenshot: 9 of the newest 10 rows were session
// churn). Categorizing by pattern (not an exhaustive map -- new event types
// keep landing, same reasoning as KNOWN_EVENT_TYPES below) lets the UI mute
// the routine category by default instead of hiding it outright.
function categorizeEvent(eventType) {
  if (/^(LOGIN_|LOGOUT|REGISTER_|EMAIL_|PASSWORD_|MFA_|DEMO_SESSION)/.test(eventType)) {
    return 'auth';
  }
  if (/^admin_|^guardrail_rule_updated$|^risk_policy_|^mock_lms_sync_|^UPDATE_USER_STATUS$/.test(eventType)) {
    return 'admin';
  }
  return 'oversight';
}

const CATEGORY_ICON = { auth: KeyRound, admin: Settings2, oversight: ShieldCheck };

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
  const [selectedId, setSelectedId] = useState(null);
  const [category, setCategory] = useState('all');

  const load = useCallback((eventType) => {
    setError('');
    // 100 (the old default) is exactly the size of a burst of routine
    // session churn -- on a demo/test org a handful of minutes of
    // logging in and out can push every real admin action outside the
    // window entirely (found while adding the category filter below: an
    // admin_settings_updated from days ago wasn't just visually buried,
    // it plain wasn't in the response). 500 is the server's own cap
    // (src/api/audit.py).
    return getAuditEvents({ eventType: eventType || null, limit: 500 })
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

  const categoryCounts = useMemo(() => {
    const counts = { auth: 0, admin: 0, oversight: 0 };
    for (const event of events || []) counts[categorizeEvent(event.event_type)] += 1;
    return counts;
  }, [events]);
  const visibleEvents = useMemo(
    () => (category === 'all' ? events : (events || []).filter((event) => categorizeEvent(event.event_type) === category)),
    [events, category],
  );

  const selectedEvent = visibleEvents?.find((event) => event.id === selectedId) || visibleEvents?.[0] || null;
  const allowedCount = events?.filter((event) => event.decision === 'ALLOW').length || 0;
  const deniedCount = events?.filter((event) => event.decision !== 'ALLOW').length || 0;
  const warningCount = events?.filter((event) => /FAILED|ROLLBACK|LOCK/i.test(event.event_type)).length || 0;

  const CATEGORY_CHIPS = [
    { key: 'all', label: t('admin.auditCategoryAll'), count: events?.length || 0 },
    { key: 'admin', label: t('admin.auditCategoryAdmin'), count: categoryCounts.admin },
    { key: 'oversight', label: t('admin.auditCategoryOversight'), count: categoryCounts.oversight },
    { key: 'auth', label: t('admin.auditCategoryAuth'), count: categoryCounts.auth },
  ];

  return (
    <section className="space-y-4 text-left" aria-labelledby="audit-title">
      {events && (
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {[
            { label: lang === 'vi' ? 'Tổng sự kiện' : 'Total events', value: events.length, icon: FileClock, tone: 'text-accent bg-accent-soft' },
            { label: lang === 'vi' ? 'Thành công' : 'Successful', value: allowedCount, icon: CheckCircle2, tone: 'text-success bg-success-soft' },
            { label: lang === 'vi' ? 'Cảnh báo' : 'Warnings', value: warningCount, icon: ShieldAlert, tone: 'text-warning bg-warning-soft' },
            { label: lang === 'vi' ? 'Bị từ chối' : 'Denied', value: deniedCount, icon: XCircle, tone: 'text-danger bg-danger-soft' },
          ].map(({ label, value, icon: Icon, tone }) => (
            <article key={label} className="admin-stat-card">
              <span className={`admin-stat-icon ${tone}`}><Icon size={16} aria-hidden="true" /></span>
              <div><p className="text-[10px] font-bold uppercase tracking-wide text-fg-muted">{label}</p><p className="mono mt-1 text-2xl font-bold text-fg">{value}</p></div>
            </article>
          ))}
        </div>
      )}

      <div className="admin-toolbar flex flex-wrap items-center justify-between gap-3">
        <h2 id="audit-title" className="text-sm font-bold text-fg flex items-center gap-2">
          <History size={16} className="text-accent" /> {t('admin.auditTitle')}
        </h2>
        {events && events.length > 0 && (
          <div className="flex flex-wrap items-center gap-1.5" role="group" aria-label={t('admin.auditFilterLabel')}>
            {CATEGORY_CHIPS.map(({ key, label, count }) => (
              <button
                key={key}
                type="button"
                onClick={() => setCategory(key)}
                aria-pressed={category === key}
                className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-[11px] font-semibold cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-accent ${
                  category === key
                    ? 'border-accent bg-accent-soft text-accent'
                    : 'border-line text-fg-secondary hover:text-fg hover:border-fg-muted'
                }`}
              >
                {label}
                <span className={`mono ${category === key ? '' : 'text-fg-muted'}`}>{count}</span>
              </button>
            ))}
          </div>
        )}
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
      ) : visibleEvents.length === 0 ? (
        <p className="text-xs text-fg-muted">{t('admin.auditEmpty')}</p>
      ) : (
        <div className="grid min-w-0 gap-4 xl:grid-cols-[minmax(0,1fr)_22rem]">
          <div className="overflow-x-auto rounded-lg border border-line bg-surface-card">
          <table className="data-table">
            <thead>
              <tr>
                <th scope="col" />
                <th scope="col">{t('admin.auditColTime')}</th>
                <th scope="col">{t('admin.auditColEvent')}</th>
                <th scope="col">{t('admin.auditColActor')}</th>
                <th scope="col" className="hidden 2xl:table-cell">{t('admin.auditColResource')}</th>
                <th scope="col">{t('admin.auditColDecision')}</th>
              </tr>
            </thead>
            <tbody>
              {visibleEvents.map((event) => {
                    const eventCategory = categorizeEvent(event.event_type);
                    const CategoryIcon = CATEGORY_ICON[eventCategory];
                    // Routine session churn (auth) is real but rarely what an
                    // Admin is scanning for -- dim it rather than hide it, so
                    // the eye lands on admin/oversight rows first without any
                    // row actually disappearing out from under a "Tất cả" view.
                    const isNoise = eventCategory === 'auth' && category === 'all';
                    return (
                    <tr key={event.id} className={`${selectedEvent?.id === event.id ? 'admin-selected-row' : ''} ${isNoise ? 'opacity-60' : ''}`}>
                      <td>
                        <button
                          type="button"
                          className="min-w-[24px] min-h-[24px] inline-flex items-center justify-center text-fg-muted hover:text-fg cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-accent rounded"
                          aria-label={t('admin.auditToggleDetails')}
                          onClick={() => setSelectedId(event.id)}
                        >
                          <ChevronRight size={14} />
                        </button>
                      </td>
                      <td className="text-fg-muted whitespace-nowrap">{formatTimestamp(event.created_at, lang)}</td>
                      <td className={`mono font-semibold ${isNoise ? 'text-fg-secondary' : 'text-fg'}`}>
                        <span className="inline-flex items-center gap-1.5">
                          <CategoryIcon size={12} className="shrink-0 text-fg-muted" aria-hidden="true" />
                          {event.event_type}
                        </span>
                      </td>
                      <td className="max-w-48 truncate text-fg-secondary">{event.actor_user_id || '—'}</td>
                      <td className="hidden text-fg-secondary 2xl:table-cell">
                        {event.resource_type ? `${event.resource_type}${event.resource_id ? ` · ${event.resource_id}` : ''}` : '—'}
                      </td>
                      <td>
                        <span className={`badge text-[9px] font-bold ${event.decision === 'ALLOW' ? 'badge-success' : 'badge-danger'}`}>
                          {event.decision}
                        </span>
                      </td>
                    </tr>
                    );
              })}
            </tbody>
          </table>
          </div>

          <aside className="admin-detail-panel" aria-label={lang === 'vi' ? 'Chi tiết sự kiện' : 'Event details'}>
            {selectedEvent && (
              <>
                <div className="border-b border-line pb-4">
                  <p className="text-[10px] font-bold uppercase tracking-wide text-fg-muted">{lang === 'vi' ? 'Chi tiết sự kiện' : 'Event details'}</p>
                  <p className="mono mt-2 break-all text-sm font-bold text-fg">{selectedEvent.event_type}</p>
                  <p className="mono mt-1 break-all text-[10px] text-fg-muted">{selectedEvent.id}</p>
                </div>
                <dl className="space-y-3 py-4 text-xs">
                  <div><dt className="text-fg-muted">{t('admin.auditColTime')}</dt><dd className="mono mt-1 text-fg">{formatTimestamp(selectedEvent.created_at, lang)}</dd></div>
                  <div><dt className="text-fg-muted">{t('admin.auditColActor')}</dt><dd className="mono mt-1 break-all text-fg">{selectedEvent.actor_user_id || '—'}</dd></div>
                  <div><dt className="text-fg-muted">{t('admin.auditColResource')}</dt><dd className="mono mt-1 break-all text-fg">{selectedEvent.resource_type ? `${selectedEvent.resource_type}${selectedEvent.resource_id ? ` · ${selectedEvent.resource_id}` : ''}` : '—'}</dd></div>
                  <div><dt className="text-fg-muted">{t('admin.auditColIp')}</dt><dd className="mono mt-1 text-fg">{selectedEvent.ip_address || '—'}</dd></div>
                  <div><dt className="text-fg-muted">{t('admin.auditColUserAgent')}</dt><dd className="mt-1 break-words text-fg-secondary">{selectedEvent.user_agent || '—'}</dd></div>
                </dl>
                <div className="border-t border-line pt-4">
                  <p className="mb-2 text-[10px] font-bold uppercase tracking-wide text-fg-muted">Metadata</p>
                  <pre className="mono max-h-64 overflow-auto rounded-md border border-line bg-surface-elevated p-3 text-[10px] leading-relaxed text-fg-secondary">
                    {JSON.stringify(selectedEvent.metadata || {}, null, 2)}
                  </pre>
                </div>
              </>
            )}
          </aside>
        </div>
      )}
    </section>
  );
}
