import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  X, Lightbulb, Check, ShieldOff, ChevronRight, Loader2, Lock,
} from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import {
  getInterventionHistory, getStudentProfile, userFacingApiError,
} from '../../lib/api';
import { riskLevelLabel, riskTypeLabel, formatDetectedAt } from '../../lib/riskLabels';

/**
 * Drawer chi tiet mot case rui ro — bang chung day du nam o day, khong nam
 * tren the case ngoai danh sach ("detail/evidence belongs in drawers").
 *
 * Cac muc: tien do 3 tuan, tom tat phan tu, lich su can thiep, goi y hanh
 * dong, roi den phan quyet dinh. Anh mau con hai muc "Bai hoc/Nhiem vu bi
 * bo lo" va "Bai nop gan nhat"; API hien tai khong tra ve hai so lieu do
 * (`/instructor/students/{id}/profile` chi co weeklyCompletionHistory,
 * riskHistory, guardrailHistory, notes, reflectionSummary) nen chua dung —
 * dat cho san o day khi backend bo sung.
 */

const SPARK_W = 330;
const SPARK_H = 96;

function Sparkline({ points }) {
  if (points.length < 2) return null;
  const padX = 16;
  const padY = 22;
  const innerW = SPARK_W - padX * 2;
  const innerH = SPARK_H - padY * 2;
  const max = 100;
  const x = (i) => padX + (i * innerW) / (points.length - 1);
  const y = (v) => padY + innerH - (Math.max(0, Math.min(max, v)) / max) * innerH;
  const falling = points[points.length - 1].rate < points[0].rate;
  const stroke = falling ? 'var(--gv-danger)' : 'var(--gv-teal)';

  return (
    <svg viewBox={`0 0 ${SPARK_W} ${SPARK_H}`} width={SPARK_W} height={SPARK_H}
      preserveAspectRatio="xMinYMid meet"
      style={{ maxWidth: '100%', display: 'block' }}>
      <path
        d={points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${x(i)} ${y(p.rate)}`).join(' ')}
        fill="none" stroke={stroke} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
      />
      {points.map((p, i) => {
        const anchor = i === 0 ? 'start' : i === points.length - 1 ? 'end' : 'middle';
        const lx = x(i) + (i === 0 ? -2 : i === points.length - 1 ? 2 : 0);
        return (
          <g key={p.label}>
            <circle cx={x(i)} cy={y(p.rate)} r="3.5" fill="var(--gv-card)" stroke={stroke} strokeWidth="2" />
            <text x={lx} y={y(p.rate) - 9} textAnchor={anchor} fontSize="12.5" fontWeight="600" fill={stroke}>
              {Math.round(p.rate)}%
            </text>
            <text x={lx} y={SPARK_H - 4} textAnchor={anchor} fontSize="12.5" fill="var(--gv-text-2)">
              {p.label}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

export default function RiskCaseDrawer({ risk, onClose, onDecide, isSubmitting, decisionError }) {
  const { t, lang } = useLanguage();
  const [history, setHistory] = useState([]);
  const [profile, setProfile] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [note, setNote] = useState('');

  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    setLoadError(null);
    setNote('');
    Promise.all([
      getInterventionHistory(risk.id).catch(() => ({ interventions: [] })),
      risk.studentId ? getStudentProfile(risk.studentId).catch(() => null) : Promise.resolve(null),
    ])
      .then(([hist, prof]) => {
        if (cancelled) return;
        setHistory(hist?.interventions || hist || []);
        setProfile(prof);
      })
      .catch((err) => { if (!cancelled) setLoadError(userFacingApiError(err).message); })
      .finally(() => { if (!cancelled) setIsLoading(false); });
    return () => { cancelled = true; };
  }, [risk.id, risk.studentId]);

  // Uu tien chuoi tuan nam ngay trong evidence cua chinh case (dung 3 tuan
  // ma luat rui ro da dung de ket luan); neu khong co thi lay lich su chung
  // cua sinh vien tu ho so.
  const evidenceRates = Array.isArray(risk.evidence?.completionRates)
    ? risk.evidence.completionRates
    : null;
  const evidenceWeeks = Array.isArray(risk.evidence?.weekNumbers) ? risk.evidence.weekNumbers : null;

  let points = [];
  if (evidenceRates && evidenceRates.length >= 2) {
    points = evidenceRates.map((rate, i) => ({
      rate,
      label: evidenceWeeks?.[i] != null
        ? `${t('instructor.dashWeekShort')} ${evidenceWeeks[i]}`
        : `${t('instructor.dashWeekShort')} ${i + 1}`,
    }));
  } else if (profile?.weeklyCompletionHistory?.length >= 2) {
    points = profile.weeklyCompletionHistory.slice(-3).map((row) => ({
      rate: row.rate,
      label: `${t('instructor.dashWeekShort')} ${row.week}`,
    }));
  }

  const trend = points.length >= 2
    ? Math.round(points[points.length - 1].rate - points[0].rate)
    : null;

  const noteRequired = false;

  return (
    <>
      <div className="gv-drawer__scrim" onClick={onClose} aria-hidden="true" />
      <aside className="gv-drawer" role="dialog" aria-label={risk.studentAlias}>
        <header className="gv-drawer__head">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <h2 className="gv-section-title truncate">{risk.studentAlias}</h2>
                <span className={`gv-badge gv-badge--${
                  String(risk.riskLevel).toUpperCase() === 'HIGH' ? 'danger'
                    : String(risk.riskLevel).toUpperCase() === 'MEDIUM' ? 'amber' : 'teal'}`}
                >
                  {riskLevelLabel(t, risk.riskLevel)}
                </span>
              </div>
              <p className="gv-meta mt-1">
                {riskTypeLabel(t, risk.riskType, lang)}
                {profile?.courses?.length ? ` · ${profile.courses.map((c) => c.code).join(', ')}` : ''}
              </p>
            </div>
            <button type="button" className="gv-btn gv-btn--ghost" style={{ padding: 8 }}
              onClick={onClose} aria-label={t('common.close')}>
              <X size={16} />
            </button>
          </div>
        </header>

        <div className="gv-drawer__body flex flex-col" style={{ gap: 20 }}>
          {isLoading && (
            <p className="gv-body-sm gv-muted flex items-center gap-2">
              <Loader2 size={15} className="animate-spin" /> {t('states.loadingTitle')}
            </p>
          )}
          {loadError && <p className="gv-body-sm" style={{ color: 'var(--gv-danger)' }}>{loadError}</p>}

          {/* 1. Tien do hoc tap */}
          {points.length >= 2 && (
            <section>
              <p className="gv-sec-label">1. {t('instructor.drawerProgress')}</p>
              <div className="gv-stat">
                <div className="flex items-baseline justify-between gap-3">
                  <span className="gv-body-sm gv-muted">{t('instructor.drawerProgressHint')}</span>
                  {trend !== null && (
                    <span style={{
                      fontSize: 19, fontWeight: 700,
                      color: trend < 0 ? 'var(--gv-danger)' : 'var(--gv-success)',
                    }}>
                      {trend > 0 ? '+' : ''}{trend}%
                    </span>
                  )}
                </div>
                <Sparkline points={points} />
              </div>
            </section>
          )}

          {/* 2. Ly do he thong danh dau */}
          <section>
            <p className="gv-sec-label">2. {t('instructor.drawerReason')}</p>
            <p className="gv-body-sm">{risk.evidence?.reason || risk.assignmentTitle || '—'}</p>
            <p className="gv-meta mt-2">
              {t('instructor.detectedAtLabel')}: {formatDetectedAt(risk.generatedAt, lang)}
              {risk.isOverdue && ` · ${risk.daysOpen} ${t('instructor.daysOpenUnit')}`}
            </p>
          </section>

          {/* 3. Tom tat phan tu — chi hien khi sinh vien da dong y chia se */}
          <section>
            <p className="gv-sec-label">3. {t('instructor.drawerReflection')}</p>
            {risk.evidence?.noteWithheld || (profile && !profile.reflectionSharingEnabled) ? (
              <p className="gv-body-sm gv-muted flex items-start gap-2">
                <Lock size={14} className="mt-0.5 shrink-0" />
                {t('instructor.reflectionWithheld')}
              </p>
            ) : (
              <p className="gv-quote">
                {risk.evidence?.note || profile?.reflectionSummary || t('instructor.drawerNoReflection')}
              </p>
            )}
          </section>

          {/* 4. Lich su can thiep */}
          <section>
            <p className="gv-sec-label">4. {t('instructor.drawerHistory')}</p>
            {history.length === 0 ? (
              <p className="gv-body-sm gv-muted">{t('instructor.drawerNoHistory')}</p>
            ) : (
              <ul className="flex flex-col" style={{ gap: 8 }}>
                {history.map((item, index) => (
                  <li key={item.id || index} className="gv-stat">
                    <div className="flex items-center justify-between gap-2">
                      <span className="gv-body-sm" style={{ fontWeight: 600 }}>
                        {item.decision === 'REJECT'
                          ? t('instructor.dismissedBadge') : t('instructor.intervenedBadge')}
                      </span>
                      <span className="gv-meta">{formatDetectedAt(item.decidedAt || item.createdAt, lang)}</span>
                    </div>
                    {item.note && <p className="gv-body-sm gv-muted mt-1">{item.note}</p>}
                  </li>
                ))}
              </ul>
            )}
          </section>

          {/* 5. Goi y hanh dong — AI/he thong goi y, GV quyet dinh */}
          <section>
            <p className="gv-sec-label">5. {t('instructor.drawerSuggestion')}</p>
            <div className="gv-note flex items-start gap-2.5">
              <Lightbulb size={16} className="mt-0.5 shrink-0" style={{ color: 'var(--gv-amber)' }} />
              <span>{risk.recommendedIntervention || t('instructor.drawerNoSuggestion')}</span>
            </div>
            {risk.studentId && (
              <Link
                to={`/instructor/students/${risk.studentId}`}
                className="gv-link mt-3"
              >
                {t('instructor.viewFullProfileBtn')} <ChevronRight size={15} />
              </Link>
            )}
          </section>
        </div>

        <footer className="gv-drawer__foot">
          <label className="block">
            <span className="gv-field-label">{t('instructor.drawerNoteLabel')}</span>
            <textarea
              className="gv-textarea" rows={2} maxLength={500}
              value={note} onChange={(event) => setNote(event.target.value)}
              placeholder={t('instructor.drawerNotePlaceholder')}
            />
          </label>

          {decisionError && (
            <p className="gv-body-sm" style={{ color: 'var(--gv-danger)' }}>{decisionError}</p>
          )}

          {/* Mot CTA chinh duy nhat; "Bo qua" la hanh dong phu, nhe hon. */}
          <button
            type="button" className="gv-btn gv-btn--teal w-full"
            disabled={isSubmitting || noteRequired}
            onClick={() => onDecide('APPROVE', note)}
          >
            <Check size={16} /> {t('instructor.markInterveneBtn')}
          </button>
          <button
            type="button" className="gv-btn gv-btn--ghost w-full"
            disabled={isSubmitting}
            onClick={() => onDecide('REJECT', note)}
          >
            <ShieldOff size={16} /> {t('instructor.dismissAlertBtn')}
          </button>
          <p className="gv-meta">{t('instructor.decisionAuditNote')}</p>
        </footer>
      </aside>
    </>
  );
}
