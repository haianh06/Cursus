import React, { useEffect, useMemo, useState } from 'react';
import {
  Check, ShieldOff, Eye, UserCircle2, Download, Users,
} from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import {
  exportInstructorReport, getInstructorAlerts, getInstructorDashboard,
  reviewAlert, userFacingApiError,
} from '../../lib/api';
import { riskLevelLabel, riskTypeLabel, formatDetectedAt } from '../../lib/riskLabels';
import RiskCaseDrawer from './RiskCaseDrawer';
import { GvStickyHeader, GvPager, usePaged } from './GvChrome';
import ErrorState from '../shared/ErrorState';
import EmptyState from '../shared/EmptyState';

/**
 * Rui ro & Canh bao — man quan ly CASE, khong phai danh sach sinh vien.
 *
 * Bo cuc: header + mot thanh bo loc duy nhat + hai cot "Chua xu ly" /
 * "Da xu ly". The case chi mang thong tin tom tat (ten, lop, muc rui ro,
 * qua han, MOT dong ly do, sparkline 3 tuan); toan bo bang chung day du
 * nam trong drawer ben phai. Mau do chi dung cho muc cao va qua han —
 * khong to ca the mau nguy hiem.
 */

function riskTone(level) {
  const value = String(level || '').toUpperCase();
  if (value === 'HIGH') return 'danger';
  if (value === 'MEDIUM') return 'amber';
  return 'teal';
}

const SPARK_W = 260;
const SPARK_H = 62;

/** Sparkline 3 diem tuan tren the case — chi 3 diem theo spec. */
function CaseSparkline({ rates }) {
  if (!rates || rates.length < 2) return null;
  const padX = 20;
  const padY = 16;
  const innerW = SPARK_W - padX * 2;
  const innerH = SPARK_H - padY * 2;
  const x = (i) => padX + (i * innerW) / (rates.length - 1);
  const y = (v) => padY + innerH - (Math.max(0, Math.min(100, v)) / 100) * innerH;
  const falling = rates[rates.length - 1] < rates[0];
  const stroke = falling ? 'var(--gv-danger)' : 'var(--gv-teal)';

  return (
    // Khong dung `w-full`: keo gian viewBox se phong to luon chu ben trong
    // (12.5px -> ~29px o the case rong 600px), lam vo thang chu va de chu.
    <svg viewBox={`0 0 ${SPARK_W} ${SPARK_H}`} width={SPARK_W} height={SPARK_H}
      preserveAspectRatio="xMinYMid meet"
      style={{ maxWidth: '100%', display: 'block' }} aria-hidden="true">
      <path
        d={rates.map((r, i) => `${i === 0 ? 'M' : 'L'} ${x(i)} ${y(r)}`).join(' ')}
        fill="none" stroke={stroke} strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"
      />
      {rates.map((r, i) => {
        const anchor = i === 0 ? 'start' : i === rates.length - 1 ? 'end' : 'middle';
        const lx = x(i) + (i === 0 ? -4 : i === rates.length - 1 ? 4 : 0);
        return (
          <g key={i}>
            <circle cx={x(i)} cy={y(r)} r="3" fill="var(--gv-card)" stroke={stroke} strokeWidth="1.75" />
            <text x={lx} y={y(r) - 7} textAnchor={anchor} fontSize="12.5" fontWeight="600" fill={stroke}>
              {Math.round(r)}%
            </text>
          </g>
        );
      })}
    </svg>
  );
}

