import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertTriangle, Clock, ShieldCheck, CircleCheckBig, ArrowUp, ArrowDown,
  ChevronRight, Megaphone, FileText, Shield, Download, Mail, CalendarClock,
  BookOpen, FileCheck2, Users, UserCircle2,
} from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import { GvStickyHeader } from './GvChrome';
import {
  exportInstructorReport, getClassComparison, getGuardrailReviewQueue,
  getInstructorAlerts, getInstructorAnnouncements, getInstructorDashboard,
  sendInstructorDigestEmail, userFacingApiError,
} from '../../lib/api';
import { riskLevelLabel } from '../../lib/riskLabels';
import ErrorState from '../shared/ErrorState';
import EmptyState from '../shared/EmptyState';

/**
 * Dashboard GV — tra loi dung mot cau hoi: "Hom nay toi can chu y dieu gi?".
 *
 * Bo cuc theo anh mau: header + 4 KPI + (Can chu y ngay | Thong bao & Thao
 * tac nhanh) + (Suc khoe lop | So sanh cac lop). Man hinh nay chi hien so
 * lieu tong hop; toan bo bang chung chi tiet cua mot case nam o trang
 * "Rui ro & Canh bao", dung nguyen tac "dashboard shows summary, not
 * detailed evidence" trong spec.
 *
 * Ve du lieu: chi ve nhung gi backend that su tra ve.
 *  - Delta "so voi tuan truoc" chi co cho ty le hoan thanh, vi
 *    classAvgCompletionByWeek la chuoi theo tuan duy nhat ma API cung cap.
 *    Ba KPI dem (nguy co / qua han / guardrail) khong co lich su nen khong
 *    ve delta — bia ra mot con so o day se la so gia doi lot so do that.
 *  - Anh mau con co bo loc "Tuan"; backend chua co tham so tuan cho
 *    /instructor/dashboard nen chua dung, tranh mot control nhin nhu loc
 *    toan trang nhung khong loc gi.
 */

/** Mau theo he trang thai trong spec: cao = do, trung binh = amber,
 *  thap/an toan = teal. Khong dung do cho muc thap. */
function riskTone(level) {
  const value = String(level || '').toUpperCase();
  if (value === 'HIGH') return 'danger';
  if (value === 'MEDIUM') return 'amber';
  return 'teal';
}

const MAX_ATTENTION_ROWS = 5;
const MAX_NOTICES = 3;

function formatDateTime(value, lang) {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '—';
  return new Intl.DateTimeFormat(lang === 'vi' ? 'vi-VN' : 'en-US', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  }).format(date);
}

function percent(value) {
  if (value === null || value === undefined) return null;
  return Math.round(value * 100);
}

/** Delta co dau + mau ngu nghia. `goodWhenUp` phan biet "tang la tot"
 *  (ty le hoan thanh) voi "tang la xau" (so case). */
function Delta({ value, unit = '', goodWhenUp, label }) {
  if (value === null || value === undefined || value === 0) {
    return <span className="gv-meta">{label}</span>;
  }
  const up = value > 0;
  const good = up === goodWhenUp;
  const Icon = up ? ArrowUp : ArrowDown;
  return (
    <span
      className="flex items-center gap-1.5"
      style={{ fontSize: 13, lineHeight: 1.4 }}
    >
      <Icon size={13} style={{ color: good ? 'var(--gv-success)' : 'var(--gv-danger)' }} />
      <span style={{ color: good ? 'var(--gv-success)' : 'var(--gv-danger)', fontWeight: 600 }}>
        {Math.abs(value)}{unit}
      </span>
      <span className="gv-muted">{label}</span>
    </span>
  );
}

function KpiCard({ icon: Icon, iconBg, iconColor, label, value, children }) {
  return (
    <div className="gv-card p-5 flex items-center gap-4 min-w-0">
      <span className="gv-kpi-icon" style={{ background: iconBg }}>
        <Icon size={22} style={{ color: iconColor }} />
      </span>
      <div className="min-w-0 flex-1">
        <p className="gv-body-sm gv-muted truncate" style={{ fontWeight: 500 }}>{label}</p>
        <p className="gv-kpi-value mt-0.5">{value}</p>
        <div className="mt-1">{children}</div>
      </div>
    </div>
  );
}

