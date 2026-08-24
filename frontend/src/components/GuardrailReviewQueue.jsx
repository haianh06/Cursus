import React, { useEffect, useState } from 'react';
import {
  ShieldAlert, ShieldCheck, ShieldOff, AlertTriangle, RefreshCw, Clock, Lock,
  Eye, EyeOff
} from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';
import { getGuardrailReviewQueue, resolveGuardrailReview } from '../lib/api';
import { formatDetectedAt } from '../lib/riskLabels';

/** Lý do chặn đã biết từ src/services/guardrail_service.py. */
const KNOWN_BLOCK_REASONS = ['academic_integrity'];

function blockReasonLabel(t, reason) {
  if (!reason) return null;
  return KNOWN_BLOCK_REASONS.includes(reason)
    ? t(`guardrail.reason_${reason}`)
    : reason;
}

/**
 * Hàng đợi xem xét Guardrail — TRANG RIÊNG (docs/08 mục 4.4 Khối 3).
 *
 * Vì sao tách khỏi Instructor Home: khối này bắt buộc hiển thị nguyên văn câu
 * hỏi của sinh viên để giảng viên có bằng chứng mà quyết định. Đặt nó trên
 * dashboard tổng quan là để lộ nội dung riêng của SV ngay màn đầu tiên. Tách
 * ra trang riêng thì dashboard sạch, còn nội dung nhạy cảm chỉ xuất hiện khi
 * giảng viên chủ động mở đúng trang này.
 */
