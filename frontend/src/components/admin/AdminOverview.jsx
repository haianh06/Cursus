import React, { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  AlertTriangle,
  BookOpen,
  ChevronLeft,
  ChevronRight,
  History,
  Layers,
  Sparkles,
  UserPlus,
  Users,
} from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import { getAdminOverview, getLlmQuotaStatus, userFacingApiError } from '../../lib/api';
import {
  adminAuditDecisionLabel,
  adminCriticalChangeEventLabel,
  adminPriorityLabel,
  adminResourceLabel,
  adminSystemStatusLabel,
  adminTriggerLabel,
  adminWorkQueueSummary,
} from './adminDisplay';
import AdminAsyncRegion from './AdminAsyncRegion';
import { workQueueHref } from './adminWorkQueueLinks';

const PRIORITY_STYLE = {
  CRITICAL: 'border-danger/40 bg-danger-soft text-danger',
  HIGH: 'border-warning/40 bg-warning-soft text-warning',
  MEDIUM: 'border-line text-fg-secondary',
  LOW: 'border-line text-fg-secondary',
};

/** How many rows the overview shows before you ask for the rest, and how many
 *  it pages by once you have. The preview is small on purpose: an overview
 *  that renders every open item is a list page wearing a dashboard's name. */
const QUEUE_PREVIEW_SIZE = 5;
const QUEUE_PAGE_SIZE = 10;

/** The audit trail gets the same treatment for the same reason. The API sends
 *  ten rows and the page used to render all ten: 847px of card, 54% of the
 *  whole overview, for a section whose job is only to answer "did anything
 *  change under me while I was away". Five answers that; the rest of the trail
 *  lives on the audit log, which has the filters this block will never have. */
const CHANGES_PREVIEW_SIZE = 5;

/** Where "see the whole history" goes. The full audit log is the second block
 *  on the system log screen, so the link still needs the anchor to land on it
 *  rather than on the data access history above it. */
const AUDIT_LOG_HREF = '/admin/governance/logs#audit-log';

function age(seconds, t) {
  if (!seconds || seconds < 60) return t('admin.ageJustNow');
  const hours = Math.floor(seconds / 3600);
  if (hours < 1) return t('admin.ageMinutes', { count: Math.floor(seconds / 60) });
  if (hours < 24) return t('admin.ageHours', { count: hours });
  return t('admin.ageDays', { count: Math.floor(hours / 24) });
}

/** The count is the content; the label only says which count it is. At 24px
 *  against a 12px label the two read as one paragraph, so a card 279px wide
 *  said nothing from across the room. 30px against 11px puts the number where
 *  the eye lands first without reaching for colour or shadow — the hierarchy
 *  does the work that decoration would otherwise have to. */
function SummaryMetric({ icon: Icon, label, value }) {
  return (
    <div className="rounded-lg border border-line bg-surface p-3">
      <div className="flex items-start justify-between gap-2">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-fg-secondary">{label}</p>
        <span className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-accent/20 bg-accent-soft text-accent">
          <Icon size={15} aria-hidden="true" />
        </span>
      </div>
      <p className="mono mt-1 text-3xl font-bold leading-tight text-fg">{value}</p>
    </div>
  );
}

/** A rate, plus the provenance that makes it defensible: which window, measured
 *  when, measured how. The provenance is real content but it is reference, not
 *  news — six lines of grey metadata competing with the work queue is how a
 *  work surface turns into a spec sheet. So it collapses, and the disclosure
 *  says what is inside rather than "details". An absent denominator reads as
 *  "not measured yet" instead of a fabricated 0%. */
