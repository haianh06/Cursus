import React, { useEffect, useRef, useState } from 'react';
import {
  X, AlertTriangle, Check, ShieldOff, FileText, Clock, Lock, RefreshCw, Info, History,
  CalendarPlus
} from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';
import { getInterventionHistory, getRiskDetail } from '../lib/api';
import { riskLevelLabel, riskTypeLabel, isHighRisk, formatDetectedAt } from '../lib/riskLabels';
import { buildMeetingCalendarUrl } from '../lib/calendarLink';

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

function Row({ label, children }) {
  return (
    <div className="space-y-1">
      <p className="text-[10px] font-black uppercase tracking-wider text-slate-500 dark:text-slate-400">
        {label}
      </p>
      <div className="text-xs text-[#15181C] dark:text-slate-100 font-medium">{children}</div>
    </div>
  );
}

/**
 * Risk Case Detail — bảng trượt từ phải, 400px trên desktop, full width trên mobile.
 *
 * Nguồn dữ liệu: GET /instructor/risks/{id} (đã có require_instructor_risk_owner
 * ở backend nên GV không đọc được case của lớp mình không dạy).
 *
 * Riêng tư: endpoint này KHÔNG trả nội dung hỏi đáp của sinh viên, nên bảng
 * này không có gì để lộ. Nếu sau này backend thêm bằng chứng dạng hội thoại,
 * phải kiểm tra lại ràng buộc "chỉ hiện đúng SV đang xem" trước khi render.
 *
 * @param riskId        Case đang mở. Đổi giá trị này là dữ liệu cũ bị xoá ngay.
 * @param open          Có hiển thị hay không.
 * @param onClose       Đóng bảng.
 * @param decision            Quyết định đã bấm trong phiên ('APPROVE' | 'REJECT' | undefined).
 * @param onDecision          (riskId, decision) => void — do component cha xử lý
 *                            để danh sách và bảng chi tiết không lệch trạng thái.
 * @param anyDecisionPending  Có quyết định nào đang bay (khoá mọi nút).
 * @param busyDecision        Quyết định đang bay CỦA case này, để nhãn "Đang gửi…"
 *                            bám đúng nút vừa bấm.
 * @param decisionError       Lỗi gửi quyết định của case này. Bắt buộc hiện Ở ĐÂY:
 *                            bảng này phủ kín màn hình và có aria-modal, nên lỗi
 *                            báo ở dưới nền thì giảng viên không thấy được.
 */