function CaseCard({ risk, resolved, selected, onOpen, onDecide, busy, t, lang, courseCode }) {
  const rates = Array.isArray(risk.evidence?.completionRates) ? risk.evidence.completionRates : null;

  return (
    <div className={`gv-case ${selected ? 'gv-case--selected' : ''} ${resolved ? 'gv-case--done' : ''}`}>
      <div className="flex items-start justify-between gap-3">
        <button type="button" className="flex items-center gap-2.5 min-w-0 text-left cursor-pointer"
          onClick={onOpen}>
          <UserCircle2 size={30} style={{ color: 'var(--gv-text-2)', flex: '0 0 auto' }} />
          <span className="min-w-0">
            <span className="block gv-card-title truncate">{risk.studentAlias}</span>
            <span className="block gv-meta truncate">
              {riskTypeLabel(t, risk.riskType, lang)} · {courseCode || '—'}
            </span>
          </span>
        </button>
        <div className="flex flex-col items-end gap-1.5 shrink-0">
          <span className={`gv-badge gv-badge--${riskTone(risk.riskLevel)}`}>
            {riskLevelLabel(t, risk.riskLevel)}
          </span>
          {!resolved && risk.isOverdue && (
            <span className="gv-meta" style={{ color: 'var(--gv-danger)', fontWeight: 600 }}>
              {t('instructor.riskOverdueLabel')} {risk.daysOpen} {t('instructor.daysOpenUnit')}
            </span>
          )}
          {resolved && (
            <span className="gv-meta">{formatDetectedAt(risk.generatedAt, lang)}</span>
          )}
        </div>
      </div>

      {/* Mot dong ly do chinh — bang chung day du o drawer */}
      <p className="gv-body-sm" style={{
        display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden',
      }}>
        {risk.evidence?.reason || risk.assignmentTitle || '—'}
      </p>

      {rates && rates.length >= 2 && (
        <div>
          <p className="gv-meta">{t('instructor.riskTrend3w')}</p>
          <CaseSparkline rates={rates} />
        </div>
      )}

      <div className="flex items-center justify-between gap-2 flex-wrap">
        <button type="button" className="gv-link" onClick={onOpen}>
          <Eye size={15} /> {t('instructor.riskViewDetail')}
        </button>

        {resolved ? (
          <span className="gv-meta">{t('instructor.riskHandledBy')}</span>
        ) : (
          <span className="flex items-center gap-2">
            <button type="button" className="gv-btn gv-btn--teal" style={{ padding: '8px 12px' }}
              disabled={busy} onClick={() => onDecide(risk, 'APPROVE')}>
              <Check size={15} /> {t('instructor.markInterveneBtn')}
            </button>
            <button type="button" className="gv-btn gv-btn--ghost" style={{ padding: '8px 12px' }}
              disabled={busy} onClick={() => onDecide(risk, 'REJECT')}>
              <ShieldOff size={15} /> {t('instructor.dismissAlertBtn')}
            </button>
          </span>
        )}
      </div>
    </div>
  );
}

