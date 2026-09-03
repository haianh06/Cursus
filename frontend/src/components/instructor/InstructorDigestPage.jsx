import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertTriangle, Send, Users, ChevronRight, Trophy, Lightbulb,
  Check, ShieldAlert, ShieldOff, UserCircle2,
} from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import { GvStickyHeader } from './GvChrome';
import {
  getInstructorDashboard, getInstructorDigest, getInstructorAlerts,
  getGuardrailReviewQueue, sendInstructorDigestEmail, userFacingApiError,
} from '../../lib/api';
import { riskLevelLabel, formatDetectedAt } from '../../lib/riskLabels';
import ErrorState from '../shared/ErrorState';
import EmptyState from '../shared/EmptyState';

/**
 * Digest tuan — ban tom tat dieu hanh, KHONG phai dashboard thu hai.
 *
 * Dung 3 KPI, moi khoi tom tat toi da 3 muc, khong co bang dai.
 *
 * Sparkline duoc dung tu CHINH payload digest: moi case deu co moc thoi gian
 * (`generatedAt` / `createdAt`), nen chi can goi mot lan voi cua so gap doi
 * roi gom theo ngay o client — khong phai goi API nhieu lan, cung khong bia
 * ra chuoi so.
 */

const SPARK_W = 150;
const SPARK_H = 46;

/** Gom moc thoi gian theo ngay thanh chuoi `days` diem, cu nhat truoc. */
function dailySeries(timestamps, days) {
  const buckets = new Array(days).fill(0);
  const startOfToday = new Date();
  startOfToday.setHours(0, 0, 0, 0);
  timestamps.forEach((iso) => {
    if (!iso) return;
    const at = new Date(iso);
    if (Number.isNaN(at.getTime())) return;
    const dayDiff = Math.floor((startOfToday - new Date(at).setHours(0, 0, 0, 0)) / 86400e3);
    const index = days - 1 - dayDiff;
    if (index >= 0 && index < days) buckets[index] += 1;
  });
  return buckets;
}

function Sparkline({ values, color }) {
  if (!values.length) return null;
  const max = Math.max(1, ...values);
  const x = (i) => (i * SPARK_W) / Math.max(1, values.length - 1);
  const y = (v) => SPARK_H - 4 - (v / max) * (SPARK_H - 10);
  const line = values.map((v, i) => `${i === 0 ? 'M' : 'L'} ${x(i)} ${y(v)}`).join(' ');
  const area = `${line} L ${SPARK_W} ${SPARK_H} L 0 ${SPARK_H} Z`;
  return (
    <svg viewBox={`0 0 ${SPARK_W} ${SPARK_H}`} style={{ width: SPARK_W, height: SPARK_H }} aria-hidden="true">
      <path d={area} fill={color} opacity="0.12" />
      <path d={line} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      {values.map((v, i) => (
        <circle key={i} cx={x(i)} cy={y(v)} r="2.2" fill={color} />
      ))}
    </svg>
  );
}

function DigestKpi({ label, value, delta, values, color, t }) {
  const up = delta !== null && delta > 0;
  return (
    <div className="gv-card p-5 flex items-start justify-between gap-4 min-w-0">
      <div className="min-w-0">
        <p className="gv-body-sm gv-muted" style={{ fontWeight: 500 }}>{label}</p>
        <p className="gv-kpi-value mt-1">{value}</p>
        {delta === null || delta === 0 ? (
          <p className="gv-meta mt-1.5">{t('instructor.dashNoTrend')}</p>
        ) : (
          <p className="gv-meta mt-1.5 flex items-center gap-1.5">
            <span style={{ color: up ? 'var(--gv-amber)' : 'var(--gv-success)', fontWeight: 600 }}>
              {up ? '↑' : '↓'} {Math.abs(delta)}%
            </span>
            {t('instructor.dashVsLastWeek')}
          </p>
        )}
      </div>
      <div className="shrink-0"><Sparkline values={values} color={color} /></div>
    </div>
  );
}