export default function RiskCaseDrawer({
  riskId,
  open,
  onClose,
  decision,
  onDecision,
  anyDecisionPending = false,
  busyDecision = null,
  decisionError = null,
}) {
  const { t, lang } = useLanguage();

  const [detail, setDetail] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [loadError, setLoadError] = useState(null);
  const [reloadToken, setReloadToken] = useState(0);
  /** Ô ghi chú can thiệp GV tự nhập — nạp lại từ detail.instructor_note mỗi
   *  khi case đổi, để không lẫn nháp của case trước sang case sau. */
  const [note, setNote] = useState('');
  /** F10 — mọi lần GV từng bấm quyết định ở case này, mới nhất trước. Nạp
   *  song song với detail; rỗng là bình thường (case chưa từng bị đụng). */
  const [history, setHistory] = useState([]);
  /** Nạp lịch sử can thiệp từ 2 chỗ độc lập (mở bảng, và ngay sau khi bấm
   *  quyết định) — 2 request có thể về không đúng thứ tự gửi đi. Đếm số thứ
   *  tự để CHỈ áp kết quả của request mới nhất, tránh request cũ về muộn ghi
   *  đè lên dòng vừa bấm (đã từng xảy ra: request mở bảng lúc case còn rỗng
   *  về sau request-sau-quyết-định, xoá mất dòng vừa ghi). */
  const historyRequestIdRef = useRef(0);

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
   * response về muộn — nếu không, mở nhanh hai SV liên tiếp có thể khiến dữ
   * liệu của SV trước loé lên trong bảng của SV sau (lộ chéo).
   */
  useEffect(() => {
    // Chỉ xoá nội dung khi bảng đã rời hẳn DOM. Trước đây effect này bám vào
    // `open` nên lúc bắt đầu đóng, nội dung bị xoá ngay trong khi panel còn
    // trượt ra suốt SLIDE_MS — người dùng thấy bảng tự rỗng ruột rồi mới biến mất.
    if (!shouldRender) {
      setDetail(null);
      setLoadError(null);
      setIsLoading(false);
      setNote('');
      setHistory([]);
      return undefined;
    }

    if (!open || !riskId) {
      setIsLoading(false);
      return undefined;
    }

    // Đổi case: xoá dữ liệu case cũ TRƯỚC khi gọi, không để lẫn sang case mới.
    setDetail(null);
    setLoadError(null);
    setNote('');
    setHistory([]);

    let cancelled = false;
    setIsLoading(true);
    const historyRequestId = ++historyRequestIdRef.current;

    Promise.all([getRiskDetail(riskId), getInterventionHistory(riskId).catch(() => [])])
      .then(([data, historyData]) => {
        if (!cancelled) {
          setDetail(data);
          setNote(data.instructor_note || '');
          // Chỉ áp nếu chưa có request lịch sử nào mới hơn được gửi đi
          // trong lúc chờ (vd. GV đã bấm quyết định trước khi fetch này về).
          if (historyRequestIdRef.current === historyRequestId) setHistory(historyData);
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

  // Vừa gửi xong 1 quyết định (decision đổi từ rỗng sang có giá trị) — nạp
  // lại riêng lịch sử để dòng vừa bấm hiện ngay, không cần đóng/mở lại bảng.
  useEffect(() => {
    if (!decision || !riskId || !open) return;
    const historyRequestId = ++historyRequestIdRef.current;
    getInterventionHistory(riskId)
      .then((data) => {
        if (historyRequestIdRef.current === historyRequestId) setHistory(data);
      })
      .catch(() => {});
  }, [decision, riskId, open]);

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
    // Bám `shouldRender` chứ không phải `open`: bảng còn nằm trên màn hình
    // suốt SLIDE_MS sau khi bắt đầu đóng, gỡ listener sớm là Tab thoát ra được
    // trong lúc dialog vẫn đang hiển thị.
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
      // Danh sách tính lại mỗi lần Tab, vì nội dung bảng đổi giữa các trạng
      // thái loading/error/success nên tập phần tử focus được cũng đổi theo.
      const focusables = Array.from(panel.querySelectorAll(FOCUSABLE));
      if (focusables.length === 0) return;

      const first = focusables[0];
      const last = focusables[focusables.length - 1];

      // Nếu focus đang ở ngoài bảng (thường là <body> ngay sau khi mở, hoặc sau
      // khi phần tử đang focus bị unmount lúc đổi trạng thái) thì so sánh với
      // first/last đều sai, bẫy focus thành vô hiệu và Tab thoát ra nền phía
      // sau — trong khi aria-modal đang nói với screen reader là nền bị chặn.
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

  const resolved = detail ? detail.status === 'reviewed' || Boolean(decision) : Boolean(decision);
  const levelLabel = detail ? riskLevelLabel(t, detail.risk_level) : null;
  const typeLabel = detail ? riskTypeLabel(t, detail.risk_type) : null;
  const high = detail ? isHighRisk(detail.risk_level) : false;
  const detectedAt = detail ? formatDetectedAt(detail.generated_at, lang) : null;

  return (
    <div className="fixed inset-0 z-50">
      {/* Nền mờ — bấm ra ngoài để đóng. aria-hidden vì đã có nút Đóng thật. */}
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
        className={`absolute inset-y-0 right-0 w-full sm:w-[400px] flex flex-col shadow-2xl transition-transform duration-200 ease-out motion-reduce:transition-none ${
          slidIn ? 'translate-x-0' : 'translate-x-full'
        }`}
        style={{ backgroundColor: 'var(--bg-card)', color: 'var(--text-primary)' }}
      >
        {/* HEADER */}
        <div className="px-5 py-4 border-b flex items-start justify-between gap-3 shrink-0"
          style={{ borderColor: 'var(--border-ui)' }}
        >
          <div className="min-w-0">
            <h2
              id="risk-drawer-title"
              className="text-base font-black font-serif-heading text-[#15181C] dark:text-white"
            >
              {t('instructor.drawerTitle')}
            </h2>
            {detail && (
              <p className="text-xs font-bold text-slate-600 dark:text-slate-400 truncate">
                {detail.display_name}
              </p>
            )}
          </div>
          <button
            ref={closeBtnRef}
            type="button"
            onClick={onClose}
            aria-label={t('instructor.drawerClose')}
            className="p-1.5 rounded-lg text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 cursor-pointer shrink-0"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* BODY — 4 trạng thái riêng của bảng, không dùng chung với dashboard */}
        {/* tabIndex=0: đây là vùng cuộn, ở trạng thái success nó không chứa
            phần tử focus được nào nên người dùng bàn phím sẽ không cuộn nổi
            xuống phần bị cắt nếu vùng này không tự nhận được focus. */}
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-5" tabIndex={0}>
          {isLoading && (
            <div className="space-y-3 animate-pulse" aria-live="polite">
              <p className="text-xs text-slate-500 dark:text-slate-400 font-medium">{t('instructor.drawerLoading')}</p>
              <div className="h-16 rounded-xl bg-slate-100 dark:bg-slate-800" />
              <div className="h-24 rounded-xl bg-slate-100 dark:bg-slate-800" />
              <div className="h-24 rounded-xl bg-slate-100 dark:bg-slate-800" />
            </div>
          )}

          {/* role=alert: khối loading mang aria-live biến mất đúng lúc khối này
              xuất hiện, nên nếu không tự khai báo thì lỗi tải sẽ không được
              đọc lên cho người dùng screen reader. */}
          {!isLoading && loadError && (
            <div role="alert" className="p-4 rounded-xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800/60 space-y-3 text-center">
              <AlertTriangle className="w-8 h-8 text-red-600 dark:text-red-400 mx-auto" />
              <p className="text-xs font-black text-red-900 dark:text-red-200">
                {t('instructor.drawerError')}
              </p>
              <p className="text-[11px] text-red-700 dark:text-red-400/90 font-mono-code break-words">
                {loadError}
              </p>
              <button
                type="button"
                onClick={() => setReloadToken((value) => value + 1)}
                className="px-3 py-1.5 bg-danger-ink hover:bg-[#7F2F2A] text-white text-xs font-bold rounded-xl inline-flex items-center gap-2 cursor-pointer"
              >
                <RefreshCw className="w-3.5 h-3.5" /> {t('states.retryBtn')}
              </button>
            </div>
          )}

          {!isLoading && !loadError && detail && (
            <>
              <div className="flex flex-wrap items-center gap-2">
                {levelLabel && (
                  <span
                    className={`px-2 py-0.5 rounded-md text-[10px] font-black font-mono-code uppercase ${
                      high
                        ? 'bg-danger-ink text-white'
                        : 'bg-brand-soft text-brand dark:bg-amber-950/60 dark:text-amber-300'
                    }`}
                  >
                    {levelLabel}
                  </span>
                )}
                {typeLabel && (
                  <span className="text-[11px] font-bold text-slate-700 dark:text-slate-300">
                    {typeLabel}
                  </span>
                )}
                <span
                  className={`px-2 py-0.5 rounded-md text-[10px] font-black font-mono-code uppercase ${
                    resolved
                      ? 'bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300'
                      : 'bg-brand text-white'
                  }`}
                >
                  {resolved ? t('instructor.resolvedBadge') : t('instructor.statusPending')}
                </span>
              </div>

              <Row label={t('instructor.studentLabel')}>{detail.display_name}</Row>

              {detail.course_id && (
                <Row label={t('instructor.courseLabel')}>
                  <span className="font-mono-code">{detail.course_id}</span>
                </Row>
              )}

              <Row label={t('instructor.reasonLabel')}>
                <span className="font-extrabold">{detail.reason}</span>
              </Row>

              <Row label={t('instructor.actionLabel')}>
                <div className="flex flex-wrap items-center gap-2">
                  <span>{detail.suggested_action}</span>
                  {/* F11 — mo san su kien Google Calendar that (khong OAuth),
                      GV tu xem lai va bam Luu tren trang Google. He thong
                      khong tu gui loi moi, giu dung tinh than HITL. */}
                  <a
                    href={buildMeetingCalendarUrl({ studentName: detail.display_name, note })}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 px-2 py-0.5 rounded-lg text-[11px] font-black text-brand hover:text-brand-hover border border-brand/30 hover:border-brand/60 transition-colors"
                  >
                    <CalendarPlus className="w-3 h-3" />
                    {t('instructor.scheduleMeetingBtn')}
                  </a>
                </div>
              </Row>

              {detail.assignment_title && (
                <Row label={t('instructor.assignmentLabel')}>
                  <span className="flex items-center gap-1.5">
                    <FileText className="w-3 h-3 shrink-0" />
                    {detail.assignment_title}
                  </span>
                </Row>
              )}

              {detectedAt && (
                <Row label={t('instructor.detectedAt')}>
                  <span className="flex items-center gap-1.5 font-mono-code">
                    <Clock className="w-3 h-3 shrink-0" />
                    {detectedAt}
                  </span>
                </Row>
              )}

              {/* F10 — dòng thời gian can thiệp: TẤT CẢ các lần GV từng bấm
                  quyết định ở case này, không chỉ ghi chú mới nhất. Chỉ hiện
                  khi có ít nhất 1 dòng — case chưa từng bị đụng thì im lặng,
                  không hiện khối rỗng. */}
              {history.length > 0 && (
                <div className="space-y-1.5">
                  <p className="text-[10px] font-black uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
                    <History className="w-3 h-3" />
                    {t('instructor.interventionHistoryTitle')}
                  </p>
                  <div className="space-y-2">
                    {history.map((entry) => (
                      <div
                        key={entry.id}
                        className="p-2.5 rounded-xl bg-[#FAF8F3] dark:bg-[#15181C] border border-[#E6E2D8] dark:border-[#3A352C] space-y-0.5"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-[10px] font-black uppercase font-mono-code text-brand">
                            {t(`instructor.decisionLabel.${entry.decision}`)}
                          </span>
                          <span className="text-[10px] text-slate-500 dark:text-slate-400 font-mono-code shrink-0">
                            {formatDetectedAt(entry.created_at, lang)}
                          </span>
                        </div>
                        <p className="text-[11px] text-slate-700 dark:text-slate-300 font-medium">{entry.note}</p>
                        <p className="text-[10px] text-slate-500 dark:text-slate-400">{entry.instructor_name}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Lịch sử hoàn thành: spec yêu cầu, backend chưa trả field nào.
                  Để sẵn khối có nhãn rõ thay vì bịa dữ liệu — khi Người A bổ
                  sung field thì chỉ việc thay nội dung khối này. */}
              <div className="space-y-1">
                <p className="text-[10px] font-black uppercase tracking-wider text-slate-500 dark:text-slate-400">
                  {t('instructor.historyTitle')}
                </p>
                <div className="p-3 rounded-xl bg-amber-50 dark:bg-amber-950/40 border border-amber-300 dark:border-amber-700/60 flex items-start gap-2">
                  <Info className="w-3.5 h-3.5 text-amber-700 dark:text-amber-400 shrink-0 mt-px" />
                  <span className="text-[11px] font-bold text-amber-900 dark:text-amber-200">
                    {t('instructor.historyUnavailable')}
                  </span>
                </div>
              </div>

              <p className="text-[11px] text-slate-600 dark:text-slate-400 font-medium flex items-start gap-1.5">
                <Lock className="w-3 h-3 shrink-0 mt-0.5" />
                <span>{t('instructor.drawerPrivacyNote')}</span>
              </p>
            </>
          )}
        </div>

        {/* FOOTER — quyết định HITL, cùng hai lựa chọn như ngoài danh sách */}
        {!isLoading && !loadError && detail && (
          <div className="px-5 py-4 border-t shrink-0 space-y-2" style={{ borderColor: 'var(--border-ui)' }}>
            {/* Lỗi gửi quyết định phải hiện Ở ĐÂY. Bảng này là fixed inset-0
                z-50 + aria-modal, nên banner lỗi ở dưới nền vừa bị lớp phủ che
                vừa bị screen reader coi là vùng chết. */}
            {decisionError && (
              <div role="alert" className="p-2.5 bg-red-50 dark:bg-red-950/40 border border-red-300 dark:border-red-800/60 rounded-xl flex items-start gap-2">
                <AlertTriangle className="w-3.5 h-3.5 text-red-600 dark:text-red-400 shrink-0 mt-px" />
                <span className="text-[11px] font-bold text-red-900 dark:text-red-200 break-words">
                  {decisionError}
                </span>
              </div>
            )}

            {resolved ? (
              <div
                className={`px-3 py-2 rounded-xl text-xs font-black flex items-center justify-center gap-1.5 ${
                  decision === 'APPROVE'
                    ? 'bg-emerald-100 dark:bg-emerald-950/60 border border-emerald-300 text-emerald-900 dark:text-[#A7D4B0]'
                    : 'bg-slate-200 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-slate-800 dark:text-slate-200'
                }`}
              >
                {decision === 'REJECT' ? <ShieldOff className="w-3.5 h-3.5" /> : <Check className="w-3.5 h-3.5" />}
                <span>
                  {decision === 'APPROVE' && t('instructor.intervenedBadge')}
                  {decision === 'REJECT' && t('instructor.dismissedBadge')}
                  {!decision && t('instructor.resolvedBadge')}
                </span>
              </div>
            ) : (
              <div className="space-y-2">
                <div className="space-y-1">
                  <label htmlFor="risk-note" className="text-[10px] font-black uppercase tracking-wider text-slate-500 dark:text-slate-400">
                    {t('instructor.noteLabel')}
                  </label>
                  <textarea
                    id="risk-note"
                    value={note}
                    onChange={(event) => setNote(event.target.value)}
                    disabled={anyDecisionPending}
                    rows={2}
                    placeholder={t('instructor.notePlaceholder')}
                    className="w-full rounded-xl border px-3 py-2 text-xs font-medium resize-none disabled:opacity-60"
                    style={{ borderColor: 'var(--border-ui)', backgroundColor: 'var(--bg-card)', color: 'var(--text-primary)' }}
                  />
                </div>
                <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => onDecision(detail.risk_id, 'APPROVE', note)}
                  disabled={anyDecisionPending}
                  className="flex-1 py-2 rounded-xl text-xs font-black bg-brand hover:bg-brand-hover text-white shadow-xs transition-all cursor-pointer disabled:opacity-60 disabled:cursor-wait"
                >
                  {busyDecision === 'APPROVE' ? t('instructor.sending') : t('instructor.interveneBtn')}
                </button>
                <button
                  type="button"
                  onClick={() => onDecision(detail.risk_id, 'REJECT', note)}
                  disabled={anyDecisionPending}
                  className="flex-1 py-2 rounded-xl text-xs font-black border border-[#D6D1C2] dark:border-[#3A352C] text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-all cursor-pointer disabled:opacity-60 disabled:cursor-wait"
                >
                  {busyDecision === 'REJECT' ? t('instructor.sending') : t('instructor.dismissBtn')}
                </button>
                </div>
              </div>
            )}
            <p className="text-[10px] text-slate-500 dark:text-slate-400 font-medium text-center">
              {t('instructor.noNotificationNote')}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