function SignalMetric({ icon: Icon, label, metric }) {
  const { t, lang } = useLanguage();
  const hasValue = metric?.value !== null && metric?.value !== undefined;
  const value = hasValue ? `${Math.round(metric.value * 100)}%` : t('admin.metricNoDenominator');
  const denominator = metric?.numerator !== undefined && metric?.denominator !== undefined
    ? `${metric.numerator} / ${metric.denominator}`
    : null;
  // Two shapes, both real: a window has start/end, a snapshot has as_of. The
  // API sends POINT_IN_TIME today, so checking only for start/end reported
  // "not provided" for provenance the backend had in fact supplied.
  const periodWindow = metric?.period?.start && metric?.period?.end;
  const periodAsOf = metric?.period?.as_of;
  const period = periodWindow
    ? `${metric.period.start} – ${metric.period.end}`
    : periodAsOf
      ? new Date(periodAsOf).toLocaleString(lang)
      : t('admin.metricPeriodUnavailable');

  return (
    <div>
      <div className="flex items-center gap-2">
        <span className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-accent/20 bg-accent-soft text-accent">
          <Icon size={15} aria-hidden="true" />
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-fg">{label}</p>
          {denominator && <p className="mono text-xs text-fg-secondary">{denominator}</p>}
        </div>
        <p className={`mono shrink-0 font-bold ${hasValue ? 'text-2xl text-accent' : 'text-xs text-fg-secondary'}`}>
          {value}
        </p>
      </div>
      <details className="mt-1">
        <summary className="inline-flex min-h-11 cursor-pointer items-center text-xs font-semibold text-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent">
          {t('admin.metricProvenance')}
        </summary>
        <dl className="mb-1 space-y-1 text-xs text-fg-secondary">
          <div>
            <dt className="inline font-semibold">{t('admin.metricPeriod')}:</dt>{' '}
            <dd className="inline">{period}</dd>
          </div>
          <div>
            <dt className="inline font-semibold">{t('admin.metricMeasuredAt')}:</dt>{' '}
            <dd className="inline">
              {metric?.measured_at ? new Date(metric.measured_at).toLocaleString(lang) : '—'}
            </dd>
          </div>
          <div>
            <dt className="inline font-semibold">{t('admin.metricMethod')}:</dt>{' '}
            <dd className="inline">{metric?.method_note || '—'}</dd>
          </div>
        </dl>
      </details>
    </div>
  );
}

/** Gemini gives no way to check remaining quota ahead of a call, so this is
 *  purely reactive: how many real 429s the app has actually hit in the last
 *  24h, and when the last one landed. No live "exhausted right now" claim —
 *  just the log, which is what the data can actually support. */
function LlmQuotaCard({ status, t, lang }) {
  if (!status) return null;
  const hasRecentEvents = status.countInWindow > 0;
  return (
    <div
      className={`rounded-lg border p-3 ${hasRecentEvents ? 'border-warning/40 bg-warning-soft' : 'border-line bg-surface'}`}
    >
      <div className="flex items-center gap-2">
        <span
          className={`inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border ${hasRecentEvents ? 'border-warning/30 bg-white/40 text-warning' : 'border-accent/20 bg-accent-soft text-accent'}`}
        >
          <Sparkles size={15} aria-hidden="true" />
        </span>
        <p className="text-sm font-semibold text-fg">{t('admin.llmQuotaTitle')}</p>
      </div>
      <p className={`mt-2 text-xs ${hasRecentEvents ? 'text-warning font-semibold' : 'text-fg-secondary'}`}>
        {hasRecentEvents ? t('admin.llmQuotaExhausted') : t('admin.llmQuotaHealthy')}
      </p>
      <dl className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-fg-secondary">
        <div>
          <dt className="inline font-semibold">{t('admin.llmQuotaCount24h')}:</dt>{' '}
          <dd className="mono inline">{status.countInWindow}</dd>
        </div>
        <div>
          <dt className="inline font-semibold">{t('admin.llmQuotaLastExhausted')}:</dt>{' '}
          <dd className="inline">
            {status.lastExhaustedAt ? new Date(status.lastExhaustedAt).toLocaleString(lang) : t('admin.llmQuotaNever')}
          </dd>
        </div>
      </dl>
    </div>
  );
}

/** One queue row, one line on desktop.
 *
 *  This was a stacked card: severity on line one, subject and message on line
 *  two, age on line three, a bordered button on the right — roughly 80px for
 *  four short facts. Ten of those is a whole viewport, which is how the
 *  overview stopped showing an overview. A desktop admin screen has width to
 *  spare and no vertical room to waste, so the facts sit in columns and the
 *  row lands near 44px. Below `md` it wraps instead, because five columns in
 *  375px is not a table, it is a mess.
 *
 *  The desktop row carries no vertical padding of its own. The "Mở" link is
 *  already 44px tall to stay a legal touch target, so `py-1` was adding 8px on
 *  top of a height something else had settled — 53px per row, six rows of
 *  waste per screen. Mobile keeps the padding: there the row wraps to three
 *  lines and the link no longer sets the height. */
