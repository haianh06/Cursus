import React, { useEffect, useRef, useState } from 'react';
import { X, AlertTriangle, CheckCircle, FileText, Clock, Lock, RefreshCw, MessageSquare, Info } from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import { getAlertDetail } from '../../lib/api';

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

function riskLevelLabel(t, level) {
  const normalized = (level || '').toUpperCase();
  if (normalized === 'HIGH') return t('instructor.riskHigh');
  if (normalized === 'MEDIUM') return t('instructor.riskMedium');
  return t('instructor.riskLow');
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
 * Risk Case Detail — bảng trượt từ phải, đúng mục 6.4: "bấm vào xem chi tiết
 * (biểu đồ tiến độ riêng, lịch sử gần đây)".
 *
 * Nguồn dữ liệu: GET /instructor/risks/{id} (`getAlertDetail`), đã có
 * `require_instructor_risk_owner` ở backend nên GV không đọc được case của
 * lớp mình không dạy (src/security/ownership.py).
 *
 * Riêng tư: endpoint không trả nội dung chat/reflection thô — `sharedNote`
 * chỉ xuất hiện khi chính sinh viên đã bật `shareWithAdvisor`. Nếu sau này
 * backend thêm trường mới, kiểm tra lại nguyên tắc này trước khi render.
 */
export default function RiskCaseDrawer({ riskId, open, onClose, onIntervene }) {
  const { t, lang } = useLanguage();

  const [detail, setDetail] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [loadError, setLoadError] = useState(null);
  const [reloadToken, setReloadToken] = useState(0);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);
  const [justIntervened, setJustIntervened] = useState(false);

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
   * Nạp chi tiết. Xoá sạch dữ liệu case cũ NGAY khi riskId đổi, và bỏ qua
   * response về muộn — nếu không, mở nhanh hai case liên tiếp có thể khiến
   * dữ liệu của case trước loé lên trong bảng của case sau (lộ chéo).
   */
  useEffect(() => {
    if (!shouldRender) {
      setDetail(null);
      setLoadError(null);
      setIsLoading(false);
      setJustIntervened(false);
      setSubmitError(null);
      return undefined;
    }

    if (!open || !riskId) {
      setIsLoading(false);
      return undefined;
    }

    setDetail(null);
    setLoadError(null);
    setJustIntervened(false);
    setSubmitError(null);

    let cancelled = false;
    setIsLoading(true);

    getAlertDetail(riskId)
      .then((data) => {
        if (!cancelled) setDetail(data);
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

  const resolved = detail ? detail.status === 'INTERVENTION_APPROVED' || justIntervened : justIntervened;

  const handleIntervene = () => {
    if (!detail || isSubmitting) return;
    setIsSubmitting(true);
    setSubmitError(null);
    onIntervene(detail.id)
      .then(() => setJustIntervened(true))
      .catch((err) => setSubmitError(err.message))
      .finally(() => setIsSubmitting(false));
  };

  const dateFormatter = new Intl.DateTimeFormat(lang === 'vi' ? 'vi-VN' : 'en-US', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });

  const timeline = Array.isArray(detail?.timeline) ? detail.timeline : [];
  const completedCount = timeline.filter((task) => task.status === 'COMPLETED').length;
  const progressRatio = timeline.length > 0 ? completedCount / timeline.length : null;
  const interventions = Array.isArray(detail?.interventions) ? detail.interventions : [];

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
                {detail.reasons?.[0] || detail.recommendedIntervention}
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
                  <Clock className="w-3 h-3 shrink-0" /> {dateFormatter.format(new Date(detail.generatedAt))}
                </span>
              </Row>

              {/* Biểu đồ tiến độ riêng — mục 6.4 */}
              <div className="space-y-2">
                <p className="text-[10px] font-black uppercase tracking-wider text-fg-muted">
                  {t('instructor.progressTitle')}
                </p>
                {timeline.length === 0 ? (
                  <p className="text-[11px] text-fg-muted">{t('instructor.noProgressData')}</p>
                ) : (
                  <>
                    <div className="h-2 rounded-full bg-surface-elevated overflow-hidden">
                      <div
                        className="h-full rounded-full"
                        style={{
                          width: `${Math.round((progressRatio ?? 0) * 100)}%`,
                          background: (progressRatio ?? 0) < 0.5 ? 'var(--danger)' : (progressRatio ?? 0) < 0.75 ? 'var(--warning)' : 'var(--success)',
                        }}
                      />
                    </div>
                    <p className="text-[10px] text-fg-muted mono">
                      {completedCount}/{timeline.length}
                    </p>
                    <ul className="space-y-1.5 max-h-40 overflow-y-auto">
                      {timeline.slice(-8).reverse().map((task) => (
                        <li key={task.taskId} className="flex items-center justify-between gap-2 text-[11px]">
                          <span className="truncate text-fg-secondary">{task.title}</span>
                          <span
                            className={`shrink-0 font-bold ${
                              task.status === 'COMPLETED' ? 'text-success' : task.overdue ? 'text-danger' : 'text-fg-muted'
                            }`}
                          >
                            {task.status === 'COMPLETED' ? '✓' : task.overdue ? t('instructor.taskOverdueTag') : task.status}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </>
                )}
              </div>

              {/* Lịch sử gần đây (can thiệp) — mục 6.4 */}
              <div className="space-y-2">
                <p className="text-[10px] font-black uppercase tracking-wider text-fg-muted">
                  {t('instructor.interventionsTitle')}
                </p>
                {interventions.length === 0 ? (
                  <p className="text-[11px] text-fg-muted">{t('instructor.noInterventionsYet')}</p>
                ) : (
                  <ul className="space-y-2">
                    {interventions.map((item) => (
                      <li key={item.id} className="p-2.5 rounded-lg bg-surface-elevated text-[11px] space-y-0.5">
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-bold text-fg">{item.actionLabel || item.action}</span>
                          <span className="text-fg-muted mono text-[10px]">
                            {dateFormatter.format(new Date(item.createdAt))}
                          </span>
                        </div>
                        <p className="text-fg-muted">{item.advisorName}</p>
                        {item.note && <p className="text-fg-secondary italic">"{item.note}"</p>}
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              {detail.sharedNote && (
                <div className="p-3 rounded-xl bg-accent-soft border border-accent/20 space-y-1">
                  <p className="text-[10px] font-black uppercase tracking-wider text-accent flex items-center gap-1.5">
                    <MessageSquare className="w-3 h-3" /> {t('instructor.sharedNoteTitle')}
                  </p>
                  <p className="text-[11px] text-fg-secondary italic">"{detail.sharedNote.summary}"</p>
                </div>
              )}

              {detail.privacyNote && (
                <p className="text-[11px] text-fg-muted font-medium flex items-start gap-1.5">
                  <Lock className="w-3 h-3 shrink-0 mt-0.5" />
                  <span>{detail.privacyNote}</span>
                </p>
              )}
            </>
          )}
        </div>

        {/* FOOTER */}
        {!isLoading && !loadError && detail && (
          <div className="px-5 py-4 border-t shrink-0 space-y-2" style={{ borderColor: 'var(--border-ui)' }}>
            {submitError && (
              <div role="alert" className="p-2.5 bg-danger-soft border border-danger/30 rounded-xl">
                <span className="text-[11px] font-bold text-danger break-words">{submitError}</span>
              </div>
            )}
            {resolved ? (
              <div className="px-3 py-2 rounded-xl text-xs font-black flex items-center justify-center gap-1.5 badge-success">
                <CheckCircle className="w-3.5 h-3.5" /> {t('instructor.intervenedState')}
              </div>
            ) : (
              <button
                type="button"
                onClick={handleIntervene}
                disabled={isSubmitting}
                className="btn btn-accent w-full py-2 rounded-xl text-xs font-black cursor-pointer disabled:opacity-60 disabled:cursor-wait"
              >
                {isSubmitting ? t('instructor.sendingState') : t('instructor.interveneBtn')}
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
