import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Download, Users, Search, X, FileText,
  FileWarning, FileCheck2, CircleCheckBig, ChevronRight, Info,
} from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import { GvStickyHeader, GvPager, usePaged } from './GvChrome';
import ErrorState from '../shared/ErrorState';
import EmptyState from '../shared/EmptyState';
import {
  exportInstructorReport, getAssignmentSubmissions, getInstructorAlerts,
  getInstructorDashboard, listInstructorAssignments, userFacingApiError,
} from '../../lib/api';
import { riskLevelLabel, formatDetectedAt } from '../../lib/riskLabels';

/**
 * Bai tap nop — man data-heavy nen dung bang, khong dung luoi the.
 *
 * Bo cuc: header + mot thanh bo loc + 4 KPI thap + bang + drawer chi tiet.
 *
 * Chua co API cham diem bai tap cho giang vien (backend chi co
 * PATCH /instructor/quizzes/{id}/submissions/{id}/grade cho quiz), nen phan
 * "Phan hoi & cham diem" trong drawer la CHI DOC va CTA chinh chuyen thanh
 * "Xem ho so rui ro" — dat mot nut "Bat dau cham" khong co backend se la nut
 * chet.
 */

const STATUS = {
  NOT: 'NOT_SUBMITTED',
  LATE: 'LATE',
  ON_TIME: 'ON_TIME',
  GRADED: 'GRADED',
};

function rowStatus(row) {
  if (!row.submitted) return STATUS.NOT;
  if (String(row.gradingStatus || '').toUpperCase() === 'GRADED') return STATUS.GRADED;
  return row.isLate ? STATUS.LATE : STATUS.ON_TIME;
}

function statusTone(status) {
  if (status === STATUS.NOT) return 'neutral';
  if (status === STATUS.LATE) return 'danger';
  if (status === STATUS.GRADED) return 'teal';
  return 'teal';
}

function lateDays(row, dueDate) {
  if (!row.submitted || !row.submittedAt || !dueDate) return 0;
  const diff = new Date(row.submittedAt) - new Date(dueDate);
  return diff <= 0 ? 0 : Math.ceil(diff / 86400e3);
}

function KpiCard({ icon: Icon, iconBg, iconColor, label, value, share }) {
  return (
    <div className="gv-card p-4 flex items-center gap-3.5 min-w-0">
      <span className="gv-kpi-icon" style={{ width: 44, height: 44, background: iconBg }}>
        <Icon size={19} style={{ color: iconColor }} />
      </span>
      <div className="min-w-0">
        <p className="gv-body-sm gv-muted truncate" style={{ fontWeight: 500 }}>{label}</p>
        <p className="flex items-baseline gap-2">
          <span style={{ fontSize: 30, fontWeight: 700, lineHeight: 1.15 }}>{value}</span>
          {share !== null && <span className="gv-meta">{share}%</span>}
        </p>
      </div>
    </div>
  );
}