function QueueItem({ item, t }) {
  return (
    <li className="border-b border-line last:border-b-0">
      {/* The type column is `max-content`, not a fixed width: "Tác vụ nạp
          chương trình học" and "Guardrail safety event" are far longer than
          "Yêu cầu dữ liệu", and a number picked for one language truncates the
          other. Let the longest label in the current locale set the width and
          give the rest to the message. */}
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 py-1 md:grid md:grid-cols-[4.5rem_minmax(8.5rem,max-content)_6.5rem_minmax(0,1fr)_5rem_auto] md:gap-y-0 md:py-0">
        <span
          className={`inline-flex items-center justify-center rounded-md border px-2 py-0.5 text-[11px] font-bold ${PRIORITY_STYLE[item.priority] || PRIORITY_STYLE.MEDIUM}`}
        >
          {adminPriorityLabel(t, item.priority)}
        </span>

        {/* Which of the five sources this row came from. It was a visible
            column, became a `title` on the priority chip during the compact
            pass, and that was wrong: the type decides where "Mở" goes and who
            can actually clear the item, so hiding it behind a hover left the
            reader guessing from the sentence. */}
        <span className="truncate text-xs font-semibold text-fg-secondary">
          {adminTriggerLabel(t, item.trigger_type)}
        </span>

        {/* The subject id, because a hundred unresolved risks all summarise to
            the same sentence. Without it the only way to tell two rows apart
            is to open both. */}
        <span className="mono truncate text-xs text-fg-secondary">
          {item.subject_user_id || '—'}
        </span>

        <span className="min-w-0 truncate text-sm text-fg" title={adminWorkQueueSummary(t, item)}>
          {adminWorkQueueSummary(t, item)}
        </span>

        <span className="text-xs text-fg-secondary md:text-right">{age(item.age_seconds, t)}</span>

        <Link
          to={workQueueHref(item)}
          className="inline-flex min-h-11 items-center gap-1 rounded-lg px-2 text-sm font-semibold text-accent hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent md:justify-self-end"
        >
          {t('admin.workQueueOpen')}
          <ChevronRight size={14} aria-hidden="true" />
        </Link>
      </div>
    </li>
  );
}

/** Queue composition from `work_queue.by_type`. Real data, and the one thing a
 *  truncated list cannot tell you: whether the twelve open items are twelve of
 *  the same problem or four different ones. */
function QueueBreakdown({ byType, t }) {
  const rows = Object.entries(byType || {}).sort((a, b) => b[1] - a[1]);
  if (rows.length === 0) return null;
  return (
    <dl className="flex flex-col">
      {rows.map(([type, count]) => (
        <div key={type} className="flex items-center justify-between gap-3 border-b border-line py-1.5 last:border-b-0">
          <dt className="min-w-0 truncate text-sm text-fg-secondary">{adminTriggerLabel(t, type)}</dt>
          <dd className="mono shrink-0 text-base font-bold text-fg">{count}</dd>
        </div>
      ))}
    </dl>
  );
}

/** One audit row from the allow-list the API returns. Every field rendered here
 *  is named explicitly rather than spread, so widening the readout stays a
 *  deliberate edit instead of a side effect of the backend adding a column. */
function CriticalChange({ change, lang, t }) {
  const resource = change.resource_type
    ? `${adminResourceLabel(t, change.resource_type)}${change.resource_id ? ` · ${change.resource_id}` : ''}`
    : null;
  return (
    <li className="rounded-lg border border-line p-3 text-sm">
      <p className="font-semibold text-fg">
        {adminCriticalChangeEventLabel(t, change.event_type)} · {adminAuditDecisionLabel(t, change.decision)}
      </p>
      <dl className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-fg-secondary">
        {change.actor_user_id && (
          <div>
            <dt className="inline font-semibold">{t('admin.auditActor')}:</dt>{' '}
            <dd className="mono inline">{change.actor_user_id}</dd>
          </div>
        )}
        {change.subject_user_id && (
          <div>
            <dt className="inline font-semibold">{t('admin.caseSubject')}:</dt>{' '}
            <dd className="mono inline">{change.subject_user_id}</dd>
          </div>
        )}
        {resource && (
          <div>
            <dt className="inline font-semibold">{t('admin.auditResource')}:</dt>{' '}
            <dd className="inline">{resource}</dd>
          </div>
        )}
        <div>
          <dt className="inline font-semibold">{t('admin.auditTime')}:</dt>{' '}
          <dd className="inline">{change.created_at ? new Date(change.created_at).toLocaleString(lang) : '—'}</dd>
        </div>
      </dl>
    </li>
  );
}