/** Line chart ty le hoan thanh theo tuan. SVG noi tuyen — dung dung cach
 *  WeeklyStudyHoursChart cua SV ve, khong them thu vien bieu do moi. */
function ClassHealthChart({ points, t }) {
  const width = 640;
  const height = 210;
  const padX = 46;
  const padTop = 18;
  const padBottom = 30;

  if (!points.length) {
    return (
      <div
        className="flex items-center justify-center gv-body-sm gv-muted"
        style={{ height: 210 }}
      >
        {t('instructor.dashHealthEmpty')}
      </div>
    );
  }

  const innerW = width - padX * 2;
  const innerH = height - padTop - padBottom;
  const stepX = points.length > 1 ? innerW / (points.length - 1) : 0;
  const x = (i) => padX + (points.length > 1 ? i * stepX : innerW / 2);
  const y = (v) => padTop + innerH - (Math.max(0, Math.min(100, v)) / 100) * innerH;

  const line = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${x(i)} ${y(p.rate)}`).join(' ');

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className="w-full"
      style={{ height: 210 }}
      role="img"
      aria-label={t('instructor.dashHealth')}
    >
      {[0, 25, 50, 75, 100].map((tick) => (
        <g key={tick}>
          <line
            x1={padX} x2={width - padX} y1={y(tick)} y2={y(tick)}
            stroke="var(--gv-border)" strokeWidth="1"
          />
          <text
            x={padX - 8} y={y(tick) + 4} textAnchor="end"
            fontSize="12.5" fill="var(--gv-text-2)"
          >
            {tick}%
          </text>
        </g>
      ))}

      <path d={line} fill="none" stroke="var(--gv-teal)" strokeWidth="2.5"
        strokeLinecap="round" strokeLinejoin="round" />

      {points.map((p, i) => {
        // Diem dau/cuoi neo theo canh thay vi canh giua, neu khong nhan gia
        // tri cua diem dau se de len nhan cua truc Y ngay ben trai.
        const isFirst = i === 0;
        const isLast = i === points.length - 1;
        const anchor = isFirst ? 'start' : isLast ? 'end' : 'middle';
        const labelX = x(i) + (isFirst ? 3 : isLast ? -3 : 0);
        return (
          <g key={p.week}>
            <circle cx={x(i)} cy={y(p.rate)} r="4.5" fill="var(--gv-card)"
              stroke="var(--gv-teal)" strokeWidth="2.5" />
            <text x={labelX} y={y(p.rate) - 13} textAnchor={anchor}
              fontSize="12.5" fontWeight="600" fill="var(--gv-teal)">
              {p.rate}%
            </text>
              <text x={labelX} y={height - 9} textAnchor={anchor}
              fontSize="12.5" fill="var(--gv-text-2)">
              {t('instructor.dashWeekShort')} {p.week}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

export default function InstructorHome({ user }) {
  const { t, lang } = useLanguage();
  const navigate = useNavigate();

  const [courses, setCourses] = useState([]);
  const [selectedCourseId, setSelectedCourseId] = useState('ALL');
  const [classSize, setClassSize] = useState(0);
  const [highRiskCount, setHighRiskCount] = useState(null);
  const [overdueCount, setOverdueCount] = useState(null);
  const [guardrailPending, setGuardrailPending] = useState(null);
  const [weeklyRates, setWeeklyRates] = useState([]);
  const [attention, setAttention] = useState([]);
  const [announcements, setAnnouncements] = useState([]);
  const [comparison, setComparison] = useState([]);

  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [busyAction, setBusyAction] = useState(null);
  const [actionMessage, setActionMessage] = useState(null);

  const loadDashboard = async () => {
    setIsLoading(true);
    setLoadError(null);
    try {
      const [dashboard, alerts, notices, guardrail, classes] = await Promise.all([
        getInstructorDashboard(selectedCourseId),
        getInstructorAlerts(selectedCourseId).catch(() => []),
        getInstructorAnnouncements().catch(() => []),
        getGuardrailReviewQueue().catch(() => []),
        getClassComparison().catch(() => []),
      ]);

      setCourses(dashboard.courses || []);
      setClassSize(dashboard.classSize ?? 0);
      setHighRiskCount(dashboard.highRiskCount ?? 0);
      setOverdueCount(dashboard.overdueCount ?? 0);
      // `classCompletionPoints` mang theo so tuan that; `classAvgCompletionByWeek`
      // la mang tran nen chi danh nhan duoc theo vi tri — dung ban co so tuan
      // khi backend tra ve, con lai giu duong cu de khong vo neu thieu.
      const points = dashboard.classCompletionPoints;
      setWeeklyRates(
        Array.isArray(points) && points.length
          ? points.map((row) => ({ week: row.week, rate: percent(row.rate) ?? 0 }))
          : (dashboard.classAvgCompletionByWeek || []).map((rate, index) => ({
            week: index + 1,
            rate: percent(rate) ?? 0,
          }))
      );

      setGuardrailPending(
        (guardrail || []).filter((row) => (row.reviewStatus || 'PENDING') === 'PENDING').length
      );

      // Chi lay case CHUA xu ly, uu tien qua han > rui ro cao > moi nhat.
      const pending = (alerts || []).filter((row) => row.status === 'INTERVENTION_PENDING');
      const rank = { HIGH: 2, MEDIUM: 1, LOW: 0 };
      const sorted = [...pending].sort((a, b) => {
        if (Boolean(b.isOverdue) !== Boolean(a.isOverdue)) {
          return Boolean(b.isOverdue) - Boolean(a.isOverdue);
        }
        const byLevel = (rank[b.riskLevel] || 0) - (rank[a.riskLevel] || 0);
        if (byLevel !== 0) return byLevel;
        return new Date(b.generatedAt || 0) - new Date(a.generatedAt || 0);
      });
      setAttention(sorted.slice(0, MAX_ATTENTION_ROWS));

      setAnnouncements((notices || []).slice(0, MAX_NOTICES));
      setComparison(classes || []);
    } catch (err) {
      setLoadError(userFacingApiError(err));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadDashboard();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedCourseId]);

  const completion = useMemo(() => {
    if (!weeklyRates.length) return { value: null, delta: null };
    const last = weeklyRates[weeklyRates.length - 1].rate;
    const prev = weeklyRates.length > 1 ? weeklyRates[weeklyRates.length - 2].rate : null;
    return { value: last, delta: prev === null ? null : last - prev };
  }, [weeklyRates]);

  const primaryCourse = courses.find((c) => c.id === selectedCourseId) || null;

  const runAction = async (key, fn) => {
    setBusyAction(key);
    setActionMessage(null);
    try {
      await fn();
    } catch (err) {
      setActionMessage({ tone: 'error', text: userFacingApiError(err) });
    } finally {
      setBusyAction(null);
    }
  };

  const handleExport = () => runAction('export', async () => {
    const { blob, filename } = await exportInstructorReport(selectedCourseId);
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  });

  const handleDigest = () => runAction('digest', async () => {
    await sendInstructorDigestEmail();
    setActionMessage({ tone: 'ok', text: t('instructor.dashDigestSent') });
  });

  // Chi 5 thao tac, va moi thao tac deu tro toi mot endpoint/route co that.
  const quickActions = [
    { key: 'export', icon: Download, label: t('instructor.dashQaExport'), onClick: handleExport },
    { key: 'digest', icon: Mail, label: t('instructor.dashQaDigest'), onClick: handleDigest },
    { key: 'activity', icon: CalendarClock, label: t('instructor.dashQaActivity'), onClick: () => navigate('/instructor/activities') },
    { key: 'quiz', icon: BookOpen, label: t('instructor.dashQaQuiz'), onClick: () => navigate('/instructor/quizzes') },
    { key: 'submissions', icon: FileCheck2, label: t('instructor.dashQaSubmissions'), onClick: () => navigate('/instructor/submissions') },
  ];

  if (isLoading) {
    return (
      <div className="gv-ui p-7 space-y-4 animate-pulse">
        <div className="gv-panel" style={{ height: 108 }} />
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
          {[0, 1, 2, 3].map((i) => <div key={i} className="gv-card" style={{ height: 108 }} />)}
        </div>
        <div className="grid grid-cols-1 xl:grid-cols-[55fr_45fr] gap-4">
          <div className="gv-panel" style={{ height: 340 }} />
          <div className="gv-panel" style={{ height: 340 }} />
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
          onRetry={loadDashboard}
          retryLabel={t('states.retryBtn')}
        />
      </div>
    );
  }

  return (
    <div className="gv-ui gv-page">
      {/* ── Header (ghim khi cuon) ──────────────────────────────── */}
      <GvStickyHeader>
        <header className="gv-panel px-6 py-5 flex flex-col xl:flex-row xl:items-end gap-5 xl:gap-6">
          <div className="min-w-0 flex-1">
            <h1 className="gv-page-title" style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {t('instructor.dashGreeting')}, {user?.name || t('nav.instructorHome')} <span aria-hidden="true">👋</span>
            </h1>
            <p className="gv-body-sm gv-muted mt-1.5">
              {t('instructor.dashSubtitle')}
              {primaryCourse && <> · {primaryCourse.code} — {classSize} {t('instructor.studentsUnit')}</>}
            </p>
          </div>

          <div className="flex flex-wrap items-end gap-3 shrink-0">
            <label className="block" style={{ width: 230 }}>
              <span className="gv-field-label">{t('instructor.dashClassField')}</span>
              <span className="relative flex items-center">
                <Users size={15} className="absolute left-3 pointer-events-none" style={{ color: 'var(--gv-text-2)' }} />
                <select
                  className="gv-select"
                  style={{ paddingLeft: 34 }}
                  value={selectedCourseId}
                  onChange={(event) => setSelectedCourseId(event.target.value)}
                >
                  <option value="ALL">{t('instructor.allCourses')}</option>
                  {courses.map((course) => (
                    <option key={course.id} value={course.id}>
                      {course.code} — {course.name}
                    </option>
                  ))}
                </select>
                <ChevronRight size={15} className="absolute right-3 pointer-events-none rotate-90" style={{ color: 'var(--gv-text-2)' }} />
              </span>
            </label>

            <button type="button" className="gv-btn gv-btn--teal gv-ctl" onClick={() => navigate('/instructor/risks')}>
              <Users size={16} /> {t('instructor.dashViewRisk')}
            </button>
            <button type="button" className="gv-btn gv-btn--amber gv-ctl" onClick={() => navigate('/instructor/guardrail-reviews')}>
              <Shield size={16} /> {t('instructor.dashViewGuardrail')}
            </button>
          </div>
        </header>
      </GvStickyHeader>

      <div className="gv-page__body">
        {/* ── 4 KPI ──────────────────────────────────────────────── */}
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4" style={{ gap: 16 }}>
          <KpiCard
            icon={AlertTriangle} iconBg="var(--gv-danger-soft)" iconColor="var(--gv-danger)"
            label={t('instructor.dashKpiAtRisk')} value={highRiskCount ?? '—'}
          >
            <span className="gv-meta">{classSize > 0 ? `${classSize} ${t('instructor.studentsUnit')}` : t('instructor.dashNoTrend')}</span>
          </KpiCard>

          <KpiCard
            icon={Clock} iconBg="var(--gv-amber-soft)" iconColor="var(--gv-amber)"
            label={t('instructor.dashKpiOverdue')} value={overdueCount ?? '—'}
          >
            <span className="gv-meta">{t('instructor.dashNoTrend')}</span>
          </KpiCard>

          <KpiCard
            icon={ShieldCheck} iconBg="var(--gv-amber-soft)" iconColor="var(--gv-amber)"
            label={t('instructor.dashKpiGuardrail')} value={guardrailPending ?? '—'}
          >
            <span className="gv-meta">{t('instructor.dashNoTrend')}</span>
          </KpiCard>

          <KpiCard
            icon={CircleCheckBig} iconBg="var(--gv-teal-soft)" iconColor="var(--gv-teal)"
            label={t('instructor.dashKpiCompletion')}
            value={completion.value === null ? '—' : `${completion.value}%`}
          >
            <Delta
              value={completion.delta} unit="%" goodWhenUp
              label={completion.delta === null ? t('instructor.dashNoTrend') : t('instructor.dashVsLastWeek')}
            />
          </KpiCard>
        </div>

        {/* ── Can chu y ngay | Thong bao + Thao tac nhanh ─────────── */}
        <div className="grid grid-cols-1 xl:grid-cols-[55fr_45fr]" style={{ gap: 16 }}>

          <section className="gv-panel p-6 min-w-0">
            <div className="flex items-center justify-between gap-3 mb-4">
              <h2 className="gv-section-title">{t('instructor.dashAttention')}</h2>
              <button type="button" className="gv-link" onClick={() => navigate('/instructor/risks')}>
                {t('instructor.dashViewAll')} <ChevronRight size={15} />
              </button>
            </div>

            {attention.length === 0 ? (
              <EmptyState title={t('instructor.dashNoAttention')} />
            ) : (
              <table className="w-full" style={{ borderCollapse: 'collapse' }}>
                <thead>
                  <tr>
                    <th className="gv-th">{t('instructor.dashColStudent')}</th>
                    <th className="gv-th">{t('instructor.dashColRisk')}</th>
                    <th className="gv-th">{t('instructor.dashColReason')}</th>
                    <th className="gv-th" style={{ textAlign: 'right' }}>{t('instructor.dashColUpdated')}</th>
                  </tr>
                </thead>
                <tbody>
                  {attention.map((row) => (
                    <tr key={row.id} className="gv-row">
                      <td className="gv-td" style={{ paddingRight: 12 }}>
                        <button
                          type="button"
                          className="flex items-center gap-2.5 text-left min-w-0 cursor-pointer"
                          onClick={() => navigate(`/instructor/students/${row.studentId}`)}
                        >
                          <UserCircle2 size={30} style={{ color: 'var(--gv-text-2)', flex: '0 0 auto' }} />
                          <span className="min-w-0">
                            <span className="block truncate" style={{ fontWeight: 600 }}>{row.studentAlias}</span>
                            <span className="block gv-meta truncate">
                              {courses.find((c) => c.id === row.courseId)?.code || '—'}
                            </span>
                          </span>
                        </button>
                      </td>
                      <td className="gv-td" style={{ paddingRight: 12 }}>
                        <span className={`gv-badge gv-badge--${riskTone(row.riskLevel)}`}>
                          {riskLevelLabel(t, row.riskLevel)}
                        </span>
                      </td>
                      <td className="gv-td" style={{ paddingRight: 12 }}>
                        <span className="block" style={{
                          display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden',
                        }}>
                          {row.assignmentTitle}
                        </span>
                        {row.isOverdue && (
                          <span className="gv-meta" style={{ color: 'var(--gv-danger)', fontWeight: 600 }}>
                            {row.daysOpen} {t('instructor.dashWeekShort').toLowerCase() === 'week' ? 'days open' : 'ngày chưa xử lý'}
                          </span>
                        )}
                      </td>
                      <td className="gv-td gv-meta" style={{ textAlign: 'right', whiteSpace: 'nowrap' }}>
                        {formatDateTime(row.generatedAt, lang)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>

          <div className="flex flex-col min-w-0" style={{ gap: 16 }}>
            <section className="gv-panel p-6">
              <div className="flex items-center justify-between gap-3 mb-4">
                <h2 className="gv-section-title">{t('instructor.dashAdminNotices')}</h2>
              </div>

              {announcements.length === 0 ? (
                <EmptyState title={t('instructor.dashNoNotices')} />
              ) : (
                <ul className="flex flex-col" style={{ gap: 12 }}>
                  {announcements.map((notice, index) => {
                    const Icon = [Megaphone, FileText, Shield][index % 3];
                    return (
                      <li key={notice.id} className="gv-card p-4 flex items-start gap-3">
                        <span className="gv-kpi-icon" style={{ width: 38, height: 38, background: 'var(--gv-teal-soft)' }}>
                          <Icon size={17} style={{ color: 'var(--gv-teal)' }} />
                        </span>
                        <div className="min-w-0 flex-1">
                          <div className="flex items-start justify-between gap-3">
                            <p className="gv-card-title truncate">{notice.title}</p>
                            <span className="gv-meta shrink-0">{formatDateTime(notice.createdAt, lang)}</span>
                          </div>
                          <p className="gv-body-sm gv-muted mt-1" style={{
                            display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden',
                          }}>
                            {notice.content}
                          </p>
                        </div>
                      </li>
                    );
                  })}
                </ul>
              )}
            </section>

            <section className="gv-panel p-6">
              <h2 className="gv-section-title mb-4">{t('instructor.dashQuickActions')}</h2>
              <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-5" style={{ gap: 12 }}>
                {quickActions.map((action) => (
                  <button
                    key={action.key}
                    type="button"
                    className="gv-quick"
                    onClick={action.onClick}
                    disabled={busyAction === action.key}
                  >
                    <action.icon size={19} style={{ color: 'var(--gv-teal)' }} />
                    <span>{action.label}</span>
                  </button>
                ))}
              </div>
              {actionMessage && (
                <p
                  className="gv-body-sm mt-3"
                  style={{ color: actionMessage.tone === 'ok' ? 'var(--gv-success)' : 'var(--gv-danger)' }}
                >
                  {actionMessage.text}
                </p>
              )}
            </section>
          </div>
        </div>

        {/* ── Suc khoe lop | So sanh cac lop ──────────────────────── */}
        <div className="grid grid-cols-1 xl:grid-cols-2" style={{ gap: 16 }}>
          <section className="gv-panel p-6 min-w-0">
            <div className="flex items-center justify-between gap-3 mb-2">
              <h2 className="gv-section-title">{t('instructor.dashHealth')}</h2>
              <span className="gv-meta">{t('instructor.dashHealthMetric')}</span>
            </div>
            <ClassHealthChart points={weeklyRates} t={t} />
          </section>

          <section className="gv-panel p-6 min-w-0">
            <div className="flex items-center justify-between gap-3 mb-4">
              <h2 className="gv-section-title">{t('instructor.compareTitle')}</h2>
              <button type="button" className="gv-link" onClick={() => navigate('/instructor/risks')}>
                {t('instructor.dashViewAll')} <ChevronRight size={15} />
              </button>
            </div>

            <div style={{ overflowX: 'auto' }}>
              <table className="w-full" style={{ borderCollapse: 'collapse', minWidth: 420 }}>
                <thead>
                  <tr>
                    <th className="gv-th">{t('instructor.compareColClass')}</th>
                    <th className="gv-th" style={{ textAlign: 'right' }}>{t('instructor.compareColSize')}</th>
                    <th className="gv-th" style={{ textAlign: 'right' }}>{t('instructor.compareColCompletion')}</th>
                    <th className="gv-th" style={{ textAlign: 'right' }}>{t('instructor.compareColHighRisk')}</th>
                    <th className="gv-th" style={{ textAlign: 'right' }}>{t('instructor.compareColOverdue')}</th>
                  </tr>
                </thead>
                <tbody>
                  {comparison.map((row) => (
                    <tr key={row.courseId} className="gv-row">
                      <td className="gv-td" style={{ paddingRight: 12, maxWidth: 190 }}>
                        <span className="block truncate" style={{ fontWeight: 600 }}>{row.code}</span>
                        <span className="block gv-meta truncate">{row.name}</span>
                      </td>
                      <td className="gv-td gv-meta" style={{ textAlign: 'right' }}>{row.classSize}</td>
                      <td className="gv-td" style={{ textAlign: 'right', fontWeight: 600, color: 'var(--gv-teal)' }}>
                        {/* Luu y don vi: classAvgCompletionByWeek la phan so 0-1,
                            nhung latestWeekCompletion o /classes/compare da duoc
                            backend nhan 100 san (instructor.py: round(w*100,1)).
                            Nhan them lan nua o day tung cho ra 2500%. */}
                        {row.latestWeekCompletion === null || row.latestWeekCompletion === undefined
                          ? '—' : `${Math.round(row.latestWeekCompletion)}%`}
                      </td>
                      <td className="gv-td" style={{ textAlign: 'right', fontWeight: 600, color: row.highRiskCount ? 'var(--gv-danger)' : 'inherit' }}>
                        {row.highRiskCount}
                      </td>
                      <td className="gv-td" style={{ textAlign: 'right', fontWeight: 600, color: row.overdueCount ? 'var(--gv-amber)' : 'inherit' }}>
                        {row.overdueCount}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {comparison.length === 0 && (
                <EmptyState title={t('instructor.dashHealthEmpty')} />
              )}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