export default function AssignmentSubmissionsPanel() {
  const { t, lang } = useLanguage();

  const [courses, setCourses] = useState([]);
  const [selectedCourseId, setSelectedCourseId] = useState('ALL');
  const [assignments, setAssignments] = useState([]);
  const [selectedAssignmentId, setSelectedAssignmentId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [alerts, setAlerts] = useState([]);

  const [statusFilter, setStatusFilter] = useState('ALL');
  const [query, setQuery] = useState('');
  const [openStudentId, setOpenStudentId] = useState(null);

  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [isExporting, setIsExporting] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    setLoadError(null);
    Promise.all([
      getInstructorDashboard(selectedCourseId).catch(() => ({ courses: [] })),
      listInstructorAssignments(selectedCourseId).catch(() => ({ assignments: [] })),
      getInstructorAlerts(selectedCourseId).catch(() => []),
    ])
      .then(([dashboard, assignmentData, alertRows]) => {
        if (cancelled) return;
        setCourses(dashboard.courses || []);
        const list = assignmentData.assignments || assignmentData || [];
        // Sap theo han nop giam dan, va mo san bai DA den han gan nhat —
        // do la bai giang vien dang phai cham. Lay phan tu dau danh sach
        // API se roi vao mot bai tap tuong lai bat ky, khong co bai nop nao.
        const sorted = [...list].sort(
          (a, b) => new Date(b.dueDate || 0) - new Date(a.dueDate || 0)
        );
        const now = Date.now();
        const due = sorted.find((a) => new Date(a.dueDate || 0).getTime() <= now);
        setAssignments(sorted);
        setAlerts(alertRows || []);
        setSelectedAssignmentId((due || sorted[0])?.id ?? null);
      })
      .catch((err) => { if (!cancelled) setLoadError(userFacingApiError(err).message); })
      .finally(() => { if (!cancelled) setIsLoading(false); });
    return () => { cancelled = true; };
  }, [selectedCourseId]);

  useEffect(() => {
    if (!selectedAssignmentId) { setDetail(null); return undefined; }
    let cancelled = false;
    getAssignmentSubmissions(selectedAssignmentId)
      .then((data) => { if (!cancelled) setDetail(data); })
      .catch((err) => { if (!cancelled) setLoadError(userFacingApiError(err).message); });
    return () => { cancelled = true; };
  }, [selectedAssignmentId]);

  // useMemo de tham chieu mang on dinh giua cac lan render — neu khong
  // hai useMemo ben duoi se tinh lai moi render.
  const rows = useMemo(() => detail?.submissions || [], [detail]);
  const dueDate = detail?.dueDate || null;

  const counts = useMemo(() => {
    const acc = { [STATUS.NOT]: 0, [STATUS.LATE]: 0, [STATUS.ON_TIME]: 0, [STATUS.GRADED]: 0 };
    rows.forEach((row) => { acc[rowStatus(row)] += 1; });
    return acc;
  }, [rows]);

  const total = rows.length || 1;
  const share = (n) => Math.round((n / total) * 100);

  // Muc rui ro dang mo cua tung sinh vien — de cot "Lien quan rui ro".
  const riskByStudent = useMemo(() => {
    const map = new Map();
    alerts.filter((a) => a.status === 'INTERVENTION_PENDING').forEach((a) => {
      const rank = { HIGH: 2, MEDIUM: 1, LOW: 0 };
      const prev = map.get(a.studentId);
      if (!prev || (rank[a.riskLevel] || 0) > (rank[prev.level] || 0)) {
        map.set(a.studentId, { level: a.riskLevel, count: (prev?.count || 0) + 1 });
      } else {
        map.set(a.studentId, { ...prev, count: prev.count + 1 });
      }
    });
    return map;
  }, [alerts]);

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    return rows
      .filter((row) => statusFilter === 'ALL' || rowStatus(row) === statusFilter)
      .filter((row) => !q || String(row.displayName || '').toLowerCase().includes(q));
  }, [rows, statusFilter, query]);

  // 8 dong / trang: vua het chieu cao khung xem ma khong phai cuon bang.
  const rowsPage = usePaged(visible, 8);

  const openRow = rows.find((row) => row.studentId === openStudentId) || null;
  const openRisk = openRow ? riskByStudent.get(openRow.studentId) : null;

  const handleExport = async () => {
    setIsExporting(true);
    try {
      const { blob, filename } = await exportInstructorReport(selectedCourseId);
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setLoadError(userFacingApiError(err).message);
    } finally {
      setIsExporting(false);
    }
  };

  const statusLabel = (status) => ({
    [STATUS.NOT]: t('instructor.subStatusNot'),
    [STATUS.LATE]: t('instructor.subStatusLate'),
    [STATUS.ON_TIME]: t('instructor.subStatusOnTime'),
    [STATUS.GRADED]: t('instructor.subStatusGraded'),
  }[status]);

  if (isLoading) {
    return (
      <div className="gv-ui p-7 space-y-4 animate-pulse">
        <div className="gv-panel" style={{ height: 80 }} />
        <div className="gv-card" style={{ height: 74 }} />
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
          {[0, 1, 2, 3].map((i) => <div key={i} className="gv-card" style={{ height: 84 }} />)}
        </div>
        <div className="gv-panel" style={{ height: 340 }} />
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="gv-ui p-7">
        <ErrorState
          title={t('states.errorTitle')}
          description={loadError}
          onRetry={() => setSelectedCourseId((v) => v)}
          retryLabel={t('states.retryBtn')}
        />
      </div>
    );
  }

  return (
    <div className="gv-ui gv-page">
      <GvStickyHeader>
        <header className="gv-panel px-6 py-5">
          <h1 className="gv-page-title">{t('instructor.subPageTitle')}</h1>
        </header>

        <div className="gv-filterbar">
          <label style={{ width: 230 }}>
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

          <label style={{ width: 280 }}>
            <span className="gv-field-label">{t('instructor.subFilterAssignment')}</span>
            <select className="gv-select" value={selectedAssignmentId || ''}
              onChange={(e) => { setSelectedAssignmentId(e.target.value); setOpenStudentId(null); }}
              disabled={assignments.length === 0}>
              {assignments.length === 0 && <option value="">{t('instructor.subNoAssignment')}</option>}
              {assignments.map((a) => <option key={a.id} value={a.id}>{a.title}</option>)}
            </select>
          </label>

          <label style={{ width: 175 }}>
            <span className="gv-field-label">{t('instructor.subFilterStatus')}</span>
            <select className="gv-select" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
              <option value="ALL">{t('instructor.riskFilterAll')}</option>
              <option value={STATUS.NOT}>{t('instructor.subStatusNot')}</option>
              <option value={STATUS.LATE}>{t('instructor.subStatusLate')}</option>
              <option value={STATUS.ON_TIME}>{t('instructor.subStatusOnTime')}</option>
              <option value={STATUS.GRADED}>{t('instructor.subStatusGraded')}</option>
            </select>
          </label>

          <label style={{ width: 230 }}>
            <span className="gv-field-label">{t('instructor.subSearch')}</span>
            <span className="relative flex items-center">
              <Search size={15} className="absolute left-3 pointer-events-none" style={{ color: 'var(--gv-text-2)' }} />
              <input className="gv-select" style={{ paddingLeft: 34, cursor: 'text' }}
                value={query} onChange={(e) => setQuery(e.target.value)}
                placeholder={t('instructor.subSearch')} />
            </span>
          </label>

          <button type="button" className="gv-btn gv-btn--ghost gv-ctl" style={{ marginLeft: 'auto' }}
            onClick={handleExport} disabled={isExporting}>
            <Download size={16} /> {t('instructor.exportBtn')}
          </button>
        </div>
      </GvStickyHeader>

      <div className="gv-page__body">
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4" style={{ gap: 16 }}>
          <KpiCard icon={FileText} iconBg="#F2EFE7" iconColor="var(--gv-text-2)"
            label={t('instructor.subKpiNotSubmitted')} value={counts[STATUS.NOT]} share={share(counts[STATUS.NOT])} />
          <KpiCard icon={FileWarning} iconBg="var(--gv-danger-soft)" iconColor="var(--gv-danger)"
            label={t('instructor.subKpiLate')} value={counts[STATUS.LATE]} share={share(counts[STATUS.LATE])} />
          <KpiCard icon={FileCheck2} iconBg="var(--gv-teal-soft)" iconColor="var(--gv-teal)"
            label={t('instructor.subKpiOnTime')} value={counts[STATUS.ON_TIME]} share={share(counts[STATUS.ON_TIME])} />
          <KpiCard icon={CircleCheckBig} iconBg="var(--gv-teal-soft)" iconColor="var(--gv-success)"
            label={t('instructor.subKpiGraded')} value={counts[STATUS.GRADED]} share={share(counts[STATUS.GRADED])} />
        </div>

        <section className="gv-panel p-6 min-w-0">
          <h2 className="gv-section-title mb-4">
            {t('instructor.subListTitle')} ({visible.length})
          </h2>

          {visible.length === 0 ? (
            <EmptyState title={t('instructor.subEmpty')} />
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table className="w-full" style={{ borderCollapse: 'collapse', minWidth: 900 }}>
                <thead>
                  <tr>
                    <th className="gv-th">{t('instructor.subColStudent')}</th>
                    <th className="gv-th">{t('instructor.subColAssignment')}</th>
                    <th className="gv-th">{t('instructor.subColDue')}</th>
                    <th className="gv-th">{t('instructor.subColStatus')}</th>
                    <th className="gv-th" style={{ textAlign: 'right' }}>{t('instructor.subColLateDays')}</th>
                    <th className="gv-th" style={{ textAlign: 'right' }}>{t('instructor.subColGrade')}</th>
                    <th className="gv-th" style={{ textAlign: 'right' }}>{t('instructor.subColRisk')}</th>
                  </tr>
                </thead>
                <tbody>
                  {rowsPage.slice.map((row) => {
                    const status = rowStatus(row);
                    const late = lateDays(row, dueDate);
                    const risk = riskByStudent.get(row.studentId);
                    const selected = openStudentId === row.studentId;
                    return (
                      <tr
                        key={row.studentId}
                        className="gv-row cursor-pointer"
                        style={selected ? { background: 'var(--gv-teal-soft)' } : undefined}
                        onClick={() => setOpenStudentId(selected ? null : row.studentId)}
                      >
                        <td className="gv-td" style={{ paddingRight: 12, minHeight: 54 }}>
                          <span className="block truncate" style={{ fontWeight: 600, maxWidth: 190 }}>
                            {row.displayName}
                          </span>
                        </td>
                        <td className="gv-td" style={{ paddingRight: 12 }}>
                          <span className="block truncate" style={{ maxWidth: 220 }}>
                            {detail?.assignmentTitle || '—'}
                          </span>
                        </td>
                        <td className="gv-td gv-meta" style={{ paddingRight: 12, whiteSpace: 'nowrap' }}>
                          {formatDetectedAt(dueDate, lang)}
                        </td>
                        <td className="gv-td" style={{ paddingRight: 12 }}>
                          <span className={`gv-badge gv-badge--${statusTone(status)}`}>{statusLabel(status)}</span>
                        </td>
                        <td className="gv-td" style={{
                          textAlign: 'right', fontWeight: 600,
                          color: late > 0 ? 'var(--gv-danger)' : 'inherit',
                        }}>
                          {late || 0}
                        </td>
                        <td className="gv-td" style={{ textAlign: 'right', fontWeight: 600 }}>
                          {row.grade === null || row.grade === undefined ? '—' : row.grade}
                        </td>
                        <td className="gv-td" style={{ textAlign: 'right' }}>
                          {risk ? (
                            <span className={`gv-badge gv-badge--${
                              String(risk.level).toUpperCase() === 'HIGH' ? 'danger'
                                : String(risk.level).toUpperCase() === 'MEDIUM' ? 'amber' : 'teal'}`}>
                              {riskLevelLabel(t, risk.level)}
                            </span>
                          ) : <span className="gv-meta">—</span>}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
          <GvPager {...rowsPage} onChange={rowsPage.setPage}
            label={t('instructor.subListTitle')} />
        </section>
      </div>

      {openRow && (
        <>
          <div className="gv-drawer__scrim" onClick={() => setOpenStudentId(null)} aria-hidden="true" />
          <aside className="gv-drawer" role="dialog" aria-label={t('instructor.subDrawerTitle')}>
            <header className="gv-drawer__head flex items-start justify-between gap-3">
              <div className="min-w-0">
                <h2 className="gv-section-title truncate">{openRow.displayName}</h2>
                <p className="gv-meta mt-1 truncate">{detail?.assignmentTitle}</p>
              </div>
              <button type="button" className="gv-btn gv-btn--ghost" style={{ padding: 8 }}
                onClick={() => setOpenStudentId(null)} aria-label="Đóng">
                <X size={16} />
              </button>
            </header>

            <div className="gv-drawer__body flex flex-col" style={{ gap: 20 }}>
              <section>
                <p className="gv-sec-label">1. {t('instructor.subSecInfo')}</p>
                <div className="gv-stat flex flex-col" style={{ gap: 8 }}>
                  <div className="flex items-center justify-between gap-3">
                    <span className="gv-body-sm gv-muted">{t('instructor.subColStatus')}</span>
                    <span className={`gv-badge gv-badge--${statusTone(rowStatus(openRow))}`}>
                      {statusLabel(rowStatus(openRow))}
                    </span>
                  </div>
                  <div className="flex items-center justify-between gap-3">
                    <span className="gv-body-sm gv-muted">{t('instructor.subColDue')}</span>
                    <span className="gv-body-sm">{formatDetectedAt(dueDate, lang)}</span>
                  </div>
                  <div className="flex items-center justify-between gap-3">
                    <span className="gv-body-sm gv-muted">{t('instructor.subSubmittedAt')}</span>
                    <span className="gv-body-sm">
                      {openRow.submittedAt ? formatDetectedAt(openRow.submittedAt, lang) : '—'}
                      {lateDays(openRow, dueDate) > 0 && (
                        <span style={{ color: 'var(--gv-danger)', fontWeight: 600 }}>
                          {' '}({lateDays(openRow, dueDate)} {t('instructor.daysOpenUnit').split(' ')[0]})
                        </span>
                      )}
                    </span>
                  </div>
                  {openRow.content && (
                    <div className="flex items-center justify-between gap-3">
                      <span className="gv-body-sm gv-muted">{t('instructor.subLength')}</span>
                      <span className="gv-body-sm">
                        {String(openRow.content).trim().split(/\s+/).length} {t('instructor.subWords')}
                      </span>
                    </div>
                  )}
                </div>
              </section>

              <section>
                <p className="gv-sec-label">2. {t('instructor.subSecFeedback')}</p>
                <div className="gv-stat flex flex-col" style={{ gap: 8 }}>
                  <div className="flex items-center justify-between gap-3">
                    <span className="gv-body-sm gv-muted">{t('instructor.subGradeLabel')}</span>
                    <span className="gv-body-sm" style={{ fontWeight: 700 }}>
                      {openRow.grade === null || openRow.grade === undefined ? '— / 10' : `${openRow.grade} / 10`}
                    </span>
                  </div>
                  <p className="gv-body-sm gv-muted">
                    {openRow.feedback || t('instructor.subNoFeedback')}
                  </p>
                </div>
                <p className="gv-meta mt-2 flex items-start gap-1.5">
                  <Info size={13} className="mt-0.5 shrink-0" />
                  {t('instructor.subGradingUnavailable')}
                </p>
              </section>

              <section>
                <p className="gv-sec-label">3. {t('instructor.subSecRisk')}</p>
                {openRisk ? (
                  <div className="gv-stat flex flex-col" style={{ gap: 8 }}>
                    <div className="flex items-center justify-between gap-3">
                      <span className="gv-body-sm gv-muted">{t('instructor.subRiskLevelNow')}</span>
                      <span className={`gv-badge gv-badge--${
                        String(openRisk.level).toUpperCase() === 'HIGH' ? 'danger'
                          : String(openRisk.level).toUpperCase() === 'MEDIUM' ? 'amber' : 'teal'}`}>
                        {riskLevelLabel(t, openRisk.level)}
                      </span>
                    </div>
                    <div className="flex items-center justify-between gap-3">
                      <span className="gv-body-sm gv-muted">{t('instructor.subOpenAlerts')}</span>
                      <span className="gv-body-sm" style={{ fontWeight: 700 }}>{openRisk.count}</span>
                    </div>
                  </div>
                ) : (
                  <p className="gv-body-sm gv-muted">{t('instructor.subNoRisk')}</p>
                )}
              </section>
            </div>

            <footer className="gv-drawer__foot">
              <Link to={`/instructor/students/${openRow.studentId}`}
                className="gv-btn gv-btn--teal w-full">
                <ChevronRight size={16} /> {t('instructor.subViewRiskProfile')}
              </Link>
            </footer>
          </aside>
        </>
      )}
    </div>
  );
}