export default function AdminOverview() {
  const { t, lang } = useLanguage();
  const [overview, setOverview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [queuePage, setQueuePage] = useState(1);
  const [queueExpanded, setQueueExpanded] = useState(false);
  const [quotaStatus, setQuotaStatus] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getAdminOverview();
      setOverview(response.data ?? response);
    } catch (err) {
      setError({ ...userFacingApiError(err, lang), status: err?.status, code: err?.code });
    } finally {
      setLoading(false);
    }
  }, [lang]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    let cancelled = false;
    getLlmQuotaStatus()
      .then((data) => !cancelled && setQuotaStatus(data))
      .catch(() => {});
    return () => { cancelled = true; };
  }, []);

  const pulse = overview?.school_pulse || {};
  const fullQueue = overview?.work_queue?.items || [];
  const changes = overview?.recent_critical_changes || [];
  const recentChanges = changes.slice(0, CHANGES_PREVIEW_SIZE);
  const healthy = overview?.system_status === 'HEALTHY';

  const totalQueuePages = Math.max(1, Math.ceil(fullQueue.length / QUEUE_PAGE_SIZE));
  const currentQueuePage = Math.min(queuePage, totalQueuePages);
  const queueStart = (currentQueuePage - 1) * QUEUE_PAGE_SIZE;
  const queue = queueExpanded
    ? fullQueue.slice(queueStart, queueStart + QUEUE_PAGE_SIZE)
    : fullQueue.slice(0, QUEUE_PREVIEW_SIZE);

  useEffect(() => {
    setQueuePage((page) => Math.min(page, totalQueuePages));
  }, [totalQueuePages]);

  return (
    <AdminAsyncRegion loading={loading} error={error} onRetry={load}>
      {/* Dashboard order: what the school looks like, then what needs doing,
          then the trail. The previous build led with ten full-height queue
          cards, so at 100% zoom the first screen was nothing but alerts and
          every number sat below the fold — an overview you had to scroll to
          get an overview from. */}
      <div className="flex flex-col gap-4">
        <section
          aria-labelledby="admin-overview-status"
          className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1"
        >
          <h2 id="admin-overview-status" className="font-display text-lg font-bold text-fg">
            {t('admin.overviewSummaryTitle')}
          </h2>
          <p className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-fg-secondary">
            <span className="inline-flex items-center gap-2 font-semibold">
              <span
                className={`h-2 w-2 rounded-full ${healthy ? 'bg-success' : 'bg-warning'}`}
                aria-hidden="true"
              />
              {adminSystemStatusLabel(t, overview?.system_status)}
            </span>
            <span>
              {t('admin.lastUpdated')}:{' '}
              <span className="mono">
                {overview?.last_updated ? new Date(overview.last_updated).toLocaleString(lang) : '—'}
              </span>
            </span>
          </p>
        </section>

        <section aria-labelledby="admin-school-pulse">
          <h2 id="admin-school-pulse" className="sr-only">{t('admin.schoolPulseTitle')}</h2>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <SummaryMetric icon={Users} label={t('admin.pulseStudents')} value={pulse.active_students ?? 0} />
            <SummaryMetric icon={UserPlus} label={t('admin.pulseInstructors')} value={pulse.active_instructors ?? 0} />
            <SummaryMetric icon={BookOpen} label={t('admin.pulseCourses')} value={pulse.courses ?? 0} />
            <SummaryMetric icon={Layers} label={t('admin.pulseSections')} value={pulse.sections ?? 0} />
          </div>
        </section>

        <div className="grid gap-4 lg:grid-cols-3">
          <section
            aria-labelledby="admin-work-queue"
            className="rounded-lg border border-line bg-surface p-4 lg:col-span-2"
          >
            <div className="mb-2 flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
              <h2 id="admin-work-queue" className="flex items-center gap-2 font-display text-lg font-bold text-fg">
                <AlertTriangle size={15} className="text-accent" aria-hidden="true" />
                {t('admin.workQueueTitle')}
                <span className="mono text-base font-bold text-accent">{fullQueue.length}</span>
              </h2>
              <p className="text-xs text-fg-secondary">{t('admin.workQueueDescription')}</p>
            </div>

            {fullQueue.length === 0 ? (
              <p className="border-t border-line pt-3 text-sm text-fg-secondary">{t('admin.workQueueEmpty')}</p>
            ) : (
              <ul className="border-t border-line">
                {queue.map((item) => (
                  <QueueItem key={`${item.trigger_type}:${item.trigger_id}`} item={item} t={t} />
                ))}
              </ul>
            )}

            {fullQueue.length > QUEUE_PREVIEW_SIZE && (
              <div className="mt-1 flex flex-wrap items-center justify-between gap-x-3 gap-y-1 border-t border-line">
                <button
                  type="button"
                  onClick={() => { setQueueExpanded((open) => !open); setQueuePage(1); }}
                  aria-expanded={queueExpanded}
                  className="inline-flex min-h-11 items-center gap-1 rounded-lg text-sm font-semibold text-accent hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
                >
                  {queueExpanded
                    ? t('admin.workQueueShowLess')
                    : t('admin.workQueueShowAll').replace('{count}', String(fullQueue.length))}
                  <ChevronRight size={14} aria-hidden="true" />
                </button>

                {queueExpanded && totalQueuePages > 1 && (
                  <div className="flex items-center gap-2">
                    <p className="mono text-xs text-fg-secondary">
                      {t('admin.workQueuePageSummary')
                        .replace('{page}', String(currentQueuePage))
                        .replace('{pages}', String(totalQueuePages))
                        .replace('{count}', String(fullQueue.length))}
                    </p>
                    <button
                      type="button"
                      disabled={currentQueuePage === 1}
                      onClick={() => setQueuePage((page) => Math.max(1, page - 1))}
                      aria-label={t('admin.workQueuePrevious')}
                      title={t('admin.workQueuePrevious')}
                      className="inline-flex h-11 w-11 items-center justify-center rounded-lg border border-line text-fg-secondary transition hover:border-accent hover:text-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent disabled:cursor-not-allowed disabled:opacity-40"
                    >
                      <ChevronLeft size={16} aria-hidden="true" />
                    </button>
                    <button
                      type="button"
                      disabled={currentQueuePage === totalQueuePages}
                      onClick={() => setQueuePage((page) => Math.min(totalQueuePages, page + 1))}
                      aria-label={t('admin.workQueueNext')}
                      title={t('admin.workQueueNext')}
                      className="inline-flex h-11 w-11 items-center justify-center rounded-lg border border-line text-fg-secondary transition hover:border-accent hover:text-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent disabled:cursor-not-allowed disabled:opacity-40"
                    >
                      <ChevronRight size={16} aria-hidden="true" />
                    </button>
                  </div>
                )}
              </div>
            )}
          </section>

          {/* The API reports one overall status, derived from failed ingest
              jobs. There is no per-service health behind it, so this panel
              carries what the backend actually measures rather than an
              API / Database / AI Service row set that nothing is watching. */}
          <section
            aria-labelledby="admin-overview-signals"
            className="rounded-lg border border-line bg-surface p-4"
          >
            <h2 id="admin-overview-signals" className="mb-2 font-display text-lg font-bold text-fg">
              {t('admin.overviewSignalsTitle')}
            </h2>
            <div className="border-t border-line">
              <QueueBreakdown byType={overview?.work_queue?.by_type} t={t} />
            </div>
            <div className="mt-2 flex flex-col gap-2 border-t border-line pt-2">
              <SignalMetric icon={AlertTriangle} label={t('admin.overviewSignalsRisk')} metric={pulse.unresolved_risk} />
              <SignalMetric icon={UserPlus} label={t('admin.overviewSignalsActivation')} metric={pulse.invitation_activation} />
            </div>
            <div className="mt-2 border-t border-line pt-2">
              <LlmQuotaCard status={quotaStatus} t={t} lang={lang} />
            </div>
          </section>
        </div>

        <section aria-labelledby="admin-recent-changes" className="rounded-lg border border-line bg-surface p-4">
          <h2 id="admin-recent-changes" className="mb-2 flex items-center gap-2 font-display text-lg font-bold text-fg">
            <History size={15} className="text-accent" aria-hidden="true" />
            {t('admin.recentChangesTitle')}
          </h2>
          {changes.length === 0 ? (
            <p className="border-t border-line pt-3 text-sm text-fg-secondary">{t('admin.recentChangesEmpty')}</p>
          ) : (
            <>
              <ul className="flex flex-col gap-2">
                {recentChanges.map((change) => <CriticalChange key={change.id} change={change} lang={lang} t={t} />)}
              </ul>
              {/* A link, not a "show more" toggle. Expanding in place could only
                  ever reveal the ten rows the overview endpoint returns, which
                  is not "the whole history" by any reading — the audit log is
                  the surface that holds the rest and can filter it. */}
              <Link
                to={AUDIT_LOG_HREF}
                className="mt-1 inline-flex min-h-11 items-center gap-1 rounded-lg text-sm font-semibold text-accent hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
              >
                {t('admin.recentChangesShowAll')}
                <ChevronRight size={14} aria-hidden="true" />
              </Link>
            </>
          )}
        </section>
      </div>
    </AdminAsyncRegion>
  );
}
