import React, { useEffect, useRef, useState } from 'react';
import { X, AlertTriangle, CheckCircle, ShieldOff, FileText, Clock, Lock, RefreshCw, Info } from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import { getAlertDetail, getInterventionHistory } from '../../lib/api';
import { riskLevelLabel, riskTypeLabel, formatDetectedAt } from '../../lib/riskLabels';

/** Thời gian trượt ra/vào — khớp với duration-200 bên dưới. */
const SLIDE_MS = 220;

const FOCUSABLE = [
  'a[href]',
  'button:not([disabled])',
  'textarea:not([disabled])',
  'input:not([disabled])',
  'select:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(',');

function riskLevelBadgeClass(level) {
  const normalized = (level || '').toUpperCase();
  if (normalized === 'HIGH') return 'badge-danger';
  if (normalized === 'MEDIUM') return 'badge-warning';
  return 'badge-success';
}

function Row({ label, children }) {
  return (
    <div className="space-y-1">
      <p className="text-[10px] font-black uppercase tracking-wider text-fg-muted">{label}</p>
      <div className="text-xs text-fg font-medium">{children}</div>
    </div>
  );
}

/**
 * Risk Case Detail — bảng trượt từ phải, đúng mục 6.4: "bấm vào xem chi tiết".
 *
 * Nguồn dữ liệu: GET /instructor/risks/{id} (`getAlertDetail`) cho thông tin
 * case, GET /instructor/risks/{id}/interventions (`getInterventionHistory`)
 * cho lịch sử can thiệp — cả hai đều đã có `require_instructor_risk_owner`
 * ở backend nên GV không đọc được case của lớp mình không dạy
 * (src/security/ownership.py).
 *
 * Quyết định (Can thiệp/Bỏ qua) đi qua `onDecision` do component cha truyền
 * vào (InstructorRiskPage.jsx / InstructorStudentProfile.jsx) — dùng đúng
 * 1 đường ghi quyết định cho cả list và drawer, không tách riêng logic.
 */
export default function RiskCaseDrawer({
  riskId,
  open,
  onClose,
  decision,
  onDecision,
  anyDecisionPending,
  busyDecision,
  decisionError,
}) {
  const { t, lang } = useLanguage();

  const [detail, setDetail] = useState(null);
  const [history, setHistory] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [loadError, setLoadError] = useState(null);
  const [reloadToken, setReloadToken] = useState(0);
  const [noteDraft, setNoteDraft] = useState('');

  const [shouldRender, setShouldRender] = useState(open);
  const [slidIn, setSlidIn] = useState(false);

  const panelRef = useRef(null);
  const closeBtnRef = useRef(null);
  const lastFocusedRef = useRef(null);

  // Gắn/tháo khỏi DOM có độ trễ để còn kịp chạy hiệu ứng trượt.
  useEffect(() => {
    if (open) {
      setShouldRender(true);
      const raf = requestAnimationFrame(() => setSlidIn(true));
      return () => cancelAnimationFrame(raf);
    }
    setSlidIn(false);
    const timer = setTimeout(() => setShouldRender(false), SLIDE_MS);
    return () => clearTimeout(timer);
  }, [open]);

  /**
   * Nạp chi tiết + lịch sử can thiệp. Xoá sạch dữ liệu case cũ NGAY khi
   * riskId đổi, và bỏ qua response về muộn — nếu không, mở nhanh hai case
   * liên tiếp có thể khiến dữ liệu của case trước loé lên trong bảng của
   * case sau (lộ chéo).
   */
  useEffect(() => {
    if (!shouldRender) {
      setDetail(null);
      setHistory([]);
      setLoadError(null);
      setIsLoading(false);
      setNoteDraft('');
      return undefined;
    }

    if (!open || !riskId) {
      setIsLoading(false);
      return undefined;
    }

    setDetail(null);
    setHistory([]);
    setLoadError(null);
    setNoteDraft('');

    let cancelled = false;
    setIsLoading(true);

    Promise.all([getAlertDetail(riskId), getInterventionHistory(riskId).catch(() => [])])
      .then(([detailData, historyData]) => {
        if (!cancelled) {
          setDetail(detailData);
          setHistory(historyData || []);
        }
      })
      .catch((err) => {
        if (!cancelled) setLoadError(err.message);
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [open, riskId, reloadToken, shouldRender]);

  // Nhớ phần tử đang focus trước khi mở, trả lại đúng chỗ đó khi đóng.
  useEffect(() => {
    if (!open) return undefined;
    lastFocusedRef.current = document.activeElement;
    const raf = requestAnimationFrame(() => closeBtnRef.current?.focus());
    return () => {
      cancelAnimationFrame(raf);
      const target = lastFocusedRef.current;
      if (target && typeof target.focus === 'function') target.focus();
    };
  }, [open]);

  // Esc để đóng + giữ Tab quanh quẩn trong bảng (focus trap).
  useEffect(() => {
    if (!shouldRender) return undefined;

    const onKeyDown = (event) => {
      if (event.key === 'Escape') {
        event.stopPropagation();
        onClose();
        return;
      }
      if (event.key !== 'Tab') return;

      const panel = panelRef.current;
      if (!panel) return;
      const focusables = Array.from(panel.querySelectorAll(FOCUSABLE));
      if (focusables.length === 0) return;

      const first = focusables[0];
      const last = focusables[focusables.length - 1];

      if (!panel.contains(document.activeElement)) {
        event.preventDefault();
        (event.shiftKey ? last : first).focus();
        return;
      }

      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };

    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [shouldRender, onClose]);

  // Khoá cuộn nền suốt thời gian bảng còn trên màn hình, kể cả lúc đang trượt ra.
  useEffect(() => {
    if (!shouldRender) return undefined;
    const previous = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = previous;
    };
  }, [shouldRender]);

  if (!shouldRender) return null;

  // `status` chỉ phân biệt đã-xử-lý/chưa, không phân biệt được Can thiệp
  // hay Bỏ qua (cả hai đều set resolved_at) — resolutionType mới cho biết
  // chính xác. Ưu tiên quyết định trong phiên này (vừa bấm) hơn dữ liệu cũ.
  const backendDecision =
    detail?.resolutionType === 'INSTRUCTOR_REJECTED' ? 'REJECT'
    : (detail?.resolutionType === 'INSTRUCTOR_APPROVE' || detail?.resolutionType === 'INSTRUCTOR_EDIT') ? 'APPROVE'
    : null;
  const effectiveDecision = decision || backendDecision;
  const resolved = detail ? detail.status !== 'INTERVENTION_PENDING' || Boolean(effectiveDecision) : false;

  const dateFormatter = new Intl.DateTimeFormat(lang === 'vi' ? 'vi-VN' : 'en-US', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });

  return (
    <div className="fixed inset-0 z-50">
      <div
        aria-hidden="true"
        onClick={onClose}
        className={`absolute inset-0 bg-black/40 transition-opacity duration-200 motion-reduce:transition-none ${
          slidIn ? 'opacity-100' : 'opacity-0'
        }`}
      />

      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="risk-drawer-title"
        className={`absolute inset-y-0 right-0 w-full sm:w-[420px] flex flex-col shadow-2xl transition-transform duration-200 ease-out motion-reduce:transition-none card ${
          slidIn ? 'translate-x-0' : 'translate-x-full'
        }`}
        style={{ borderRadius: 0 }}
      >
        {/* HEADER */}
        <div className="px-5 py-4 border-b flex items-start justify-between gap-3 shrink-0" style={{ borderColor: 'var(--border-ui)' }}>
          <div className="min-w-0">
            <h2 id="risk-drawer-title" className="text-base font-black text-fg">
              {t('instructor.drawerTitle')}
            </h2>
            {detail && <p className="text-xs font-bold text-fg-muted truncate">{detail.studentAlias}</p>}
          </div>
          <button
            ref={closeBtnRef}
            type="button"
            onClick={onClose}
            aria-label={t('instructor.drawerClose')}
            className="p-1.5 rounded-lg text-fg-muted hover:bg-surface-elevated cursor-pointer shrink-0"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* BODY */}
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-5" tabIndex={0}>
          {isLoading && (
            <div className="space-y-3 animate-pulse" aria-live="polite">
              <p className="text-xs text-fg-muted font-medium">{t('instructor.drawerLoading')}</p>
              <div className="h-16 rounded-xl bg-surface-elevated" />
              <div className="h-24 rounded-xl bg-surface-elevated" />
            </div>
          )}

          {!isLoading && loadError && (
            <div role="alert" className="p-4 rounded-xl bg-danger-soft border border-danger/30 space-y-3 text-center">
              <AlertTriangle className="w-8 h-8 text-danger mx-auto" />
              <p className="text-xs font-black text-danger">{t('instructor.drawerError')}</p>
              <p className="text-[11px] text-danger mono break-words">{loadError}</p>
              <button
                type="button"
                onClick={() => setReloadToken((value) => value + 1)}
                className="btn btn-outline text-xs px-3 py-1.5 rounded-xl inline-flex items-center gap-2 cursor-pointer"
              >
                <RefreshCw className="w-3.5 h-3.5" /> {t('states.retryBtn')}
              </button>
            </div>
          )}

          {!isLoading && !loadError && detail && (
            <>
              <div className="flex flex-wrap items-center gap-2">
                <span className={`badge ${riskLevelBadgeClass(detail.riskLevel)} text-[10px] font-black uppercase`}>
                  {riskLevelLabel(t, detail.riskLevel)}
                </span>
                <span tabIndex={0} title={t('instructor.riskDefinitionTooltip')} aria-label={t('instructor.riskDefinitionTooltip')}
                  className="inline-flex text-fg-muted hover:text-fg cursor-help outline-none focus-visible:ring-2 focus-visible:ring-accent rounded-full">
                  <Info size={13} />
                </span>
                <span className={`badge ${resolved ? 'badge-success' : 'badge-neutral'} text-[10px] font-black uppercase`}>
                  {resolved ? t('instructor.intervenedState') : t('instructor.atRiskStudents')}
                </span>
              </div>

              <Row label={t('instructor.studentLabel')}>
                {detail.studentAlias} <span className="mono text-fg-muted">{detail.studentId}</span>
              </Row>

              {detail.courseId && <Row label={t('instructor.courseLabel')}>{detail.courseId}</Row>}

              <Row label={t('instructor.reasonLabel')}>
                {riskTypeLabel(t, detail.riskType, lang)}
              </Row>

              <Row label={t('instructor.actionLabel')}>{detail.recommendedIntervention}</Row>

              {detail.assignmentTitle && (
                <Row label={t('instructor.assignmentLabel')}>
                  <span className="flex items-center gap-1.5">
                    <FileText className="w-3 h-3 shrink-0" /> {detail.assignmentTitle}
                  </span>
                </Row>
              )}

              <Row label={t('instructor.detectedAtLabel')}>
                <span className="flex items-center gap-1.5 mono">
                  <Clock className="w-3 h-3 shrink-0" /> {formatDetectedAt(detail.generatedAt, lang)}
                </span>
              </Row>

              {!resolved && detail.isOverdue && (
                <p className="text-[11px] font-black uppercase text-danger flex items-center gap-1.5">
                  <AlertTriangle className="w-3 h-3 shrink-0" />
                  {t('instructor.overdueBadge', { days: detail.daysOpen })}
                </p>
              )}

              {detail.instructorNote && (
                <Row label={t('instructor.notesTitle')}>
                  <span className="italic">"{detail.instructorNote}"</span>
                </Row>
              )}

              {/* Lịch sử can thiệp — mục 6.4 (F10) */}
              <div className="space-y-2">
                <p className="text-[10px] font-black uppercase tracking-wider text-fg-muted">
                  {t('instructor.interventionsTitle')}
                </p>
                {history.length === 0 ? (
                  <p className="text-[11px] text-fg-muted">{t('instructor.noInterventionsYet')}</p>
                ) : (
                  <ul className="space-y-2">
                    {history.map((item) => (
                      <li key={item.id} className="p-2.5 rounded-lg bg-surface-elevated text-[11px] space-y-0.5">
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-bold text-fg">
                            {item.decision === 'REJECT' ? t('instructor.dismissedBadge') : t('instructor.intervenedBadge')}
                          </span>
                          <span className="text-fg-muted mono text-[10px]">
                            {dateFormatter.format(new Date(item.createdAt))}
                          </span>
                        </div>
                        <p className="text-fg-muted">{item.instructorName}</p>
                        {item.note && <p className="text-fg-secondary italic">"{item.note}"</p>}
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <p className="text-[11px] text-fg-muted font-medium flex items-start gap-1.5">
                <Lock className="w-3 h-3 shrink-0 mt-0.5" />
                <span>{t('instructor.noNotificationNote')}</span>
              </p>
            </>
          )}
        </div>

        {/* FOOTER */}
        {!isLoading && !loadError && detail && (
          <div className="px-5 py-4 border-t shrink-0 space-y-2" style={{ borderColor: 'var(--border-ui)' }}>
            {decisionError && (
              <div role="alert" className="p-2.5 bg-danger-soft border border-danger/30 rounded-xl">
                <span className="text-[11px] font-bold text-danger break-words">{decisionError}</span>
              </div>
            )}
            {resolved ? (
              <div className="px-3 py-2 rounded-xl text-xs font-black flex items-center justify-center gap-1.5 badge-success">
                {effectiveDecision === 'REJECT' ? <ShieldOff className="w-3.5 h-3.5" /> : <CheckCircle className="w-3.5 h-3.5" />}
                {effectiveDecision === 'REJECT' ? t('instructor.dismissedBadge') : t('instructor.intervenedState')}
              </div>
            ) : (
              <>
                <textarea
                  className="input text-xs w-full min-h-[52px]"
                  placeholder={t('instructor.notePlaceholder')}
                  value={noteDraft}
                  onChange={(event) => setNoteDraft(event.target.value)}
                  disabled={anyDecisionPending}
                />
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => onDecision(detail.id, 'APPROVE', noteDraft || undefined)}
                    disabled={anyDecisionPending}
                    className="btn btn-accent flex-1 py-2 rounded-xl text-xs font-black cursor-pointer disabled:opacity-60 disabled:cursor-wait"
                  >
                    {busyDecision === 'APPROVE' ? t('instructor.sendingState') : t('instructor.interveneBtn')}
                  </button>
                  <button
                    type="button"
                    onClick={() => onDecision(detail.id, 'REJECT', noteDraft || undefined)}
                    disabled={anyDecisionPending}
                    className="btn btn-outline flex-1 py-2 rounded-xl text-xs font-black cursor-pointer disabled:opacity-60 disabled:cursor-wait"
                  >
                    {busyDecision === 'REJECT' ? t('instructor.sendingState') : t('instructor.dismissBtn')}
                  </button>
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