export default function GuardrailReviewQueue() {
  const { t, lang } = useLanguage();

  const [reviews, setReviews] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  /** Quyết định đang gửi: { caseId, decision } — giữ cả decision để nhãn
   *  "Đang gửi…" bám đúng nút vừa bấm. */
  const [pendingAction, setPendingAction] = useState(null);
  /** { [caseId]: 'KEEP' | 'UNBLOCK' } — quyết định đã bấm trong phiên. */
  const [decisions, setDecisions] = useState({});
  /** Các case bấm nhưng server KHÔNG nhận: { [caseId]: message }. */
  const [unsaved, setUnsaved] = useState({});
  /** Case đang mở nội dung hỏi đáp — mỗi lúc chỉ một, xem giải thích ở render. */
  const [expandedId, setExpandedId] = useState(null);

  const load = async () => {
    setIsLoading(true);
    setLoadError(null);
    try {
      const data = await getGuardrailReviewQueue();
      setReviews(data);
    } catch (err) {
      setLoadError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  /**
   * Gửi quyết định.
   *
   * Thất bại thì KHÔNG ghi vào `decisions`. Trước đây vẫn ghi để luồng demo
   * chạy mượt, nhưng làm vậy nút biến mất (hết đường thử lại) và bộ đếm "chờ
   * xem xét" giảm đi, tức là màn hình báo ít việc tồn đọng hơn thực tế trên
   * máy chủ. Giữ nguyên nút + báo lỗi rõ mới là trung thực.
   */
  const decide = async (caseId, decision) => {
    if (!caseId || pendingAction) return;
    setUnsaved(prev => {
      const next = { ...prev };
      delete next[caseId];
      return next;
    });
    setPendingAction({ caseId, decision });
    try {
      await resolveGuardrailReview(caseId, decision);
      setDecisions(prev => ({ ...prev, [caseId]: decision }));
    } catch (err) {
      setUnsaved(prev => ({ ...prev, [caseId]: err.message }));
    } finally {
      setPendingAction(null);
    }
  };

  /**
   * Trạng thái phía máy chủ. Thiếu trường thì coi là CHƯA xử lý — hướng an
   * toàn. Trước đây viết `!== 'PENDING'` nên response thiếu trường sẽ biến mọi
   * case chưa ai đụng thành "đã giữ chặn" và giấu luôn hai nút quyết định.
   */
  const serverResolved = item =>
    item.reviewStatus === 'KEPT_BLOCKED' || item.reviewStatus === 'UNBLOCKED';

  const pendingCount = reviews.filter(
    item => !decisions[item.id] && !serverResolved(item)
  ).length;

  const anyDecisionPending = Boolean(pendingAction);

  if (isLoading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-28 bg-[#15181C] dark:bg-[#1C1A16] rounded-2xl border border-slate-700 dark:border-[#3A352C]" />
        <div className="h-64 bg-white dark:bg-[#1C1A16] rounded-2xl border border-slate-200 dark:border-[#3A352C]" />
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="p-12 text-center space-y-4 max-w-lg mx-auto bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800/60 rounded-2xl my-8 shadow-xl">
        <AlertTriangle className="w-12 h-12 text-red-600 dark:text-red-400 mx-auto" />
        <h3 className="text-lg font-black text-red-900 dark:text-red-200 font-serif-heading">
          {t('states.errorTitle')}
        </h3>
        <p className="text-xs text-red-800 dark:text-red-300/90 font-medium">{t('states.errorDesc')}</p>
        <p className="text-[11px] text-red-700 dark:text-red-400/90 font-mono-code break-words">{loadError}</p>
        <button
          type="button"
          onClick={load}
          className="px-4 py-2 bg-danger-ink hover:bg-[#7F2F2A] text-white text-xs font-bold rounded-xl inline-flex items-center gap-2 cursor-pointer shadow-md"
        >
          <RefreshCw className="w-4 h-4" /> {t('states.retryBtn')}
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-12">

      <div className="bg-surface-elevated border border-line rounded-lg p-6 flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="space-y-1 min-w-0">
          <div className="inline-flex items-center gap-2 px-3 py-1 bg-surface border border-line rounded-full text-xs font-extrabold text-accent font-mono-code">
            <ShieldAlert className="w-3.5 h-3.5 text-accent" />
            <span>{t('guardrail.pending', { count: pendingCount })}</span>
          </div>
          <h1 className="text-2xl font-black text-fg font-serif-heading">{t('guardrail.pageTitle')}</h1>
          <p className="text-xs text-fg-muted font-medium">{t('guardrail.pageSubtitle')}</p>
        </div>

        <div className="p-3 bg-surface border border-line rounded-2xl flex items-start gap-2 text-xs text-fg-muted max-w-xs font-medium">
          <Lock className="w-4 h-4 text-[#A7D4B0] shrink-0 mt-px" />
          <span>{t('guardrail.privacyNote')}</span>
        </div>
      </div>

      <div className="cursus-card rounded-3xl p-6 shadow-sm space-y-4">
        <div className="flex items-center justify-between border-b border-[#E6E2D8] dark:border-[#3A352C] pb-3">
          <h2 className="text-base font-black text-[#15181C] dark:text-white flex items-center gap-2 font-serif-heading">
            <ShieldAlert className="w-5 h-5 text-danger-ink dark:text-red-400" />
            <span>{t('guardrail.queueTitle')}</span>
          </h2>
          <span className="text-xs text-red-700 dark:text-red-300 font-extrabold font-mono-code">
            {t('guardrail.pending', { count: pendingCount })}
          </span>
        </div>

        {reviews.length === 0 ? (
          <div className="p-8 text-center bg-[#FAF8F3] dark:bg-[#15181C] border border-dashed border-[#E6E2D8] dark:border-[#3A352C] rounded-2xl space-y-2">
            <ShieldCheck className="w-8 h-8 text-slate-400 dark:text-slate-500 mx-auto" />
            <p className="text-xs text-slate-600 dark:text-slate-400 font-bold">{t('guardrail.empty')}</p>
          </div>
        ) : (
          <div className="space-y-4">
            {reviews.map(item => {
              const decision = decisions[item.id];
              const resolved = Boolean(decision) || serverResolved(item);
              const busyDecision = pendingAction?.caseId === item.id
                ? pendingAction.decision
                : null;
              const notSaved = unsaved[item.id];
              const createdAt = formatDetectedAt(item.createdAt, lang);
              const reasonLabel = blockReasonLabel(t, item.blockReason);
              const isExpanded = expandedId === item.id;
              // Nhãn kết quả: ưu tiên quyết định vừa bấm, không có thì đọc
              // trạng thái máy chủ. Trước đây chỉ nhìn `decision` nên một case
              // server báo UNBLOCKED lại hiện thành "Đã giữ chặn" — ngược hẳn.
              const unblocked = decision === 'UNBLOCK' || item.reviewStatus === 'UNBLOCKED';

              return (
                <div
                  key={item.id}
                  className="p-4 bg-[#FAF8F3] dark:bg-[#15181C] border border-[#E6E2D8] dark:border-[#3A352C] rounded-2xl space-y-3"
                >
                  <div className="flex items-center justify-between gap-3 text-xs">
                    <span className="font-black text-[#15181C] dark:text-white truncate">
                      {item.studentAlias}
                    </span>
                    {createdAt && (
                      <span className="text-slate-500 dark:text-slate-400 font-mono-code text-[10px] flex items-center gap-1 shrink-0">
                        <Clock className="w-3 h-3" />
                        {createdAt}
                      </span>
                    )}
                  </div>

                  {reasonLabel && (
                    <span className="inline-block px-2 py-0.5 rounded-md bg-danger-soft dark:bg-red-950/60 text-danger-ink dark:text-red-300 text-[10px] font-black font-mono-code uppercase">
                      {reasonLabel}
                    </span>
                  )}

                  {/* Nội dung hỏi đáp phải MỞ TỪNG CASE, và mỗi lúc chỉ một.
                      Bày nguyên văn câu hỏi của cả N sinh viên cùng lúc vẫn là
                      phơi nội dung riêng theo lô, dù đã tách khỏi dashboard —
                      ràng buộc là "chỉ đúng sinh viên đang xem". Mở case này
                      thì case đang mở tự đóng lại. */}
                  <button
                    type="button"
                    onClick={() => setExpandedId(isExpanded ? null : item.id)}
                    aria-expanded={isExpanded}
                    className="text-[11px] font-black text-brand hover:text-brand-hover inline-flex items-center gap-1 cursor-pointer"
                  >
                    {isExpanded ? <EyeOff className="w-3 h-3" /> : <Eye className="w-3 h-3" />}
                    {isExpanded ? t('guardrail.hideContent') : t('guardrail.showContent')}
                  </button>

                  {isExpanded && (
                    <>
                      <div className="space-y-1">
                        <p className="text-[10px] font-black uppercase tracking-wider text-slate-500 dark:text-slate-400">
                          {t('guardrail.questionLabel')}
                        </p>
                        <div className="p-3 bg-white dark:bg-[#1C1A16] border border-[#E6E2D8] dark:border-[#3A352C] rounded-xl text-xs text-slate-800 dark:text-slate-200 italic font-medium">
                          “{item.question}”
                        </div>
                      </div>

                      {item.blockedAnswer && (
                        <div className="space-y-1">
                          <p className="text-[10px] font-black uppercase tracking-wider text-slate-500 dark:text-slate-400">
                            {t('guardrail.answerLabel')}
                          </p>
                          <div className="p-3 bg-white dark:bg-[#1C1A16] border-l-4 border-l-danger-ink border border-[#E6E2D8] dark:border-[#3A352C] rounded-xl text-xs text-slate-700 dark:text-slate-300 font-medium">
                            {item.blockedAnswer}
                          </div>
                        </div>
                      )}
                    </>
                  )}

                  {notSaved && (
                    <div role="alert" className="p-2.5 bg-red-50 dark:bg-red-950/40 border border-red-300 dark:border-red-800/60 rounded-xl flex items-start gap-2">
                      <AlertTriangle className="w-3.5 h-3.5 text-red-600 dark:text-red-400 shrink-0 mt-px" />
                      <div className="space-y-0.5">
                        <p className="text-[11px] font-black text-red-900 dark:text-red-200">
                          {t('guardrail.notSavedNotice')}
                        </p>
                        <p className="text-[10px] text-red-700 dark:text-red-400/90 font-mono-code break-words">
                          {notSaved}
                        </p>
                      </div>
                    </div>
                  )}

                  {resolved ? (
                    <div
                      className={`text-xs font-black p-2 rounded-xl text-center font-mono-code flex items-center justify-center gap-1.5 ${
                        unblocked
                          ? 'bg-emerald-100 dark:bg-emerald-950/60 text-emerald-900 dark:text-[#A7D4B0]'
                          : 'bg-slate-200 dark:bg-slate-800 text-slate-800 dark:text-slate-200'
                      }`}
                    >
                      {unblocked
                        ? <ShieldOff className="w-3.5 h-3.5" />
                        : <ShieldCheck className="w-3.5 h-3.5" />}
                      <span>
                        {unblocked ? t('guardrail.unblockedState') : t('guardrail.keptState')}
                      </span>
                    </div>
                  ) : (
                    /* Khoá theo `anyDecisionPending` vì guard trong decide() là
                       toàn cục — khoá riêng case đang gửi sẽ khiến case khác
                       trông bấm được mà cú bấm bị nuốt. */
                    <div className="flex items-center gap-2 pt-1">
                      <button
                        type="button"
                        onClick={() => decide(item.id, 'KEEP')}
                        disabled={anyDecisionPending}
                        className="flex-1 py-2 bg-danger-ink hover:bg-[#7F2F2A] text-white text-xs font-black rounded-xl transition-all shadow-xs cursor-pointer disabled:opacity-60 disabled:cursor-wait"
                      >
                        {busyDecision === 'KEEP'
                          ? t('guardrail.sending')
                          : (notSaved ? t('guardrail.retryBtn') : t('guardrail.keepBtn'))}
                      </button>
                      <button
                        type="button"
                        onClick={() => decide(item.id, 'UNBLOCK')}
                        disabled={anyDecisionPending}
                        className="flex-1 py-2 bg-success-ink hover:bg-[#245530] text-white text-xs font-black rounded-xl transition-all shadow-xs cursor-pointer disabled:opacity-60 disabled:cursor-wait"
                      >
                        {busyDecision === 'UNBLOCK' ? t('guardrail.sending') : t('guardrail.unblockBtn')}
                      </button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