export default function InstructorRiskPage() {
  const { t, lang } = useLanguage();

  const [alerts, setAlerts] = useState([]);
  const [courses, setCourses] = useState([]);
  const [selectedCourseId, setSelectedCourseId] = useState('ALL');
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);

  const [levelFilter, setLevelFilter] = useState('ALL');
  const [typeFilter, setTypeFilter] = useState('ALL');
  const [timeFilter, setTimeFilter] = useState('7');
  const [sortBy, setSortBy] = useState('SEVERITY');

  const [openRiskId, setOpenRiskId] = useState(null);
  const [busyId, setBusyId] = useState(null);
  const [decisionError, setDecisionError] = useState(null);
  const [isExporting, setIsExporting] = useState(false);

  const load = async () => {
    setIsLoading(true);
    setLoadError(null);
    try {
      const [rows, dashboard] = await Promise.all([
        getInstructorAlerts(selectedCourseId),
        getInstructorDashboard(selectedCourseId).catch(() => ({ courses: [] })),
      ]);
      setAlerts(rows || []);
      setCourses(dashboard.courses || []);
    } catch (err) {
      setLoadError(userFacingApiError(err).message);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedCourseId]);

  // `studentAlias`/`courseId` tu API la ID tho — doi sang ma lop cho de doc.
  const courseCodeById = useMemo(
    () => new Map(courses.map((c) => [c.id, c.code])),
    [courses]
  );

  const riskTypes = useMemo(
    () => [...new Set(alerts.map((row) => row.riskType).filter(Boolean))],
    [alerts]
  );

  const filtered = useMemo(() => {
    const now = Date.now();
    const windowMs = timeFilter === 'ALL' ? null : Number(timeFilter) * 86400e3;
    const rank = { HIGH: 2, MEDIUM: 1, LOW: 0 };

    return alerts
      .filter((row) => levelFilter === 'ALL' || String(row.riskLevel).toUpperCase() === levelFilter)
      .filter((row) => typeFilter === 'ALL' || row.riskType === typeFilter)
      .filter((row) => {
        if (!windowMs) return true;
        const at = new Date(row.generatedAt).getTime();
        return Number.isNaN(at) ? true : now - at <= windowMs;
      })
      .sort((a, b) => {
        if (sortBy === 'NEWEST') return new Date(b.generatedAt || 0) - new Date(a.generatedAt || 0);
        if (sortBy === 'OVERDUE') return (b.daysOpen || 0) - (a.daysOpen || 0);
        if (Boolean(b.isOverdue) !== Boolean(a.isOverdue)) {
          return Boolean(b.isOverdue) - Boolean(a.isOverdue);
        }
        return (rank[b.riskLevel] || 0) - (rank[a.riskLevel] || 0);
      });
  }, [alerts, levelFilter, typeFilter, timeFilter, sortBy]);

  const unresolved = filtered.filter((row) => row.status === 'INTERVENTION_PENDING');
  const resolved = filtered.filter((row) => row.status !== 'INTERVENTION_PENDING');
  const openRisk = alerts.find((row) => row.id === openRiskId) || null;

  // Hai cot phan trang doc lap — "chua xu ly" thuong dai gap nhieu lan "da
  // xu ly", ep chung mot chi so trang se lam cot ngan nhay trang trong.
  const unresolvedPage = usePaged(unresolved, 5);
  const resolvedPage = usePaged(resolved, 5);

  const decide = async (risk, decision, note = null) => {
    setBusyId(risk.id);
    setDecisionError(null);
    try {
      await reviewAlert(risk.id, decision, note || null);
      setOpenRiskId(null);
      await load();
    } catch (err) {
      setDecisionError(userFacingApiError(err).message);
    } finally {
      setBusyId(null);
    }
  };

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
      setDecisionError(userFacingApiError(err).message);
    } finally {
      setIsExporting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="gv-ui p-7 space-y-4 animate-pulse">
        <div className="gv-panel" style={{ height: 92 }} />
        <div className="gv-card" style={{ height: 74 }} />
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          <div className="gv-panel" style={{ height: 300 }} />
          <div className="gv-panel" style={{ height: 300 }} />
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
      {/* Tieu de va thanh bo loc ghim cung nhau: bo loc la thu giang vien
          doi lien tuc khi doc danh sach dai, cuon mat no la mat luon ngu canh. */}
      <GvStickyHeader>
        <header className="gv-panel px-6 py-5 flex flex-col xl:flex-row xl:items-end gap-4">
          <div className="min-w-0 flex-1">
            <h1 className="gv-page-title">{t('instructor.riskPageTitle')}</h1>
            <p className="gv-body-sm gv-muted mt-1.5">{t('instructor.riskPageSubtitle')}</p>
          </div>
          <label className="block shrink-0" style={{ width: 260 }}>
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
        </header>

        {/* Mot thanh bo loc duy nhat */}
        <div className="gv-filterbar">
          <label style={{ width: 170 }}>
            <span className="gv-field-label">{t('instructor.riskFilterLevel')}</span>
            <select className="gv-select" value={levelFilter} onChange={(e) => setLevelFilter(e.target.value)}>
              <option value="ALL">{t('instructor.riskFilterAll')}</option>
              <option value="HIGH">{riskLevelLabel(t, 'HIGH')}</option>
              <option value="MEDIUM">{riskLevelLabel(t, 'MEDIUM')}</option>
              <option value="LOW">{riskLevelLabel(t, 'LOW')}</option>
            </select>
          </label>

          <label style={{ width: 190 }}>
            <span className="gv-field-label">{t('instructor.riskFilterType')}</span>
            <select className="gv-select" value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}>
              <option value="ALL">{t('instructor.riskFilterAll')}</option>
              {riskTypes.map((type) => (
                <option key={type} value={type}>{riskTypeLabel(t, type, lang)}</option>
              ))}
            </select>
          </label>

          <label style={{ width: 160 }}>
            <span className="gv-field-label">{t('instructor.riskFilterTime')}</span>
            <select className="gv-select" value={timeFilter} onChange={(e) => setTimeFilter(e.target.value)}>
              <option value="7">{t('instructor.riskTime7')}</option>
              <option value="30">{t('instructor.riskTime30')}</option>
              <option value="ALL">{t('instructor.riskTimeAll')}</option>
            </select>
          </label>

          <label style={{ width: 230 }}>
            <span className="gv-field-label">{t('instructor.riskFilterSort')}</span>
            <select className="gv-select" value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
              <option value="SEVERITY">{t('instructor.riskSortSeverity')}</option>
              <option value="NEWEST">{t('instructor.riskSortNewest')}</option>
              <option value="OVERDUE">{t('instructor.riskSortOverdue')}</option>
            </select>
          </label>

          <button type="button" className="gv-btn gv-btn--ghost gv-ctl" style={{ marginLeft: 'auto' }}
            onClick={handleExport} disabled={isExporting}>
            <Download size={16} /> {t('instructor.exportBtn')}
          </button>
        </div>
      </GvStickyHeader>

      <div className="gv-page__body">
        {decisionError && !openRisk && (
          <p className="gv-body-sm" style={{ color: 'var(--gv-danger)' }}>{decisionError}</p>
        )}

        {/* Chua xu ly | Da xu ly */}
        <div className="grid grid-cols-1 xl:grid-cols-2 items-start" style={{ gap: 16 }}>
          <section className="gv-panel p-5 min-w-0">
            <div className="flex items-center gap-2 mb-4">
              <h2 className="gv-section-title">{t('instructor.riskColUnresolved')}</h2>
              <span className="gv-badge gv-badge--danger">{unresolved.length}</span>
            </div>
            {unresolved.length === 0 ? (
              <EmptyState title={t('instructor.riskNoUnresolved')} />
            ) : (
              <div className="flex flex-col" style={{ gap: 12 }}>
                {unresolvedPage.slice.map((risk) => (
                  <CaseCard
                    key={risk.id} risk={risk} resolved={false}
                    selected={openRiskId === risk.id}
                    onOpen={() => { setDecisionError(null); setOpenRiskId(risk.id); }}
                    onDecide={decide} busy={busyId === risk.id} t={t} lang={lang}
                    courseCode={courseCodeById.get(risk.courseId)}
                  />
                ))}
              </div>
            )}
            <GvPager {...unresolvedPage} onChange={unresolvedPage.setPage}
              label={t('instructor.riskColUnresolved')} />
          </section>

          <section className="gv-panel p-5 min-w-0">
            <div className="flex items-center gap-2 mb-4">
              <h2 className="gv-section-title">{t('instructor.riskColResolved')}</h2>
              <span className="gv-badge gv-badge--neutral">{resolved.length}</span>
            </div>
            {resolved.length === 0 ? (
              <EmptyState title={t('instructor.riskNoResolved')} />
            ) : (
              <div className="flex flex-col" style={{ gap: 12 }}>
                {resolvedPage.slice.map((risk) => (
                  <CaseCard
                    key={risk.id} risk={risk} resolved
                    selected={openRiskId === risk.id}
                    onOpen={() => { setDecisionError(null); setOpenRiskId(risk.id); }}
                    onDecide={decide} busy={busyId === risk.id} t={t} lang={lang}
                    courseCode={courseCodeById.get(risk.courseId)}
                  />
                ))}
              </div>
            )}
            <GvPager {...resolvedPage} onChange={resolvedPage.setPage}
              label={t('instructor.riskColResolved')} />
          </section>
        </div>
      </div>

      {openRisk && (
        <RiskCaseDrawer
          risk={openRisk}
          onClose={() => setOpenRiskId(null)}
          onDecide={(decision, note) => decide(openRisk, decision, note)}
          isSubmitting={busyId === openRisk.id}
          decisionError={decisionError}
        />
      )}
    </div>
  );
}