export default function InstructorDigestPage() {
  const { t, lang } = useLanguage();
  const navigate = useNavigate();

  const [days, setDays] = useState(7);
  const [courses, setCourses] = useState([]);
  const [selectedCourseId, setSelectedCourseId] = useState('ALL');

  const [digest, setDigest] = useState(null);
  const [wideDigest, setWideDigest] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [allAlerts, setAllAlerts] = useState([]);
  const [guardrailQueue, setGuardrailQueue] = useState([]);

  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [isSending, setIsSending] = useState(false);
  const [sendResult, setSendResult] = useState(null);

  const load = async () => {
    setIsLoading(true);
    setLoadError(null);
    try {
      const [main, wide, dash, alerts, queue] = await Promise.all([
        getInstructorDigest(days, selectedCourseId),
        // Cua so gap doi: vua de ve sparkline theo ngay, vua de tinh delta
        // "so voi ky truoc" ma khong can them endpoint nao.
        getInstructorDigest(days * 2, selectedCourseId),
        getInstructorDashboard(selectedCourseId).catch(() => null),
        getInstructorAlerts(selectedCourseId).catch(() => []),
        getGuardrailReviewQueue().catch(() => []),
      ]);
      setDigest(main);
      setWideDigest(wide);
      setDashboard(dash);
      setAllAlerts(alerts || []);
      setGuardrailQueue(queue || []);
    } catch (err) {
      setLoadError(userFacingApiError(err).message);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [days, selectedCourseId]);

  useEffect(() => {
    if (dashboard?.courses) setCourses(dashboard.courses);
  }, [dashboard]);

  const series = useMemo(() => {
    const riskStamps = (wideDigest?.newRiskCases || []).map((r) => r.generatedAt);
    const guardStamps = (wideDigest?.newGuardrailCases || []).map((g) => g.createdAt);
    return {
      risk: dailySeries(riskStamps, days),
      guardrail: dailySeries(guardStamps, days),
    };
  }, [wideDigest, days]);

  /** Delta % giua ky nay va ky lien truoc, dua tren cung mot payload. */
  const deltaOf = (current, wide) => {
    const previous = (wide ?? 0) - (current ?? 0);
    if (!previous) return current ? 100 : null;
    return Math.round(((current - previous) / previous) * 100);
  };

  const summary = digest?.summary || { newRiskCount: 0, newGuardrailCount: 0, kudosCount: 0 };
  const wideSummary = wideDigest?.summary || summary;

  const highRiskPending = allAlerts.filter(
    (a) => a.status === 'INTERVENTION_PENDING' && String(a.riskLevel).toUpperCase() === 'HIGH'
  ).length;
  const overduePending = allAlerts.filter((a) => a.status === 'INTERVENTION_PENDING' && a.isOverdue).length;
  const resolvedCount = allAlerts.filter((a) => a.status !== 'INTERVENTION_PENDING').length;
  const guardrailPending = guardrailQueue.filter((g) => (g.reviewStatus || 'PENDING') === 'PENDING').length;

  const weeklyRates = dashboard?.classAvgCompletionByWeek || [];
  const latestCompletion = weeklyRates.length
    ? Math.round(weeklyRates[weeklyRates.length - 1] * 100) : null;

  const fill = (key, n) => t(`instructor.${key}`).replace('{n}', n);

  // Ca hai khoi duoi deu suy ra tu so lieu that, khong phai cau viet san.
  const highlights = [
    latestCompletion !== null ? fill('digHlCompletion', latestCompletion) : null,
    resolvedCount > 0 ? fill('digHlResolved', resolvedCount) : null,
    summary.kudosCount > 0 ? fill('digHlKudos', summary.kudosCount) : null,
  ].filter(Boolean).slice(0, 3);

  const suggestions = [
    highRiskPending > 0 ? fill('digSgHighRisk', highRiskPending) : null,
    guardrailPending > 0 ? fill('digSgGuardrail', guardrailPending) : null,
    summary.newPracticeCount > 0 ? fill('digSgPractice', summary.newPracticeCount) : null,
    overduePending > 0 ? fill('digSgOverdue', overduePending) : null,
  ].filter(Boolean).slice(0, 3);

  const handleSend = async () => {
    setIsSending(true);
    setSendResult(null);
    try {
      await sendInstructorDigestEmail(days);
      setSendResult({ tone: 'ok', text: t('instructor.digSent') });
    } catch (err) {
      setSendResult({ tone: 'error', text: userFacingApiError(err).message });
    } finally {
      setIsSending(false);
    }
  };

  if (isLoading) {
    return (
      <div className="gv-ui p-7 space-y-4 animate-pulse">
        <div className="gv-panel" style={{ height: 88 }} />
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {[0, 1, 2].map((i) => <div key={i} className="gv-card" style={{ height: 120 }} />)}
        </div>
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          <div className="gv-panel" style={{ height: 280 }} />
          <div className="gv-panel" style={{ height: 280 }} />
        </div>
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="gv-ui p-7">
        <ErrorState
          title={t('states.errorTitle')}
          description={loadError}
          onRetry={load}
          retryLabel={t('states.retryBtn')}
        />
      </div>
    );
  }

  return (
    <div className="gv-ui gv-page">
      <GvStickyHeader>
        {/* Header mot hang: tieu de | khoang thoi gian | lop | gui email */}
        <header className="gv-panel px-6 py-4 flex flex-wrap items-end gap-3">
          <h1 className="gv-page-title gv-title-inline mr-2" style={{ flex: '0 0 auto' }}>
            {t('instructor.digPageTitle')}
          </h1>

          <label style={{ width: 175 }}>
            <span className="gv-field-label">{t('instructor.digRange')}</span>
            <select className="gv-select" value={days} onChange={(e) => setDays(Number(e.target.value))}>
              <option value={7}>{t('instructor.digRange7')}</option>
              <option value={14}>{t('instructor.digRange14')}</option>
              <option value={30}>{t('instructor.digRange30')}</option>
            </select>
          </label>

          <label style={{ width: 260 }}>
            <span className="gv-field-label">{t('instructor.dashClassField')}</span>
            <span className="relative flex items-center">
              <Users size={15} className="absolute left-3 pointer-events-none" style={{ color: 'var(--gv-text-2)' }} />
              <select className="gv-select" style={{ paddingLeft: 34 }}
                value={selectedCourseId} onChange={(e) => setSelectedCourseId(e.target.value)}>
                <option value="ALL">{t('instructor.allCourses')}</option>
                {courses.map((c) => <option key={c.id} value={c.id}>{c.code} — {c.name}</option>)}
              </select>
            </span>
          </label>

          <button type="button" className="gv-btn gv-btn--teal-outline gv-ctl"
            style={{ marginLeft: 'auto' }} onClick={handleSend} disabled={isSending}>
            <Send size={16} /> {t('instructor.digSendEmail')}
          </button>
        </header>
      </GvStickyHeader>

      <div className="gv-page__body">

        {sendResult && (
          <p className="gv-body-sm"
            style={{ color: sendResult.tone === 'ok' ? 'var(--gv-success)' : 'var(--gv-danger)' }}>
            {sendResult.text}
          </p>
        )}

        {/* Dung 3 KPI */}
        <div className="grid grid-cols-1 sm:grid-cols-3" style={{ gap: 16 }}>
          <DigestKpi
            label={t('instructor.digKpiRisk')} value={summary.newRiskCount}
            delta={deltaOf(summary.newRiskCount, wideSummary.newRiskCount)}
            values={series.risk} color="var(--gv-amber)" t={t}
          />
          <DigestKpi
            label={t('instructor.digKpiGuardrail')} value={summary.newGuardrailCount}
            delta={deltaOf(summary.newGuardrailCount, wideSummary.newGuardrailCount)}
            values={series.guardrail} color="var(--gv-teal)" t={t}
          />
          <DigestKpi
            label={t('instructor.digKpiKudos')} value={summary.kudosCount}
            delta={deltaOf(summary.kudosCount, wideSummary.kudosCount)}
            values={[]} color="var(--gv-success)" t={t}
          />
        </div>

        {/* Case rui ro moi | Luot chan guardrail moi — moi ben toi da 3 muc */}
        <div className="grid grid-cols-1 xl:grid-cols-2 items-start" style={{ gap: 16 }}>
          <section className="gv-panel p-6 min-w-0">
            <div className="flex items-center justify-between gap-3 mb-4">
              <span className="flex items-center gap-2.5">
                <AlertTriangle size={19} style={{ color: 'var(--gv-amber)' }} />
                <h2 className="gv-section-title">{t('instructor.digNewRisk')}</h2>
              </span>
              <button type="button" className="gv-link" onClick={() => navigate('/instructor/risks')}>
                {t('instructor.dashViewAll')} ({summary.newRiskCount}) <ChevronRight size={15} />
              </button>
            </div>

            {(digest?.newRiskCases || []).length === 0 ? (
              <EmptyState title={t('instructor.digNoRisk')} />
            ) : (
              <ul className="flex flex-col" style={{ gap: 12 }}>
                {digest.newRiskCases.slice(0, 3).map((row) => (
                  <li key={row.id}>
                    <button type="button" className="gv-case"
                      onClick={() => navigate('/instructor/risks')}>
                      <span className="flex items-start justify-between gap-3 w-full">
                        <span className="flex items-start gap-2.5 min-w-0">
                          <UserCircle2 size={30} style={{ color: 'var(--gv-text-2)', flex: '0 0 auto' }} />
                          <span className="min-w-0">
                            <span className="block gv-card-title truncate">{row.studentAlias}</span>
                            <span className="block gv-body-sm gv-muted" style={{
                              display: '-webkit-box', WebkitLineClamp: 2,
                              WebkitBoxOrient: 'vertical', overflow: 'hidden',
                            }}>
                              {row.evidence?.reason || row.assignmentTitle}
                            </span>
                            <span className="block gv-meta mt-1">
                              {t('instructor.digDetectedAt')}: {formatDetectedAt(row.generatedAt, lang)}
                            </span>
                          </span>
                        </span>
                        <span className={`gv-badge gv-badge--${
                          String(row.riskLevel).toUpperCase() === 'HIGH' ? 'danger'
                            : String(row.riskLevel).toUpperCase() === 'MEDIUM' ? 'amber' : 'teal'} shrink-0`}>
                          {riskLevelLabel(t, row.riskLevel)}
                        </span>
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="gv-panel p-6 min-w-0">
            <div className="flex items-center justify-between gap-3 mb-4">
              <span className="flex items-center gap-2.5">
                <ShieldAlert size={19} style={{ color: 'var(--gv-teal)' }} />
                <h2 className="gv-section-title">{t('instructor.digNewGuardrail')}</h2>
              </span>
              <button type="button" className="gv-link"
                onClick={() => navigate('/instructor/guardrail-reviews')}>
                {t('instructor.dashViewAll')} ({summary.newGuardrailCount}) <ChevronRight size={15} />
              </button>
            </div>

            {(digest?.newGuardrailCases || []).length === 0 ? (
              <EmptyState title={t('instructor.digNoGuardrail')} />
            ) : (
              <ul className="flex flex-col" style={{ gap: 12 }}>
                {digest.newGuardrailCases.slice(0, 3).map((row) => (
                  <li key={row.id}>
                    <button type="button" className="gv-case"
                      onClick={() => navigate('/instructor/guardrail-reviews')}>
                      <span className="flex items-center justify-between gap-3 w-full">
                        <span className="flex items-center gap-2.5 min-w-0">
                          <span className="gv-kpi-icon shrink-0"
                            style={{ width: 38, height: 38, background: 'var(--gv-teal-soft)' }}>
                            <ShieldOff size={17} style={{ color: 'var(--gv-teal)' }} />
                          </span>
                          <span className="min-w-0">
                            <span className="block gv-card-title truncate">{row.studentAlias}</span>
                            <span className="block gv-meta truncate">
                              {formatDetectedAt(row.createdAt, lang)}
                            </span>
                          </span>
                        </span>
                        <span className={`gv-badge gv-badge--${
                          (row.reviewStatus || 'PENDING') === 'PENDING' ? 'amber' : 'neutral'} shrink-0`}>
                          {(row.reviewStatus || 'PENDING') === 'PENDING'
                            ? t('guardrail.pendingBadge')
                            : row.reviewStatus === 'UNBLOCKED'
                              ? t('guardrail.unblockedState') : t('guardrail.keptState')}
                        </span>
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>

        {/* Diem sang | Goi y hanh dong — moi ben toi da 3 gach dau dong */}
        <div className="grid grid-cols-1 xl:grid-cols-2 items-start" style={{ gap: 16 }}>
          <section className="gv-panel p-6 min-w-0">
            <div className="flex items-center gap-2.5 mb-4">
              <Trophy size={19} style={{ color: 'var(--gv-amber)' }} />
              <h2 className="gv-section-title">{t('instructor.digHighlights')}</h2>
            </div>
            {highlights.length === 0 ? (
              <EmptyState title={t('instructor.digNoHighlight')} />
            ) : (
              <ul className="flex flex-col" style={{ gap: 12 }}>
                {highlights.map((text) => (
                  <li key={text} className="flex items-start gap-2.5 gv-body-sm">
                    <Check size={16} className="mt-0.5 shrink-0" style={{ color: 'var(--gv-success)' }} />
                    <span>{text}</span>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="gv-panel p-6 min-w-0">
            <div className="flex items-center gap-2.5 mb-4">
              <Lightbulb size={19} style={{ color: 'var(--gv-amber)' }} />
              <h2 className="gv-section-title">{t('instructor.digSuggestions')}</h2>
            </div>
            <ul className="flex flex-col" style={{ gap: 12 }}>
              {(suggestions.length ? suggestions : [t('instructor.digSgAllClear')]).map((text) => (
                <li key={text} className="flex items-start gap-2.5 gv-body-sm">
                  <Check size={16} className="mt-0.5 shrink-0" style={{ color: 'var(--gv-teal)' }} />
                  <span>{text}</span>
                </li>
              ))}
            </ul>
          </section>
        </div>
      </div>
    </div>
  );
}
